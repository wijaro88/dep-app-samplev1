# Instalador del Dashboard de Tracking de Vehículos

## 📋 Requisitos Previos

- Windows con PowerShell (viene incluido en Windows)
- Conexión a Internet

## 🚀 Instalación en PC Nuevo (desde cero)

### Paso 1: Copiar archivos del proyecto

Copie la carpeta completa `programas_ET` al nuevo PC. Puede usar:
- USB/Memoria
- Compartir por red
- Email/OneDrive
- Git clone (si está en un repositorio)

**Archivos mínimos necesarios:**
```
programas_ET/
├── dashboard_vehiculos_sql.py
├── db_manager.py
├── init_database.py
├── requirements.txt
├── INSTALAR.bat
├── ejecutar_dashboard_sql.bat
└── .streamlit/
    └── config.toml (si existe)
```

### Paso 2: Instalar Python

Si el PC **NO** tiene Python:

1. Abra PowerShell como Administrador
2. Ejecute este comando para instalar Python usando winget (Windows 10/11):
   ```powershell
   winget install Python.Python.3.12
   ```
   
   **O descargue manualmente:**
   - Vaya a https://www.python.org/downloads/
   - Descargue Python 3.8 o superior
   - **IMPORTANTE:** Durante la instalación, marque ✅ "Add Python to PATH"

3. Reinicie PowerShell y verifique:
   ```powershell
   python --version
   ```

### Paso 3: Ejecutar el instalador

1. Navegue a la carpeta del proyecto:
   ```powershell
   cd "ruta\completa\a\programas_ET"
   ```

2. Ejecute el instalador:
   ```powershell
   .\INSTALAR.bat
   ```

3. El instalador hará automáticamente:
   - ✅ Verificar Python
   - ✅ Crear entorno virtual
   - ✅ Instalar todas las dependencias
   - ✅ Crear la base de datos vacía
   - ✅ Configurar todo para ejecutar

### Paso 4: Ejecutar el Dashboard

```powershell
.\ejecutar_dashboard_sql.bat
```

El dashboard se abrirá automáticamente en su navegador en: **http://localhost:8501**

## 📦 Instalación Manual (si INSTALAR.bat falla)

Si el instalador automático no funciona, ejecute estos comandos uno por uno en PowerShell:

```powershell
# 1. Navegar a la carpeta
cd "ruta\completa\a\programas_ET"

# 2. Crear entorno virtual (volver a carpeta padre primero)
cd ..
python -m venv .venv

# 3. Activar entorno virtual
.\.venv\Scripts\Activate.ps1

# Si da error de políticas de ejecución, ejecute primero:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 4. Volver a programas_ET
cd programas_ET

# 5. Actualizar pip
python -m pip install --upgrade pip

# 6. Instalar dependencias
pip install -r requirements.txt

# 7. Crear base de datos
python init_database.py

# 8. Ejecutar dashboard
streamlit run dashboard_vehiculos_sql.py
```

## 📦 Dependencias Incluidas

- **streamlit**: Framework de la aplicación web
- **pandas**: Procesamiento de datos
- **numpy**: Cálculos numéricos
- **requests**: Llamadas a la API
- **lxml**: Procesamiento XML
- **folium**: Generación de mapas
- **streamlit-folium**: Integración de mapas con Streamlit

## 🗄️ Base de Datos

La instalación crea automáticamente la base de datos SQLite con las siguientes tablas:

- **posiciones_vehiculos**: Almacena el historial de posiciones GPS
- **alertas_velocidad**: Registra alertas de exceso de velocidad
- **sesiones_tracking**: Historial de sesiones de monitoreo
- **geocercas**: Definición de geocercas

## ▶️ Ejecución

Después de instalar, ejecute el dashboard con:

```bash
# Windows
ejecutar_dashboard_sql.bat

# Manual
streamlit run dashboard_vehiculos_sql.py
```

El dashboard estará disponible en: **http://localhost:8501**

## 📁 Archivos del Proyecto

```
programas_ET/
├── dashboard_vehiculos_sql.py    # Aplicación principal
├── db_manager.py                 # Gestor de base de datos
├── init_database.py              # Script de inicialización de BD
├── requirements.txt              # Dependencias Python
├── INSTALAR.bat                  # Instalador automático
├── ejecutar_dashboard_sql.bat    # Ejecutor del dashboard
├── README_INSTALACION.md         # Este archivo
├── vehiculos_tracking.db         # Base de datos SQLite
└── .streamlit/                   # Configuración de Streamlit
```

## 🔧 Solución de Problemas

### Error: Python no encontrado
- Instale Python desde https://python.org
- Asegúrese de marcar "Add Python to PATH" durante la instalación

### Error al instalar dependencias
- Actualice pip: `python -m pip install --upgrade pip`
- Instale dependencias una por una si falla el requirements.txt

### Base de datos bloqueada
- Cierre todas las instancias del dashboard
- Elimine el archivo `vehiculos_tracking.db` y ejecute `init_database.py` nuevamente

## 📞 Soporte

**Ing. WILSON JAVIER ROCHA ORJUELA**  
Analista Medio de Datos  
La Ascensión S.A  
📧 wilson.rocha@laascension.com  
📱 311 566 29 50
