"""Importacion del pedido: ESTAREPP o pedidos PTE indistintamente.

Igual que en Calculo_Tablas_Reparto:
- Si la primera linea contiene SKU, ID LOC. y DEM.L -> pedido PTE (CSV ';').
- Si es .txt -> ESTAREPP (ancho fijo), con selector de estados Inicial / 1 / 2.
Ambos acaban en la misma tabla PEDIDO con Tienda, Aparte, SKU, Lotes, Unidades
y Pais (cruzado con Tiendas_Web).
"""

from pathlib import Path

from bd.basedatos import BaseDatos
from modulos import utilidades as u
from modulos.importar_estarepp import ImportarESTAREPP
from modulos.importar_pedidos_pte import ImportarPedidosPTE


TIPO_IMPORTACION = "PEDIDO"


def detectar_tipo(ruta):
    ruta = Path(ruta)
    with open(ruta, "r", encoding="latin-1", errors="ignore") as fichero:
        primera_linea = fichero.readline().upper()

    if "SKU" in primera_linea and "ID LOC." in primera_linea and "DEM.L" in primera_linea:
        return "PEDIDOS_PTE"

    if ruta.suffix.lower() == ".txt":
        return "ESTAREPP"

    return "DESCONOCIDO"


class ImportarPedido:

    def __init__(self, parent=None, bd=None):
        self.parent = parent
        self.bd = bd if bd is not None else BaseDatos()

    def seleccionar_e_importar(self):
        ruta = u.seleccionar_fichero(
            self.parent,
            "Importar pedido (ESTAREPP o pedidos)",
            [("Todos los ficheros", "*.*"), ("ESTAREPP", "*.txt"), ("CSV", "*.csv")],
        )
        if ruta is None:
            return None
        return self.importar_desde_ruta(ruta)

    def importar_desde_ruta(self, ruta, selector_estados=None):
        tipo = detectar_tipo(ruta)

        if tipo == "ESTAREPP":
            importador = ImportarESTAREPP(
                [ruta], bd=self.bd, parent=self.parent,
                selector_estados=selector_estados,
            )
            if not importador.importar():
                return None
            estados = importador.estados_seleccionados or set()
            texto_estados = ", ".join(
                "Inicial" if e == "INICIAL" else "Estado " + e for e in sorted(estados)
            )
        elif tipo == "PEDIDOS_PTE":
            ImportarPedidosPTE(ruta, bd=self.bd).importar()
            texto_estados = ""
        else:
            raise ValueError(
                "Formato de pedido no reconocido.\n\n"
                "Se admite un ESTAREPP (.txt) o un fichero de pedidos con las "
                "columnas Sku, Id Loc. y Dem.L."
            )

        sin_pais = self.actualizar_pais()

        registros, tiendas_apartes, lotes, unidades = self.bd.consultar(
            """
            SELECT COUNT(*),
                   COUNT(DISTINCT CAST(Tienda AS TEXT) || '-' || CAST(Aparte AS TEXT)),
                   IFNULL(SUM(Lotes), 0), IFNULL(SUM(Unidades), 0)
            FROM PEDIDO
            """
        )[0]

        detalle = (
            ("ESTAREPP" if tipo == "ESTAREPP" else "Pedidos PTE")
            + (" (" + texto_estados + ")" if texto_estados else "")
            + " | " + u.formatear_numero(tiendas_apartes) + " tiendas-aparte"
            + " | " + u.formatear_numero(round(lotes)) + " lotes"
            + " | " + u.formatear_numero(unidades) + " uds"
        )
        if sin_pais:
            detalle += " | " + str(len(sin_pais)) + " tiendas sin pais"

        self.bd.registrar_importacion(
            TIPO_IMPORTACION, ruta, u.nombre_archivo(ruta), u.ahora(), registros, detalle
        )
        return {
            "registros": registros,
            "detalle": detalle,
            "tipo": tipo,
            "tiendas_sin_pais": sin_pais,
        }

    def actualizar_pais(self):
        """Cruza Tienda con Tiendas_Web. Devuelve las tiendas sin pais."""
        self.bd.ejecutar(
            """
            UPDATE PEDIDO
            SET Pais = IFNULL((
                SELECT TW.Pais FROM Tiendas_Web TW
                WHERE TW.Tienda = PEDIDO.Tienda
                LIMIT 1
            ), '')
            """
        )
        filas = self.bd.consultar(
            "SELECT DISTINCT Tienda FROM PEDIDO WHERE IFNULL(Pais, '') = '' ORDER BY Tienda"
        )
        return [f[0] for f in filas]
