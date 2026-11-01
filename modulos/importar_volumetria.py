"""Importacion de la volumetria del SKU (Excel), igual que en Calculo_Tablas_Reparto.

- Primera hoja del .xlsx; se busca la fila de cabeceras con MOD., CAL., COL. y TA.
- Columnas: PROD., UXL, EST.MERC., DESCRIPCIÓN, UDS./BULTO, BULTOS/PALET, UXM,
  BLOQ.ENT., T.CONT.MED. y opcionales CAMPAÑA y AÑO.
- Solo se importa EST.MERC. 01_UNICA (sin columna = 01_UNICA).
- Las tallas no numericas se omiten.
"""

from pathlib import Path

from openpyxl import load_workbook

from bd.basedatos import BaseDatos, COLUMNAS_VOLUMETRIA
from modulos import utilidades as u


TIPO_IMPORTACION = "VOLUMETRIA"


class ImportarVolumetria:

    PERFIL_VOLUMETRIA_FIJO = "01_UNICA"

    CAMPANA_CABECERAS = ["CAMPAÑA", "CAMPANA", "CAMP.", "CAMP", "CAMPAÑA TIPO", "CAMPANA TIPO"]
    ANIO_CABECERAS = ["AÑO", "ANO", "YEAR"]

    def __init__(self, parent=None, bd=None):
        self.parent = parent
        self.bd = bd if bd is not None else BaseDatos()
        self.ruta = None

    def seleccionar_e_importar(self):
        ruta = u.seleccionar_fichero(
            self.parent,
            "Importar volumetria del SKU",
            [("Excel", "*.xlsx"), ("Todos los ficheros", "*.*")],
        )
        if ruta is None:
            return None
        return self.importar_desde_ruta(ruta)

    def normalizar_estado_mercancia(self, valor):
        perfil = u.texto(valor).upper().replace("-", "_").replace(" ", "_")
        while "__" in perfil:
            perfil = perfil.replace("__", "_")

        compacto = perfil.replace("_", "")
        if compacto in ("UNICA", "1UNICA", "01UNICA"):
            return self.PERFIL_VOLUMETRIA_FIJO

        return perfil

    def buscar_fila_cabeceras(self, hoja):
        for indice, fila in enumerate(hoja.iter_rows(values_only=True), start=1):
            valores = [u.texto(v).upper() for v in fila]
            if "MOD." in valores and "CAL." in valores and "COL." in valores and "TA." in valores:
                return indice, valores
            if indice > 50:
                break
        raise ValueError(
            "No se encontraron cabeceras validas en la volumetria.\n\n"
            "Debe tener las columnas MOD., CAL., COL. y TA."
        )

    @staticmethod
    def buscar_indice_opcional(mapa, candidatos):
        for nombre in candidatos:
            if nombre in mapa:
                return mapa[nombre]
        return None

    def importar_desde_ruta(self, ruta):
        self.ruta = Path(ruta)

        libro = load_workbook(self.ruta, read_only=True, data_only=True)
        try:
            hoja = libro[libro.sheetnames[0]]
            fila_cabecera, cabeceras = self.buscar_fila_cabeceras(hoja)
            mapa = {c: i for i, c in enumerate(cabeceras) if c != ""}

            indice_campana = self.buscar_indice_opcional(mapa, self.CAMPANA_CABECERAS)
            indice_anio = self.buscar_indice_opcional(mapa, self.ANIO_CABECERAS)

            def valor(fila, cabecera):
                i = mapa.get(cabecera)
                if i is None or i >= len(fila):
                    return None
                return fila[i]

            def valor_indice(fila, i):
                if i is None or i >= len(fila):
                    return None
                return fila[i]

            registros = []
            omitidos_talla = 0
            omitidos_otro_perfil = 0

            for fila in hoja.iter_rows(min_row=fila_cabecera + 1, values_only=True):
                if fila is None:
                    continue

                tipo = u.entero_texto(valor(fila, "PROD."), 1)
                modelo = u.entero_texto(valor(fila, "MOD."), 4)
                calidad = u.entero_texto(valor(fila, "CAL."), 3)
                color = u.entero_texto(valor(fila, "COL."), 3)
                talla = u.talla_numerica(valor(fila, "TA."))
                uxl = u.entero(valor(fila, "UXL"), 0)

                if modelo == "0000" and calidad == "000" and color == "000" and uxl == 0:
                    continue
                if talla is None:
                    omitidos_talla += 1
                    continue

                if "EST.MERC." in mapa:
                    perfil = self.normalizar_estado_mercancia(valor(fila, "EST.MERC."))
                else:
                    perfil = self.PERFIL_VOLUMETRIA_FIJO

                if perfil != self.PERFIL_VOLUMETRIA_FIJO:
                    omitidos_otro_perfil += 1
                    continue

                campana = u.texto(valor_indice(fila, indice_campana)).upper()
                anio = u.normalizar_anio(valor_indice(fila, indice_anio))
                sku_base = u.crear_sku_base(modelo, calidad, color, talla)
                sku = (
                    u.crear_sku(modelo, calidad, color, talla, campana, anio)
                    if campana != "" and anio != "" else ""
                )

                registros.append((
                    tipo, modelo, calidad, color, talla, campana, anio, uxl,
                    self.PERFIL_VOLUMETRIA_FIJO,
                    u.texto(valor(fila, "DESCRIPCIÓN")),
                    u.entero(valor(fila, "UDS./BULTO"), 0),
                    u.entero(valor(fila, "BULTOS/PALET"), 0),
                    u.texto(valor(fila, "UXM")),
                    u.texto(valor(fila, "BLOQ.ENT.")),
                    u.texto(valor(fila, "T.CONT.MED.")),
                    sku,
                    sku_base,
                ))
        finally:
            libro.close()

        if not registros:
            raise ValueError("La volumetria no tiene lineas validas 01_UNICA.")

        nombres = [c for c, _ in COLUMNAS_VOLUMETRIA]
        self.bd.recrear_tabla("VOLUMETRIA", COLUMNAS_VOLUMETRIA)
        self.bd.insertar_lote("VOLUMETRIA", nombres, registros)
        self.bd.ejecutar("CREATE INDEX IF NOT EXISTS IX_VOL_SKU ON VOLUMETRIA (SKUCompleto)")
        self.bd.ejecutar("CREATE INDEX IF NOT EXISTS IX_VOL_BASE ON VOLUMETRIA (SKUBase)")
        self.bd.guardar()

        detalle = "Perfil 01_UNICA"
        if omitidos_otro_perfil:
            detalle += " | " + u.formatear_numero(omitidos_otro_perfil) + " de otro perfil omitidos"
        if omitidos_talla:
            detalle += " | " + u.formatear_numero(omitidos_talla) + " tallas no numericas omitidas"
        if indice_campana is None or indice_anio is None:
            detalle += " | sin Campaña/Año: cruce por SKU base"

        self.bd.registrar_importacion(
            TIPO_IMPORTACION, self.ruta, u.nombre_archivo(self.ruta), u.ahora(),
            len(registros), detalle,
        )
        return {"registros": len(registros), "detalle": detalle}
