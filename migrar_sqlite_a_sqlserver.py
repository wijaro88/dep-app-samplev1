"""
Script para migrar datos de SQLite a SQL Server
Transfiere todos los datos históricos manteniendo la estructura
"""
import sqlite3
import pyodbc
import pandas as pd
from datetime import datetime
from config_db import get_connection_string

def conectar_sqlite():
    """Conecta a la base de datos SQLite existente"""
    return sqlite3.connect('vehiculos_tracking.db')

def conectar_sqlserver():
    """Conecta a SQL Server"""
    return pyodbc.connect(get_connection_string(), timeout=30)

def migrar_posiciones_vehiculos():
    """Migra tabla posiciones_vehiculos"""
    print("📍 Migrando posiciones_vehiculos...")
    
    sqlite_conn = conectar_sqlite()
    sqlserver_conn = conectar_sqlserver()
    
    # Leer datos de SQLite
    df = pd.read_sql("SELECT * FROM posiciones_vehiculos", sqlite_conn)
    
    if df.empty:
        print("   ⚠️ No hay datos para migrar")
        sqlite_conn.close()
        sqlserver_conn.close()
        return 0
    
    # Insertar en SQL Server
    cursor = sqlserver_conn.cursor()
    registros = 0
    
    for _, row in df.iterrows():
        try:
            cursor.execute('''
            INSERT INTO posiciones_vehiculos
            (timestamp, vehiculo, latitud, longitud, velocidad, kilometraje,
             estado_online, estado_gps, evento, satelites, region, hora_evento,
             sesion_dia, fecha_registro)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['timestamp'],
                row['vehiculo'],
                row['latitud'],
                row['longitud'],
                row['velocidad'],
                row['kilometraje'],
                row['estado_online'],
                row['estado_gps'],
                row['evento'],
                row['satelites'],
                row['region'],
                row['hora_evento'],
                row['sesion_dia'],
                row['fecha_registro']
            ))
            registros += 1
            
            if registros % 1000 == 0:
                print(f"   ✓ {registros} registros migrados...")
                sqlserver_conn.commit()
                
        except Exception as e:
            print(f"   ❌ Error en registro: {e}")
    
    sqlserver_conn.commit()
    sqlite_conn.close()
    sqlserver_conn.close()
    
    print(f"   ✅ Total migrado: {registros} registros\n")
    return registros

def migrar_alertas_velocidad():
    """Migra tabla alertas_velocidad"""
    print("⚡ Migrando alertas_velocidad...")
    
    sqlite_conn = conectar_sqlite()
    sqlserver_conn = conectar_sqlserver()
    
    df = pd.read_sql("SELECT * FROM alertas_velocidad", sqlite_conn)
    
    if df.empty:
        print("   ⚠️ No hay datos para migrar")
        sqlite_conn.close()
        sqlserver_conn.close()
        return 0
    
    cursor = sqlserver_conn.cursor()
    registros = 0
    
    for _, row in df.iterrows():
        try:
            cursor.execute('''
            INSERT INTO alertas_velocidad
            (timestamp, vehiculo, velocidad, latitud, longitud, evento,
             umbral_configurado, sesion_dia, fecha_registro, atendida,
             fecha_atencion, comentario_atencion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['timestamp'],
                row['vehiculo'],
                row['velocidad'],
                row['latitud'],
                row['longitud'],
                row['evento'],
                row['umbral_configurado'],
                row['sesion_dia'],
                row['fecha_registro'],
                1 if row.get('atendida') else 0,
                row.get('fecha_atencion'),
                row.get('comentario_atencion')
            ))
            registros += 1
            
        except Exception as e:
            print(f"   ❌ Error en registro: {e}")
    
    sqlserver_conn.commit()
    sqlite_conn.close()
    sqlserver_conn.close()
    
    print(f"   ✅ Total migrado: {registros} alertas\n")
    return registros

def migrar_sesiones_tracking():
    """Migra tabla sesiones_tracking"""
    print("📊 Migrando sesiones_tracking...")
    
    sqlite_conn = conectar_sqlite()
    sqlserver_conn = conectar_sqlserver()
    
    df = pd.read_sql("SELECT * FROM sesiones_tracking", sqlite_conn)
    
    if df.empty:
        print("   ⚠️ No hay datos para migrar")
        sqlite_conn.close()
        sqlserver_conn.close()
        return 0
    
    cursor = sqlserver_conn.cursor()
    registros = 0
    
    for _, row in df.iterrows():
        try:
            cursor.execute('''
            INSERT INTO sesiones_tracking
            (fecha, sesion, inicio_sesion, fin_sesion, total_vehiculos,
             total_registros, total_alertas)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['fecha'],
                row['sesion'],
                row['inicio_sesion'],
                row.get('fin_sesion'),
                row.get('total_vehiculos', 0),
                row.get('total_registros', 0),
                row.get('total_alertas', 0)
            ))
            registros += 1
            
        except Exception as e:
            print(f"   ❌ Error en registro: {e}")
    
    sqlserver_conn.commit()
    sqlite_conn.close()
    sqlserver_conn.close()
    
    print(f"   ✅ Total migrado: {registros} sesiones\n")
    return registros

def migrar_geocercas():
    """Migra tabla geocercas"""
    print("🗺️ Migrando geocercas...")
    
    sqlite_conn = conectar_sqlite()
    sqlserver_conn = conectar_sqlserver()
    
    df = pd.read_sql("SELECT * FROM geocercas", sqlite_conn)
    
    if df.empty:
        print("   ⚠️ No hay datos para migrar")
        sqlite_conn.close()
        sqlserver_conn.close()
        return 0
    
    cursor = sqlserver_conn.cursor()
    registros = 0
    
    for _, row in df.iterrows():
        try:
            cursor.execute('''
            SET IDENTITY_INSERT geocercas ON;
            INSERT INTO geocercas
            (id, nombre, descripcion, lat_min, lat_max, lon_min, lon_max,
             color, activa, fecha_creacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            SET IDENTITY_INSERT geocercas OFF;
            ''', (
                row['id'],
                row['nombre'],
                row.get('descripcion', ''),
                row['lat_min'],
                row['lat_max'],
                row['lon_min'],
                row['lon_max'],
                row.get('color', '#FF0000'),
                1 if row.get('activa', 1) else 0,
                row.get('fecha_creacion', datetime.now())
            ))
            registros += 1
            
        except Exception as e:
            print(f"   ❌ Error en registro: {e}")
    
    sqlserver_conn.commit()
    sqlite_conn.close()
    sqlserver_conn.close()
    
    print(f"   ✅ Total migrado: {registros} geocercas\n")
    return registros

def migrar_vehiculos_geocercas():
    """Migra tabla vehiculos_geocercas"""
    print("🚗 Migrando vehiculos_geocercas...")
    
    sqlite_conn = conectar_sqlite()
    sqlserver_conn = conectar_sqlserver()
    
    df = pd.read_sql("SELECT * FROM vehiculos_geocercas", sqlite_conn)
    
    if df.empty:
        print("   ⚠️ No hay datos para migrar")
        sqlite_conn.close()
        sqlserver_conn.close()
        return 0
    
    cursor = sqlserver_conn.cursor()
    registros = 0
    
    for _, row in df.iterrows():
        try:
            cursor.execute('''
            INSERT INTO vehiculos_geocercas
            (vehiculo, geocerca_id, activa, fecha_asignacion)
            VALUES (?, ?, ?, ?)
            ''', (
                row['vehiculo'],
                row['geocerca_id'],
                1 if row.get('activa', 1) else 0,
                row.get('fecha_asignacion', datetime.now())
            ))
            registros += 1
            
        except Exception as e:
            print(f"   ❌ Error en registro: {e}")
    
    sqlserver_conn.commit()
    sqlite_conn.close()
    sqlserver_conn.close()
    
    print(f"   ✅ Total migrado: {registros} asignaciones\n")
    return registros

def migrar_alertas_geocerca():
    """Migra tabla alertas_geocerca"""
    print("🔔 Migrando alertas_geocerca...")
    
    sqlite_conn = conectar_sqlite()
    sqlserver_conn = conectar_sqlserver()
    
    df = pd.read_sql("SELECT * FROM alertas_geocerca", sqlite_conn)
    
    if df.empty:
        print("   ⚠️ No hay datos para migrar")
        sqlite_conn.close()
        sqlserver_conn.close()
        return 0
    
    cursor = sqlserver_conn.cursor()
    registros = 0
    
    for _, row in df.iterrows():
        try:
            cursor.execute('''
            INSERT INTO alertas_geocerca
            (timestamp, vehiculo, geocerca_nombre, latitud, longitud,
             tipo_violacion, atendida, fecha_atencion, comentario_atencion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['timestamp'],
                row['vehiculo'],
                row['geocerca_nombre'],
                row['latitud'],
                row['longitud'],
                row.get('tipo_violacion', 'SALIDA'),
                1 if row.get('atendida') else 0,
                row.get('fecha_atencion'),
                row.get('comentario_atencion')
            ))
            registros += 1
            
        except Exception as e:
            print(f"   ❌ Error en registro: {e}")
    
    sqlserver_conn.commit()
    sqlite_conn.close()
    sqlserver_conn.close()
    
    print(f"   ✅ Total migrado: {registros} alertas de geocerca\n")
    return registros

def verificar_conexiones():
    """Verifica que ambas bases estén accesibles"""
    print("🔍 Verificando conexiones...\n")
    
    # Verificar SQLite
    try:
        conn = conectar_sqlite()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas = [row[0] for row in cursor.fetchall()]
        print(f"✅ SQLite conectado - {len(tablas)} tablas encontradas:")
        for tabla in tablas:
            print(f"   • {tabla}")
        conn.close()
    except Exception as e:
        print(f"❌ Error SQLite: {e}")
        return False
    
    print()
    
    # Verificar SQL Server
    try:
        conn = conectar_sqlserver()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
        """)
        tablas = [row[0] for row in cursor.fetchall()]
        print(f"✅ SQL Server conectado - {len(tablas)} tablas encontradas:")
        for tabla in tablas:
            print(f"   • {tabla}")
        conn.close()
    except Exception as e:
        print(f"❌ Error SQL Server: {e}")
        return False
    
    print()
    return True

def main():
    """Ejecuta la migración completa"""
    print("=" * 60)
    print("  MIGRACIÓN DE DATOS: SQLite → SQL Server")
    print("=" * 60)
    print()
    
    if not verificar_conexiones():
        print("❌ No se pudo conectar a las bases de datos")
        return
    
    print("🚀 Iniciando migración...\n")
    inicio = datetime.now()
    
    # Migrar todas las tablas
    total = 0
    total += migrar_geocercas()
    total += migrar_vehiculos_geocercas()
    total += migrar_sesiones_tracking()
    total += migrar_posiciones_vehiculos()
    total += migrar_alertas_velocidad()
    total += migrar_alertas_geocerca()
    
    fin = datetime.now()
    duracion = (fin - inicio).total_seconds()
    
    print("=" * 60)
    print(f"✅ MIGRACIÓN COMPLETADA")
    print(f"   Total de registros migrados: {total}")
    print(f"   Tiempo transcurrido: {duracion:.2f} segundos")
    print("=" * 60)

if __name__ == "__main__":
    main()
