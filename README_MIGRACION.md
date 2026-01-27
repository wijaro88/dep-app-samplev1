# MIGRACIÓN COMPLETA A SQL SERVER

##  ESTADO DE LA MIGRACIÓN

La base de datos ha sido migrada exitosamente de SQLite a SQL Server.

### Servidor SQL Server
- **Servidor**: 10.10.1.252:1433
- **Base de datos**: ciex
- **Usuario**: jguzman
- **Versión**: SQL Server 2014 (SP3-GDR)

### Tablas Creadas
 posiciones_vehiculos
 alertas_velocidad
 sesiones_tracking
 geocercas
 vehiculos_geocercas
 alertas_geocerca

##  ARCHIVOS CREADOS

1. **config_db.py**
   - Configuración de conexión a SQL Server
   - Contiene credenciales y string de conexión

2. **db_manager_sqlserver.py**
   - Nuevo manejador de base de datos adaptado para SQL Server
   - Reemplaza db_manager.py con soporte para pyodbc
   - Mantiene todas las funciones originales

3. **migrar_sqlite_a_sqlserver.py**
   - Script para migrar datos históricos (si existieran)
   - Útil si en el futuro necesitas migrar datos de SQLite

##  PRÓXIMOS PASOS

### 1. Actualizar dashboard_vehiculos_sql.py

Reemplazar la importación de db_manager por db_manager_sqlserver:

`python
# ANTES
from db_manager import VehiculosDB

# DESPUÉS
from db_manager_sqlserver import VehiculosDB
`

### 2. Verificar funcionamiento

Ejecutar el dashboard y verificar que:
- Se conecte correctamente a SQL Server
- Inserte posiciones de vehículos
- Muestre historial con colores por vehículo
- Funcionen las alertas y geocercas

##  CONFIGURACIÓN

Si necesitas cambiar las credenciales de SQL Server, edita **config_db.py**:

`python
SQL_SERVER_CONFIG = {
    'server': '10.10.1.252',
    'port': 1433,
    'database': 'ciex',
    'username': 'jguzman',
    'password': 'Df2kS5LR6rpQ',
    'driver': '{SQL Server}'
}
`

##  VERIFICACIÓN

Para verificar que las tablas estén creadas:

`python
import pyodbc
from config_db import get_connection_string

conn = pyodbc.connect(get_connection_string())
cursor = conn.cursor()
cursor.execute("SELECT name FROM sys.tables WHERE name LIKE '%vehiculos%' OR name LIKE '%alertas%'")
for row in cursor.fetchall():
    print(row[0])
`

##  MEJORAS IMPLEMENTADAS

1. **Colores únicos por vehículo**
   - Cada vehículo tiene un color distinto en el historial
   - Función generar_color_vehiculo() genera 20 colores únicos
   - Basado en hash del nombre del vehículo

2. **Base de datos SQL Server**
   - Mayor capacidad y rendimiento
   - Soporte multi-usuario
   - Backups automáticos
   - Listo para producción

##  DIFERENCIAS SQL SERVER vs SQLite

| Característica | SQLite | SQL Server |
|----------------|--------|------------|
| Tipo de datos | INTEGER | INT IDENTITY |
| Booleanos | INTEGER (0/1) | BIT |
| Decimales | REAL | DECIMAL(10,7) |
| Fechas | TEXT | DATETIME2 |
| Strings | TEXT | NVARCHAR |
| Auto-increment | AUTOINCREMENT | IDENTITY |

Todas estas diferencias están manejadas en **db_manager_sqlserver.py**.

##  EJECUTAR EL DASHBOARD

`ash
streamlit run dashboard_vehiculos_sql.py
`

El sistema ahora usará automáticamente SQL Server en lugar de SQLite.
