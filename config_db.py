"""
Configuración de conexión a SQL Server y API
Lee desde variables de entorno (.env) o Streamlit secrets
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

def get_sql_config():
    """
    Obtiene la configuración de SQL Server desde:
    1. Streamlit secrets (para deploy en cloud)
    2. Variables de entorno (.env para desarrollo local)
    """
    try:
        # Intentar cargar desde Streamlit secrets
        import streamlit as st
        if hasattr(st, 'secrets') and 'sql_server' in st.secrets:
            return {
                'server': st.secrets['sql_server']['server'],
                'port': int(st.secrets['sql_server']['port']),
                'database': st.secrets['sql_server']['database'],
                'username': st.secrets['sql_server']['username'],
                'password': st.secrets['sql_server']['password'],
                'driver': st.secrets['sql_server'].get('driver', '{SQL Server}')
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
        'driver': '{' + os.getenv('SQL_DRIVER', 'SQL Server') + '}'
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
