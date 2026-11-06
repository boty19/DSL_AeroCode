# AeroCode — Fase 3: analizador léxico y sintáctico

Lee un archivo con código AeroCode y muestra su árbol de derivación o la lista de errores.

## Uso

### Interfaz gráfica

```
python interfaz.py
```

- **Editor** con números de línea y colores según el tipo de token (el resaltado usa el mismo lexer).
- **Insertar instrucción:** un formulario por instrucción (despegar, girar, mover G0/G1, repetir, si/sino…). Cada campo se valida con el lexer y el parser, y el botón *Insertar* solo se activa si el código resultante es válido.
- **Análisis automático** mientras se escribe, o con F5. Pestañas de *Resultado* (doble clic en un error lleva a la línea), *Tokens*, *Árbol de derivación* y *Ayuda del lenguaje*.
- Abrir y guardar archivos `.aero`, y cargar los programas de `pruebas/` desde el menú *Ejemplos*.

### Línea de comandos

```
python main.py pruebas/mision_valida.aero
python main.py pruebas/mision_valida.aero --tokens
python main.py pruebas/mision_valida.aero --dot arbol.dot
python pruebas.py
```

## Archivos y su relación con las fases

| Archivo | Qué hace | Se apoya en |
| --- | --- | --- |
| `lexer.py` | Matriz de transiciones del AFD de 14 estados y tablas de tokens | Fase 1, secciones 4 a 6 |
| `parser.py` | Parser descendente recursivo LL(1): un método por no terminal, comentarios P1 a P39 | Fase 2, secciones 7 a 9 |
| `arbol.py` | Nodos del árbol, impresión en texto y exportación a Graphviz | Fase 2, sección 10 |
| `main.py` | Lee el archivo, ejecuta léxico y sintáctico y muestra el resultado | — |
| `interfaz.py` | Interfaz gráfica (tkinter): editor, formularios de inserción, tokens, errores y árbol | Usa `lexer.py` y `parser.py` sin cambios |
| `pruebas.py` | 11 pruebas automáticas | Trazas de las Fases 1 y 2 |
| `pruebas/*.aero` | Programas válidos y con errores | — |

## Manejo de errores

- **Léxicos:** se reportan todos, con línea y columna. Si hay alguno, no se ejecuta el análisis sintáctico.
- **Sintácticos:** se reporta el token esperado y el encontrado. El parser se recupera en modo pánico (descarta tokens hasta `;`, `}` o el inicio de otra instrucción) y sigue buscando más errores.
- El programa termina con código 0 si el archivo es válido y 1 si tiene errores.
