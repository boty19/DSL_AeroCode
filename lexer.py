"""Analizador léxico de AeroCode.

Implementa el AFD de 14 estados de la Fase 1 (q0..q12 + qE) como una
matriz de transiciones. No usa expresiones regulares de Python: cada
carácter se clasifica en una de las 14 clases de símbolos y la matriz
decide el siguiente estado.
"""

from dataclasses import dataclass


@dataclass
class Token:
    tipo: str
    lexema: str
    linea: int
    columna: int

    def __str__(self):
        return f"{self.tipo}('{self.lexema}') en {self.linea}:{self.columna}"


@dataclass
class ErrorLexico:
    mensaje: str
    lexema: str
    linea: int
    columna: int

    def __str__(self):
        return f"Error léxico en {self.linea}:{self.columna}: {self.mensaje} '{self.lexema}'"


# --- Clases de símbolos (columnas de la matriz, Fase 1 sección 6) ----------

def clase_de(c):
    if "a" <= c <= "z":
        return "m"          # minúscula
    if c == "G":
        return "G"          # inicio de comando
    if c in "XYZ":
        return "E"          # eje
    if "0" <= c <= "9":
        return "D"          # dígito
    if c in " \t\r":
        return "B"          # blanco
    if c == "\n":
        return "\\n"        # salto de línea
    if c in "+-*/(){};":
        return "S"          # símbolo simple
    if c in "<>":
        return "R"          # relacional
    if c in "_.#=!":
        return c            # cada uno es su propia clase
    return "O"              # otro símbolo (Σ_txt)


# --- Matriz de transiciones δ (estado, clase) -> estado ---------------------
# Una pareja que no aparece aquí va al sumidero qE.

TODAS_MENOS_SALTO = ["m", "G", "E", "D", "_", ".", "#", "B", "S", "=", "R", "!", "O"]

TRANSICIONES = {
    0: {"m": 1, "G": 2, "E": 9, "D": 4, "#": 7, "B": 8, "\\n": 8,
        "S": 9, "=": 10, "R": 10, "!": 11},
    1: {"m": 1, "D": 1, "_": 1},            # identificador
    2: {"D": 3},                            # G sola: falta un dígito
    3: {"D": 3},                            # comando G D+
    4: {"D": 4, ".": 5},                    # parte entera
    5: {"D": 6},                            # punto: falta un decimal
    6: {"D": 6},                            # parte decimal
    7: {c: 7 for c in TODAS_MENOS_SALTO},   # comentario hasta fin de línea
    8: {"B": 8, "\\n": 8},                  # blancos
    9: {},                                  # símbolo simple: sin salida
    10: {"=": 12},                          # = < >  (puede seguir =)
    11: {"=": 12},                          # ! (necesita =)
    12: {},                                 # operador doble: sin salida
}

# Estados de aceptación y el tipo de token que producen.
# "TABLA" significa que el token se decide mirando el lexema.
ACEPTACION = {
    1: "TABLA_RESERVADAS",
    3: "COMANDO",
    4: "NUM",
    6: "NUM",
    7: "COMENTARIO",
    8: "ESPACIO",
    9: "TABLA_SIMBOLOS",
    10: "TABLA_SIMBOLOS",
    12: "TABLA_SIMBOLOS",
}

# Mensajes para los estados que no aceptan (Fase 1, tabla de errores).
ERRORES_ESTADO = {
    2: "comando incompleto (falta el número después de G)",
    5: "número mal formado (falta un dígito después del punto)",
    11: "operador incompleto (después de ! debe ir =)",
}

PALABRAS_RESERVADAS = {
    "despegar": "DESPEGAR", "aterrizar": "ATERRIZAR", "girar": "GIRAR",
    "velocidad": "VELOCIDAD", "esperar": "ESPERAR", "repetir": "REPETIR",
    "si": "SI", "sino": "SINO", "bateria": "BATERIA", "altura": "ALTURA",
}

# Tabla de tokens de los estados compartidos q9, q10 y q12.
SIMBOLOS = {
    "X": "EJE", "Y": "EJE", "Z": "EJE",
    "+": "MAS", "-": "MENOS", "*": "MULT", "/": "DIV",
    "(": "PAR_A", ")": "PAR_C", "{": "LLAVE_A", "}": "LLAVE_C", ";": "PUNTO_COMA",
    "=": "ASIG", "<": "MENOR", ">": "MAYOR",
    "==": "IGUAL", "<=": "MENOR_IG", ">=": "MAYOR_IG", "!=": "DIST",
}

DESCARTADOS = {"COMENTARIO", "ESPACIO"}


def tipo_de_token(estado, lexema):
    tipo = ACEPTACION[estado]
    if tipo == "TABLA_RESERVADAS":
        return PALABRAS_RESERVADAS.get(lexema, "ID")
    if tipo == "TABLA_SIMBOLOS":
        return SIMBOLOS[lexema]
    return tipo


def analizar(texto):
    """Divide el texto en tokens. Devuelve (tokens, errores).

    Sigue el algoritmo de la Fase 1: desde q0 se avanza mientras exista
    transición (lexema más largo); al cortar, si el estado acepta se emite
    el token, si no se reporta un error, y se vuelve a q0 sin consumir el
    símbolo que provocó el corte.
    """
    tokens, errores = [], []
    i, linea, columna = 0, 1, 1

    while i < len(texto):
        estado, inicio = 0, i
        lin_ini, col_ini = linea, columna

        while i < len(texto):
            siguiente = TRANSICIONES[estado].get(clase_de(texto[i]))
            if siguiente is None:        # δ(estado, clase) = qE: corte
                break
            estado = siguiente
            if texto[i] == "\n":
                linea, columna = linea + 1, 1
            else:
                columna += 1
            i += 1

        lexema = texto[inicio:i]

        if lexema == "":                 # desde q0 el símbolo ya va a qE
            errores.append(ErrorLexico("carácter no reconocido", texto[i], linea, columna))
            i += 1
            columna += 1
        elif estado in ACEPTACION:
            tipo = tipo_de_token(estado, lexema)
            if tipo not in DESCARTADOS:
                tokens.append(Token(tipo, lexema, lin_ini, col_ini))
        else:
            errores.append(ErrorLexico(ERRORES_ESTADO[estado], lexema, lin_ini, col_ini))

    tokens.append(Token("EOF", "", linea, columna))
    return tokens, errores
