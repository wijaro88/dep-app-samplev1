# Deploy en Streamlit Cloud

## Archivos creados para deploy:

### 1. `.env` (LOCAL - NO SUBIR A GIT)
Variables de entorno para desarrollo local

### 2. `.env.example`
Plantilla de variables de entorno

### 3. `requirements.txt`
Dependencias de Python para Streamlit Cloud

### 4. `.streamlit/secrets.toml.example`
Plantilla para secrets de Streamlit Cloud

### 5. `.gitignore`
Evita subir archivos sensibles

---

## Pasos para deploy en Streamlit Cloud:

### 1. Subir código a GitHub
```bash
git init
git add .
git commit -m "Dashboard de vehículos con SQL Server"
git remote add origin <tu-repo>
git push -u origin main
```

### 2. Configurar secrets en Streamlit Cloud

Ve a **Streamlit Cloud > App Settings > Secrets** y pega:

```toml
[sql_server]
server = "10.10.1.252"
port = 1433
database = "ciex"
username = "jguzman"
password = "Df2kS5LR6rpQ"
driver = "SQL Server"
```

### 3. Deploy
- Conecta tu repositorio de GitHub
- Selecciona `dashboard_vehiculos_sql.py` como archivo principal
- Click en "Deploy"

---

## Desarrollo local

Las credenciales se leen automáticamente desde `.env`:
- ✅ No necesitas cambiar código
- ✅ No expones credenciales en el código
- ✅ Mismo código funciona local y en cloud

---

## Importante

- ⚠️ **NUNCA** subas `.env` a GitHub
- ⚠️ El servidor SQL debe ser accesible desde internet para Streamlit Cloud
- ⚠️ Considera usar VPN o túnel SSH si el servidor está en red privada
