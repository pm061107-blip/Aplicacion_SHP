@echo off
setlocal EnableExtensions

title Compilar Aplicacion_SHP 1.0

set "PROYECTO=C:\Trabajos\Aplicacion_SHP"
set "PYTHON=C:\Users\juanmcp\AppData\Local\Programs\Python\Python314-32\python.exe"
set "NOMBRE_APP=Aplicacion_SHP"

echo ============================================================
echo  COMPILACION DE APLICACION_SHP 1.0
echo ============================================================
echo.

if not exist "%PROYECTO%\main.py" (
    echo ERROR: No se encuentra:
    echo %PROYECTO%\main.py
    pause
    exit /b 1
)

if not exist "%PYTHON%" (
    echo ERROR: No se encuentra Python en:
    echo %PYTHON%
    pause
    exit /b 1
)

if not exist "%PROYECTO%\config\config.json" (
    echo ERROR: Falta config\config.json
    pause
    exit /b 1
)

cd /d "%PROYECTO%"

echo Comprobando librerias (pyodbc y openpyxl)...
"%PYTHON%" -c "import pyodbc, openpyxl" >nul 2>&1
if errorlevel 1 (
    echo Instalando pyodbc y openpyxl...
    "%PYTHON%" -m pip install pyodbc openpyxl
    if errorlevel 1 (
        echo ERROR: No se pudieron instalar pyodbc / openpyxl.
        pause
        exit /b 1
    )
)

echo Verificando version de fuentes...
"%PYTHON%" -c "from modulos.version_aplicacion import VERSION_APP; assert VERSION_APP == '1.0', 'Version de fuentes incorrecta: ' + str(VERSION_APP)"
if errorlevel 1 (
    echo ERROR: Las fuentes no corresponden a 1.0.
    pause
    exit /b 1
)

echo Verificando imports...
"%PYTHON%" -c "import modulos.formulario_principal, modulos.formulario_datos, modulos.sincronizador, modulos.importar_pedido, modulos.importar_expediciones, modulos.importar_contenedores_hai, modulos.importar_volumetria, modulos.calculo_volumetria"
if errorlevel 1 (
    echo ERROR: No se pueden importar los modulos. Revisa que se haya extraido todo el ZIP.
    pause
    exit /b 1
)

echo Cerrando posibles ejecuciones anteriores...
taskkill /F /IM "%NOMBRE_APP%.exe" >nul 2>&1

echo Comprobando PyInstaller...
"%PYTHON%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    "%PYTHON%" -m pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: No se pudo instalar PyInstaller.
        pause
        exit /b 1
    )
)

rem ------------------------------------------------------------
rem Proteccion de datos del EXE: shp.db guarda lo importado.
rem Se copia a copias_compilacion\FECHA y se restaura en el EXE nuevo.
rem ------------------------------------------------------------
set "DATOS_EXE=%PROYECTO%\dist\%NOMBRE_APP%\_internal"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "FECHA_COPIA=%%i"
if "%FECHA_COPIA%"=="" set "FECHA_COPIA=sin_fecha"
set "COPIA_DATOS=%PROYECTO%\copias_compilacion\%FECHA_COPIA%"
set "HAY_COPIA_DB=0"

if exist "%DATOS_EXE%\shp.db" (
    echo Copiando datos del EXE actual a:
    echo %COPIA_DATOS%
    if not exist "%COPIA_DATOS%" mkdir "%COPIA_DATOS%"
    copy /Y "%DATOS_EXE%\shp.db" "%COPIA_DATOS%\shp.db" >nul
    if errorlevel 1 (
        echo ERROR: No se pudo copiar shp.db del EXE.
        echo No se borra dist para no perder datos. Cierra la aplicacion y repite.
        pause
        exit /b 1
    )
    set "HAY_COPIA_DB=1"
)

echo.
echo Limpiando compilaciones anteriores...
if exist "build" rmdir /S /Q "build"
if exist "dist" rmdir /S /Q "dist"
if exist "%NOMBRE_APP%.spec" del /F /Q "%NOMBRE_APP%.spec"
for /D /R "%PROYECTO%" %%D in (__pycache__) do @if exist "%%D" rmdir /S /Q "%%D"

echo Verificando sintaxis de fuentes...
"%PYTHON%" -m compileall -q main.py bd config modulos
if errorlevel 1 (
    echo ERROR: Hay errores de sintaxis en los modulos Python.
    pause
    exit /b 1
)

echo.
echo Compilando...
echo.

"%PYTHON%" -m PyInstaller ^
  --noconsole ^
  --onedir ^
  --clean ^
  --noconfirm ^
  --name "%NOMBRE_APP%" ^
  --hidden-import=tkinter ^
  --hidden-import=tkinter.ttk ^
  --hidden-import=tkinter.filedialog ^
  --hidden-import=tkinter.messagebox ^
  --hidden-import=tkinter.simpledialog ^
  --hidden-import=pyodbc ^
  --hidden-import=openpyxl ^
  --hidden-import=modulos.dialogos_ui ^
  --hidden-import=modulos.dialogo_progreso ^
  --hidden-import=modulos.dialogo_estados_estarepp ^
  --hidden-import=modulos.ventanas_tk ^
  --hidden-import=modulos.version_aplicacion ^
  --hidden-import=modulos.sincronizador ^
  --hidden-import=modulos.componente_refresco ^
  --hidden-import=modulos.visor_tabla ^
  --hidden-import=modulos.formulario_principal ^
  --hidden-import=modulos.formulario_datos ^
  --hidden-import=modulos.importar_pedido ^
  --hidden-import=modulos.importar_estarepp ^
  --hidden-import=modulos.importar_pedidos_pte ^
  --hidden-import=modulos.posiciones_estarepp ^
  --hidden-import=modulos.importar_expediciones ^
  --hidden-import=modulos.importar_contenedores_hai ^
  --hidden-import=modulos.importar_volumetria ^
  --hidden-import=modulos.calculo_volumetria ^
  --hidden-import=modulos.utilidades ^
  --add-data "config\config.json;config" ^
  "main.py"

if errorlevel 1 (
    echo.
    echo ============================================================
    echo  ERROR: LA COMPILACION NO HA FINALIZADO CORRECTAMENTE
    echo ============================================================
    if "%HAY_COPIA_DB%"=="1" echo Tus datos del EXE anterior estan a salvo en: %COPIA_DATOS%
    pause
    exit /b 1
)

set "EXE=%PROYECTO%\dist\%NOMBRE_APP%\%NOMBRE_APP%.exe"

if not exist "%EXE%" (
    echo ERROR: PyInstaller finalizo, pero no se encuentra el EXE:
    echo %EXE%
    pause
    exit /b 1
)

if "%HAY_COPIA_DB%"=="1" (
    copy /Y "%COPIA_DATOS%\shp.db" "%PROYECTO%\dist\%NOMBRE_APP%\_internal\shp.db" >nul
    if errorlevel 1 (
        echo AVISO: no se pudo restaurar shp.db. Copia manualmente:
        echo %COPIA_DATOS%\shp.db
    ) else (
        echo OK - shp.db restaurada en el EXE nuevo.
    )
)

echo.
echo ============================================================
echo  COMPILACION FINALIZADA CORRECTAMENTE
echo ============================================================
echo.
echo Aplicacion generada en:
echo %EXE%
echo.
echo Para instalarla en otro PC, copia la carpeta completa:
echo %PROYECTO%\dist\%NOMBRE_APP%
echo No copies solo el EXE.
echo.

choice /C SN /N /M "Quieres abrir ahora la aplicacion? [S/N]: "
if errorlevel 2 goto FIN

start "" "%EXE%"

:FIN
echo.
pause
endlocal
