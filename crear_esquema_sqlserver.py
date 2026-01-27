"""
Script para crear el esquema en SQL Server
"""
import pyodbc
from config_db import get_connection_string

def ejecutar_script_sql():
    """Ejecuta el script de creación de esquema"""
    
    # Leer script SQL
    with open('create_sqlserver_schema.sql', 'r', encoding='utf-8') as f:
        script = f.read()
    
    # Separar en statements individuales
    statements = [s.strip() for s in script.split(';') if s.strip()]
    
    # Conectar y ejecutar
    conn = pyodbc.connect(get_connection_string())
    cursor = conn.cursor()
    
    print("🔨 Creando esquema en SQL Server...")
    print()
    
    for i, statement in enumerate(statements, 1):
        if not statement or statement.startswith('--'):
            continue
            
        try:
            print(f"   Ejecutando statement {i}/{len(statements)}...")
            cursor.execute(statement)
            conn.commit()
            print(f"   ✅ OK")
        except Exception as e:
            print(f"   ⚠️ {e}")
            # Continuar si la tabla ya existe
            if "already an object" in str(e).lower():
                continue
            else:
                raise
    
    print()
    print("✅ Esquema creado exitosamente")
    
    # Verificar tablas creadas
    cursor.execute("""
    SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_TYPE = 'BASE TABLE'
    ORDER BY TABLE_NAME
    """)
    
    tablas = [row[0] for row in cursor.fetchall()]
    print(f"\n📋 Tablas creadas ({len(tablas)}):")
    for tabla in tablas:
        cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
        count = cursor.fetchone()[0]
        print(f"   • {tabla}: {count} registros")
    
    conn.close()

if __name__ == "__main__":
    ejecutar_script_sql()
