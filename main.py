"""AeroCode: analiza un archivo y muestra su árbol de derivación o sus errores.

Uso:
    python main.py programa.aero
    python main.py programa.aero --tokens          # muestra también los tokens
    python main.py programa.aero --dot arbol.dot   # exporta el árbol a Graphviz
"""

import argparse
import sys

import lexer
import parser
from arbol import imprimir, a_dot


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    opciones = argparse.ArgumentParser(description="Analizador léxico y sintáctico de AeroCode")
    opciones.add_argument("archivo", help="archivo con código AeroCode")
    opciones.add_argument("--tokens", action="store_true", help="muestra la lista de tokens")
    opciones.add_argument("--dot", metavar="SALIDA", help="guarda el árbol en formato Graphviz")
    args = opciones.parse_args()

    try:
        with open(args.archivo, encoding="utf-8") as f:
            texto = f.read()
    except OSError as e:
        print(f"No se pudo leer el archivo: {e}")
        return 2

    # Fase 1: análisis léxico
    tokens, errores_lexicos = lexer.analizar(texto)
    if args.tokens:
        print("=== Tokens ===")
        for t in tokens:
            print(f"  {t}")
        print()

    # Si el léxico falla, el sintáctico no puede continuar: los tokens
    # estarían incompletos y producirían errores en cascada.
    if errores_lexicos:
        print(f"=== {len(errores_lexicos)} error(es) léxico(s) ===")
        for e in errores_lexicos:
            print(f"  {e}")
        return 1

    # Fase 2: análisis sintáctico
    arbol, errores_sintacticos = parser.analizar(tokens)
    if errores_sintacticos:
        print(f"=== {len(errores_sintacticos)} error(es) sintáctico(s) ===")
        for e in errores_sintacticos:
            print(f"  {e}")
        return 1

    print("=== Árbol de derivación ===")
    print(imprimir(arbol))
    print()
    print(f"Programa válido: {len(tokens) - 1} tokens.")

    if args.dot:
        with open(args.dot, "w", encoding="utf-8") as f:
            f.write(a_dot(arbol))
        print(f"Árbol exportado a {args.dot}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
