"""
Configuración de conexión a SQL Server y API
Lee desde variables de entorno (.env) o Streamlit secrets
"""
import os
import platform
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

def get_sql_driver():
    """
    Detecta el driver ODBC correcto según el sistema operativo
    """
    system = platform.system()
    
    if system == 'Windows':
        return '{SQL Server}'
    else:  # Linux/Mac
        # Intentar drivers en orden de preferencia
        import pyodbc
        available_drivers = [x for x in pyodbc.drivers()]
        
        # Preferir ODBC Driver 18, luego 17
        for driver in ['{ODBC Driver 18 for SQL Server}', '{ODBC Driver 17 for SQL Server}']:
            if driver in available_drivers:
                return driver
        
        # Fallback a FreeTDS si está disponible
        if '{FreeTDS}' in available_drivers:
            return '{FreeTDS}'
        
        # Si no hay ninguno disponible, retornar el preferido y dejar que falle con error claro
        return '{ODBC Driver 18 for SQL Server}'

def get_sql_config():
    """
    Obtiene la configuración de SQL Server desde:
    1. Streamlit secrets (para deploy en cloud)
    2. Variables de entorno (.env para desarrollo local)
    """
    driver = get_sql_driver()
    
    try:
        # Intentar cargar desde Streamlit secrets
        import streamlit as st
        if hasattr(st, 'secrets') and 'sqlserver' in st.secrets:
            return {
                'server': st.secrets['sqlserver']['server'],
                'port': int(st.secrets['sqlserver']['port']),
                'database': st.secrets['sqlserver']['database'],
                'username': st.secrets['sqlserver']['username'],
                'password': st.secrets['sqlserver']['password'],
                'driver': driver
            }
    except:
        pass
    
    # Si no hay secrets, usar variables de entorno
    return {
        'server': os.getenv('SQL_SERVER', '10.10.1.252'),
        'port': int(os.getenv('SQL_PORT', '1433')),
        'database': os.getenv('SQL_DATABASE', 'ciex'),
        'username': os.getenv('SQL_USERNAME', 'jguzman'),
        'password': os.getenv('SQL_PASSWORD', 'Df2kS5LR6rpQ'),
        'driver': driver
    }

def get_api_config():
    """
    Obtiene la configuración de la API WorldFleet desde:
    1. Streamlit secrets (para deploy en cloud)
    2. Variables de entorno (.env para desarrollo local)
    """
    try:
        # Intentar cargar desde Streamlit secrets
        import streamlit as st
        if hasattr(st, 'secrets') and 'api' in st.secrets:
            return {
                'username': st.secrets['api']['username'],
                'password': st.secrets['api']['password'],
                'empresa': st.secrets['api']['empresa'],
                'url': st.secrets['api']['url']
            }
    except:
        pass
    
    # Si no hay secrets, usar variables de entorno
    return {
        'username': os.getenv('API_USERNAME', 'wsascension'),
        'password': os.getenv('API_PASSWORD', 'Ascension24!'),
        'empresa': os.getenv('API_EMPRESA', 'ASCENSION'),
        'url': os.getenv('API_URL', 'https://www.worldfleetlog.com/WebFleetStationServices/Online.asmx')
    }

def get_connection_string():
    """Genera el string de conexión para SQL Server"""
    config = get_sql_config()
    
    connection_string = (
        f"DRIVER={config['driver']};"
        f"SERVER={config['server']},{config['port']};"
        f"DATABASE={config['database']};"
        f"UID={config['username']};"
        f"PWD={config['password']};"
        f"TrustServerCertificate=yes;"
    )
    
    return connection_string
