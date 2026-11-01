# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('config/config.json', 'config')],
    hiddenimports=['tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox', 'tkinter.simpledialog', 'pyodbc', 'openpyxl', 'modulos.dialogos_ui', 'modulos.dialogo_progreso', 'modulos.dialogo_estados_estarepp', 'modulos.ventanas_tk', 'modulos.version_aplicacion', 'modulos.sincronizador', 'modulos.componente_refresco', 'modulos.visor_tabla', 'modulos.formulario_principal', 'modulos.formulario_datos', 'modulos.importar_pedido', 'modulos.importar_estarepp', 'modulos.importar_pedidos_pte', 'modulos.posiciones_estarepp', 'modulos.importar_expediciones', 'modulos.importar_contenedores_hai', 'modulos.importar_volumetria', 'modulos.calculo_volumetria', 'modulos.utilidades'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Aplicacion_SHP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Aplicacion_SHP',
)
