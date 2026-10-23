import re
import tkinter as tk
from datetime import date
from tkinter import ttk

from bd import basedatos
from logica import solicitudes

FONDO = "#F3F4F8"
TARJETA = "#FFFFFF"
BORDE = "#E3E6EE"
TEXTO = "#1B2033"
SUAVE = "#6B7285"
ACENTO = "#4F46E5"
ACENTO_OSCURO = "#4338CA"
ACENTO_CLARO = "#EEF0FF"
# estado -> (color del texto, color de fondo)
ESTADOS = {
    "Aprobada": ("#15803D", "#DCFCE7"),
    "Rechazada": ("#B91C1C", "#FEE2E2"),
    "Pendiente de director": ("#B45309", "#FEF3C7"),
    "Pendiente de jefe inmediato": ("#B45309", "#FEF3C7"),
    "Por revisar": ("#475569", "#E2E8F0"),
}
ERROR = ESTADOS["Rechazada"]

FUENTE = ("Segoe UI", 10)
FUENTE_NEGRITA = ("Segoe UI", 10, "bold")
FUENTE_PEQUENA = ("Segoe UI", 9)

# (clave, etiqueta, fila, columna, columnas que ocupa)
CAMPOS = [
    ("empleado", "Empleado", 0, 0, 1),
    ("ciudad", "Ciudad de destino", 0, 1, 1),
    ("fecha_salida", "Fecha de salida (AAAA-MM-DD)", 0, 2, 1),
    ("noches", "Noches", 1, 0, 1),
    ("valor_noche", "Hotel por noche (COP)", 1, 1, 1),
    ("valor_tiquete", "Tiquete (COP)", 1, 2, 1),
    ("motivo", "Motivo del viaje", 2, 0, 3),
]
COLUMNAS = [  # (clave, título, % del ancho de la tabla)
    ("radicado", "Radicado", 10.5), ("fecha_radicado", "Fecha", 11), ("ciudad", "Ciudad", 12.5),
    ("fecha_salida", "Salida", 11), ("noches", "Noches", 8.5), ("valor_noche", "Hotel", 10),
    ("valor_tiquete", "Tiquete", 11.5), ("estado", "Estado", 25),
]


def entero(texto, nombre):
    """Convierte '310.000', '$ 310,000' o '2' en entero; los puntos y comas son solo formato."""
    digitos = re.sub(r"[.,$\s]|cop", "", texto.lower())
    if not digitos.isdigit():
        raise ValueError(f"{nombre} debe ser un número entero.")
    return int(digitos)


def pesos(valor):
    return f"${valor:,}".replace(",", ".")


class Aplicacion(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Viáticos · Altiplano")
        self.geometry("1100x720")
        self.minsize(960, 640)
        self.configure(bg=FONDO)

        estilo = ttk.Style(self)
        estilo.theme_use("clam")
        estilo.configure("Treeview", background=TARJETA, fieldbackground=TARJETA, foreground=TEXTO,
                         font=FUENTE, rowheight=32, borderwidth=0)
        estilo.configure("Treeview.Heading", background="#F8F9FC", foreground=SUAVE, font=FUENTE_NEGRITA,
                         relief="flat", padding=(8, 8))
        estilo.map("Treeview", background=[("selected", ACENTO_CLARO)], foreground=[("selected", TEXTO)])
        estilo.map("Treeview.Heading", background=[("active", "#F8F9FC")])
        estilo.configure("Vertical.TScrollbar", background=BORDE, troughcolor=TARJETA, borderwidth=0,
                         arrowsize=0)

        self.crear_cabecera()
        self.contenido = tk.Frame(self, bg=FONDO)
        self.contenido.pack(fill=tk.BOTH, expand=True, padx=28, pady=(0, 24))
        self.contenido.rowconfigure(0, weight=1)
        self.contenido.columnconfigure(0, weight=1)
        self.paginas = {
            "registrar": self.crear_pagina_registro(),
            "consultar": self.crear_pagina_consulta(),
        }
        self.mostrar_pagina("registrar")

    # ---------- piezas reutilizables ----------
    def tarjeta(self, padre):
        return tk.Frame(padre, bg=TARJETA, highlightthickness=1, highlightbackground=BORDE)

    def entrada(self, padre):
        return tk.Entry(padre, font=FUENTE, bg=TARJETA, fg=TEXTO, insertbackground=ACENTO, relief=tk.FLAT,
                        highlightthickness=1, highlightbackground=BORDE, highlightcolor=ACENTO)

    def boton_principal(self, padre, texto, comando):
        boton = tk.Button(padre, text=texto, command=comando, font=FUENTE_NEGRITA, bg=ACENTO, fg="white",
                          activebackground=ACENTO_OSCURO, activeforeground="white", relief=tk.FLAT, bd=0,
                          padx=22, pady=9, cursor="hand2")
        boton.bind("<Enter>", lambda _: boton.config(bg=ACENTO_OSCURO))
        boton.bind("<Leave>", lambda _: boton.config(bg=ACENTO))
        return boton

    def etiqueta_estado(self, padre, estado):
        color, fondo = ESTADOS.get(estado, ESTADOS["Por revisar"])
        return tk.Label(padre, text=f"  {estado}  ", font=FUENTE_NEGRITA, fg=color, bg=fondo, pady=3)

    # ---------- cabecera y navegación ----------
    def crear_cabecera(self):
        cabecera = tk.Frame(self, bg=FONDO)
        cabecera.pack(fill=tk.X, padx=28, pady=(22, 16))
        textos = tk.Frame(cabecera, bg=FONDO)
        textos.pack(side=tk.LEFT)
        tk.Label(textos, text="Viáticos", font=("Segoe UI", 20, "bold"), bg=FONDO, fg=TEXTO).pack(anchor="w")
        tk.Label(textos, text="Altiplano S.A.S. · solicitudes de viaje", font=FUENTE, bg=FONDO,
                 fg=SUAVE).pack(anchor="w")
        navegacion = tk.Frame(cabecera, bg="#E8EAF2", padx=3, pady=3)
        navegacion.pack(side=tk.RIGHT)
        self.botones_nav = {}
        for clave, texto in (("registrar", "Registrar"), ("consultar", "Consultar")):
            boton = tk.Button(navegacion, text=texto, font=FUENTE_NEGRITA, relief=tk.FLAT, bd=0, padx=18,
                              pady=6, cursor="hand2", command=lambda c=clave: self.mostrar_pagina(c))
            boton.pack(side=tk.LEFT)
            self.botones_nav[clave] = boton

    def mostrar_pagina(self, clave):
        self.paginas[clave].tkraise()
        for nombre, boton in self.botones_nav.items():
            activo = nombre == clave
            boton.config(bg=TARJETA if activo else "#E8EAF2", fg=ACENTO if activo else SUAVE,
                         activebackground=TARJETA, activeforeground=ACENTO)

    # ---------- página: registrar ----------
    def crear_pagina_registro(self):
        pagina = tk.Frame(self.contenido, bg=FONDO)
        pagina.grid(row=0, column=0, sticky="nsew")
        pagina.columnconfigure(0, weight=1)
        # el resultado va arriba del formulario para que siempre se vea, aunque la ventana sea baja
        self.zona_resultado = tk.Frame(pagina, bg=FONDO)
        self.zona_resultado.grid(row=0, column=0, sticky="ew")
        formulario = self.tarjeta(pagina)
        formulario.grid(row=1, column=0, sticky="ew")
        cuerpo = tk.Frame(formulario, bg=TARJETA, padx=24, pady=16)
        cuerpo.pack(fill=tk.BOTH)
        cuerpo.columnconfigure((0, 1, 2), weight=1, uniform="col")
        tk.Label(cuerpo, text="Nueva solicitud", font=("Segoe UI", 13, "bold"), bg=TARJETA, fg=TEXTO).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        self.campos = {}
        for clave, etiqueta, fila, columna, ancho in CAMPOS:
            marco = tk.Frame(cuerpo, bg=TARJETA)
            marco.grid(row=fila + 1, column=columna, columnspan=ancho, sticky="ew",
                       padx=(0, 12) if columna < 2 and ancho == 1 else 0, pady=(0, 8))
            tk.Label(marco, text=etiqueta, font=FUENTE_PEQUENA, bg=TARJETA, fg=SUAVE).pack(anchor="w")
            self.campos[clave] = self.entrada(marco)
            self.campos[clave].pack(fill=tk.X, ipady=5, pady=(3, 0))
        self.campos["fecha_salida"].insert(0, date.today().isoformat())
        self.boton_principal(cuerpo, "Registrar solicitud", self.registrar).grid(
            row=4, column=0, columnspan=3, sticky="e", pady=(2, 0))
        return pagina

    def limpiar_resultado(self):
        for hijo in self.zona_resultado.winfo_children():
            hijo.destroy()

    def mostrar_error(self, mensaje):
        self.limpiar_resultado()
        color, fondo = ERROR
        tk.Label(self.zona_resultado, text=mensaje, font=FUENTE, fg=color, bg=fondo, anchor="w", justify=tk.LEFT,
                 wraplength=900, padx=16, pady=12).pack(fill=tk.X, pady=(0, 14))

    def mostrar_confirmacion(self, resultado):
        self.limpiar_resultado()
        tarjeta = self.tarjeta(self.zona_resultado)
        tarjeta.pack(fill=tk.X, pady=(0, 14))
        cuerpo = tk.Frame(tarjeta, bg=TARJETA, padx=24, pady=12)
        cuerpo.pack(fill=tk.X)
        fila = tk.Frame(cuerpo, bg=TARJETA)
        fila.pack(fill=tk.X)
        tk.Label(fila, text=f"Solicitud {resultado['radicado']} registrada", font=("Segoe UI", 14, "bold"),
                 bg=TARJETA, fg=TEXTO).pack(side=tk.LEFT)
        self.etiqueta_estado(fila, resultado["estado"]).pack(side=tk.RIGHT)
        tk.Label(cuerpo, text=resultado["motivo"], font=FUENTE, bg=TARJETA, fg=TEXTO, anchor="w",
                 justify=tk.LEFT, wraplength=900).pack(anchor="w", pady=(6, 0))
        tk.Label(cuerpo, text=f"Costo estimado: {pesos(resultado['costo_estimado'])} COP", font=FUENTE_PEQUENA,
                 bg=TARJETA, fg=SUAVE).pack(anchor="w", pady=(2, 0))

    def registrar(self):
        datos = {clave: campo.get().strip() for clave, campo in self.campos.items()}
        try:
            if not all(datos.values()):
                raise ValueError("Completa los siete datos antes de registrar.")
            try:
                fecha_salida = date.fromisoformat(datos["fecha_salida"]).isoformat()
            except ValueError:
                raise ValueError("La fecha de salida debe tener el formato AAAA-MM-DD.") from None
            resultado = solicitudes.registrar_solicitud(
                datos["empleado"], datos["ciudad"], fecha_salida, entero(datos["noches"], "Noches"),
                datos["motivo"], entero(datos["valor_noche"], "El valor por noche"),
                entero(datos["valor_tiquete"], "El valor del tiquete"))
        except ValueError as error:
            self.mostrar_error(str(error))
            return
        self.mostrar_confirmacion(resultado)
        for clave, campo in self.campos.items():  # formulario limpio: un doble clic no duplica la solicitud
            campo.delete(0, tk.END)
        self.campos["fecha_salida"].insert(0, date.today().isoformat())

    # ---------- página: consultar ----------
    def crear_pagina_consulta(self):
        pagina = tk.Frame(self.contenido, bg=FONDO)
        pagina.grid(row=0, column=0, sticky="nsew")
        pagina.columnconfigure(0, weight=1)
        pagina.rowconfigure(1, weight=1)
        barra = self.tarjeta(pagina)
        barra.grid(row=0, column=0, sticky="ew")
        cuerpo = tk.Frame(barra, bg=TARJETA, padx=20, pady=14)
        cuerpo.pack(fill=tk.X)
        self.consulta = self.entrada(cuerpo)
        self.consulta.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=7)
        self.consulta.bind("<Return>", lambda _: self.consultar())
        self.boton_principal(cuerpo, "Buscar", self.consultar).pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(pagina, text="Escribe el nombre de un empleado y presiona Enter.", font=FUENTE_PEQUENA,
                 bg=FONDO, fg=SUAVE).grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.mensaje_consulta = tk.Label(pagina, text="", font=FUENTE_NEGRITA, bg=FONDO, fg=SUAVE, anchor="w")
        self.mensaje_consulta.grid(row=2, column=0, sticky="e", pady=(8, 0))

        marco = self.tarjeta(pagina)
        marco.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
        self.tabla = ttk.Treeview(marco, columns=[c for c, _, _ in COLUMNAS], show="headings", selectmode="browse")
        for clave, titulo, _ in COLUMNAS:
            self.tabla.heading(clave, text=titulo, anchor="w")
            self.tabla.column(clave, anchor="w", stretch=False)
        self.tabla.bind("<Configure>", self.ajustar_columnas)
        desplazamiento = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=desplazamiento.set)
        desplazamiento.pack(side=tk.RIGHT, fill=tk.Y)
        self.tabla.pack(fill=tk.BOTH, expand=True)
        for estado, (color, _) in ESTADOS.items():
            self.tabla.tag_configure(estado, foreground=color)
        return pagina

    def ajustar_columnas(self, evento):
        """Reparte el ancho de la tabla entre las columnas para que nada quede cortado."""
        for clave, _, porcentaje in COLUMNAS:
            self.tabla.column(clave, width=int((evento.width - 4) * porcentaje / 100))

    def consultar(self):
        self.tabla.delete(*self.tabla.get_children())
        nombre = self.consulta.get().strip()
        if not nombre:
            return
        try:
            filas = solicitudes.consultar_solicitudes(nombre)
        except ValueError as error:
            self.mensaje_consulta.config(text=str(error), fg=ERROR[0])
            return
        for fila in filas:
            valores = [pesos(fila[c]) if c in ("valor_noche", "valor_tiquete") else fila[c]
                       for c, _, _ in COLUMNAS]
            self.tabla.insert("", tk.END, values=valores, tags=(fila["estado"],))
        self.mensaje_consulta.config(text=f"{len(filas)} solicitud(es)", fg=ACENTO)


if __name__ == "__main__":
    basedatos.crear_base()
    Aplicacion().mainloop()
