"""Importa el fichero de Contenedores HAI (CSV ';' ANSI).

Cabecera esperada (el nombre del fichero puede cambiar):
MATRICULA;ETIQUETA;ET. DE TIENDA;SKUS;ESTADO;DISPONIBILIDAD;UXL;EM;CANTIDAD;LOTES;
LARGO;ANCHO;ALTO;PESO;POSICIÓN;REF POSICIÓN;F. ENTRADA POS.;OT;OLA;CADENA;TCM;CD;
RUTA;MERCADO;TIENDA;SECC;AP

Una matricula puede llevar varias lineas (una por SKU).
"""

from bd.basedatos import BaseDatos, COLUMNAS_CONTENEDORES_HAI
from modulos import utilidades as u


TIPO_IMPORTACION = "CONTENEDORES_HAI"


class ImportarContenedoresHAI:

    def __init__(self, parent=None, bd=None):
        self.parent = parent
        self.bd = bd if bd is not None else BaseDatos()

    def seleccionar_e_importar(self):
        ruta = u.seleccionar_fichero(
            self.parent,
            "Importar fichero de CONTENEDORES HAI",
            [("CSV", "*.csv"), ("Todos los ficheros", "*.*")],
        )
        if ruta is None:
            return None
        return self.importar_desde_ruta(ruta)

    def importar_desde_ruta(self, ruta):
        cabeceras, filas = u.leer_csv(ruta)
        mapa = u.mapa_cabeceras(cabeceras)

        if "MATRICULA" not in mapa or "SKUS" not in mapa:
            raise ValueError(
                "El fichero no parece de CONTENEDORES HAI.\n\n"
                "Debe tener las columnas MATRICULA y SKUS."
            )

        def v(fila, *nombres):
            for nombre in nombres:
                i = mapa.get(nombre)
                if i is not None and i < len(fila):
                    return u.texto(fila[i])
            return ""

        nombres = [c for c, _ in COLUMNAS_CONTENEDORES_HAI]
        registros = []

        for fila in filas:
            matricula = v(fila, "MATRICULA")
            if matricula == "":
                continue

            sku_original = v(fila, "SKUS")
            partes = u.descomponer_sku(sku_original)
            talla = u.talla_numerica(partes["Talla"])

            sku_base = ""
            sku_completo = ""
            if partes["Modelo"] and talla is not None:
                sku_base = u.crear_sku_base(partes["Modelo"], partes["Calidad"], partes["Color"], talla)
                sku_completo = u.crear_sku(
                    partes["Modelo"], partes["Calidad"], partes["Color"], talla,
                    partes["Campana"], partes["Anio"],
                )

            tienda_texto = v(fila, "TIENDA")
            tienda, nombre_tienda = u.tienda_desde_texto(tienda_texto)

            registro = {
                "Matricula": matricula,
                "Etiqueta": v(fila, "ETIQUETA"),
                "EtiquetaTienda": v(fila, "ETDETIENDA"),
                "SkuOriginal": sku_original,
                "TipoProducto": partes["Tipo"],
                "Modelo": partes["Modelo"],
                "Calidad": partes["Calidad"],
                "Color": partes["Color"],
                "Talla": talla,
                "Campana": partes["Campana"],
                "Anio": partes["Anio"],
                "CdSku": partes["Cd"],
                "SKUBase": sku_base,
                "SKUCompleto": sku_completo,
                "Estado": v(fila, "ESTADO"),
                "Disponibilidad": v(fila, "DISPONIBILIDAD"),
                "UxL": u.entero(v(fila, "UXL"), 0),
                "EM": v(fila, "EM"),
                "Unidades": u.entero(v(fila, "CANTIDAD"), 0),
                "Lotes": u.entero(v(fila, "LOTES"), 0),
                "Largo": u.entero(v(fila, "LARGO"), 0),
                "Ancho": u.entero(v(fila, "ANCHO"), 0),
                "Alto": u.entero(v(fila, "ALTO"), 0),
                "Peso": u.entero(v(fila, "PESO"), 0),
                "Posicion": v(fila, "POSICION"),
                "RefPosicion": v(fila, "REFPOSICION"),
                "FechaEntradaPos": v(fila, "FENTRADAPOS"),
                "OT": v(fila, "OT"),
                "Ola": v(fila, "OLA"),
                "Cadena": v(fila, "CADENA"),
                "TCM": v(fila, "TCM"),
                "CentroDistribucion": v(fila, "CD"),
                "Ruta": v(fila, "RUTA"),
                "Mercado": v(fila, "MERCADO"),
                "TiendaTexto": tienda_texto,
                "Tienda": tienda,
                "NombreTienda": nombre_tienda,
                "Seccion": v(fila, "SECC", "SECCION"),
                "Aparte": u.entero(v(fila, "AP", "APARTE"), 0),
            }
            registros.append(tuple(registro[c] for c in nombres))

        if not registros:
            raise ValueError("El fichero de contenedores HAI no tiene lineas validas.")

        self.bd.recrear_tabla("CONTENEDORES_HAI", COLUMNAS_CONTENEDORES_HAI)
        self.bd.insertar_lote("CONTENEDORES_HAI", nombres, registros)
        self.bd.ejecutar("CREATE INDEX IF NOT EXISTS IX_HAI_MATRICULA ON CONTENEDORES_HAI (Matricula)")
        self.bd.ejecutar("CREATE INDEX IF NOT EXISTS IX_HAI_SKU ON CONTENEDORES_HAI (SKUCompleto)")
        self.bd.ejecutar("CREATE INDEX IF NOT EXISTS IX_HAI_TIENDA ON CONTENEDORES_HAI (Tienda, Aparte)")
        self.bd.guardar()

        matriculas, tiendas = self.bd.consultar(
            "SELECT COUNT(DISTINCT Matricula), COUNT(DISTINCT Tienda) FROM CONTENEDORES_HAI"
        )[0]
        detalle = (
            u.formatear_numero(matriculas) + " matriculas | "
            + u.formatear_numero(tiendas) + " tiendas"
        )
        self.bd.registrar_importacion(
            TIPO_IMPORTACION, ruta, u.nombre_archivo(ruta), u.ahora(), len(registros), detalle
        )
        return {"registros": len(registros), "detalle": detalle}
