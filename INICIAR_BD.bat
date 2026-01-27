@echo off
echo ================================================
echo   INICIALIZACION DE BASE DE DATOS SQLite
echo   Sistema de Tracking de Vehiculos
echo ================================================
echo.

cd /d "%~dp0"
cd ..\..
call .venv\Scripts\activate
cd data_dash_streamlit\programas_ET

python init_database.py

echo.
echo ================================================
pause
