"""
Script de inicialización de la base de datos SQLite para tracking de vehículos
"""
import sqlite3
from datetime import datetime
import os

# Ruta de la base de datos
DB_PATH = os.path.join(os.path.dirname(__file__), 'vehiculos_tracking.db')

def crear_base_datos():
    """Crea la base de datos y las tablas necesarias"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabla de posiciones de vehículos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS posiciones_vehiculos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        vehiculo TEXT NOT NULL,
        latitud REAL NOT NULL,
        longitud REAL NOT NULL,
        velocidad REAL DEFAULT 0,
        kilometraje REAL DEFAULT 0,
        estado_online TEXT,
        estado_gps TEXT,
        evento TEXT,
        satelites INTEGER DEFAULT 0,
        region TEXT,
        hora_evento TEXT,
        sesion_dia TEXT NOT NULL,
        fecha_registro DATE NOT NULL,
        UNIQUE(timestamp, vehiculo)
    )
    ''')
    
    # Índices para consultas rápidas
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_vehiculo 
    ON posiciones_vehiculos(vehiculo)
    ''')
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_timestamp 
    ON posiciones_vehiculos(timestamp)
    ''')
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_sesion 
    ON posiciones_vehiculos(sesion_dia, fecha_registro)
    ''')
    
    # Tabla de alertas de velocidad
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS alertas_velocidad (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        vehiculo TEXT NOT NULL,
        velocidad REAL NOT NULL,
        latitud REAL NOT NULL,
        longitud REAL NOT NULL,
        evento TEXT,
        umbral_configurado REAL NOT NULL,
        sesion_dia TEXT NOT NULL,
        fecha_registro DATE NOT NULL,
        atendida INTEGER DEFAULT 0,
        fecha_atencion DATETIME,
        comentario_atencion TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_alertas_vehiculo 
    ON alertas_velocidad(vehiculo)
    ''')
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_alertas_timestamp 
    ON alertas_velocidad(timestamp)
    ''')
    
    # Tabla de configuración/sesiones
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sesiones_tracking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha DATE NOT NULL,
        sesion TEXT NOT NULL,
        inicio_sesion DATETIME NOT NULL,
        fin_sesion DATETIME,
        total_vehiculos INTEGER DEFAULT 0,
        total_registros INTEGER DEFAULT 0,
        total_alertas INTEGER DEFAULT 0,
        UNIQUE(fecha, sesion)
    )
    ''')
    
    # Tabla de geocercas (zonas permitidas)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS geocercas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        descripcion TEXT,
        lat_min REAL NOT NULL,
        lat_max REAL NOT NULL,
        lon_min REAL NOT NULL,
        lon_max REAL NOT NULL,
        color TEXT DEFAULT '#FF0000',
        activa INTEGER DEFAULT 1,
        fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Tabla de asignación vehículo-geocerca
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vehiculos_geocercas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehiculo TEXT NOT NULL,
        geocerca_id INTEGER NOT NULL,
        fecha_asignacion DATETIME DEFAULT CURRENT_TIMESTAMP,
        activa INTEGER DEFAULT 1,
        FOREIGN KEY (geocerca_id) REFERENCES geocercas(id),
        UNIQUE(vehiculo, geocerca_id)
    )
    ''')
    
    # Tabla de alertas de geocerca
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS alertas_geocerca (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        vehiculo TEXT NOT NULL,
        geocerca_nombre TEXT NOT NULL,
        latitud REAL NOT NULL,
        longitud REAL NOT NULL,
        tipo_violacion TEXT DEFAULT 'SALIDA',
        distancia_km REAL,
        atendida INTEGER DEFAULT 0,
        fecha_atencion DATETIME,
        comentario_atencion TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_alertas_geocerca_vehiculo 
    ON alertas_geocerca(vehiculo)
    ''')
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_alertas_geocerca_timestamp 
    ON alertas_geocerca(timestamp)
    ''')
    
    conn.commit()
    conn.close()
    
    print(f"✓ Base de datos creada exitosamente en: {DB_PATH}")
    print("✓ Tablas creadas:")
    print("  - posiciones_vehiculos")
    print("  - alertas_velocidad")
    print("  - sesiones_tracking")

def verificar_estructura():
    """Verifica que la base de datos tenga la estructura correcta"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verificar tablas
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
    """)
    
    tablas = cursor.fetchall()
    print("\n📊 Tablas en la base de datos:")
    for tabla in tablas:
        print(f"  - {tabla[0]}")
        
        # Mostrar estructura de cada tabla
        cursor.execute(f"PRAGMA table_info({tabla[0]})")
        columnas = cursor.fetchall()
        print(f"    Columnas:")
        for col in columnas:
            print(f"      {col[1]} ({col[2]})")
    
    # Contar registros
    cursor.execute("SELECT COUNT(*) FROM posiciones_vehiculos")
    total_posiciones = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM alertas_velocidad")
    total_alertas = cursor.fetchone()[0]
    
    print(f"\n📈 Estadísticas:")
    print(f"  - Posiciones registradas: {total_posiciones}")
    print(f"  - Alertas registradas: {total_alertas}")
    
    conn.close()

def limpiar_datos_antiguos(dias=30):
    """Limpia datos más antiguos que X días"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    fecha_limite = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    fecha_limite = fecha_limite.replace(day=fecha_limite.day - dias)
    
    cursor.execute("""
        DELETE FROM posiciones_vehiculos 
        WHERE fecha_registro < ?
    """, (fecha_limite.date(),))
    
    posiciones_eliminadas = cursor.rowcount
    
    cursor.execute("""
        DELETE FROM alertas_velocidad 
        WHERE fecha_registro < ?
    """, (fecha_limite.date(),))
    
    alertas_eliminadas = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"\n🗑️ Limpieza de datos antiguos (>{dias} días):")
    print(f"  - Posiciones eliminadas: {posiciones_eliminadas}")
    print(f"  - Alertas eliminadas: {alertas_eliminadas}")

if __name__ == "__main__":
    print("=" * 60)
    print("INICIALIZACIÓN DE BASE DE DATOS - TRACKING DE VEHÍCULOS")
    print("=" * 60)
    
    crear_base_datos()
    verificar_estructura()
    
    print("\n" + "=" * 60)
    print("✓ Inicialización completada")
    print("=" * 60)
