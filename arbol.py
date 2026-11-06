"""Árbol de derivación: nodos, impresión en texto y exportación a Graphviz."""


class Nodo:
    def __init__(self, etiqueta, token=None):
        self.etiqueta = etiqueta    # "<expr>", "NUM", "ε", ...
        self.token = token          # solo en las hojas que son tokens
        self.hijos = []

    def agregar(self, hijo):
        self.hijos.append(hijo)
        return hijo

    def texto(self):
        if self.token is not None:
            return f"{self.etiqueta} '{self.token.lexema}'"
        return self.etiqueta

    def hojas(self):
        """Hojas de izquierda a derecha, sin ε: deben dar la cadena de tokens."""
        if not self.hijos:
            return [] if self.etiqueta == "ε" else [self.etiqueta]
        resultado = []
        for hijo in self.hijos:
            resultado.extend(hijo.hojas())
        return resultado


def imprimir(nodo, prefijo="", ultimo=True, es_raiz=True):
    """Devuelve el árbol como texto con ramas ├── y └──."""
    if es_raiz:
        lineas = [nodo.texto()]
        hijo_prefijo = ""
    else:
        lineas = [prefijo + ("└── " if ultimo else "├── ") + nodo.texto()]
        hijo_prefijo = prefijo + ("    " if ultimo else "│   ")
    for k, hijo in enumerate(nodo.hijos):
        lineas.append(imprimir(hijo, hijo_prefijo, k == len(nodo.hijos) - 1, False))
    return "\n".join(lineas)


def a_dot(raiz):
    """Exporta el árbol en formato DOT de Graphviz (para dibujarlo como imagen)."""
    lineas = ["digraph arbol {", '  node [fontname="Arial", shape=plaintext];']
    contador = [0]

    def visitar(nodo):
        nid = f"n{contador[0]}"
        contador[0] += 1
        etiqueta = nodo.texto().replace("\\", "\\\\").replace('"', '\\"')
        color = ', fontcolor="#1a6fd6"' if nodo.token is not None else ""
        lineas.append(f'  {nid} [label="{etiqueta}"{color}];')
        for hijo in nodo.hijos:
            lineas.append(f"  {nid} -> {visitar(hijo)};")
        return nid

    visitar(raiz)
    lineas.append("}")
    return "\n".join(lineas)
