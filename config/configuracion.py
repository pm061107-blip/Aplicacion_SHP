import json
from pathlib import Path


class Configuracion:

    def __init__(self):

        self.archivo = Path(__file__).parent / "config.json"

        with open(self.archivo, "r", encoding="utf-8") as f:
            self.datos = json.load(f)

    def obtener(self, clave):

        return self.datos.get("rutas", {}).get(clave, "")

    def tiendas_web(self):

        return self.obtener("tiendas_web")

    def access_maestro(self):

        return self.obtener("access_maestro")

    def tablas_access(self):
        """Diccionario TablaLocal -> NombreTablaEnAccess."""

        return dict(self.datos.get("tablas_access", {}))
