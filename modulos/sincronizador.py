import csv
import io
import os
import sqlite3
import time
import unicodedata
from datetime import date, datetime, time as dtime
from decimal import Decimal

from bd.basedatos import BaseDatos
from config.configuracion import Configuracion


def normalizar_nombre(texto):
    """Minusculas, sin tildes ni espacios: para localizar tablas en Access."""
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return "".join(c for c in texto.lower() if c.isalnum() or c == "_")


class Sincronizador:

    def __init__(self, config=None, bd=None):
        self.config = config if config is not None else Configuracion()
        self.bd = bd if bd is not None else BaseDatos()

    # ---------------------------------------------------------
    # Estado persistente de Tiendas_Web
    # ---------------------------------------------------------
    def _asegurar_tabla_importacion_tiendas_web(self):
        self.bd.conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS TIENDAS_WEB_IMPORTACION (
                Id INTEGER PRIMARY KEY,
                Ruta TEXT NOT NULL,
                NombreArchivo TEXT NOT NULL,
                FechaHora TEXT NOT NULL,
                Registros INTEGER NOT NULL
            )
            """
        )
        self.bd.conexion.commit()

    def _nombre_archivo(self, ruta):
        return os.path.basename(str(ruta).replace("\\", "/"))

    def obtener_estado_tiendas_web(self):
        self._asegurar_tabla_importacion_tiendas_web()

        try:
            registros_locales = int(self.bd.contar_registros("Tiendas_Web") or 0)
        except Exception:
            registros_locales = 0

        metadata = None
        try:
            cursor = self.bd.conexion.cursor()
            cursor.execute(
                """
                SELECT Ruta, NombreArchivo, FechaHora, Registros
                FROM TIENDAS_WEB_IMPORTACION
                WHERE Id = 1
                """
            )
            metadata = cursor.fetchone()
        except Exception:
            metadata = None

        if metadata is None:
            return {
                "hay_copia_local": registros_locales > 0,
                "registros_locales": registros_locales,
                "ruta_ultima": "",
                "nombre_ultima": "",
                "fecha_ultima": "",
                "registros_ultima": 0,
            }

        return {
            "hay_copia_local": registros_locales > 0,
            "registros_locales": registros_locales,
            "ruta_ultima": str(metadata[0] or ""),
            "nombre_ultima": str(metadata[1] or ""),
            "fecha_ultima": str(metadata[2] or ""),
            "registros_ultima": int(metadata[3] or 0),
        }

    # ---------------------------------------------------------
    # Lectura y validacion completa de Tiendas_Web
    # ---------------------------------------------------------
    @staticmethod
    def _normalizar_cabecera(valor):
        texto = str(valor or "").replace("\ufeff", "").strip().upper()
        return "".join(caracter for caracter in texto if caracter.isalnum())

    def _resolver_indices_tiendas_web(self, cabeceras):
        normalizadas = [self._normalizar_cabecera(valor) for valor in cabeceras]

        def buscar(candidatos):
            for candidato in candidatos:
                if candidato in normalizadas:
                    return normalizadas.index(candidato)
            return None

        indice_tienda = buscar(("TIEND9", "TIENDA", "CODTIENDA"))
        indice_nombre = buscar(("NOMBRE", "NOMBRETIENDA", "DESTIENDA"))
        indice_pais = buscar(("ORINOM", "PAIS", "NOMBREPAIS"))

        if None not in (indice_tienda, indice_nombre, indice_pais):
            return indice_tienda, indice_nombre, indice_pais

        # Compatibilidad con el formato historico usado por la aplicacion.
        if len(cabeceras) >= 5:
            return 0, 1, 4

        raise ValueError(
            "El fichero no contiene las columnas necesarias de Tiendas_Web. "
            "Se esperaban Tienda, Nombre y Pais."
        )

    @staticmethod
    def _convertir_tienda(valor, numero_linea):
        texto = str(valor or "").strip()
        if texto == "":
            raise ValueError(
                "La tienda esta vacia en la linea " + str(numero_linea) + "."
            )

        try:
            tienda = int(texto)
        except Exception as error:
            raise ValueError(
                "La tienda '" + texto + "' no es un entero valido en la linea "
                + str(numero_linea) + "."
            ) from error

        if tienda <= 0:
            raise ValueError(
                "La tienda debe ser mayor que cero en la linea "
                + str(numero_linea) + "."
            )

        return tienda

    def _leer_tiendas_web(self, ruta):
        # Primero se copia todo el fichero a memoria. La tabla SQLite no se toca
        # hasta que la lectura y la validacion han finalizado correctamente.
        with open(ruta, "rb") as fichero:
            contenido = fichero.read()

        if not contenido:
            raise ValueError("El fichero TIENDAS_WEB.TXT esta vacio.")

        texto = contenido.decode("latin-1")
        lector = csv.reader(io.StringIO(texto, newline=""), delimiter="\t")

        try:
            cabeceras = next(lector)
        except StopIteration as error:
            raise ValueError("El fichero TIENDAS_WEB.TXT no contiene cabecera.") from error

        indice_tienda, indice_nombre, indice_pais = (
            self._resolver_indices_tiendas_web(cabeceras)
        )
        indice_maximo = max(indice_tienda, indice_nombre, indice_pais)

        registros = []
        errores = []

        for numero_linea, fila in enumerate(lector, start=2):
            if not fila or all(str(valor or "").strip() == "" for valor in fila):
                continue

            if len(fila) <= indice_maximo:
                errores.append(
                    "Linea " + str(numero_linea)
                    + ": numero insuficiente de columnas."
                )
                if len(errores) >= 20:
                    break
                continue

            try:
                tienda = self._convertir_tienda(
                    fila[indice_tienda],
                    numero_linea,
                )
                nombre = str(fila[indice_nombre] or "").strip()
                pais = str(fila[indice_pais] or "").strip()
                registros.append((tienda, nombre, pais))
            except ValueError as error:
                errores.append(str(error))
                if len(errores) >= 20:
                    break

        if errores:
            mensaje = "No se ha importado Tiendas_Web por errores de formato:\n\n"
            mensaje += "\n".join(errores)
            if len(errores) >= 20:
                mensaje += "\n\nSe muestran como maximo los primeros 20 errores."
            raise ValueError(mensaje)

        if not registros:
            raise ValueError(
                "El fichero TIENDAS_WEB.TXT no contiene ningun registro valido."
            )

        return registros

    def _leer_tiendas_web_con_reintentos(self, ruta, intentos=3):
        ultimo_error = None

        for intento in range(1, max(1, int(intentos)) + 1):
            try:
                return self._leer_tiendas_web(ruta)
            except FileNotFoundError:
                raise
            except (PermissionError, OSError) as error:
                ultimo_error = error
                if intento < intentos:
                    time.sleep(0.25 * intento)

        if ultimo_error is not None:
            raise ultimo_error

        raise OSError("No se pudo leer TIENDAS_WEB.TXT.")

    # ---------------------------------------------------------
    # Sustitucion atomica de Tiendas_Web
    # ---------------------------------------------------------
    def _reemplazar_tiendas_web(self, ruta, registros, fecha_hora):
        self._asegurar_tabla_importacion_tiendas_web()

        conexion = self.bd.conexion
        cursor = conexion.cursor()

        try:
            cursor.execute("PRAGMA busy_timeout = 5000")
            cursor.execute("BEGIN IMMEDIATE")

            cursor.execute("DROP TABLE IF EXISTS TIENDAS_WEB_NUEVA")
            cursor.execute(
                """
                CREATE TEMP TABLE TIENDAS_WEB_NUEVA (
                    Tienda INTEGER,
                    Nombre TEXT,
                    Pais TEXT
                )
                """
            )
            cursor.executemany(
                """
                INSERT INTO TIENDAS_WEB_NUEVA (Tienda, Nombre, Pais)
                VALUES (?, ?, ?)
                """,
                registros,
            )

            cursor.execute("SELECT COUNT(*) FROM TIENDAS_WEB_NUEVA")
            total_temporal = int(cursor.fetchone()[0] or 0)
            if total_temporal != len(registros):
                raise RuntimeError(
                    "La tabla temporal no contiene todos los registros leidos."
                )

            cursor.execute("DELETE FROM Tiendas_Web")
            cursor.execute(
                """
                INSERT INTO Tiendas_Web (Tienda, Nombre, Pais)
                SELECT Tienda, Nombre, Pais
                FROM TIENDAS_WEB_NUEVA
                """
            )

            cursor.execute("SELECT COUNT(*) FROM Tiendas_Web")
            total_final = int(cursor.fetchone()[0] or 0)
            if total_final != len(registros):
                raise RuntimeError(
                    "La sustitucion de Tiendas_Web no ha quedado completa."
                )

            cursor.execute("DELETE FROM TIENDAS_WEB_IMPORTACION WHERE Id = 1")
            cursor.execute(
                """
                INSERT INTO TIENDAS_WEB_IMPORTACION
                    (Id, Ruta, NombreArchivo, FechaHora, Registros)
                VALUES
                    (1, ?, ?, ?, ?)
                """,
                (
                    str(ruta),
                    self._nombre_archivo(ruta),
                    fecha_hora,
                    total_final,
                ),
            )

            cursor.execute("DROP TABLE IF EXISTS TIENDAS_WEB_NUEVA")
            conexion.commit()
            return total_final

        except Exception:
            conexion.rollback()
            raise

    # ---------------------------------------------------------
    # Resultado y mensajes de error
    # ---------------------------------------------------------
    @staticmethod
    def _clasificar_error(error):
        if isinstance(error, PermissionError):
            return (
                "PERMISO",
                "Windows ha denegado el acceso al fichero. Puede estar "
                "bloqueado temporalmente o la sesion de red puede no tener "
                "permiso de lectura.",
            )
        if isinstance(error, FileNotFoundError):
            return (
                "NO_ENCONTRADO",
                "No se encuentra el fichero o la unidad de red no esta disponible.",
            )
        if isinstance(error, ValueError):
            return ("FORMATO", str(error))
        if isinstance(error, sqlite3.Error):
            return (
                "BASE_DATOS",
                "No se pudo actualizar la copia local de Tiendas_Web: " + str(error),
            )
        if isinstance(error, OSError):
            return (
                "RED_O_SISTEMA",
                "No se pudo leer el fichero por un problema de red o del sistema: "
                + str(error),
            )
        return ("DESCONOCIDO", str(error))

    def _resultado_error(self, ruta, error):
        estado = self.obtener_estado_tiendas_web()
        tipo_error, descripcion = self._clasificar_error(error)

        return {
            "exito": False,
            "ruta": str(ruta or ""),
            "nombre_archivo": self._nombre_archivo(ruta) if ruta else "",
            "fecha_hora": "",
            "registros": 0,
            "tipo_error": tipo_error,
            "descripcion_error": descripcion,
            "error_tecnico": str(error),
            **estado,
        }

    # ---------------------------------------------------------
    # Sincronizar Tiendas_Web sin destruir la copia anterior
    # ---------------------------------------------------------
    def sincronizar_tiendas_web(self, intentos=3):
        ruta = self.config.tiendas_web()

        print()
        print("========================================")
        print(" SINCRONIZANDO TIENDAS_WEB")
        print("========================================")

        if not str(ruta or "").strip():
            error = FileNotFoundError(
                "La ruta de Tiendas_Web no esta configurada."
            )
            resultado = self._resultado_error(ruta, error)
            print("ERROR - " + resultado["descripcion_error"])
            return resultado

        try:
            registros = self._leer_tiendas_web_con_reintentos(
                ruta,
                intentos=intentos,
            )
            fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            total = self._reemplazar_tiendas_web(
                ruta,
                registros,
                fecha_hora,
            )

            print("OK - " + str(total) + " registros importados")
            print("========================================")

            return {
                "exito": True,
                "ruta": str(ruta),
                "nombre_archivo": self._nombre_archivo(ruta),
                "fecha_hora": fecha_hora,
                "registros": total,
                "tipo_error": "",
                "descripcion_error": "",
                "error_tecnico": "",
                "hay_copia_local": total > 0,
                "registros_locales": total,
                "ruta_ultima": str(ruta),
                "nombre_ultima": self._nombre_archivo(ruta),
                "fecha_ultima": fecha_hora,
                "registros_ultima": total,
            }

        except Exception as error:
            resultado = self._resultado_error(ruta, error)

            print("ERROR - No se pudo actualizar Tiendas_Web")
            print(resultado["descripcion_error"])
            if resultado["hay_copia_local"]:
                print(
                    "Se conserva la copia local con "
                    + str(resultado["registros_locales"])
                    + " registros."
                )
            else:
                print("No existe una copia local disponible.")
            print("========================================")

            return resultado

    # ---------------------------------------------------------
    # Sincronizar las tablas del Access maestro
    # ---------------------------------------------------------
    @staticmethod
    def _valor_sqlite(valor):
        if valor is None:
            return None
        if isinstance(valor, bool):
            return int(valor)
        if isinstance(valor, (int, float, str)):
            return valor
        if isinstance(valor, Decimal):
            return float(valor)
        if isinstance(valor, datetime):
            return valor.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(valor, (date, dtime)):
            return valor.isoformat()
        if isinstance(valor, (bytes, bytearray, memoryview)):
            return None
        return str(valor)

    @staticmethod
    def _conectar_access(ruta):
        import pyodbc

        cadena = (
            r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
            f"DBQ={ruta};"
        )
        return pyodbc.connect(cadena)

    @staticmethod
    def _resolver_tabla_access(conexion, nombre_configurado):
        """Devuelve el nombre real de la tabla aunque cambien tildes o mayusculas."""
        buscado = normalizar_nombre(nombre_configurado)
        try:
            for fila in conexion.cursor().tables(tableType="TABLE"):
                if normalizar_nombre(fila.table_name) == buscado:
                    return fila.table_name
        except Exception:
            pass
        return nombre_configurado

    def _reemplazar_tabla_local(self, tabla_local, columnas, filas):
        """Sustitucion atomica: si algo falla se conserva la copia anterior."""
        conexion = self.bd.conexion
        cursor = conexion.cursor()
        temporal = tabla_local + "__NUEVA"
        definicion = ", ".join('"' + c.replace('"', "") + '"' for c in columnas)
        marcadores = ", ".join(["?"] * len(columnas))

        try:
            cursor.execute("PRAGMA busy_timeout = 5000")
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute(f"DROP TABLE IF EXISTS {temporal}")
            cursor.execute(f"CREATE TABLE {temporal} ({definicion})")
            cursor.executemany(f"INSERT INTO {temporal} VALUES ({marcadores})", filas)
            cursor.execute(f"DROP TABLE IF EXISTS {tabla_local}")
            cursor.execute(f"ALTER TABLE {temporal} RENAME TO {tabla_local}")
            conexion.commit()
        except Exception:
            conexion.rollback()
            raise

    def obtener_estado_access(self):
        estado = {}
        for tabla_local, tabla_access in self.config.tablas_access().items():
            info = self.bd.obtener_importacion(tabla_local) or {}
            estado[tabla_local] = {
                "tabla_access": tabla_access,
                "registros_locales": self.bd.contar_registros(tabla_local),
                "fecha_ultima": info.get("fecha", ""),
            }
        return estado

    def sincronizar_access(self):
        ruta = self.config.access_maestro()
        tablas = self.config.tablas_access()

        print()
        print("========================================")
        print(" SINCRONIZANDO ACCESS MAESTRO")
        print("========================================")

        resultado = {
            "exito": False,
            "ruta": str(ruta or ""),
            "fecha_hora": "",
            "tablas": {},
            "descripcion_error": "",
        }

        conexion = None
        try:
            if not str(ruta or "").strip():
                raise FileNotFoundError("La ruta del Access maestro no esta configurada.")
            if not os.path.exists(ruta):
                raise FileNotFoundError("No se encuentra el fichero: " + str(ruta))
            conexion = self._conectar_access(ruta)
        except Exception as error:
            if isinstance(error, ImportError):
                descripcion = "Falta la libreria pyodbc (pip install pyodbc)."
            else:
                descripcion = self._clasificar_error(error)[1]
            resultado["descripcion_error"] = descripcion
            for tabla_local, tabla_access in tablas.items():
                resultado["tablas"][tabla_local] = {
                    "exito": False,
                    "tabla_access": tabla_access,
                    "registros": 0,
                    "error": descripcion,
                }
            print("ERROR - " + descripcion)
            resultado.update(self._estado_resumen_access())
            return resultado

        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        resultado["fecha_hora"] = fecha_hora
        errores = []

        try:
            for tabla_local, tabla_configurada in tablas.items():
                try:
                    tabla_real = self._resolver_tabla_access(conexion, tabla_configurada)
                    cursor = conexion.cursor()
                    cursor.execute("SELECT * FROM [" + tabla_real + "]")
                    columnas = [str(d[0]) for d in cursor.description]
                    filas = [
                        tuple(self._valor_sqlite(v) for v in fila)
                        for fila in cursor.fetchall()
                    ]
                    self._reemplazar_tabla_local(tabla_local, columnas, filas)
                    self.bd.registrar_importacion(
                        tabla_local, ruta, tabla_real, fecha_hora, len(filas),
                        "Columnas: " + ", ".join(columnas)
                    )
                    resultado["tablas"][tabla_local] = {
                        "exito": True,
                        "tabla_access": tabla_real,
                        "registros": len(filas),
                        "error": "",
                    }
                    print("OK - " + tabla_real + ": " + str(len(filas)) + " registros")
                except Exception as error:
                    errores.append(tabla_configurada + ": " + str(error))
                    resultado["tablas"][tabla_local] = {
                        "exito": False,
                        "tabla_access": tabla_configurada,
                        "registros": 0,
                        "error": str(error),
                    }
                    print("ERROR - " + tabla_configurada + ": " + str(error))
        finally:
            try:
                conexion.close()
            except Exception:
                pass

        resultado["exito"] = not errores
        resultado["descripcion_error"] = "\n".join(errores)
        resultado.update(self._estado_resumen_access())
        print("========================================")
        return resultado

    def _estado_resumen_access(self):
        estado = self.obtener_estado_access()
        return {
            "hay_copia_local": all(e["registros_locales"] > 0 for e in estado.values()) if estado else False,
            "estado_local": estado,
        }

    # ---------------------------------------------------------
    # Refrescar todo (boton de cada formulario)
    # ---------------------------------------------------------
    def refrescar_todo(self):
        resultado_tiendas = self.sincronizar_tiendas_web()
        resultado_access = self.sincronizar_access()
        return resultado_tiendas, resultado_access

    # ---------------------------------------------------------
    # Cerrar conexion
    # ---------------------------------------------------------
    def cerrar(self):
        self.bd.cerrar()
