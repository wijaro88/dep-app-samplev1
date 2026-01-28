# Configuración de Secretos para Streamlit

Este proyecto requiere configurar secretos para conectarse a SQL Server y a la API de WorldFleet.

## Configuración Local

1. Copia el archivo `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml`
2. Edita `.streamlit/secrets.toml` con tus credenciales reales
3. El archivo `secrets.toml` está en `.gitignore` y NO se subirá al repositorio

## Configuración en Streamlit Cloud

Para desplegar esta aplicación en Streamlit Cloud:

1. Ve a https://share.streamlit.io/
2. Conecta tu repositorio GitHub
3. En la configuración de la app, ve a "Secrets"
4. Copia y pega el siguiente contenido (reemplazando con tus credenciales reales):

```toml
# Configuración de SQL Server
[sqlserver]
server = "10.10.1.252"
port = 1433
database = "ciex"
username = "jguzman"
password = "Df2kS5LR6rpQ"
driver = "SQL Server"

# Configuración de API WorldFleet
[api]
username = "wsascension"
password = "Ascension24!"
empresa = "ASCENSION"
url = "https://www.worldfleetlog.com/WebFleetStationServices/Online.asmx"
```

## Uso en el Código

Para acceder a los secretos en tu código Streamlit:

```python
import streamlit as st

# SQL Server
server = st.secrets["sqlserver"]["server"]
database = st.secrets["sqlserver"]["database"]
username = st.secrets["sqlserver"]["username"]
password = st.secrets["sqlserver"]["password"]

# API
api_user = st.secrets["api"]["username"]
api_pass = st.secrets["api"]["password"]
api_empresa = st.secrets["api"]["empresa"]
```

## Seguridad

⚠️ **IMPORTANTE**: 
- Nunca compartas el archivo `secrets.toml` en Git
- No incluyas credenciales en el código fuente
- Usa variables de entorno o el sistema de secretos de Streamlit
