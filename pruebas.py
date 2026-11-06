"""Pruebas automáticas de AeroCode. Ejecutar con:  python pruebas.py"""

import os
import unittest

import lexer
import parser

CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pruebas")


def leer(nombre):
    with open(os.path.join(CARPETA, nombre), encoding="utf-8") as f:
        return f.read()


def tipos(texto):
    tokens, errores = lexer.analizar(texto)
    return [t.tipo for t in tokens[:-1]], errores


def buscar(nodo, etiqueta):
    """Primer nodo con esa etiqueta, recorriendo el árbol en preorden."""
    if nodo.etiqueta == etiqueta:
        return nodo
    for hijo in nodo.hijos:
        encontrado = buscar(hijo, etiqueta)
        if encontrado:
            return encontrado
    return None


class PruebasLexico(unittest.TestCase):
    def test_matriz_tiene_13_estados_mas_qE(self):
        self.assertEqual(sorted(lexer.TRANSICIONES), list(range(13)))

    def test_programa_completo_de_la_fase_1(self):
        # Fase 1, sección 7: 104 tokens contando el comentario (103 sin él).
        lista, errores = tipos(leer("mision_completa.aero"))
        self.assertEqual(errores, [])
        self.assertEqual(len(lista), 103)

    def test_lexema_mas_largo(self):
        self.assertEqual(tipos("G01")[0], ["COMANDO"])
        self.assertEqual(tipos(">=")[0], ["MAYOR_IG"])
        self.assertEqual(tipos("X10")[0], ["EJE", "NUM"])
        self.assertEqual(tipos("12.5x")[0], ["NUM", "ID"])

    def test_palabras_reservadas(self):
        self.assertEqual(tipos("si sino silla")[0], ["SI", "SINO", "ID"])

    def test_errores_lexicos(self):
        _, errores = lexer.analizar(leer("errores_lexicos.aero"))
        lexemas = [e.lexema for e in errores]
        self.assertEqual(lexemas, ["G", "3.", "!", "@"])


class PruebasSintactico(unittest.TestCase):
    def analizar(self, texto):
        tokens, errores_lexicos = lexer.analizar(texto)
        self.assertEqual(errores_lexicos, [])
        return parser.analizar(tokens)

    def test_programas_validos(self):
        for nombre in ("mision_valida.aero", "mision_completa.aero"):
            arbol, errores = self.analizar(leer(nombre))
            self.assertEqual(errores, [], nombre)

    def test_hojas_del_arbol_son_los_tokens(self):
        texto = leer("mision_valida.aero")
        tokens, _ = lexer.analizar(texto)
        arbol, _ = parser.analizar(tokens)
        self.assertEqual(arbol.hojas(), [t.tipo for t in tokens[:-1]])

    def test_precedencia_multiplicacion_antes_que_suma(self):
        # En 2 + 3 * 4, el * debe quedar dentro del <term> que sigue al +.
        arbol, _ = self.analizar("lado = 2 + 3 * 4;")
        expr_prima = buscar(arbol, "<expr'>")
        self.assertEqual(expr_prima.hijos[0].etiqueta, "MAS")
        term_derecho = expr_prima.hijos[1]
        self.assertIn("MULT", term_derecho.hojas())

    def test_menos_despues_de_termino_es_resta(self):
        # G1 X 10 -5 se lee como X (10 - 5): un solo eje.
        arbol, errores = self.analizar("G1 X 10 -5;")
        self.assertEqual(errores, [])
        self.assertEqual(arbol.hojas().count("EJE"), 1)

    def test_errores_sintacticos_con_recuperacion(self):
        _, errores = self.analizar(leer("errores_sintacticos.aero"))
        lineas = [e.token.linea for e in errores]
        self.assertEqual(lineas, [3, 4, 5, 6])
        self.assertIn("se esperaba '{'", str(errores[1]))

    def test_llave_sobrante(self):
        _, errores = self.analizar("aterrizar; } girar 90;")
        self.assertEqual(len(errores), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
