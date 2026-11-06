"""Analizador sintáctico de AeroCode: descendente recursivo LL(1).

Cada no terminal de la gramática final (Fase 2, sección 7) es un método.
Cada decisión entre producciones se toma mirando un solo token, con los
conjuntos PRIMERO y SIGUIENTE de la Fase 2 (sección 8). Los comentarios
"P<n>" indican el número de la producción que se aplica.
"""

from arbol import Nodo

# Conjuntos de la Fase 2, sección 8.
INS = {"DESPEGAR", "ATERRIZAR", "GIRAR", "VELOCIDAD", "ESPERAR",
       "ID", "COMANDO", "REPETIR", "SI"}
EXP = {"MENOS", "PAR_A", "NUM", "ID", "BATERIA", "ALTURA"}
REL = {"IGUAL", "DIST", "MENOR", "MENOR_IG", "MAYOR", "MAYOR_IG"}

# Lexema que se muestra en los mensajes de error para cada tipo de token.
NOMBRES = {
    "PUNTO_COMA": "';'", "PAR_A": "'('", "PAR_C": "')'", "LLAVE_A": "'{'",
    "LLAVE_C": "'}'", "ASIG": "'='", "EJE": "un eje (X, Y, Z)",
    "NUM": "un número", "ID": "un identificador", "EOF": "el fin del archivo",
}


def nombre(tipo):
    return NOMBRES.get(tipo, f"'{tipo.lower()}'")


class ErrorSintactico(Exception):
    def __init__(self, token, esperado):
        self.token = token
        self.esperado = esperado
        encontrado = "el fin del archivo" if token.tipo == "EOF" else f"'{token.lexema}'"
        super().__init__(
            f"Error sintáctico en {token.linea}:{token.columna}: "
            f"se esperaba {esperado} y se encontró {encontrado}")


class AnalizadorSintactico:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.errores = []

    # --- utilidades -------------------------------------------------------

    @property
    def actual(self):
        return self.tokens[self.pos]

    def coincidir(self, tipo, padre):
        """Consume un token del tipo esperado y lo cuelga del árbol como hoja."""
        if self.actual.tipo != tipo:
            raise ErrorSintactico(self.actual, nombre(tipo))
        hoja = padre.agregar(Nodo(tipo, self.actual))
        self.pos += 1
        return hoja

    def vacio(self, padre):
        padre.agregar(Nodo("ε"))

    def recuperar(self):
        """Modo pánico: descarta tokens hasta un punto seguro para continuar.

        Se detiene después de un ';' o antes de '}', del inicio de una
        instrucción o del fin del archivo.
        """
        while self.actual.tipo not in INS | {"LLAVE_C", "EOF"}:
            tipo = self.actual.tipo
            self.pos += 1
            if tipo == "PUNTO_COMA":
                return

    # --- no terminales ----------------------------------------------------

    def programa(self):
        # P1: <programa> ::= <instrucciones>
        raiz = Nodo("<programa>")
        self.instrucciones(raiz)
        while self.actual.tipo != "EOF":   # sobra un '}' sin su '{'
            self.errores.append(ErrorSintactico(self.actual, "una instrucción"))
            self.pos += 1
            self.instrucciones(raiz)
        return raiz

    def instrucciones(self, padre):
        nodo = padre.agregar(Nodo("<instrucciones>"))
        while True:
            if self.actual.tipo in INS:
                # P2: <instrucciones> ::= <instruccion> <instrucciones>
                self.instruccion(nodo)
                nodo = nodo.agregar(Nodo("<instrucciones>"))
            elif self.actual.tipo in {"EOF", "LLAVE_C"}:
                # P3: <instrucciones> ::= ε     (SIGUIENTE = { $, } })
                self.vacio(nodo)
                return
            else:
                self.errores.append(ErrorSintactico(self.actual, "una instrucción"))
                self.pos += 1
                self.recuperar()

    def instruccion(self, padre):
        nodo = padre.agregar(Nodo("<instruccion>"))
        try:
            t = self.actual.tipo
            if t in {"DESPEGAR", "GIRAR", "VELOCIDAD", "ESPERAR"}:
                # P4, P6, P7, P8: <instruccion> ::= despegar|girar|velocidad|esperar <expr> ;
                self.coincidir(t, nodo)
                self.expr(nodo)
                self.coincidir("PUNTO_COMA", nodo)
            elif t == "ATERRIZAR":
                # P5: <instruccion> ::= aterrizar ;
                self.coincidir("ATERRIZAR", nodo)
                self.coincidir("PUNTO_COMA", nodo)
            elif t == "ID":
                # P9: <instruccion> ::= ID = <expr> ;
                self.coincidir("ID", nodo)
                self.coincidir("ASIG", nodo)
                self.expr(nodo)
                self.coincidir("PUNTO_COMA", nodo)
            elif t == "COMANDO":
                # P10: <instruccion> ::= COMANDO <coords> ;
                self.coincidir("COMANDO", nodo)
                self.coords(nodo)
                self.coincidir("PUNTO_COMA", nodo)
            elif t == "REPETIR":
                # P11: <instruccion> ::= repetir <expr> <bloque>
                self.coincidir("REPETIR", nodo)
                self.expr(nodo)
                self.bloque(nodo)
            elif t == "SI":
                # P12: <instruccion> ::= si ( <cond> ) <bloque> <sino_opt>
                self.coincidir("SI", nodo)
                self.coincidir("PAR_A", nodo)
                self.cond(nodo)
                self.coincidir("PAR_C", nodo)
                self.bloque(nodo)
                self.sino_opt(nodo)
        except ErrorSintactico as e:
            self.errores.append(e)
            self.recuperar()

    def sino_opt(self, padre):
        nodo = padre.agregar(Nodo("<sino_opt>"))
        if self.actual.tipo == "SINO":
            # P13: <sino_opt> ::= sino <bloque>
            self.coincidir("SINO", nodo)
            self.bloque(nodo)
        else:
            # P14: <sino_opt> ::= ε     (SIGUIENTE = INS ∪ { $, } })
            self.vacio(nodo)

    def coords(self, padre):
        nodo = padre.agregar(Nodo("<coords>"))
        while self.actual.tipo == "EJE":
            # P15: <coords> ::= <coord> <coords>
            self.coord(nodo)
            nodo = nodo.agregar(Nodo("<coords>"))
        # P16: <coords> ::= ε     (SIGUIENTE = { ; })
        self.vacio(nodo)

    def coord(self, padre):
        # P17: <coord> ::= EJE <expr>
        nodo = padre.agregar(Nodo("<coord>"))
        self.coincidir("EJE", nodo)
        self.expr(nodo)

    def bloque(self, padre):
        # P18: <bloque> ::= { <instrucciones> }
        nodo = padre.agregar(Nodo("<bloque>"))
        self.coincidir("LLAVE_A", nodo)
        self.instrucciones(nodo)
        self.coincidir("LLAVE_C", nodo)

    def cond(self, padre):
        # P19: <cond> ::= <expr> <oprel> <expr>
        nodo = padre.agregar(Nodo("<cond>"))
        self.expr(nodo)
        self.oprel(nodo)
        self.expr(nodo)

    def oprel(self, padre):
        # P20 a P25: <oprel> ::= == | != | < | <= | > | >=
        nodo = padre.agregar(Nodo("<oprel>"))
        if self.actual.tipo not in REL:
            raise ErrorSintactico(self.actual, "un operador relacional (==, !=, <, <=, >, >=)")
        self.coincidir(self.actual.tipo, nodo)

    def expr(self, padre):
        # P26: <expr> ::= <term> <expr'>
        nodo = padre.agregar(Nodo("<expr>"))
        self.term(nodo)
        self.expr_prima(nodo)

    def expr_prima(self, padre):
        nodo = padre.agregar(Nodo("<expr'>"))
        if self.actual.tipo in {"MAS", "MENOS"}:
            # P27 / P28: <expr'> ::= + <term> <expr'> | - <term> <expr'>
            self.coincidir(self.actual.tipo, nodo)
            self.term(nodo)
            self.expr_prima(nodo)
        else:
            # P29: <expr'> ::= ε
            self.vacio(nodo)

    def term(self, padre):
        # P30: <term> ::= <factor> <term'>
        nodo = padre.agregar(Nodo("<term>"))
        self.factor(nodo)
        self.term_prima(nodo)

    def term_prima(self, padre):
        nodo = padre.agregar(Nodo("<term'>"))
        if self.actual.tipo in {"MULT", "DIV"}:
            # P31 / P32: <term'> ::= * <factor> <term'> | / <factor> <term'>
            self.coincidir(self.actual.tipo, nodo)
            self.factor(nodo)
            self.term_prima(nodo)
        else:
            # P33: <term'> ::= ε
            self.vacio(nodo)

    def factor(self, padre):
        nodo = padre.agregar(Nodo("<factor>"))
        t = self.actual.tipo
        if t == "MENOS":
            # P34: <factor> ::= - <factor>
            self.coincidir("MENOS", nodo)
            self.factor(nodo)
        elif t == "PAR_A":
            # P35: <factor> ::= ( <expr> )
            self.coincidir("PAR_A", nodo)
            self.expr(nodo)
            self.coincidir("PAR_C", nodo)
        elif t in {"NUM", "ID", "BATERIA", "ALTURA"}:
            # P36 a P39: <factor> ::= NUM | ID | bateria | altura
            self.coincidir(t, nodo)
        else:
            raise ErrorSintactico(self.actual, "una expresión (número, variable, sensor, '-' o '(')")


def analizar(tokens):
    """Devuelve (árbol, errores)."""
    parser = AnalizadorSintactico(tokens)
    arbol = parser.programa()
    return arbol, parser.errores
