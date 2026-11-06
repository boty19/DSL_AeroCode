"""Interfaz gráfica de AeroCode.

Permite escribir un programa (a mano o con formularios que solo aceptan
datos válidos), analizarlo y ver los tokens, los errores y el árbol de
derivación. Usa los mismos módulos lexer.py y parser.py que main.py.

Uso:  python interfaz.py
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import lexer
import parser

CARPETA = os.path.dirname(os.path.abspath(__file__))
CARPETA_EJEMPLOS = os.path.join(CARPETA, "pruebas")

# Colores del resaltado, por tipo de token.
COLORES = {
    "reservada": ("#1f4fbf", True),
    "COMANDO": ("#8a2be2", True),
    "EJE": ("#c25e00", True),
    "NUM": ("#1a7f37", False),
    "operador": ("#555555", False),
    "comentario": ("#8c8c8c", False),
}
RESERVADAS = set(lexer.PALABRAS_RESERVADAS.values())
OPERADORES = {"MAS", "MENOS", "MULT", "DIV", "ASIG", "IGUAL", "DIST", "MENOR",
              "MENOR_IG", "MAYOR", "MAYOR_IG", "PAR_A", "PAR_C", "LLAVE_A",
              "LLAVE_C", "PUNTO_COMA"}

AYUDA = """INSTRUCCIONES DISPONIBLES

  despegar <expresión>;          Despega hasta esa altura (m)
  aterrizar;                     Aterriza
  girar <expresión>;             Gira esos grados
  velocidad <expresión>;         Cambia la velocidad (m/s)
  esperar <expresión>;           Espera esos segundos
  nombre = <expresión>;          Guarda un valor en una variable
  G0 X.. Y.. Z..;                Movimiento rápido a una posición
  G1 X.. Y.. Z..;                Movimiento lineal controlado
  repetir <expresión> { ... }    Repite el bloque
  si (<condición>) { ... }       Ejecuta el bloque si se cumple
  si (<condición>) { ... } sino { ... }

EXPRESIONES
  Números: 10, 2.5     Variables: lado, punto_1     Sensores: bateria, altura
  Operadores: + - * /  (el * y el / se aplican antes que + y -)
  Paréntesis: (lado + 2) * 3      Signo: -5

CONDICIONES
  <expresión> <operador> <expresión>   con  ==  !=  <  <=  >  >=

REGLAS DEL LÉXICO
  · Variables y palabras reservadas en minúsculas, sin tildes.
  · Solo G, X, Y, Z van en mayúscula.
  · Comentarios: desde # hasta el final de la línea.
  · Cada instrucción simple termina en punto y coma (;).
"""


# ---------------------------------------------------------------------------
# Análisis (usa exactamente los módulos de la Fase 3)
# ---------------------------------------------------------------------------

def analizar_texto(texto):
    """Devuelve (tokens, errores, árbol). Si hay errores léxicos no se
    ejecuta el sintáctico, igual que en main.py."""
    tokens, errores_lexicos = lexer.analizar(texto)
    if errores_lexicos:
        return tokens, errores_lexicos, None
    arbol, errores_sintacticos = parser.analizar(tokens)
    return tokens, errores_sintacticos, (None if errores_sintacticos else arbol)


def posicion_error(error):
    """(línea, columna, largo) de un error léxico o sintáctico."""
    if isinstance(error, lexer.ErrorLexico):
        return error.linea, error.columna, max(1, len(error.lexema))
    return error.token.linea, error.token.columna, max(1, len(error.token.lexema))


def es_expresion_valida(texto):
    tokens, errores, _ = analizar_texto(f"tmp = {texto};")
    return not errores and texto.strip() != ""


def es_nombre_valido(texto):
    tokens, errores = lexer.analizar(texto)
    return not errores and len(tokens) == 2 and tokens[0].tipo == "ID"


# ---------------------------------------------------------------------------
# Formularios para insertar instrucciones con datos válidos
# ---------------------------------------------------------------------------

# Cada instrucción: título, campos (etiqueta, clave, tipo, opciones, valor
# inicial) y una función que arma el código con los valores.
# Tipos de campo: "expr" (expresión), "expr_opcional", "nombre", "opcion".
INSTRUCCIONES = [
    ("Despegar", [("Altura (m)", "v", "expr", None, "2.5")],
     lambda d: f"despegar {d['v']};"),
    ("Aterrizar", [], lambda d: "aterrizar;"),
    ("Girar", [("Grados", "v", "expr", None, "90")],
     lambda d: f"girar {d['v']};"),
    ("Velocidad", [("Velocidad (m/s)", "v", "expr", None, "3")],
     lambda d: f"velocidad {d['v']};"),
    ("Esperar", [("Segundos", "v", "expr", None, "1")],
     lambda d: f"esperar {d['v']};"),
    ("Asignar variable", [("Nombre", "n", "nombre", None, "lado"),
                          ("Valor", "v", "expr", None, "10")],
     lambda d: f"{d['n']} = {d['v']};"),
    ("Mover (G0 / G1)", [("Comando", "c", "opcion", ["G1", "G0", "G28"], "G1"),
                         ("X (opcional)", "x", "expr_opcional", None, "10"),
                         ("Y (opcional)", "y", "expr_opcional", None, "0"),
                         ("Z (opcional)", "z", "expr_opcional", None, "2.5")],
     lambda d: d["c"] + "".join(f" {eje}{d[k]}" if d[k] and _simple(d[k]) else
                                (f" {eje}({d[k]})" if d[k] else "")
                                for eje, k in (("X", "x"), ("Y", "y"), ("Z", "z"))) + ";"),
    ("Repetir", [("Veces", "v", "expr", None, "4")],
     lambda d: f"repetir {d['v']} {{\n§\n}}"),
    ("Si / Sino", [("Valor izquierdo", "a", "opcion_editable", ["bateria", "altura"], "bateria"),
                   ("Operador", "op", "opcion", ["<", "<=", ">", ">=", "==", "!="], "<"),
                   ("Valor derecho", "b", "expr", None, "20"),
                   ("Incluir 'sino'", "sino", "check", None, True)],
     lambda d: f"si ({d['a']} {d['op']} {d['b']}) {{\n§\n}}" + (" sino {\n§\n}" if d["sino"] else "")),
]


def _simple(valor):
    """Un valor de eje sin espacios ni operadores se pega a la letra (X10)."""
    tokens, errores = lexer.analizar(valor)
    return not errores and len(tokens) == 2 and tokens[0].tipo in {"NUM", "ID", "BATERIA", "ALTURA"}


class Formulario(tk.Toplevel):
    def __init__(self, padre, titulo, campos, armar, al_insertar):
        super().__init__(padre)
        self.title(f"Insertar: {titulo}")
        self.resizable(False, False)
        self.transient(padre)
        self.campos, self.armar, self.al_insertar = campos, armar, al_insertar
        self.variables = {}

        marco = ttk.Frame(self, padding=14)
        marco.grid(sticky="nsew")
        fila = 0
        for etiqueta, clave, tipo, opciones, inicial in campos:
            if tipo == "check":
                var = tk.BooleanVar(value=inicial)
                ttk.Checkbutton(marco, text=etiqueta, variable=var).grid(row=fila, column=0, columnspan=2, sticky="w", pady=4)
            else:
                ttk.Label(marco, text=etiqueta).grid(row=fila, column=0, sticky="w", padx=(0, 10), pady=4)
                var = tk.StringVar(value=inicial)
                if tipo in ("opcion", "opcion_editable"):
                    estado = "readonly" if tipo == "opcion" else "normal"
                    widget = ttk.Combobox(marco, textvariable=var, values=opciones, state=estado, width=22)
                else:
                    widget = ttk.Entry(marco, textvariable=var, width=25)
                widget.grid(row=fila, column=1, sticky="ew", pady=4)
                var.trace_add("write", lambda *_: self.actualizar_vista())
            self.variables[clave] = var
            fila += 1

        ttk.Label(marco, text="Código que se insertará:").grid(row=fila, column=0, columnspan=2, sticky="w", pady=(10, 2))
        self.vista = tk.Text(marco, height=4, width=40, font=("Consolas", 10), background="#f6f8fa", relief="flat")
        self.vista.grid(row=fila + 1, column=0, columnspan=2, sticky="ew")
        self.mensaje = ttk.Label(marco, text="", foreground="#c0392b", wraplength=330)
        self.mensaje.grid(row=fila + 2, column=0, columnspan=2, sticky="w", pady=(6, 0))

        botones = ttk.Frame(marco)
        botones.grid(row=fila + 3, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(botones, text="Cancelar", command=self.destroy).pack(side="right")
        self.boton_insertar = ttk.Button(botones, text="Insertar", command=self.insertar)
        self.boton_insertar.pack(side="right", padx=(0, 6))
        self.bind("<Return>", lambda e: self.insertar())
        self.bind("<Escape>", lambda e: self.destroy())
        for var in self.variables.values():
            if isinstance(var, tk.BooleanVar):
                var.trace_add("write", lambda *_: self.actualizar_vista())
        self.actualizar_vista()
        self.grab_set()

    def valores(self):
        return {k: (v.get() if isinstance(v, tk.BooleanVar) else v.get().strip()) for k, v in self.variables.items()}

    def validar(self):
        datos = self.valores()
        for etiqueta, clave, tipo, _, _ in self.campos:
            valor = datos[clave]
            if tipo in ("expr", "opcion_editable") and not es_expresion_valida(valor):
                return f"'{etiqueta}' no es una expresión válida (use números, variables, bateria, altura, + - * / y paréntesis)."
            if tipo == "expr_opcional" and valor and not es_expresion_valida(valor):
                return f"'{etiqueta}' no es una expresión válida."
            if tipo == "nombre" and not es_nombre_valido(valor):
                return f"'{valor}' no es un nombre válido: debe empezar con minúscula, usar solo minúsculas, dígitos o _, y no ser una palabra reservada."
        codigo = self.armar(datos).replace("§", "")
        _, errores, _ = analizar_texto(codigo)
        if errores:
            return str(errores[0])
        return None

    def actualizar_vista(self):
        error = self.validar()
        self.vista.configure(state="normal")
        self.vista.delete("1.0", "end")
        if error is None:
            self.vista.insert("1.0", self.armar(self.valores()).replace("§", "    ..."))
        self.vista.configure(state="disabled")
        self.mensaje.configure(text=error or "")
        self.boton_insertar.state(["disabled"] if error else ["!disabled"])

    def insertar(self):
        if self.validar() is None:
            self.al_insertar(self.armar(self.valores()))
            self.destroy()


# ---------------------------------------------------------------------------
# Ventana principal
# ---------------------------------------------------------------------------

class NumerosDeLinea(tk.Canvas):
    def __init__(self, padre, editor):
        super().__init__(padre, width=40, background="#f0f0f0", highlightthickness=0)
        self.editor = editor

    def redibujar(self):
        self.delete("all")
        indice = self.editor.index("@0,0")
        while True:
            info = self.editor.dlineinfo(indice)
            if info is None:
                break
            linea = indice.split(".")[0]
            self.create_text(34, info[1], anchor="ne", text=linea, fill="#8c8c8c", font=("Consolas", 10))
            indice = self.editor.index(f"{indice}+1line")


class Aplicacion(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AeroCode — Analizador léxico y sintáctico")
        self.geometry("1280x760")
        self.minsize(980, 600)
        self.archivo = None
        self.pendiente = None
        self.errores = []

        estilo = ttk.Style(self)
        if "vista" in estilo.theme_names():
            estilo.theme_use("vista")
        estilo.configure("Treeview", font=("Consolas", 10), rowheight=22)

        self.crear_barra()
        self.crear_cuerpo()
        self.crear_estado()
        self.bind("<F5>", lambda e: self.analizar(mostrar_arbol=True))
        self.bind("<Control-o>", lambda e: self.abrir())
        self.bind("<Control-s>", lambda e: self.guardar())
        self.cargar_ejemplo("mision_valida.aero")

    # --- construcción ---------------------------------------------------

    def crear_barra(self):
        barra = ttk.Frame(self, padding=(8, 6))
        barra.pack(side="top", fill="x")
        ttk.Button(barra, text="Nuevo", command=self.nuevo).pack(side="left")
        ttk.Button(barra, text="Abrir…", command=self.abrir).pack(side="left", padx=4)
        ttk.Button(barra, text="Guardar", command=self.guardar).pack(side="left")

        ejemplos = ttk.Menubutton(barra, text="Ejemplos")
        menu = tk.Menu(ejemplos, tearoff=False)
        if os.path.isdir(CARPETA_EJEMPLOS):
            for nombre in sorted(os.listdir(CARPETA_EJEMPLOS)):
                if nombre.endswith(".aero"):
                    menu.add_command(label=nombre, command=lambda n=nombre: self.cargar_ejemplo(n))
        ejemplos["menu"] = menu
        ejemplos.pack(side="left", padx=4)

        ttk.Button(barra, text="▶ Analizar (F5)", command=lambda: self.analizar(mostrar_arbol=True)).pack(side="left", padx=(16, 0))
        self.etiqueta_archivo = ttk.Label(barra, text="", foreground="#666666")
        self.etiqueta_archivo.pack(side="right")

    def crear_cuerpo(self):
        cuerpo = ttk.PanedWindow(self, orient="horizontal")
        cuerpo.pack(fill="both", expand=True, padx=8)

        # Panel izquierdo: formularios para insertar instrucciones.
        izquierda = ttk.LabelFrame(cuerpo, text="Insertar instrucción", padding=8)
        for titulo, campos, armar in INSTRUCCIONES:
            ttk.Button(izquierda, text=titulo,
                       command=lambda t=titulo, c=campos, a=armar: self.abrir_formulario(t, c, a)
                       ).pack(fill="x", pady=2)
        ttk.Label(izquierda, text="Cada formulario solo deja\ninsertar datos válidos.",
                  foreground="#666666", justify="left").pack(anchor="w", pady=(10, 0))
        cuerpo.add(izquierda, weight=0)

        # Centro: editor con números de línea.
        centro = ttk.Frame(cuerpo)
        marco_editor = ttk.Frame(centro)
        marco_editor.pack(fill="both", expand=True)
        self.editor = tk.Text(marco_editor, wrap="none", undo=True, font=("Consolas", 12),
                              tabs=("1c",), padx=6, pady=4)
        self.numeros = NumerosDeLinea(marco_editor, self.editor)
        barra_v = ttk.Scrollbar(marco_editor, orient="vertical", command=self.desplazar)
        self.editor.configure(yscrollcommand=lambda *a: (barra_v.set(*a), self.numeros.redibujar()))
        self.numeros.pack(side="left", fill="y")
        barra_v.pack(side="right", fill="y")
        self.editor.pack(side="left", fill="both", expand=True)
        for nombre, (color, negrita) in COLORES.items():
            fuente = ("Consolas", 12, "bold") if negrita else ("Consolas", 12)
            if nombre == "comentario":
                fuente = ("Consolas", 12, "italic")
            self.editor.tag_configure(nombre, foreground=color, font=fuente)
        self.editor.tag_configure("error", background="#ffd7d5", underline=True)
        self.editor.bind("<<Modified>>", self.al_modificar)
        self.editor.bind("<KeyRelease>", lambda e: self.numeros.redibujar())
        cuerpo.add(centro, weight=3)

        # Derecha: resultados.
        derecha = ttk.Notebook(cuerpo)
        self.lista_errores = ttk.Treeview(derecha, columns=("pos", "mensaje"), show="headings")
        self.lista_errores.heading("pos", text="Línea:Col")
        self.lista_errores.heading("mensaje", text="Mensaje")
        self.lista_errores.column("pos", width=80, anchor="center", stretch=False)
        self.lista_errores.column("mensaje", width=420)
        self.lista_errores.tag_configure("error", foreground="#c0392b")
        self.lista_errores.tag_configure("ok", foreground="#1a7f37")
        self.lista_errores.bind("<Double-1>", self.ir_a_error)
        derecha.add(self.lista_errores, text="Resultado")

        self.lista_tokens = ttk.Treeview(derecha, columns=("n", "tipo", "lexema", "pos"), show="headings")
        for col, texto, ancho in (("n", "#", 40), ("tipo", "Token", 130), ("lexema", "Lexema", 140), ("pos", "Línea:Col", 90)):
            self.lista_tokens.heading(col, text=texto)
            self.lista_tokens.column(col, width=ancho, anchor="w")
        derecha.add(self.lista_tokens, text="Tokens")

        marco_arbol = ttk.Frame(derecha)
        botones_arbol = ttk.Frame(marco_arbol)
        botones_arbol.pack(fill="x", pady=2)
        ttk.Button(botones_arbol, text="Expandir todo", command=lambda: self.expandir(True)).pack(side="left")
        ttk.Button(botones_arbol, text="Contraer todo", command=lambda: self.expandir(False)).pack(side="left", padx=4)
        self.vista_arbol = ttk.Treeview(marco_arbol, show="tree")
        self.vista_arbol.tag_configure("token", foreground="#1f4fbf")
        self.vista_arbol.tag_configure("vacio", foreground="#8c8c8c")
        barra_arbol = ttk.Scrollbar(marco_arbol, orient="vertical", command=self.vista_arbol.yview)
        self.vista_arbol.configure(yscrollcommand=barra_arbol.set)
        barra_arbol.pack(side="right", fill="y")
        self.vista_arbol.pack(fill="both", expand=True)
        derecha.add(marco_arbol, text="Árbol de derivación")

        ayuda = tk.Text(derecha, wrap="word", font=("Consolas", 10), padx=10, pady=8, background="#fbfbfb")
        ayuda.insert("1.0", AYUDA)
        ayuda.configure(state="disabled")
        derecha.add(ayuda, text="Ayuda del lenguaje")
        self.pestanas = derecha
        cuerpo.add(derecha, weight=2)

    def crear_estado(self):
        self.estado = tk.Label(self, text="", anchor="w", padx=10, pady=4, font=("Segoe UI", 10, "bold"))
        self.estado.pack(side="bottom", fill="x")

    # --- editor ----------------------------------------------------------

    def desplazar(self, *args):
        self.editor.yview(*args)
        self.numeros.redibujar()

    def al_modificar(self, _evento):
        if not self.editor.edit_modified():
            return
        self.editor.edit_modified(False)
        if self.pendiente:
            self.after_cancel(self.pendiente)
        self.pendiente = self.after(350, lambda: self.analizar(mostrar_arbol=True))

    def texto(self):
        return self.editor.get("1.0", "end-1c")

    def poner_texto(self, contenido):
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", contenido)
        self.editor.edit_reset()
        self.analizar(mostrar_arbol=True)

    def resaltar(self, tokens):
        for etiqueta in list(COLORES) + ["error"]:
            self.editor.tag_remove(etiqueta, "1.0", "end")
        for t in tokens:
            if t.tipo == "EOF":
                continue
            if t.tipo in RESERVADAS:
                etiqueta = "reservada"
            elif t.tipo in OPERADORES:
                etiqueta = "operador"
            elif t.tipo in COLORES:
                etiqueta = t.tipo
            else:
                continue
            inicio = f"{t.linea}.{t.columna - 1}"
            self.editor.tag_add(etiqueta, inicio, f"{inicio}+{len(t.lexema)}c")
        # Los comentarios no llegan como tokens: se marcan desde '#' hasta el fin de línea.
        for n, linea in enumerate(self.texto().split("\n"), start=1):
            if "#" in linea:
                self.editor.tag_add("comentario", f"{n}.{linea.index('#')}", f"{n}.end")

    def insertar_codigo(self, codigo):
        actual = self.editor.index("insert")
        linea_actual = self.editor.get(f"{actual} linestart", f"{actual} lineend")
        sangria = linea_actual[:len(linea_actual) - len(linea_actual.lstrip())]
        if linea_actual.strip():           # la línea ya tiene código: empezar una nueva
            self.editor.mark_set("insert", f"{actual} lineend")
            self.editor.insert("insert", "\n" + sangria)
        lineas = codigo.split("\n")
        texto = lineas[0] + "".join("\n" + sangria + ("    " if l == "§" else l) for l in lineas[1:])
        texto = texto.replace("§", "")
        inicio = self.editor.index("insert")
        self.editor.insert("insert", texto)
        # Si hay un bloque, dejar el cursor dentro de él.
        if "§" in codigo:
            primera = int(inicio.split(".")[0]) + 1
            self.editor.mark_set("insert", f"{primera}.end")
        self.editor.focus_set()

    # --- acciones --------------------------------------------------------

    def abrir_formulario(self, titulo, campos, armar):
        if not campos:
            self.insertar_codigo(armar({}))
            return
        Formulario(self, titulo, campos, armar, self.insertar_codigo)

    def nuevo(self):
        self.archivo = None
        self.etiqueta_archivo.configure(text="(sin guardar)")
        self.poner_texto("")

    def abrir(self):
        ruta = filedialog.askopenfilename(title="Abrir programa AeroCode",
                                          filetypes=[("AeroCode", "*.aero"), ("Todos", "*.*")])
        if ruta:
            self.cargar_archivo(ruta)

    def cargar_ejemplo(self, nombre):
        ruta = os.path.join(CARPETA_EJEMPLOS, nombre)
        if os.path.exists(ruta):
            self.cargar_archivo(ruta)

    def cargar_archivo(self, ruta):
        try:
            with open(ruta, encoding="utf-8") as f:
                contenido = f.read()
        except OSError as e:
            messagebox.showerror("AeroCode", f"No se pudo abrir el archivo:\n{e}")
            return
        self.archivo = ruta
        self.etiqueta_archivo.configure(text=os.path.basename(ruta))
        self.poner_texto(contenido)

    def guardar(self):
        ruta = self.archivo
        if not ruta:
            ruta = filedialog.asksaveasfilename(title="Guardar programa AeroCode", defaultextension=".aero",
                                                filetypes=[("AeroCode", "*.aero")])
            if not ruta:
                return
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(self.texto())
        self.archivo = ruta
        self.etiqueta_archivo.configure(text=os.path.basename(ruta))

    def analizar(self, mostrar_arbol=False):
        self.pendiente = None
        tokens, errores, arbol = analizar_texto(self.texto())
        self.errores = errores
        self.resaltar(tokens)
        self.numeros.redibujar()

        self.lista_tokens.delete(*self.lista_tokens.get_children())
        for n, t in enumerate(tokens[:-1], start=1):
            self.lista_tokens.insert("", "end", values=(n, t.tipo, t.lexema, f"{t.linea}:{t.columna}"))

        self.lista_errores.delete(*self.lista_errores.get_children())
        for k, e in enumerate(errores):
            linea, columna, largo = posicion_error(e)
            inicio = f"{linea}.{columna - 1}"
            self.editor.tag_add("error", inicio, f"{inicio}+{largo}c")
            mensaje = str(e).split(": ", 1)[-1]
            tipo = "Léxico" if isinstance(e, lexer.ErrorLexico) else "Sintáctico"
            self.lista_errores.insert("", "end", iid=str(k), values=(f"{linea}:{columna}", f"[{tipo}] {mensaje}"), tags=("error",))

        if errores:
            self.estado.configure(text=f"✖  {len(errores)} error(es). Doble clic en un error para ir a la línea.",
                                  background="#fdecea", foreground="#c0392b")
        else:
            self.lista_errores.insert("", "end", values=("", f"Programa válido: {len(tokens) - 1} tokens."), tags=("ok",))
            self.estado.configure(text=f"✔  Programa válido · {len(tokens) - 1} tokens · árbol de derivación construido",
                                  background="#e6f4ea", foreground="#1a7f37")

        if mostrar_arbol:
            self.vista_arbol.delete(*self.vista_arbol.get_children())
            if arbol is not None:
                self.agregar_nodo("", arbol)
                self.expandir(True)

    def agregar_nodo(self, padre, nodo):
        etiquetas = ("token",) if nodo.token is not None else (("vacio",) if nodo.etiqueta == "ε" else ())
        iid = self.vista_arbol.insert(padre, "end", text=nodo.texto(), tags=etiquetas)
        for hijo in nodo.hijos:
            self.agregar_nodo(iid, hijo)

    def expandir(self, abrir, item=""):
        for hijo in self.vista_arbol.get_children(item):
            self.vista_arbol.item(hijo, open=abrir)
            self.expandir(abrir, hijo)

    def ir_a_error(self, _evento):
        seleccion = self.lista_errores.selection()
        if not seleccion or not seleccion[0].isdigit():
            return
        linea, columna, _ = posicion_error(self.errores[int(seleccion[0])])
        indice = f"{linea}.{columna - 1}"
        self.editor.mark_set("insert", indice)
        self.editor.see(indice)
        self.editor.focus_set()


if __name__ == "__main__":
    Aplicacion().mainloop()
