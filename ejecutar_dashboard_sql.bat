@echo off
echo ================================================
echo   DASHBOARD DE VEHICULOS CON SQL
echo ================================================
echo.
echo Iniciando dashboard con persistencia en BD...
echo La aplicacion se abrira en tu navegador
echo.
echo Presiona Ctrl+C para detener el servidor
echo ================================================
echo.

cd /d "%~dp0"
cd ..\..
call .venv\Scripts\activate
cd data_dash_streamlit\programas_ET
streamlit run dashboard_vehiculos_sql.py

pause
