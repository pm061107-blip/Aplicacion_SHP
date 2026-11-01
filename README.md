# Aplicación SHP

Aplicación en Python (Tkinter + SQLite) para el etiquetado de la GUI GLS, la expedición de la GUI SHP y Roboshuttle.

## Estructura

- `main.py` – arranque: carga Tiendas_Web y el Access maestro y abre el menú.
- `bd/` – base local `shp.db` (conexion.py, basedatos.py, conexion_access.py).
- `config/config.json` – rutas de red y nombres de las tablas del Access.
- `modulos/` – formularios, importadores y cálculos.
- `tests/` – pruebas.

## Ejecución

```bash
python main.py
```

## Compilación

```text
compilar_aplicacion_shp.bat
```
