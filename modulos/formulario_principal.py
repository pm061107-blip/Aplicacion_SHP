import tkinter as tk
from tkinter import messagebox

from modulos.componente_refresco import BarraRefresco, mensaje_errores
from modulos.formulario_datos import FormularioDatos
from modulos.version_aplicacion import NOMBRE_VERSION
from modulos.ventanas_tk import preparar_formulario_navegable


class FormularioPrincipal:

    #---------------------------------------------------------
    # Constructor
    #---------------------------------------------------------
    def __init__(self, resultado_tiendas_web=None, resultado_access=None):

        self.ventana = tk.Tk()
        self.ventana.title("Aplicacion SHP - " + NOMBRE_VERSION)
        self.ventana.geometry("980x760")
        self.ventana.resizable(True, True)

        self.formularios_abiertos = {}

        self.crear_controles()
        preparar_formulario_navegable(self.ventana, maximizar=True)
        self.barra.mostrar(resultado_tiendas_web, resultado_access)

        mensaje = mensaje_errores(resultado_tiendas_web, resultado_access)
        if mensaje:
            self.ventana.after(
                500,
                lambda: messagebox.showwarning(
                    "Datos maestros", mensaje, parent=self.ventana
                ),
            )

    #---------------------------------------------------------
    # Crear controles
    #---------------------------------------------------------
    def crear_controles(self):

        contenedor = tk.Frame(self.ventana)
        contenedor.pack(fill="both", expand=True, padx=28, pady=24)

        tk.Label(
            contenedor,
            text="APLICACIÓN SHP",
            font=("Arial", 20, "bold")
        ).pack(pady=(0, 6))

        tk.Label(
            contenedor,
            text="Etiquetado GUI GLS  ·  Expedición GUI SHP  ·  Roboshuttle",
            font=("Arial", 11)
        ).pack(pady=(0, 16))

        self.barra = BarraRefresco(contenedor, self.ventana)
        self.barra.pack(fill="x", pady=(0, 12))

        panel = tk.Frame(contenedor)
        panel.pack(fill="both", expand=True)

        self.crear_boton_menu(
            panel, 0, 0,
            "DATOS E IMPORTACIONES",
            "Expediciones, pedido/ESTAREPP, volumetría, contenedores HAI",
            "#d9ead3",
            self.abrir_datos,
        )
        self.crear_boton_menu(
            panel, 0, 1,
            "ETIQUETADO GUI GLS",
            "Próximo paso",
            "#e6e6e6",
            None,
        )
        self.crear_boton_menu(
            panel, 1, 0,
            "EXPEDICIÓN GUI SHP",
            "Próximo paso",
            "#e6e6e6",
            None,
        )
        self.crear_boton_menu(
            panel, 1, 1,
            "ROBOSHUTTLE",
            "Próximo paso",
            "#e6e6e6",
            None,
        )

        panel.grid_columnconfigure(0, weight=1)
        panel.grid_columnconfigure(1, weight=1)
        for fila in range(2):
            panel.grid_rowconfigure(fila, weight=1)

        pie = tk.Frame(contenedor)
        pie.pack(fill="x", pady=(18, 0))

        tk.Label(
            pie, text=NOMBRE_VERSION, font=("Arial", 8), fg="#666666"
        ).pack(side="left")

        tk.Button(
            pie, text="Salir", width=18, height=2, command=self.ventana.destroy
        ).pack(side="right")

    #---------------------------------------------------------
    # Crear boton del menu
    #---------------------------------------------------------
    def crear_boton_menu(self, panel, fila, columna, titulo, texto, color, comando):

        boton = tk.Button(
            panel,
            text=titulo + "\n" + texto,
            font=("Arial", 12, "bold"),
            bg=color,
            height=5,
            command=comando,
            state="normal" if comando else "disabled",
        )
        boton.grid(row=fila, column=columna, sticky="nsew", padx=10, pady=10)

    #---------------------------------------------------------
    # Formularios secundarios (uno de cada tipo abierto)
    #---------------------------------------------------------
    def ejecutar_formulario_secundario(self, clase_formulario):

        clave = clase_formulario.__name__
        existente = self.formularios_abiertos.get(clave)

        if existente is not None:
            try:
                if int(existente.ventana.winfo_exists()) == 1:
                    preparar_formulario_navegable(existente.ventana, parent=self.ventana, maximizar=True)
                    return existente
            except Exception:
                pass
            self.formularios_abiertos.pop(clave, None)

        formulario = clase_formulario(self.ventana)
        self.formularios_abiertos[clave] = formulario
        preparar_formulario_navegable(formulario.ventana, parent=self.ventana, maximizar=True)

        def _olvidar(evento, ventana=formulario.ventana):
            if evento.widget is ventana:
                self.formularios_abiertos.pop(clave, None)
                # Al volver al menu se actualiza el estado de los maestros.
                try:
                    self.barra.mostrar()
                except Exception:
                    pass

        formulario.ventana.bind("<Destroy>", _olvidar, add="+")
        return formulario

    def abrir_datos(self):
        return self.ejecutar_formulario_secundario(FormularioDatos)

    #---------------------------------------------------------
    # Ejecutar
    #---------------------------------------------------------
    def ejecutar(self):
        self.ventana.mainloop()
