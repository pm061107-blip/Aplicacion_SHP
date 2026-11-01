"""Calculo de volumen del pedido, con las mismas reglas que Calculo_Tablas_Reparto.

Volumen unitario (m3/unidad):
1. Volumetria oficial: volumen de la caja T.CONT.MED. ("Caja 580x380x300")
   / UDS./BULTO. Por cada clave se toma la moda. Orden de busqueda:
   EXACTA+UXL -> BASE+UXL -> EXACTA -> BASE.
2. Respaldo desde contenedores (aqui Contenedores HAI): por SKU y tipo de caja
   300/400, UxB = moda de unidades por caja (empate -> mayor); volumen unitario =
   volumen de la caja / UxB; si hay 300 y 400 se usa la mediana.
   En HAI solo se usan matriculas con un unico SKU (las cajas mezcladas no dan
   una capacidad real del SKU).
3. Si no hay ninguna -> SIN VOLUMETRIA.

Volumen de la linea = volumen unitario x unidades.
Cajas = techo(volumen / volumen de la caja) para caja 300 y caja 400.
"""

import math
import re
from collections import Counter, defaultdict
from statistics import median

from bd.basedatos import BaseDatos
from modulos import utilidades as u


VOLUMEN_CAJA_300_M3 = 0.580 * 0.380 * 0.300
VOLUMEN_CAJA_400_M3 = 0.580 * 0.380 * 0.400

TIPOS_CAJA = {
    163: {"alto": 300, "tcm": "Caja 580x380x300", "volumen_m3": VOLUMEN_CAJA_300_M3},
    155: {"alto": 400, "tcm": "Caja 580x380x400", "volumen_m3": VOLUMEN_CAJA_400_M3},
}


def volumen_tcm_m3(texto_tcm):
    """Extrae medidas en mm de textos como 'Caja 580x380x300'."""
    t = str(texto_tcm or "").lower().replace(" ", "")
    m = re.search(r"(\d+(?:[\.,]\d+)?)[x×](\d+(?:[\.,]\d+)?)[x×](\d+(?:[\.,]\d+)?)", t)
    if not m:
        return None
    try:
        largo, ancho, alto = (float(x.replace(",", ".")) / 1000.0 for x in m.groups())
    except Exception:
        return None
    volumen = largo * ancho * alto
    return volumen if volumen > 0 else None


def tipo_contenedor_desde_tcm(tcm):
    """Devuelve 163 (300), 155 (400) o None."""
    t = str(tcm or "").lower().replace(" ", "")
    m = re.search(r"(\d+(?:[\.,]\d+)?)[x×](\d+(?:[\.,]\d+)?)[x×](\d+(?:[\.,]\d+)?)", t)
    if not m:
        return None
    try:
        medidas = tuple(int(round(float(x.replace(",", ".")))) for x in m.groups())
    except Exception:
        return None
    if medidas == (580, 380, 300):
        return 163
    if medidas == (580, 380, 400):
        return 155
    return None


def valor_representativo(valores):
    """Moda del volumen unitario (redondeo 12 decimales; empate -> menor)."""
    redondeados = [round(float(v), 12) for v in valores if v is not None and float(v) > 0]
    if not redondeados:
        return None
    contador = Counter(redondeados)
    return sorted(contador.items(), key=lambda x: (-x[1], x[0]))[0][0]


def moda_unidades(valores):
    valores = [int(v) for v in valores if v is not None and int(v) > 0]
    if not valores:
        return 0
    contador = Counter(valores)
    return max(contador.items(), key=lambda par: (par[1], par[0]))[0]


def cajas(volumen, volumen_caja):
    if volumen <= 0:
        return 0
    return int(math.ceil(max(0.0, volumen - 1e-12) / volumen_caja))


class CalculoVolumetria:

    def __init__(self, bd=None):
        self.bd = bd if bd is not None else BaseDatos()

    #---------------------------------------------------------
    # Indices de la volumetria oficial
    #---------------------------------------------------------
    def cargar_volumetria(self):
        exacta_uxl = defaultdict(list)
        base_uxl = defaultdict(list)
        exacta = defaultdict(list)
        base = defaultdict(list)

        filas = []
        if self.bd.existe_tabla("VOLUMETRIA"):
            filas = self.bd.consultar(
                """
                SELECT SKUCompleto, SKUBase, UxL, TCM, UdsBulto
                FROM VOLUMETRIA
                WHERE IFNULL(UdsBulto, 0) > 0
                """
            )

        for sku, sku_base, uxl, tcm, uds_bulto in filas:
            uds = u.entero(uds_bulto, 0)
            volumen_caja = volumen_tcm_m3(tcm)
            if uds <= 0 or volumen_caja is None:
                continue
            volumen_unidad = volumen_caja / uds
            sku = u.texto(sku)
            sku_base = u.texto(sku_base)
            uxl = u.entero(uxl, 0)
            if sku:
                exacta_uxl[(sku, uxl)].append(volumen_unidad)
                exacta[sku].append(volumen_unidad)
            if sku_base:
                base_uxl[(sku_base, uxl)].append(volumen_unidad)
                base[sku_base].append(volumen_unidad)

        return {
            "exacta_uxl": {k: valor_representativo(v) for k, v in exacta_uxl.items()},
            "base_uxl": {k: valor_representativo(v) for k, v in base_uxl.items()},
            "exacta": {k: valor_representativo(v) for k, v in exacta.items()},
            "base": {k: valor_representativo(v) for k, v in base.items()},
        }

    #---------------------------------------------------------
    # Respaldo: volumetria estimada desde Contenedores HAI
    #---------------------------------------------------------
    def indice_contenedores(self):
        if not self.bd.existe_tabla("CONTENEDORES_HAI"):
            return {}

        filas = self.bd.consultar(
            """
            SELECT H.SKUCompleto, H.Unidades, H.TCM
            FROM CONTENEDORES_HAI H
            JOIN (
                SELECT Matricula
                FROM CONTENEDORES_HAI
                GROUP BY Matricula
                HAVING COUNT(DISTINCT SKUCompleto) = 1
            ) M ON M.Matricula = H.Matricula
            WHERE IFNULL(H.SKUCompleto, '') <> ''
              AND CAST(IFNULL(H.Unidades, 0) AS INTEGER) > 0
            """
        )

        agrupado = defaultdict(lambda: defaultdict(list))
        for sku, unidades, tcm in filas:
            tipo = tipo_contenedor_desde_tcm(tcm)
            uds = u.entero(unidades, 0)
            if tipo is None or uds <= 0:
                continue
            agrupado[u.texto(sku)][tipo].append(uds)

        resultado = {}
        for sku, tipos in agrupado.items():
            volumenes = []
            for tipo in (163, 155):
                uxb = moda_unidades(tipos.get(tipo, []))
                if uxb > 0:
                    volumenes.append(TIPOS_CAJA[tipo]["volumen_m3"] / uxb)
            if volumenes:
                resultado[sku] = float(median(volumenes))
        return resultado

    @staticmethod
    def volumen_unitario(indices, respaldo, sku, sku_base, uxl):
        for origen, valor in (
            ("EXACTA+UXL", indices["exacta_uxl"].get((sku, uxl))),
            ("BASE+UXL", indices["base_uxl"].get((sku_base, uxl))),
            ("EXACTA", indices["exacta"].get(sku)),
            ("BASE", indices["base"].get(sku_base)),
        ):
            if valor is not None and valor > 0:
                return float(valor), origen
        valor = respaldo.get(sku)
        if valor is not None and valor > 0:
            return float(valor), "CALCULADA_CONTENEDORES"
        return None, "SIN VOLUMETRIA"

    #---------------------------------------------------------
    # Calculo del pedido
    #---------------------------------------------------------
    def calcular_pedido(self):
        """Calcula el volumen de cada linea del PEDIDO y lo agrega por tienda-aparte.

        Deja el detalle en VOLUMEN_PEDIDO y el resumen en VOLUMEN_TIENDA_APARTE.
        """
        if self.bd.contar_registros("PEDIDO") <= 0:
            raise RuntimeError("Primero hay que importar un pedido o ESTAREPP.")

        indices = self.cargar_volumetria()
        respaldo = self.indice_contenedores()

        filas = self.bd.consultar(
            """
            SELECT Tienda, Aparte, IFNULL(Pais, ''), Modelo, Calidad, Color,
                   TallaNum, TallaAlfa, Campaña, Año, UxL,
                   SUM(Unidades), SUM(Lotes)
            FROM PEDIDO
            GROUP BY Tienda, Aparte, Pais, Modelo, Calidad, Color,
                     TallaNum, TallaAlfa, Campaña, Año, UxL
            """
        )

        detalle = []
        resumen = {}
        origenes = Counter()

        for (tienda, aparte, pais, modelo, calidad, color, talla_num, talla_alfa,
             campana, anio, uxl, unidades, lotes) in filas:

            unidades = u.entero(unidades, 0)
            lotes = float(lotes or 0)
            talla = u.talla_numerica(talla_num)
            if talla is None:
                talla = u.talla_numerica(talla_alfa)

            if talla is None:
                sku = ""
                volumen_unidad, origen = None, "TALLA NO NUMERICA"
            else:
                sku_base = u.crear_sku_base(modelo, calidad, color, talla)
                sku = u.crear_sku(modelo, calidad, color, talla, campana, anio)
                volumen_unidad, origen = self.volumen_unitario(
                    indices, respaldo, sku, sku_base, u.entero(uxl, 0)
                )

            volumen = (volumen_unidad or 0.0) * unidades
            origenes[origen] += 1
            detalle.append((
                tienda, aparte, pais, sku, u.entero(uxl, 0), unidades, lotes,
                volumen_unidad, volumen, origen,
            ))

            clave = (tienda, aparte)
            r = resumen.setdefault(clave, {
                "Pais": pais, "Lineas": 0, "Unidades": 0, "Lotes": 0.0,
                "VolumenM3": 0.0, "UdsSinVolumetria": 0,
            })
            r["Lineas"] += 1
            r["Unidades"] += unidades
            r["Lotes"] += lotes
            r["VolumenM3"] += volumen
            if volumen_unidad is None:
                r["UdsSinVolumetria"] += unidades

        self.bd.recrear_tabla("VOLUMEN_PEDIDO", [
            ("Tienda", "INTEGER"), ("Aparte", "INTEGER"), ("Pais", "TEXT"),
            ("SKU", "TEXT"), ("UxL", "INTEGER"), ("Unidades", "INTEGER"),
            ("Lotes", "REAL"), ("VolumenUnitarioM3", "REAL"), ("VolumenM3", "REAL"),
            ("OrigenVolumetria", "TEXT"),
        ])
        self.bd.insertar_lote(
            "VOLUMEN_PEDIDO",
            ["Tienda", "Aparte", "Pais", "SKU", "UxL", "Unidades", "Lotes",
             "VolumenUnitarioM3", "VolumenM3", "OrigenVolumetria"],
            detalle,
        )

        columnas_resumen = [
            ("Tienda", "INTEGER"), ("Aparte", "INTEGER"), ("Pais", "TEXT"),
            ("Lineas", "INTEGER"), ("Unidades", "INTEGER"), ("Lotes", "REAL"),
            ("VolumenM3", "REAL"), ("Cajas300", "INTEGER"), ("Cajas400", "INTEGER"),
            ("UdsSinVolumetria", "INTEGER"),
        ]
        self.bd.recrear_tabla("VOLUMEN_TIENDA_APARTE", columnas_resumen)
        self.bd.insertar_lote(
            "VOLUMEN_TIENDA_APARTE",
            [c for c, _ in columnas_resumen],
            [
                (
                    tienda, aparte, r["Pais"], r["Lineas"], r["Unidades"],
                    round(r["Lotes"], 2), round(r["VolumenM3"], 6),
                    cajas(r["VolumenM3"], VOLUMEN_CAJA_300_M3),
                    cajas(r["VolumenM3"], VOLUMEN_CAJA_400_M3),
                    r["UdsSinVolumetria"],
                )
                for (tienda, aparte), r in sorted(resumen.items())
            ],
        )
        self.bd.guardar()

        volumen_total = sum(r["VolumenM3"] for r in resumen.values())
        return {
            "tiendas_apartes": len(resumen),
            "volumen_m3": volumen_total,
            "cajas_300": cajas(volumen_total, VOLUMEN_CAJA_300_M3),
            "cajas_400": cajas(volumen_total, VOLUMEN_CAJA_400_M3),
            "origenes": dict(origenes),
            "uds_sin_volumetria": sum(r["UdsSinVolumetria"] for r in resumen.values()),
        }
