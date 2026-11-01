from bd.conexion import ConexionBD


#---------------------------------------------------------
# Estructura de las tablas locales de la aplicacion
#---------------------------------------------------------
COLUMNAS_PEDIDO = [
    ("Origen", "TEXT"),            # ESTAREPP o PEDIDOS_PTE
    ("MarcaComercial", "TEXT"),
    ("Campaña", "TEXT"),
    ("Año", "INTEGER"),
    ("Tienda", "INTEGER"),
    ("Seccion", "INTEGER"),
    ("Aparte", "INTEGER"),
    ("DescTienda", "TEXT"),
    ("Pais", "TEXT"),
    ("Modelo", "INTEGER"),
    ("Calidad", "INTEGER"),
    ("Color", "INTEGER"),
    ("TallaNum", "INTEGER"),
    ("TallaAlfa", "TEXT"),
    ("SKU", "TEXT"),
    ("POC", "TEXT"),
    ("Familia", "INTEGER"),
    ("Subfamilia", "INTEGER"),
    ("Carrusel", "TEXT"),
    ("Estado", "INTEGER"),
    ("Unidades", "INTEGER"),
    ("UoL", "TEXT"),
    ("UxL", "INTEGER"),
    ("Lotes", "REAL"),
]

COLUMNAS_EXPEDICIONES = [
    ("Configuracion", "TEXT"),
    ("DescripcionConfiguracion", "TEXT"),
    ("SGAFisico", "TEXT"),
    ("CentroDistribucion", "TEXT"),
    ("Cadena", "TEXT"),
    ("Ruta", "TEXT"),
    ("DescripcionRuta", "TEXT"),
    ("Lado", "TEXT"),
    ("Muelle", "TEXT"),
    ("OrdenCarga", "TEXT"),
    ("OrdenSecuencia", "TEXT"),
    ("PropiedadMezcla", "TEXT"),
    ("Tienda", "INTEGER"),
    ("Seccion", "INTEGER"),
    ("Aparte", "INTEGER"),
    ("Destino1", "TEXT"),
    ("Destino2", "TEXT"),
    ("Destino3", "TEXT"),
    ("Destino4", "TEXT"),
    ("Destino5", "TEXT"),
    ("Destino6", "TEXT"),
    ("MasDestinos", "TEXT"),
    ("TipoMedidaPale", "TEXT"),
    ("TipoTransporte", "TEXT"),
    ("IdSGAFisicoGCB", "TEXT"),
    ("IdCentroDistribucionGCB", "TEXT"),
    ("CodigoTipoAgrupacionGCB", "TEXT"),
    ("ModoExpedicionConfiguracion", "TEXT"),
    ("ModoExpedicionRuta", "TEXT"),
    ("ModoExpedicionTSA", "TEXT"),
]

COLUMNAS_CONTENEDORES_HAI = [
    ("Matricula", "TEXT"),
    ("Etiqueta", "TEXT"),
    ("EtiquetaTienda", "TEXT"),
    ("SkuOriginal", "TEXT"),
    ("TipoProducto", "TEXT"),
    ("Modelo", "TEXT"),
    ("Calidad", "TEXT"),
    ("Color", "TEXT"),
    ("Talla", "INTEGER"),
    ("Campana", "TEXT"),
    ("Anio", "TEXT"),
    ("CdSku", "TEXT"),
    ("SKUBase", "TEXT"),
    ("SKUCompleto", "TEXT"),
    ("Estado", "TEXT"),
    ("Disponibilidad", "TEXT"),
    ("UxL", "INTEGER"),
    ("EM", "TEXT"),
    ("Unidades", "INTEGER"),
    ("Lotes", "INTEGER"),
    ("Largo", "INTEGER"),
    ("Ancho", "INTEGER"),
    ("Alto", "INTEGER"),
    ("Peso", "INTEGER"),
    ("Posicion", "TEXT"),
    ("RefPosicion", "TEXT"),
    ("FechaEntradaPos", "TEXT"),
    ("OT", "TEXT"),
    ("Ola", "TEXT"),
    ("Cadena", "TEXT"),
    ("TCM", "TEXT"),
    ("CentroDistribucion", "TEXT"),
    ("Ruta", "TEXT"),
    ("Mercado", "TEXT"),
    ("TiendaTexto", "TEXT"),
    ("Tienda", "INTEGER"),
    ("NombreTienda", "TEXT"),
    ("Seccion", "TEXT"),
    ("Aparte", "INTEGER"),
]

COLUMNAS_VOLUMETRIA = [
    ("TipoProducto", "TEXT"),
    ("Modelo", "TEXT"),
    ("Calidad", "TEXT"),
    ("Color", "TEXT"),
    ("Talla", "INTEGER"),
    ("Campana", "TEXT"),
    ("Anio", "TEXT"),
    ("UxL", "INTEGER"),
    ("EstadoMercancia", "TEXT"),
    ("Descripcion", "TEXT"),
    ("UdsBulto", "INTEGER"),
    ("BultosPalet", "INTEGER"),
    ("UXM", "TEXT"),
    ("BloqEnt", "TEXT"),
    ("TCM", "TEXT"),
    ("SKUCompleto", "TEXT"),
    ("SKUBase", "TEXT"),
]


class BaseDatos:

    #---------------------------------------------------------
    # Constructor
    #---------------------------------------------------------
    def __init__(self):

        self.bd = ConexionBD()
        self.conexion = self.bd.conectar()

    #---------------------------------------------------------
    # Crear una tabla
    #---------------------------------------------------------
    def crear_tabla(self, nombre, campos):

        lista = [f'"{campo}" {tipo}' for campo, tipo in campos]
        sql = f"CREATE TABLE IF NOT EXISTS {nombre} (" + ", ".join(lista) + ")"

        self.conexion.execute(sql)
        self.conexion.commit()

    #---------------------------------------------------------
    # Recrear una tabla de trabajo (estructura siempre al dia)
    #---------------------------------------------------------
    def recrear_tabla(self, nombre, campos):

        self.conexion.execute(f"DROP TABLE IF EXISTS {nombre}")
        self.crear_tabla(nombre, campos)

    #---------------------------------------------------------
    # Crear todas las tablas
    #---------------------------------------------------------
    def crear_tablas(self):

        self.crear_tabla(
            "Tiendas_Web",
            [("Tienda", "INTEGER"), ("Nombre", "TEXT"), ("Pais", "TEXT")]
        )
        self.ejecutar(
            "CREATE INDEX IF NOT EXISTS IX_TIENDAS_WEB_TIENDA ON Tiendas_Web (Tienda)"
        )
        self.crear_tabla(
            "TIENDAS_WEB_IMPORTACION",
            [
                ("Id", "INTEGER PRIMARY KEY"),
                ("Ruta", "TEXT NOT NULL"),
                ("NombreArchivo", "TEXT NOT NULL"),
                ("FechaHora", "TEXT NOT NULL"),
                ("Registros", "INTEGER NOT NULL"),
            ]
        )

        # Registro de la ultima importacion de cada origen
        # (ficheros del operador y tablas del Access).
        self.crear_tabla(
            "IMPORTACIONES",
            [
                ("Tipo", "TEXT PRIMARY KEY"),
                ("Ruta", "TEXT"),
                ("NombreArchivo", "TEXT"),
                ("FechaHora", "TEXT"),
                ("Registros", "INTEGER"),
                ("Detalle", "TEXT"),
            ]
        )

        self.crear_tabla("PEDIDO", COLUMNAS_PEDIDO)
        self.crear_tabla("EXPEDICIONES", COLUMNAS_EXPEDICIONES)
        self.crear_tabla("CONTENEDORES_HAI", COLUMNAS_CONTENEDORES_HAI)
        self.crear_tabla("VOLUMETRIA", COLUMNAS_VOLUMETRIA)

    #---------------------------------------------------------
    # Utilidades
    #---------------------------------------------------------
    def existe_tabla(self, nombre):

        cursor = self.conexion.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (nombre,)
        )
        return cursor.fetchone() is not None

    def columnas(self, tabla):

        cursor = self.conexion.execute(f'PRAGMA table_info("{tabla}")')
        return [str(fila[1]) for fila in cursor.fetchall()]

    def vaciar_tabla(self, nombre):

        self.conexion.execute(f"DELETE FROM {nombre}")
        self.conexion.commit()

    def insertar_diccionario(self, tabla, registro):

        columnas = ",".join(f'"{c}"' for c in registro.keys())
        marcadores = ",".join(["?"] * len(registro))
        self.conexion.execute(
            f"INSERT INTO {tabla} ({columnas}) VALUES ({marcadores})",
            tuple(registro.values())
        )

    def insertar_lote(self, tabla, columnas, filas):

        if not filas:
            return
        nombres = ",".join(f'"{c}"' for c in columnas)
        marcadores = ",".join(["?"] * len(columnas))
        self.conexion.executemany(
            f"INSERT INTO {tabla} ({nombres}) VALUES ({marcadores})",
            filas
        )

    def guardar(self):

        self.conexion.commit()

    def contar_registros(self, tabla):

        if not self.existe_tabla(tabla):
            return 0
        cursor = self.conexion.execute(f"SELECT COUNT(*) FROM {tabla}")
        return cursor.fetchone()[0]

    def ejecutar(self, sql, parametros=None):

        if parametros is None:
            self.conexion.execute(sql)
        else:
            self.conexion.execute(sql, parametros)
        self.conexion.commit()

    def consultar(self, sql, parametros=None):

        cursor = self.conexion.cursor()
        if parametros is None:
            cursor.execute(sql)
        else:
            cursor.execute(sql, parametros)
        return cursor.fetchall()

    #---------------------------------------------------------
    # Registro de importaciones
    #---------------------------------------------------------
    def registrar_importacion(self, tipo, ruta, nombre, fecha_hora, registros, detalle=""):

        self.conexion.execute(
            """
            INSERT OR REPLACE INTO IMPORTACIONES
                (Tipo, Ruta, NombreArchivo, FechaHora, Registros, Detalle)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (tipo, str(ruta or ""), str(nombre or ""), fecha_hora, int(registros or 0), detalle or "")
        )
        self.conexion.commit()

    def obtener_importacion(self, tipo):

        filas = self.consultar(
            """
            SELECT Ruta, NombreArchivo, FechaHora, Registros, Detalle
            FROM IMPORTACIONES WHERE Tipo = ?
            """,
            (tipo,)
        )
        if not filas:
            return None
        ruta, nombre, fecha, registros, detalle = filas[0]
        return {
            "ruta": ruta or "",
            "nombre": nombre or "",
            "fecha": fecha or "",
            "registros": int(registros or 0),
            "detalle": detalle or "",
        }

    #---------------------------------------------------------
    # Cerrar
    #---------------------------------------------------------
    def cerrar(self):

        self.bd.cerrar()
