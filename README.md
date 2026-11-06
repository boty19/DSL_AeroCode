# AeroCode — Diseño, auditoría e ingeniería inversa de un DSL en Python

AeroCode es un lenguaje de dominio específico para programar misiones de un dron con comandos tipo G-Code simplificado: movimientos por ejes, giros, velocidad, ciclos y decisiones según sensores.

```
# Patrulla de bodega
despegar 2.5;
velocidad 3;
lado = 10;

repetir 4 {
    G1 X lado Y0 Z2.5;
    girar 90;
}

si (bateria < 20) {
    aterrizar;
} sino {
    G0 X0 Y(lado * 2 - 5);
    esperar 1.5;
}
```

El proyecto tiene tres fases. Cada una se apoya en la anterior:

| Fase | Qué define | Herramienta formal | Documento |
| --- | --- | --- | --- |
| 1. Formalismo léxico | Qué piezas (tokens) existen | Alfabeto, expresiones regulares, AFD | [Fase 1](https://claude.ai/artifact/GgK6b9sPpmPnYjdsA8ZSga) |
| 2. Estructura sintáctica | En qué orden pueden ir los tokens | Gramática independiente del contexto (BNF), LL(1) | [Fase 2](https://claude.ai/artifact/PrshcRhm6MHyzobVZC6vGY) |
| 3. Implementación | El analizador en Python | Lexer por matriz + parser descendente recursivo | Este código |

---

## Fase 1 — Formalismo léxico

### Alfabeto Σ

Σ = Σ_lex ∪ Σ_txt. Σ_lex son los 60 símbolos que pueden formar tokens; Σ_txt son los demás caracteres, que solo se admiten dentro de comentarios.

| Conjunto | Contenido | Cantidad |
| --- | --- | --- |
| M | a … z | 26 |
| {G} | G (inicio de comando) | 1 |
| E | X, Y, Z (ejes) | 3 |
| D | 0 … 9 | 10 |
| {_} | _ | 1 |
| P | `+ - * / = ! < > ( ) { } ; . #` | 15 |
| B | espacio, \t, \r, \n | 4 |

### Tokens (30 tipos, más comentarios y espacios que se descartan)

| Categoría | Tokens |
| --- | --- |
| Palabras reservadas | DESPEGAR, ATERRIZAR, GIRAR, VELOCIDAD, ESPERAR, REPETIR, SI, SINO, BATERIA, ALTURA |
| Comando y eje | COMANDO (`G0`, `G1`, `G01`…), EJE (`X`, `Y`, `Z`) |
| Identificador y número | ID, NUM |
| Operadores | MAS, MENOS, MULT, DIV, ASIG, IGUAL, DIST, MENOR, MENOR_IG, MAYOR, MAYOR_IG |
| Delimitadores | PAR_A, PAR_C, LLAVE_A, LLAVE_C, PUNTO_COMA |

### Expresiones regulares principales

| Token | Expresión regular |
| --- | --- |
| ID | M (M \| D \| _)* |
| COMANDO | G D+ |
| EJE | X \| Y \| Z |
| NUM | D+ ( . D+ )? |
| COMENTARIO | # [^ \n]* |
| ESPACIO | ( espacio \| \t \| \r \| \n )+ |

Las palabras reservadas se reconocen como ID y luego se buscan en una tabla. Dos reglas resuelven las ambigüedades léxicas: el **lexema más largo** (`G01` es un solo token, `>=` también) y la **prioridad de las palabras reservadas** (`si` es SI, `silla` es ID).

### Autómata finito determinista

El AFD tiene **14 estados** (q0 a q12 más el sumidero qE) y 14 clases de símbolos. Los estados que no aceptan son q0, q2 (`G` sin dígitos), q5 (punto sin decimales), q11 (`!` solo) y qE.

| Estado | Significado | Acepta | Token |
| --- | --- | --- | --- |
| q0 | Inicio | No | — |
| q1 | Identificador | Sí | ID o palabra reservada (tabla) |
| q2 | `G` sola | No | — |
| q3 | Comando completo | Sí | COMANDO |
| q4 | Parte entera | Sí | NUM |
| q5 | Punto decimal | No | — |
| q6 | Parte decimal | Sí | NUM |
| q7 | Comentario | Sí | se descarta |
| q8 | Blancos | Sí | se descarta |
| q9 | Símbolo simple: `X Y Z + - * / ( ) { } ;` | Sí | según el lexema (tabla) |
| q10 | `=` `<` `>` | Sí | ASIG, MENOR, MAYOR |
| q11 | `!` | No | — |
| q12 | `==` `<=` `>=` `!=` | Sí | IGUAL, MENOR_IG, MAYOR_IG, DIST |

El AFD reconoce **un token a la vez**: avanza mientras haya transición y, al cortar, emite el token del estado actual (o reporta un error si el estado no acepta) y vuelve a q0. En [lexer.py](lexer.py), `TRANSICIONES` es esta misma matriz.

---

## Fase 2 — Estructura sintáctica

### Problemas de la gramática inicial G0

La primera versión de la gramática tenía tres defectos que se corrigieron en orden:

| Paso | Problema | Técnica |
| --- | --- | --- |
| 1 | `2 + 3 * 4` tenía dos árboles (14 o 20) | Estratificación por precedencia: `<expr>` (+ -), `<term>` (* /), `<factor>` |
| 2 | Reglas como `<expr> ::= <expr> + <term>` hacen que un parser descendente entre en un ciclo infinito | Eliminación de la recursividad por la izquierda: A → Aα \| β ⇒ A → βA', A' → αA' \| ε |
| 3 | Las dos reglas de `si` empezaban igual | Factorización por la izquierda con `<sino_opt>` |

### Gramática final LL(1)

G = (N, Σ, P, S) con 14 no terminales, los 30 tokens de la Fase 1 como terminales, 39 producciones y S = `<programa>`.

```
 1  <programa>      ::= <instrucciones>
 2  <instrucciones> ::= <instruccion> <instrucciones>
 3                    | ε
 4  <instruccion>   ::= despegar <expr> ;
 5                    | aterrizar ;
 6                    | girar <expr> ;
 7                    | velocidad <expr> ;
 8                    | esperar <expr> ;
 9                    | ID = <expr> ;
10                    | COMANDO <coords> ;
11                    | repetir <expr> <bloque>
12                    | si ( <cond> ) <bloque> <sino_opt>
13  <sino_opt>      ::= sino <bloque>
14                    | ε
15  <coords>        ::= <coord> <coords>
16                    | ε
17  <coord>         ::= EJE <expr>
18  <bloque>        ::= { <instrucciones> }
19  <cond>          ::= <expr> <oprel> <expr>
20-25 <oprel>       ::= == | != | < | <= | > | >=
26  <expr>          ::= <term> <expr'>
27  <expr'>         ::= + <term> <expr'>
28                    | - <term> <expr'>
29                    | ε
30  <term>          ::= <factor> <term'>
31  <term'>         ::= * <factor> <term'>
32                    | / <factor> <term'>
33                    | ε
34  <factor>        ::= - <factor>
35                    | ( <expr> )
36                    | NUM
37                    | ID
38                    | bateria
39                    | altura
```

### Prueba de que no es ambigua

Con los conjuntos PRIMERO y SIGUIENTE se construyó la tabla de análisis LL(1): **102 celdas y ningún conflicto**. La ambigüedad es indecidible en general, pero ser LL(1) es una condición suficiente: cada cadena tiene una sola derivación por la izquierda y, por lo tanto, un solo árbol.

La precedencia queda así: `*` y `/` se aplican antes que `+` y `-`, los operadores asocian a la izquierda (`10 - 4 - 3` = 3) y el menos unario tiene la mayor precedencia. Como los bloques siempre llevan llaves, no existe el problema del "else colgante".

---

## Fase 3 — Implementación en Python

Lee un programa AeroCode y muestra su árbol de derivación o la lista de errores.

### Uso

#### Interfaz gráfica

```
python interfaz.py
```

- **Editor** con números de línea y colores según el tipo de token (el resaltado usa el mismo lexer).
- **Insertar instrucción:** un formulario por instrucción (despegar, girar, mover G0/G1, repetir, si/sino…). Cada campo se valida con el lexer y el parser, y el botón *Insertar* solo se activa si el código resultante es válido.
- **Análisis automático** mientras se escribe, o con F5. Pestañas de *Resultado* (doble clic en un error lleva a la línea), *Tokens*, *Árbol de derivación* y *Ayuda del lenguaje*.
- Abrir y guardar archivos `.aero`, y cargar los programas de `pruebas/` desde el menú *Ejemplos*.

#### Línea de comandos

```
python main.py pruebas/mision_valida.aero
python main.py pruebas/mision_valida.aero --tokens
python main.py pruebas/mision_valida.aero --dot arbol.dot
python pruebas.py
```

### Archivos y su relación con las fases

| Archivo | Qué hace | Se apoya en |
| --- | --- | --- |
| `lexer.py` | Matriz de transiciones del AFD de 14 estados y tablas de tokens | Fase 1 |
| `parser.py` | Parser descendente recursivo LL(1): un método por no terminal, comentarios P1 a P39 | Fase 2, gramática final y tabla LL(1) |
| `arbol.py` | Nodos del árbol, impresión en texto y exportación a Graphviz | Fase 2, árbol de derivación |
| `main.py` | Lee el archivo, ejecuta léxico y sintáctico y muestra el resultado | — |
| `interfaz.py` | Interfaz gráfica (tkinter): editor, formularios de inserción, tokens, errores y árbol | Usa `lexer.py` y `parser.py` sin cambios |
| `pruebas.py` | 11 pruebas automáticas | Trazas de las Fases 1 y 2 |
| `pruebas/*.aero` | Programas válidos y con errores | — |

### Manejo de errores

- **Léxicos:** se reportan todos, con línea y columna. Si hay alguno, no se ejecuta el análisis sintáctico.
- **Sintácticos:** se reporta el token esperado y el encontrado. El parser se recupera en modo pánico (descarta tokens hasta `;`, `}` o el inicio de otra instrucción) y sigue buscando más errores.
- El programa termina con código 0 si el archivo es válido y 1 si tiene errores.
