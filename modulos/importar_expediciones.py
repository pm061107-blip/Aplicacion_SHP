"""Importa el fichero de configuracion de expediciones (CSV ';' exportado del SGA).

Cabecera esperada (el nombre del fichero puede cambiar):
Configuración;Descripción Configuración;SGA Físico;Centro de Distribución;Cadena;
Ruta;Descripción Ruta;Lado;Muelle;Orden de Carga;Orden de Secuencia;
Propiedad de mezcla de mercancía;Tienda;Sección;Aparte;Destino 1..6;Más Destinos;
Tipo de medida palé;Tipo de trasporte;Id de SGA físico ... GCB;
Id de centro de distribución ... GCB;Código de tipo agrupación operativa GCB;
Modo expedición configuración;Modo expedición ruta;Modo expedición TSA
"""

from bd.basedatos import BaseDatos, COLUMNAS_EXPEDICIONES
from modulos import utilidades as u


TIPO_IMPORTACION = "EXPEDICIONES"

# Columna local -> cabeceras normalizadas admitidas
CABECERAS = {
    "Configuracion": ["CONFIGURACION"],
    "DescripcionConfiguracion": ["DESCRIPCIONCONFIGURACION"],
    "SGAFisico": ["SGAFISICO"],
    "CentroDistribucion": ["CENTRODEDISTRIBUCION", "CENTRODISTRIBUCION"],
    "Cadena": ["CADENA"],
    "Ruta": ["RUTA"],
    "DescripcionRuta": ["DESCRIPCIONRUTA"],
    "Lado": ["LADO"],
    "Muelle": ["MUELLE"],
    "OrdenCarga": ["ORDENDECARGA", "ORDENCARGA"],
    "OrdenSecuencia": ["ORDENDESECUENCIA", "ORDENSECUENCIA"],
    "PropiedadMezcla": ["PROPIEDADDEMEZCLADEMERCANCIA", "PROPIEDADMEZCLA"],
    "Tienda": ["TIENDA"],
    "Seccion": ["SECCION"],
    "Aparte": ["APARTE"],
    "Destino1": ["DESTINO1"],
    "Destino2": ["DESTINO2"],
    "Destino3": ["DESTINO3"],
    "Destino4": ["DESTINO4"],
    "Destino5": ["DESTINO5"],
    "Destino6": ["DESTINO6"],
    "MasDestinos": ["MASDESTINOS"],
    "TipoMedidaPale": ["TIPODEMEDIDAPALE", "TIPOMEDIDAPALE"],
    "TipoTransporte": ["TIPODETRASPORTE", "TIPODETRANSPORTE"],
    "IdSGAFisicoGCB": ["IDDESGAFISICODELTIPOAGRUPACIONOPERATIVAGCB"],
    "IdCentroDistribucionGCB": ["IDDECENTRODEDISTRIBUCIONDELTIPOAGRUPACIONOPERATIVAGCB"],
    "CodigoTipoAgrupacionGCB": ["CODIGODETIPOAGRUPACIONOPERATIVAGCB"],
    "ModoExpedicionConfiguracion": ["MODOEXPEDICIONCONFIGURACION"],
    "ModoExpedicionRuta": ["MODOEXPEDICIONRUTA"],
    "ModoExpedicionTSA": ["MODOEXPEDICIONTSA"],
}

COLUMNAS_ENTERAS = {"Tienda", "Seccion", "Aparte"}


class ImportarExpediciones:

    def __init__(self, parent=None, bd=None):
        self.parent = parent
        self.bd = bd if bd is not None else BaseDatos()

    def seleccionar_e_importar(self):
        ruta = u.seleccionar_fichero(
            self.parent,
            "Importar fichero de EXPEDICIONES",
            [("CSV", "*.csv"), ("Todos los ficheros", "*.*")],
        )
        if ruta is None:
            return None
        return self.importar_desde_ruta(ruta)

    def importar_desde_ruta(self, ruta):
        cabeceras, filas = u.leer_csv(ruta)
        mapa = u.mapa_cabeceras(cabeceras)

        if not all(c in mapa for c in ("CONFIGURACION", "TIENDA", "APARTE", "RUTA")):
            raise ValueError(
                "El fichero no parece de EXPEDICIONES.\n\n"
                "Debe tener las columnas Configuración, Ruta, Tienda y Aparte."
            )

        indices = {}
        for columna, candidatos in CABECERAS.items():
            indices[columna] = next((mapa[c] for c in candidatos if c in mapa), None)

        nombres = [c for c, _ in COLUMNAS_EXPEDICIONES]
        registros = []
        descartadas = 0

        for fila in filas:
            registro = []
            for columna in nombres:
                i = indices.get(columna)
                valor = u.texto(fila[i]) if i is not None and i < len(fila) else ""
                if columna in COLUMNAS_ENTERAS:
                    valor = u.entero(valor, None)
                registro.append(valor)
            if registro[nombres.index("Tienda")] in (None, 0):
                descartadas += 1
                continue
            registros.append(tuple(registro))

        if not registros:
            raise ValueError("El fichero de expediciones no tiene lineas validas.")

        self.bd.recrear_tabla("EXPEDICIONES", COLUMNAS_EXPEDICIONES)
        self.bd.insertar_lote("EXPEDICIONES", nombres, registros)
        self.bd.ejecutar(
            "CREATE INDEX IF NOT EXISTS IX_EXPEDICIONES_TA ON EXPEDICIONES (Tienda, Seccion, Aparte)"
        )
        self.bd.guardar()

        configuraciones = self.bd.consultar(
            "SELECT COUNT(DISTINCT Configuracion), COUNT(DISTINCT Tienda) FROM EXPEDICIONES"
        )[0]
        detalle = (
            str(configuraciones[0]) + " configuraciones | "
            + str(configuraciones[1]) + " tiendas"
            + (" | " + str(descartadas) + " lineas sin tienda descartadas" if descartadas else "")
        )
        self.bd.registrar_importacion(
            TIPO_IMPORTACION, ruta, u.nombre_archivo(ruta), u.ahora(), len(registros), detalle
        )
        return {"registros": len(registros), "detalle": detalle}
