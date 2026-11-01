"""Barra comun a todos los formularios: estado de Access + Tiendas_Web y boton REFRESCAR DATOS."""

import tkinter as tk
from tkinter import messagebox

from modulos import utilidades as u
from modulos.sincronizador import Sincronizador


COLOR_OK = "#176b2c"
COLOR_AVISO = "#9a6500"
COLOR_ERROR = "#a61b1b"


def texto_estado_tiendas_web(resultado):
    if resultado.get("exito") is True:
        return (
            "TIENDAS_WEB actualizado: " + u.formatear_fecha(resultado.get("fecha_hora"))
            + " | Tiendas: " + u.formatear_numero(resultado.get("registros")),
            COLOR_OK,
        )
    if resultado.get("exito") is None and resultado.get("hay_copia_local"):
        return (
            "TIENDAS_WEB cargado: " + u.formatear_fecha(resultado.get("fecha_ultima"))
            + " | Tiendas: " + u.formatear_numero(resultado.get("registros_locales")),
            COLOR_OK,
        )
    if resultado.get("hay_copia_local"):
        return (
            "TIENDAS_WEB: usando copia local | Ultima carga: "
            + u.formatear_fecha(resultado.get("fecha_ultima"))
            + " | Tiendas: " + u.formatear_numero(resultado.get("registros_locales")),
            COLOR_AVISO,
        )
    return ("TIENDAS_WEB NO DISPONIBLE: no hay copia local.", COLOR_ERROR)


def texto_estado_access(resultado):
    estado_local = resultado.get("estado_local") or {}
    partes = []
    for tabla_local, info in estado_local.items():
        partes.append(
            info.get("tabla_access", tabla_local) + ": "
            + u.formatear_numero(info.get("registros_locales"))
        )
    resumen = " | ".join(partes)

    if resultado.get("exito") is True:
        return (
            "ACCESS actualizado: " + u.formatear_fecha(resultado.get("fecha_hora")) + "\n" + resumen,
            COLOR_OK,
        )
    fechas = [i.get("fecha_ultima") for i in estado_local.values() if i.get("fecha_ultima")]
    if resultado.get("exito") is None and resultado.get("hay_copia_local"):
        return (
            "ACCESS cargado: " + u.formatear_fecha(min(fechas) if fechas else "") + "\n" + resumen,
            COLOR_OK,
        )
    if resultado.get("hay_copia_local"):
        return (
            "ACCESS: usando copia local | Ultima carga: "
            + u.formatear_fecha(min(fechas) if fechas else "") + "\n" + resumen,
            COLOR_AVISO,
        )
    return ("ACCESS NO DISPONIBLE: faltan tablas sin copia local.\n" + resumen, COLOR_ERROR)


def estado_actual():
    """Estado guardado (sin leer la red)."""
    sincronizador = Sincronizador()
    try:
        tw = sincronizador.obtener_estado_tiendas_web()
        tiendas = {
            "exito": None,
            "fecha_hora": tw.get("fecha_ultima", ""),
            "registros": tw.get("registros_locales", 0),
            **tw,
        }
        access = {"exito": None, **sincronizador._estado_resumen_access()}
        return tiendas, access
    finally:
        sincronizador.cerrar()


def mensaje_errores(resultado_tiendas, resultado_access):
    lineas = []
    if resultado_tiendas and resultado_tiendas.get("exito") is False:
        lineas.append("TIENDAS_WEB no se ha podido actualizar:")
        lineas.append(str(resultado_tiendas.get("descripcion_error", "")))
        lineas.append(
            "Se usa la copia local." if resultado_tiendas.get("hay_copia_local")
            else "No hay copia local: no se podra saber el pais de las tiendas."
        )
        lineas.append("")
    if resultado_access and resultado_access.get("exito") is False:
        lineas.append("ACCESS (Base de datos maestro) no se ha podido actualizar:")
        lineas.append(str(resultado_access.get("descripcion_error", "")))
        if resultado_access.get("ruta"):
            lineas.append(str(resultado_access.get("ruta")))
        lineas.append(
            "Se usa la ultima copia local." if resultado_access.get("hay_copia_local")
            else "Falta alguna tabla sin copia local."
        )
    return "\n".join(lineas).strip()


class BarraRefresco:

    def __init__(self, parent, ventana, al_refrescar=None):
        self.ventana = ventana
        self.al_refrescar = al_refrescar

        self.marco = tk.LabelFrame(
            parent, text="Datos maestros (Access + Tiendas_Web)", padx=10, pady=6
        )

        textos = tk.Frame(self.marco)
        textos.pack(side="left", fill="x", expand=True, padx=(0, 12))

        self.lbl_tiendas = tk.Label(
            textos, text="Comprobando Tiendas_Web...", font=("Arial", 9, "bold"),
            anchor="w", justify="left",
        )
        self.lbl_tiendas.pack(fill="x")

        self.lbl_access = tk.Label(
            textos, text="Comprobando Access...", font=("Arial", 9, "bold"),
            anchor="w", justify="left",
        )
        self.lbl_access.pack(fill="x")

        self.boton = tk.Button(
            self.marco, text="REFRESCAR DATOS", width=22, height=2,
            bg="#fde9d9", command=self.refrescar,
        )
        self.boton.pack(side="right")

    def pack(self, **kwargs):
        self.marco.pack(**kwargs)
        return self

    def mostrar(self, resultado_tiendas=None, resultado_access=None):
        if resultado_tiendas is None or resultado_access is None:
            try:
                local_tiendas, local_access = estado_actual()
            except Exception as error:
                local_tiendas = {"exito": False, "descripcion_error": str(error)}
                local_access = {"exito": False, "descripcion_error": str(error)}
            resultado_tiendas = resultado_tiendas or local_tiendas
            resultado_access = resultado_access or local_access

        texto, color = texto_estado_tiendas_web(resultado_tiendas)
        self.lbl_tiendas.config(text=texto, fg=color)
        texto, color = texto_estado_access(resultado_access)
        self.lbl_access.config(text=texto, fg=color)

    def refrescar(self):
        texto_original = self.boton.cget("text")
        self.boton.config(state="disabled", text="REFRESCANDO...")
        try:
            self.ventana.config(cursor="watch")
            self.ventana.update_idletasks()
        except Exception:
            pass

        sincronizador = Sincronizador()
        try:
            resultado_tiendas, resultado_access = sincronizador.refrescar_todo()
        except Exception as error:
            resultado_tiendas = {"exito": False, "descripcion_error": str(error)}
            resultado_access = {"exito": False, "descripcion_error": str(error)}
        finally:
            sincronizador.cerrar()
            try:
                self.ventana.config(cursor="")
            except Exception:
                pass
            self.boton.config(state="normal", text=texto_original)

        self.mostrar(resultado_tiendas, resultado_access)

        mensaje = mensaje_errores(resultado_tiendas, resultado_access)
        if mensaje:
            messagebox.showwarning("Refrescar datos", mensaje, parent=self.ventana)
        else:
            messagebox.showinfo(
                "Refrescar datos",
                "Access y Tiendas_Web actualizados correctamente.",
                parent=self.ventana,
            )

        if self.al_refrescar is not None:
            try:
                self.al_refrescar()
            except Exception:
                pass
