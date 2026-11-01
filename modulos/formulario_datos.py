"""Formulario DATOS E IMPORTACIONES.

- Importar: Expediciones, Pedido (ESTAREPP o pedidos), Volumetria y Contenedores HAI.
- Consultar las tablas del Access y Tiendas_Web.
- Calcular el volumen del pedido por tienda-aparte (reglas de Calculo_Tablas_Reparto).
"""

import tkinter as tk
from tkinter import messagebox

from bd.basedatos import BaseDatos
from config.configuracion import Configuracion
from modulos import utilidades as u
from modulos.calculo_volumetria import CalculoVolumetria
from modulos.componente_refresco import BarraRefresco
from modulos.importar_contenedores_hai import ImportarContenedoresHAI
from modulos.importar_expediciones import ImportarExpediciones
from modulos.importar_pedido import ImportarPedido
from modulos.importar_volumetria import ImportarVolumetria
from modulos.version_aplicacion import NOMBRE_VERSION
from modulos.visor_tabla import VisorTabla


IMPORTACIONES = [
    {
        "tipo": "EXPEDICIONES",
        "titulo": "EXPEDICIONES",
        "texto": "Configuración de expediciones por tienda-sección-aparte (CSV ;)",
        "tabla": "EXPEDICIONES",
        "orden": "Tienda, Seccion, Aparte",
        "importador": ImportarExpediciones,
        "color": "#d9ead3",
    },
    {
        "tipo": "PEDIDO",
        "titulo": "PEDIDO / ESTAREPP",
        "texto": "ESTAREPP (.txt) o pedidos (Sku; Id Loc.; Dem.U; Dem.L...) indistintamente",
        "tabla": "PEDIDO",
        "orden": "Tienda, Aparte, SKU",
        "importador": ImportarPedido,
        "color": "#cfe2f3",
    },
    {
        "tipo": "VOLUMETRIA",
        "titulo": "VOLUMETRÍA",
        "texto": "Excel de volumetría del SKU (MOD., CAL., COL., TA., UDS./BULTO, T.CONT.MED.)",
        "tabla": "VOLUMETRIA",
        "orden": "SKUBase",
        "importador": ImportarVolumetria,
        "color": "#fff2cc",
    },
    {
        "tipo": "CONTENEDORES_HAI",
        "titulo": "CONTENEDORES HAI",
        "texto": "Contenedores del HAI (MATRICULA; SKUS; CANTIDAD; TCM; TIENDA; AP...)",
        "tabla": "CONTENEDORES_HAI",
        "orden": "Matricula",
        "importador": ImportarContenedoresHAI,
        "color": "#eadcf8",
    },
]


class FormularioDatos:

    def __init__(self, parent):
        self.parent = parent
        self.ventana = tk.Toplevel(parent)
        self.ventana.title("Datos e importaciones - " + NOMBRE_VERSION)
        self.ventana.geometry("1100x820")
        self.etiquetas_estado = {}
        self.etiquetas_maestros = {}

        contenedor = tk.Frame(self.ventana)
        contenedor.pack(fill="both", expand=True, padx=20, pady=14)

        cabecera = tk.Frame(contenedor)
        cabecera.pack(fill="x", pady=(0, 8))
        tk.Label(
            cabecera, text="DATOS E IMPORTACIONES", font=("Arial", 18, "bold")
        ).pack(side="left")
        tk.Button(
            cabecera, text="Cerrar", width=14, height=2, command=self.ventana.destroy
        ).pack(side="right")

        self.barra = BarraRefresco(contenedor, self.ventana, al_refrescar=self.actualizar_maestros)
        self.barra.pack(fill="x", pady=(0, 10))

        self.crear_importaciones(contenedor)
        self.crear_maestros(contenedor)
        self.crear_volumen(contenedor)

        self.barra.mostrar()
        self.actualizar_estados()
        self.actualizar_maestros()

    #---------------------------------------------------------
    # Ficheros a importar
    #---------------------------------------------------------
    def crear_importaciones(self, contenedor):
        marco = tk.LabelFrame(contenedor, text="Ficheros a importar", padx=10, pady=8)
        marco.pack(fill="x", pady=(0, 10))

        for fila, info in enumerate(IMPORTACIONES):
            tk.Label(
                marco, text=info["titulo"], font=("Arial", 11, "bold"),
                bg=info["color"], width=20, anchor="w", padx=8, pady=6,
            ).grid(row=fila * 2, column=0, rowspan=2, sticky="nsew", pady=4)

            tk.Label(
                marco, text=info["texto"], font=("Arial", 9), fg="#555555", anchor="w"
            ).grid(row=fila * 2, column=1, sticky="w", padx=10)

            estado = tk.Label(marco, text="", font=("Arial", 9, "bold"), anchor="w", justify="left")
            estado.grid(row=fila * 2 + 1, column=1, sticky="w", padx=10)
            self.etiquetas_estado[info["tipo"]] = estado

            tk.Button(
                marco, text="IMPORTAR", width=14, height=2,
                command=lambda i=info: self.importar(i),
            ).grid(row=fila * 2, column=2, rowspan=2, padx=4)
            tk.Button(
                marco, text="VER", width=10, height=2,
                command=lambda i=info: self.ver(i["titulo"], i["tabla"], i["orden"]),
            ).grid(row=fila * 2, column=3, rowspan=2, padx=4)

        marco.grid_columnconfigure(1, weight=1)

    def actualizar_estados(self):
        bd = BaseDatos()
        try:
            for info in IMPORTACIONES:
                datos = bd.obtener_importacion(info["tipo"])
                etiqueta = self.etiquetas_estado[info["tipo"]]
                if not datos or bd.contar_registros(info["tabla"]) == 0:
                    etiqueta.config(text="Sin importar", fg="#a61b1b")
                    continue
                etiqueta.config(
                    text=(
                        datos["nombre"] + " | " + u.formatear_fecha(datos["fecha"])
                        + " | " + u.formatear_numero(datos["registros"]) + " registros"
                        + ("\n" + datos["detalle"] if datos["detalle"] else "")
                    ),
                    fg="#176b2c",
                )
        finally:
            bd.cerrar()

    def importar(self, info):
        importador = info["importador"](parent=self.ventana)
        try:
            resultado = importador.seleccionar_e_importar()
        except Exception as error:
            try:
                self.ventana.config(cursor="")
            except Exception:
                pass
            messagebox.showerror(
                "Importar " + info["titulo"],
                "No se ha podido importar el fichero.\n\n" + str(error),
                parent=self.ventana,
            )
            self.actualizar_estados()
            return
        finally:
            try:
                importador.bd.cerrar()
            except Exception:
                pass

        if resultado is None:
            return

        mensaje = (
            info["titulo"] + " importado correctamente.\n\n"
            + "Registros: " + u.formatear_numero(resultado.get("registros")) + "\n"
            + resultado.get("detalle", "")
        )
        sin_pais = resultado.get("tiendas_sin_pais") or []
        if sin_pais:
            mensaje += (
                "\n\nAVISO: " + str(len(sin_pais)) + " tiendas sin pais en Tiendas_Web: "
                + ", ".join(str(t) for t in sin_pais[:20])
                + (" ..." if len(sin_pais) > 20 else "")
            )
            messagebox.showwarning("Importar " + info["titulo"], mensaje, parent=self.ventana)
        else:
            messagebox.showinfo("Importar " + info["titulo"], mensaje, parent=self.ventana)

        self.actualizar_estados()

    #---------------------------------------------------------
    # Datos maestros (Access + Tiendas_Web)
    #---------------------------------------------------------
    def crear_maestros(self, contenedor):
        marco = tk.LabelFrame(
            contenedor, text="Datos maestros cargados al abrir la aplicación", padx=10, pady=8
        )
        marco.pack(fill="x", pady=(0, 10))

        maestros = [
            (tabla_local, nombre_access, tabla_local)
            for tabla_local, nombre_access in Configuracion().tablas_access().items()
        ]
        maestros.append(("Tiendas_Web", "TIENDAS_WEB", "Tiendas_Web"))

        for fila, (clave, titulo, tabla) in enumerate(maestros):
            tk.Label(marco, text=titulo, font=("Arial", 10, "bold"), anchor="w", width=46).grid(
                row=fila, column=0, sticky="w"
            )
            etiqueta = tk.Label(marco, text="", anchor="w", font=("Arial", 9))
            etiqueta.grid(row=fila, column=1, sticky="w", padx=10)
            self.etiquetas_maestros[clave] = (etiqueta, tabla)
            tk.Button(
                marco, text="VER", width=10,
                command=lambda t=titulo, tb=tabla: self.ver(t, tb, None),
            ).grid(row=fila, column=2, padx=4, pady=2)

        marco.grid_columnconfigure(1, weight=1)

    def actualizar_maestros(self):
        bd = BaseDatos()
        try:
            for clave, (etiqueta, tabla) in self.etiquetas_maestros.items():
                total = bd.contar_registros(tabla)
                datos = bd.obtener_importacion(clave)
                texto = u.formatear_numero(total) + " registros"
                if datos:
                    texto += " | " + u.formatear_fecha(datos["fecha"])
                etiqueta.config(text=texto, fg="#176b2c" if total else "#a61b1b")
        finally:
            bd.cerrar()

    #---------------------------------------------------------
    # Volumen del pedido
    #---------------------------------------------------------
    def crear_volumen(self, contenedor):
        marco = tk.LabelFrame(
            contenedor, text="Volumen del pedido (igual que en Cálculo de Tablas)", padx=10, pady=8
        )
        marco.pack(fill="x")

        tk.Button(
            marco, text="CALCULAR VOLUMEN", width=20, height=2, bg="#d0e0e3",
            command=self.calcular_volumen,
        ).pack(side="left")
        tk.Button(
            marco, text="VER POR TIENDA-APARTE", width=22, height=2,
            command=lambda: self.ver("Volumen por tienda-aparte", "VOLUMEN_TIENDA_APARTE", "Tienda, Aparte"),
        ).pack(side="left", padx=6)
        tk.Button(
            marco, text="VER DETALLE SKU", width=18, height=2,
            command=lambda: self.ver("Volumen por SKU", "VOLUMEN_PEDIDO", "Tienda, Aparte, SKU"),
        ).pack(side="left")
        self.lbl_volumen = tk.Label(marco, text="", font=("Arial", 9, "bold"), justify="left", anchor="w")
        self.lbl_volumen.pack(side="left", padx=12, fill="x", expand=True)

    def calcular_volumen(self):
        bd = BaseDatos()
        try:
            self.ventana.config(cursor="watch")
            self.ventana.update_idletasks()
            resultado = CalculoVolumetria(bd).calcular_pedido()
        except Exception as error:
            messagebox.showerror("Calcular volumen", str(error), parent=self.ventana)
            return
        finally:
            bd.cerrar()
            try:
                self.ventana.config(cursor="")
            except Exception:
                pass

        origenes = ", ".join(
            k + ": " + u.formatear_numero(v) for k, v in sorted(resultado["origenes"].items())
        )
        texto = (
            u.formatear_numero(resultado["tiendas_apartes"]) + " tiendas-aparte | "
            + ("%.3f" % resultado["volumen_m3"]).replace(".", ",") + " m3 | "
            + "Cajas 300: " + u.formatear_numero(resultado["cajas_300"])
            + " | Cajas 400: " + u.formatear_numero(resultado["cajas_400"])
            + "\nLineas por origen: " + origenes
        )
        if resultado["uds_sin_volumetria"]:
            texto += "\nUnidades sin volumetria: " + u.formatear_numero(resultado["uds_sin_volumetria"])
        self.lbl_volumen.config(
            text=texto, fg="#9a6500" if resultado["uds_sin_volumetria"] else "#176b2c"
        )

    #---------------------------------------------------------
    # Visor
    #---------------------------------------------------------
    def ver(self, titulo, tabla, orden):
        VisorTabla(self.ventana, titulo, tabla, orden=orden)
