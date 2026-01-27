@echo off
chcp 65001 >nul
echo ================================================
echo   INSTALADOR - Dashboard Tracking Vehículos
echo ================================================
echo.

REM Verificar que todos los archivos necesarios estén presentes
set SCRIPT_DIR=%~dp0
if not exist "%SCRIPT_DIR%requirements.txt" (
    echo.
    echo ❌ ERROR: Archivos incompletos detectados
    echo.
    echo Este instalador debe estar dentro de la carpeta "programas_ET"
    echo junto con los siguientes archivos:
    echo   - dashboard_vehiculos_sql.py
    echo   - db_manager.py
    echo   - init_database.py
    echo   - requirements.txt
    echo   - ejecutar_dashboard_sql.bat
    echo.
    echo Por favor, copie la carpeta COMPLETA "programas_ET" al nuevo PC,
    echo no solo el archivo INSTALAR.bat
    echo.
    pause
    exit /b 1
)

if not exist "%SCRIPT_DIR%dashboard_vehiculos_sql.py" (
    echo.
    echo ❌ ERROR: No se encuentra dashboard_vehiculos_sql.py
    echo Por favor, copie la carpeta COMPLETA "programas_ET"
    echo.
    pause
    exit /b 1
)

if not exist "%SCRIPT_DIR%db_manager.py" (
    echo.
    echo ❌ ERROR: No se encuentra db_manager.py
    echo Por favor, copie la carpeta COMPLETA "programas_ET"
    echo.
    pause
    exit /b 1
)

if not exist "%SCRIPT_DIR%init_database.py" (
    echo.
    echo ❌ ERROR: No se encuentra init_database.py
    echo Por favor, copie la carpeta COMPLETA "programas_ET"
    echo.
    pause
    exit /b 1
)

echo ✅ Todos los archivos necesarios detectados
echo.

REM Verificar si Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Python no está instalado o no está en el PATH
    echo Por favor instale Python 3.8 o superior desde https://www.python.org
    pause
    exit /b 1
)

echo ✅ Python detectado
python --version
echo.

REM Guardar la ruta del directorio del script
set SCRIPT_DIR=%~dp0
set PARENT_DIR=%~dp0..

REM Navegar al directorio del script
cd /d "%SCRIPT_DIR%"

REM Verificar si existe el entorno virtual
if exist "%PARENT_DIR%\\.venv" (
    echo ✅ Entorno virtual encontrado
) else (
    echo 📦 Creando entorno virtual...
    cd /d "%PARENT_DIR%"
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo ❌ ERROR: No se pudo crear el entorno virtual
        pause
        exit /b 1
    )
    echo ✅ Entorno virtual creado
)
echo.

REM Volver al directorio del script
cd /d "%SCRIPT_DIR%"

REM Activar entorno virtual e instalar dependencias
echo 📦 Instalando dependencias...
call "%PARENT_DIR%\\.venv\\Scripts\\activate.bat"

REM Verificar que requirements.txt existe
if not exist "%SCRIPT_DIR%requirements.txt" (
    echo ❌ ERROR: No se encuentra el archivo requirements.txt en %SCRIPT_DIR%
    echo Asegúrese de que todos los archivos fueron copiados correctamente
    pause
    exit /b 1
)

REM Actualizar pip
python -m pip install --upgrade pip

REM Instalar dependencias usando ruta absoluta
pip install -r "%SCRIPT_DIR%requirements.txt"
if %errorlevel% neq 0 (
    echo ❌ ERROR: Falló la instalación de dependencias
    pause
    exit /b 1
)
echo ✅ Dependencias instaladas correctamente
echo.

REM Eliminar base de datos existente si se desea empezar desde cero
if exist "%SCRIPT_DIR%vehiculos_tracking.db" (
    echo ⚠️  Base de datos existente detectada
    choice /C SN /M "¿Desea eliminarla y crear una nueva (S/N)?"
    if errorlevel 2 (
        echo ✅ Se mantendrá la base de datos existente
    ) else (
        del "%SCRIPT_DIR%vehiculos_tracking.db"
        echo ✅ Base de datos eliminada
    )
)
echo.

REM Crear/Inicializar base de datos
echo 🗄️  Inicializando base de datos...
python "%SCRIPT_DIR%init_database.py"
if %errorlevel% neq 0 (
    echo ❌ ERROR: No se pudo crear la base de datos
    pause
    exit /b 1
)
echo.

echo ================================================
echo   ✅ INSTALACIÓN COMPLETADA EXITOSAMENTE
echo ================================================
echo.
echo Para ejecutar el dashboard:
echo   1. Ejecute: ejecutar_dashboard_sql.bat
echo   2. O active el entorno: ..\\.venv\\Scripts\\activate.bat
echo      Y ejecute: streamlit run dashboard_vehiculos_sql.py
echo.
echo El dashboard estará disponible en: http://localhost:8501
echo.
pause
