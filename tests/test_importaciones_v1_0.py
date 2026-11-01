"""Pruebas de la version 1.0 con ficheros sinteticos y una base temporal.

Ejecutar desde la carpeta del proyecto:  python -m unittest tests.test_importaciones_v1_0
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bd.conexion as conexion  # noqa: E402

CARPETA = Path(tempfile.mkdtemp())
_init_original = conexion.ConexionBD.__init__


def _init_temporal(self):
    _init_original(self)
    self.ruta_bd = CARPETA / "shp_test.db"


conexion.ConexionBD.__init__ = _init_temporal

from bd.basedatos import BaseDatos  # noqa: E402
from modulos.calculo_volumetria import CalculoVolumetria  # noqa: E402
from modulos.importar_contenedores_hai import ImportarContenedoresHAI  # noqa: E402
from modulos.importar_expediciones import ImportarExpediciones  # noqa: E402
from modulos.importar_pedido import ImportarPedido  # noqa: E402
from modulos.importar_volumetria import ImportarVolumetria  # noqa: E402
from modulos.utilidades import descomponer_sku  # noqa: E402


def linea_estarepp(tienda, aparte, modelo, calidad, color, talla, campana, anio, uds, uxl, estado=""):
    linea = list(" " * 94)

    def poner(a, b, valor, numero=True):
        valor = str(valor)
        valor = valor.rjust(b - a, "0") if numero else valor.ljust(b - a)
        linea[a:b] = valor[: b - a]

    poner(0, 1, "P", False); poner(1, 3, campana, False); poner(3, 8, anio)
    poner(8, 18, tienda); poner(18, 19, 1); poner(19, 20, aparte)
    poner(20, 36, "DESC", False); poner(36, 41, modelo); poner(41, 45, calidad)
    poner(45, 49, color); poner(49, 51, talla); poner(56, 59, 1); poner(59, 68, 1)
    poner(68, 78, "CAR", False); linea[78:80] = list(estado.rjust(2))
    poner(80, 89, uds); poner(89, 91, "U", False); poner(91, 94, uxl)
    return "".join(linea)


class PruebasV10(unittest.TestCase):

    def setUp(self):
        ruta = CARPETA / "shp_test.db"
        if ruta.exists():
            os.remove(ruta)
        self.bd = BaseDatos()
        self.bd.crear_tablas()
        self.bd.conexion.executemany(
            "INSERT INTO Tiendas_Web VALUES (?, ?, ?)",
            [(752, "TAR-NOVA", "ESPAÑA"), (11203, "OTRA", "BELGICA")],
        )
        self.bd.guardar()

    def tearDown(self):
        self.bd.cerrar()

    def test_sku_hai(self):
        partes = descomponer_sku("0366630440640V2026W ")
        self.assertEqual(
            (partes["Modelo"], partes["Calidad"], partes["Color"], partes["Talla"],
             partes["Campana"], partes["Anio"], partes["Cd"]),
            ("3666", "304", "406", "40", "V", "2026", "W"),
        )

    def test_expediciones(self):
        ruta = CARPETA / "cualquier_nombre.csv"
        ruta.write_text(
            "Configuración;Descripción Configuración;Ruta;Tienda;Sección;Aparte;Destino 1;Destino 3\n"
            "Bajar_silo;Bajar_silo;T_11203;11203;2;0;ROBOT PALETIZADO PA01VA01;Chute 11\n",
            encoding="latin-1",
        )
        resultado = ImportarExpediciones(bd=self.bd).importar_desde_ruta(ruta)
        self.assertEqual(resultado["registros"], 1)
        fila = self.bd.consultar("SELECT Configuracion, Tienda, Seccion, Aparte, Destino3 FROM EXPEDICIONES")[0]
        self.assertEqual(fila, ("Bajar_silo", 11203, 2, 0, "Chute 11"))

    def test_fichero_equivocado(self):
        ruta = CARPETA / "otro.csv"
        ruta.write_text("A;B\n1;2\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            ImportarExpediciones(bd=self.bd).importar_desde_ruta(ruta)
        with self.assertRaises(ValueError):
            ImportarContenedoresHAI(bd=self.bd).importar_desde_ruta(ruta)

    def test_pedido_estarepp_y_pte_y_volumen(self):
        estarepp = CARPETA / "ESTAREPP.txt"
        estarepp.write_text("\n".join([
            linea_estarepp(752, 0, 3666, 304, 406, 40, "V", 2026, 4, 2),
            linea_estarepp(11203, 2, 1111, 1, 1, 1, "I", 2026, 10, 1, " 1"),
        ]) + "\n", encoding="latin-1")
        resultado = ImportarPedido(bd=self.bd).importar_desde_ruta(
            estarepp, selector_estados=lambda resumen, **k: {"INICIAL", "1", "2"}
        )
        self.assertEqual(resultado["registros"], 2)
        filas = self.bd.consultar("SELECT Tienda, Aparte, Pais, SKU, Unidades, Lotes FROM PEDIDO ORDER BY Tienda")
        self.assertEqual(filas[0], (752, 0, "ESPAÑA", "3666/304/406/40/V/2026", 4, 2.0))

        pte = CARPETA / "pedidos.csv"
        pte.write_text(
            "Sku;Secc.;T. Art.;Id Loc.;Loc. Destino;Apt.;Dem.U;Dem.L;Em;Tabla Reparto\n"
            "0/1111/001/001/1/I/2026/W;1;Prenda;11203;OTRA;2;10;10;07;X\n",
            encoding="utf-8",
        )
        ImportarPedido(bd=self.bd).importar_desde_ruta(pte)
        fila = self.bd.consultar("SELECT Origen, Tienda, Aparte, Pais, SKU, UxL FROM PEDIDO")[0]
        self.assertEqual(fila, ("PEDIDOS_PTE", 11203, 2, "BELGICA", "1111/001/001/1/I/2026", 1))

        from openpyxl import Workbook
        libro = Workbook()
        hoja = libro.active
        hoja.append(["PROD.", "MOD.", "CAL.", "COL.", "TA.", "CAMPAÑA", "AÑO", "UXL",
                     "EST.MERC.", "DESCRIPCIÓN", "UDS./BULTO", "BULTOS/PALET", "UXM",
                     "BLOQ.ENT.", "T.CONT.MED."])
        hoja.append([0, 1111, 1, 1, 1, "I", 2026, 1, "01_UNICA", "x", 20, 0, "", "", "Caja 580x380x300"])
        hoja.append([0, 1111, 1, 1, 1, "I", 2026, 1, "02_OTRO", "x", 5, 0, "", "", "Caja 580x380x300"])
        ruta_vol = CARPETA / "vol.xlsx"
        libro.save(ruta_vol)
        self.assertEqual(ImportarVolumetria(bd=self.bd).importar_desde_ruta(ruta_vol)["registros"], 1)

        resultado = CalculoVolumetria(self.bd).calcular_pedido()
        volumen_esperado = 0.58 * 0.38 * 0.30 / 20 * 10
        self.assertAlmostEqual(resultado["volumen_m3"], volumen_esperado, places=6)
        self.assertEqual(resultado["cajas_300"], 1)
        self.assertEqual(resultado["origenes"], {"EXACTA+UXL": 1})

    def test_respaldo_contenedores_hai(self):
        ruta = CARPETA / "hai.csv"
        ruta.write_text(
            "MATRICULA;SKUS;CANTIDAD;LOTES;UXL;TCM;TIENDA;AP\n"
            "1;0111100100101I2026W;20;20;1;Caja 580x380x400;752 TAR-NOVA;0\n"
            "2;0111100100101I2026W;20;20;1;Caja 580x380x400;752 TAR-NOVA;0\n"
            "3;0111100100101I2026W;5;5;1;Caja 580x380x400;752 TAR-NOVA;0\n"
            "3;0222200200202I2026W;5;5;1;Caja 580x380x400;752 TAR-NOVA;0\n",
            encoding="latin-1",
        )
        ImportarContenedoresHAI(bd=self.bd).importar_desde_ruta(ruta)
        indice = CalculoVolumetria(self.bd).indice_contenedores()
        # La matricula 3 esta mezclada y no cuenta: UxB = 20.
        self.assertAlmostEqual(indice["1111/001/001/1/I/2026"], 0.58 * 0.38 * 0.40 / 20)
        self.assertNotIn("2222/002/002/2/I/2026", indice)


if __name__ == "__main__":
    unittest.main()
