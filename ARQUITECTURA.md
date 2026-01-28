# Infraestructura del Dashboard de Seguimiento de Flota

## 📁 Estructura del Proyecto

```
programas_ET/
│
├── 📊 DASHBOARDS (Aplicaciones Principales)
│   ├── dashboard_vehiculos_sql.py       # Dashboard con SQL Server
│   └── dashboard_vehiculos_sql2.py      # Dashboard con SQLite (PRINCIPAL)
│
├── 🗄️ BASE DE DATOS
│   ├── SQLite (Local/Desarrollo)
│   │   ├── db_manager.py                # Gestor de BD SQLite
│   │   ├── init_database.py             # Inicializar BD SQLite
│   │   └── vehiculos_tracking.db        # Archivo BD SQLite
│   │
│   └── SQL Server (Producción)
│       ├── db_manager_sqlserver.py      # Gestor de BD SQL Server
│       ├── crear_esquema_sqlserver.py   # Crear esquema
│       └── create_sqlserver_schema*.sql # Scripts SQL
│
├── ⚙️ CONFIGURACIÓN
│   ├── config_db.py                     # Configuración de conexiones BD y API
│   ├── .env                             # Variables de entorno (NO en Git)
│   ├── .env.example                     # Plantilla de variables
│   └── .streamlit/
│       ├── secrets.toml                 # Secretos Streamlit (NO en Git)
│       └── secrets.toml.example         # Plantilla de secretos
│
├── 🔧 UTILIDADES
│   ├── timezone_utils.py                # Manejo de zona horaria UTC-5
│   ├── test_api.py                      # Pruebas de API WorldFleet
│   ├── fix_dates.py                     # Corrección de fechas
│   └── migrar_sqlite_a_sqlserver.py     # Migración de datos
│
├── 📦 DEPENDENCIAS
│   ├── requirements.txt                 # Paquetes Python necesarios
│   └── packages.txt                     # Paquetes sistema (Streamlit Cloud)
│
├── 📜 SCRIPTS DE EJECUCIÓN
│   ├── ejecutar_dashboard_sql.bat       # Ejecutar dashboard SQL Server
│   ├── INICIAR_BD.bat                   # Iniciar base de datos
│   └── INSTALAR.bat                     # Instalar dependencias
│
└── 📚 DOCUMENTACIÓN
    ├── README_INSTALACION.md            # Guía de instalación
    ├── README_MIGRACION.md              # Guía de migración
    ├── DEPLOY.md                        # Guía de despliegue
    └── SECRETS_SETUP.md                 # Configuración de secretos
```

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │        Streamlit Dashboard (dashboard_vehiculos_sql2.py)  │   │
│  │  - Visualización de mapas (Folium)                       │   │
│  │  - Gráficos y métricas                                   │   │
│  │  - Filtros y controles interactivos                      │   │
│  │  - Auto-refresh cada 60 segundos                         │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓ ↑
┌─────────────────────────────────────────────────────────────────┐
│                      CAPA DE LÓGICA                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              db_manager.py (SQLite)                       │   │
│  │  - Insertar posiciones                                   │   │
│  │  - Gestión de sesiones AM/PM                             │   │
│  │  - Alertas de velocidad                                  │   │
│  │  - Gestión de geocercas                                  │   │
│  │  - Manejo de concurrencia WAL                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │            config_db.py                                   │   │
│  │  - Configuración de conexiones                           │   │
│  │  - Manejo de secretos (Streamlit/ENV)                    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓ ↑
┌─────────────────────────────────────────────────────────────────┐
│                    FUENTES DE DATOS                              │
│  ┌────────────────────────┐  ┌─────────────────────────────┐   │
│  │   SQLite Local         │  │   API WorldFleet            │   │
│  │  vehiculos_tracking.db │  │  (SOAP Service)             │   │
│  │  - Modo WAL            │  │  - Datos en tiempo real     │   │
│  │  - Timeout 30s         │  │  - XML Response             │   │
│  │  - Reintentos auto     │  │  - Caché 60s                │   │
│  └────────────────────────┘  └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 Flujo de Datos

```
1. API WorldFleet (cada 60s)
   ↓
2. Parse XML → DataFrame
   ↓
3. db_manager.insertar_posiciones()
   ↓
4. SQLite (vehiculos_tracking.db)
   ↓
5. Dashboard lee BD y muestra
   ↓
6. Usuario visualiza en Streamlit
```

## 🗃️ Estructura de Base de Datos SQLite

```sql
TABLAS PRINCIPALES:
├── posiciones_vehiculos      # Posiciones GPS de vehículos
├── alertas_velocidad         # Alertas de exceso de velocidad
├── sesiones_tracking         # Registro de sesiones AM/PM
├── geocercas                 # Definición de geocercas
├── vehiculos_geocercas       # Asignación vehículo-geocerca
└── alertas_geocerca          # Alertas de salida de geocerca
```

## 🚀 Despliegue

### Local:
- **Base de Datos:** SQLite (vehiculos_tracking.db)
- **Servidor:** Streamlit local (puerto 8501)
- **Configuración:** .env

### Producción (Streamlit Cloud):
- **Base de Datos:** SQL Server (10.10.1.252)
- **Servidor:** Streamlit Cloud
- **Configuración:** secrets.toml
- **Repositorio:** github.com/wijaro88/dep-app-samplev1

## 🔑 Configuración de Secretos

### Variables de Entorno:
```
SQL_SERVER=10.10.1.252
SQL_PORT=1433
SQL_DATABASE=ciex
SQL_USERNAME=jguzman
SQL_PASSWORD=***
API_USERNAME=wsascension
API_PASSWORD=***
API_EMPRESA=ASCENSION
```

## 📊 Funcionalidades Principales

1. **Tracking en Tiempo Real**
   - Mapa interactivo con posiciones actuales
   - Auto-actualización cada 60 segundos
   - Filtros por vehículo, fecha, hora

2. **Alertas**
   - Exceso de velocidad
   - Salida de geocerca
   - Gestión y atención de alertas

3. **Reportes**
   - Recorridos por vehículo
   - Estadísticas de sesión
   - Exportación a Excel

4. **Gestión de Geocercas**
   - Crear/editar geocercas
   - Asignar vehículos
   - Monitoreo de violaciones

## 🔧 Tecnologías Utilizadas

- **Frontend:** Streamlit
- **Mapas:** Folium
- **Base de Datos:** SQLite / SQL Server
- **API:** SOAP (WorldFleet)
- **Python:** pandas, lxml, pymssql/pyodbc
- **Deploy:** Streamlit Cloud + GitHub
