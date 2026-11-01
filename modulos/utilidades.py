"""Funciones comunes de lectura de ficheros y normalizacion."""

import csv
import io
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

from modulos.ventanas_tk import resolver_parent_tk


#---------------------------------------------------------
# Texto y numeros
#---------------------------------------------------------
def texto(valor):
    if valor is None:
        return ""
    return str(valor).strip()


def entero(valor, defecto=0):
    t = texto(valor).replace(",", ".")
    if t == "":
        return defecto
    try:
        return int(round(float(t)))
    except Exception:
        return defecto


def decimal(valor, defecto=0.0):
    t = texto(valor).replace(",", ".")
    if t == "":
        return defecto
    try:
        return float(t)
    except Exception:
        return defecto


def entero_texto(valor, ancho):
    t = texto(valor)
    try:
        t = str(int(float(t.replace(",", "."))))
    except Exception:
        pass
    return t.zfill(ancho)


def normalizar_anio(valor):
    t = texto(valor)
    try:
        return str(int(float(t)))
    except Exception:
        return t


def talla_numerica(valor):
    t = texto(valor).replace(",", ".")
    if t == "":
        return None
    try:
        numero = float(t)
        e = int(numero)
        if numero != e:
            return None
        return e
    except Exception:
        return None


def normalizar_cabecera(valor):
    """Mayusculas, sin tildes ni signos: 'Descripción Configuración' -> DESCRIPCIONCONFIGURACION."""
    t = unicodedata.normalize("NFKD", texto(valor).replace("﻿", ""))
    t = "".join(c for c in t if not unicodedata.combining(c)).upper()
    return "".join(c for c in t if c.isalnum())


#---------------------------------------------------------
# SKU
#---------------------------------------------------------
def crear_sku_base(modelo, calidad, color, talla):
    return "/".join([
        entero_texto(modelo, 4),
        entero_texto(calidad, 3),
        entero_texto(color, 3),
        str(int(talla)),
    ])


def crear_sku(modelo, calidad, color, talla, campana, anio):
    return (
        crear_sku_base(modelo, calidad, color, talla)
        + "/" + texto(campana).upper()
        + "/" + normalizar_anio(anio)
    )


def descomponer_sku(sku):
    """Admite '0366630440640V2026W' (19 caracteres) o '0/3666/304/406/40/V/2026/W'.

    Devuelve Tipo, Modelo, Calidad, Color, Talla, Campana, Anio, Cd (texto).
    """
    t = texto(sku).upper()
    vacio = {
        "Tipo": "", "Modelo": "", "Calidad": "", "Color": "",
        "Talla": "", "Campana": "", "Anio": "", "Cd": "",
    }
    if t == "":
        return vacio

    if "/" in t:
        p = [x.strip() for x in t.split("/")]
        if len(p) >= 7:
            return {
                "Tipo": p[0], "Modelo": p[1].zfill(4), "Calidad": p[2].zfill(3),
                "Color": p[3].zfill(3), "Talla": p[4], "Campana": p[5],
                "Anio": p[6], "Cd": p[7] if len(p) > 7 else "",
            }
        return vacio

    t = t.replace(" ", "")
    if len(t) >= 18:
        return {
            "Tipo": t[0:1], "Modelo": t[1:5], "Calidad": t[5:8],
            "Color": t[8:11], "Talla": t[11:13], "Campana": t[13:14],
            "Anio": t[14:18], "Cd": t[18:19],
        }
    return vacio


#---------------------------------------------------------
# Lectura de CSV (ANSI o UTF-8, separador ; o tabulador)
#---------------------------------------------------------
def leer_csv(ruta):
    with open(ruta, "rb") as fichero:
        contenido = fichero.read()

    if not contenido:
        raise ValueError("El fichero esta vacio.")

    try:
        datos = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        datos = contenido.decode("latin-1")

    primera = datos.split("\n", 1)[0]
    separador = ";"
    if primera.count("\t") > primera.count(";"):
        separador = "\t"

    lector = csv.reader(io.StringIO(datos, newline=""), delimiter=separador)
    try:
        cabeceras = next(lector)
    except StopIteration:
        raise ValueError("El fichero no tiene cabecera.")

    filas = [f for f in lector if f and any(texto(v) for v in f)]
    return cabeceras, filas


def mapa_cabeceras(cabeceras):
    return {normalizar_cabecera(c): i for i, c in enumerate(cabeceras)}


#---------------------------------------------------------
# Dialogo de seleccion de fichero ligado al formulario
#---------------------------------------------------------
def seleccionar_fichero(parent, titulo, tipos):
    ruta = filedialog.askopenfilename(
        parent=resolver_parent_tk(parent),
        title=titulo,
        filetypes=tipos,
    )
    if not ruta:
        return None
    return Path(ruta)


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def nombre_archivo(ruta):
    return os.path.basename(str(ruta).replace("\\", "/"))


def formatear_fecha(valor):
    t = texto(valor)
    if t == "":
        return "-"
    try:
        return datetime.strptime(t, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
    except Exception:
        return t


def formatear_numero(valor):
    try:
        return format(int(valor or 0), ",").replace(",", ".")
    except Exception:
        return str(valor or 0)


def tienda_desde_texto(valor):
    """'752 TAR-NOVA' -> (752, 'TAR-NOVA')."""
    t = texto(valor)
    m = re.match(r"^\s*(\d+)\s*(.*)$", t)
    if not m:
        return 0, t
    return int(m.group(1)), m.group(2).strip()
