"""Ventana para consultar cualquier tabla local: filtro, recuento y exportar a CSV."""

import csv
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from bd.basedatos import BaseDatos
from modulos import utilidades as u
from modulos.ventanas_tk import preparar_formulario_navegable


MAXIMO_FILAS_PANTALLA = 20000


class VisorTabla:

    def __init__(self, parent, titulo, tabla, orden=None):
        self.tabla = tabla
        self.orden = orden
        self.bd = BaseDatos()

        self.ventana = tk.Toplevel(parent)
        self.ventana.title(titulo)
        self.ventana.geometry("1200x700")
        self.ventana.protocol("WM_DELETE_WINDOW", self.cerrar)

        cabecera = tk.Frame(self.ventana, padx=10, pady=8)
        cabecera.pack(fill="x")

        tk.Label(cabecera, text=titulo, font=("Arial", 14, "bold")).pack(side="left")
        tk.Button(cabecera, text="Cerrar", width=12, command=self.cerrar).pack(side="right")
        tk.Button(
            cabecera, text="Exportar CSV", width=14, command=self.exportar
        ).pack(side="right", padx=6)

        filtro = tk.Frame(self.ventana, padx=10)
        filtro.pack(fill="x")
        tk.Label(filtro, text="Filtrar (contiene, en cualquier columna):").pack(side="left")
        self.var_filtro = tk.StringVar()
        entrada = tk.Entry(filtro, textvariable=self.var_filtro, width=40)
        entrada.pack(side="left", padx=6)
        entrada.bind("<Return>", lambda _e: self.cargar())
        tk.Button(filtro, text="Filtrar", width=10, command=self.cargar).pack(side="left")
        tk.Button(
            filtro, text="Quitar filtro", width=12,
            command=lambda: (self.var_filtro.set(""), self.cargar()),
        ).pack(side="left", padx=6)
        self.lbl_total = tk.Label(filtro, text="", font=("Arial", 9, "bold"))
        self.lbl_total.pack(side="right")

        marco = tk.Frame(self.ventana, padx=10, pady=8)
        marco.pack(fill="both", expand=True)

        self.arbol = ttk.Treeview(marco, show="headings")
        barra_v = ttk.Scrollbar(marco, orient="vertical", command=self.arbol.yview)
        barra_h = ttk.Scrollbar(marco, orient="horizontal", command=self.arbol.xview)
        self.arbol.configure(yscrollcommand=barra_v.set, xscrollcommand=barra_h.set)
        self.arbol.grid(row=0, column=0, sticky="nsew")
        barra_v.grid(row=0, column=1, sticky="ns")
        barra_h.grid(row=1, column=0, sticky="ew")
        marco.grid_rowconfigure(0, weight=1)
        marco.grid_columnconfigure(0, weight=1)

        self.columnas = []
        self.filas = []
        self.cargar()
        preparar_formulario_navegable(self.ventana, parent=parent, maximizar=False)

    def leer(self):
        if not self.bd.existe_tabla(self.tabla):
            return [], []
        columnas = self.bd.columnas(self.tabla)
        sql = f"SELECT * FROM {self.tabla}"
        if self.orden:
            sql += " ORDER BY " + self.orden
        filas = self.bd.consultar(sql)
        filtro = u.texto(self.var_filtro.get()).upper()
        if filtro:
            filas = [
                f for f in filas
                if any(filtro in u.texto(v).upper() for v in f)
            ]
        return columnas, filas

    def cargar(self):
        try:
            self.columnas, self.filas = self.leer()
        except Exception as error:
            messagebox.showerror("Consulta", str(error), parent=self.ventana)
            return

        self.arbol.delete(*self.arbol.get_children())
        self.arbol["columns"] = self.columnas
        for columna in self.columnas:
            self.arbol.heading(columna, text=columna)
            self.arbol.column(columna, width=max(80, min(260, len(columna) * 9)), stretch=False)

        for fila in self.filas[:MAXIMO_FILAS_PANTALLA]:
            self.arbol.insert("", "end", values=["" if v is None else v for v in fila])

        texto = "Registros: " + u.formatear_numero(len(self.filas))
        if len(self.filas) > MAXIMO_FILAS_PANTALLA:
            texto += " (se muestran " + u.formatear_numero(MAXIMO_FILAS_PANTALLA) + "; exporta para verlos todos)"
        self.lbl_total.config(text=texto)

    def exportar(self):
        if not self.columnas:
            messagebox.showinfo("Exportar", "No hay datos.", parent=self.ventana)
            return
        ruta = filedialog.asksaveasfilename(
            parent=self.ventana,
            title="Exportar a CSV",
            defaultextension=".csv",
            initialfile=self.tabla + ".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not ruta:
            return
        with open(ruta, "w", encoding="utf-8-sig", newline="") as f:
            escritor = csv.writer(f, delimiter=";")
            escritor.writerow(self.columnas)
            for fila in self.filas:
                escritor.writerow(
                    [str(v).replace(".", ",") if isinstance(v, float) else ("" if v is None else v) for v in fila]
                )
        messagebox.showinfo("Exportar", "Exportado:\n" + ruta, parent=self.ventana)

    def cerrar(self):
        try:
            self.bd.cerrar()
        finally:
            self.ventana.destroy()
