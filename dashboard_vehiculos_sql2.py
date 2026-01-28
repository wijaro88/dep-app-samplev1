import streamlit as st
import pandas as pd
import requests
from lxml import etree
from datetime import datetime, time as dt_time
import time
import numpy as np
from db_manager import VehiculosDB
import streamlit.components.v1 as components
import folium
from streamlit_folium import st_folium
from io import BytesIO

# Configuración de la página
st.set_page_config(
    page_title="Dashboard Para el Seguimiento de la Flota de La Ascension S.A.",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS base para reducir efectos de carga
st.markdown("""
<style>
    /* Reducir el efecto de carga */
    .stSpinner > div {
        border-color: rgba(0,0,0,0.1) !important;
    }
</style>
""", unsafe_allow_html=True)

# Prevenir el overlay de "Running..." 
if 'initialized' not in st.session_state:
    st.session_state.initialized = True

# Inicializar DB (sin cache para permitir actualización de métodos)
def get_db():
    return VehiculosDB()

db = get_db()

# Registrar sesión al iniciar (con manejo de errores)
try:
    db.registrar_sesion()
except Exception as e:
    print(f"⚠️ No se pudo registrar la sesión inicial: {e}")

# ==================== FUNCIONES DE PARSEO ====================

def normalize_text(text):
    """Normaliza caracteres especiales en el texto"""
    if not text:
        return None
    return (
        text.replace("?", "í")
            .replace("Aceleraci?n", "Aceleración")
            .replace("Sat?lites", "Satélites")
            .replace("Veh?culo", "Vehículo")
    )

def parse_tooltip(tooltip):
    """Parsea el tooltip y extrae los datos en formato diccionario"""
    tooltip = normalize_text(tooltip)
    data = {}
    
    if not tooltip:
        return data
    
    for item in tooltip.split("#"):
        if "=" in item:
            key, value = item.split("=", 1)
            data[key.strip()] = value.strip()
    
    return data

def parse_response(xml_content):
    """Parsea la respuesta XML y retorna un DataFrame con los datos de vehículos"""
    root = etree.fromstring(xml_content)
    
    ns = {
        "soap": "http://schemas.xmlsoap.org/soap/envelope/",
        "ns": "http://tempuri.org/"
    }
    
    vehicles = root.xpath(".//ns:CarOnlinePosItemInfo", namespaces=ns)
    
    rows = []
    
    for v in vehicles:
        tooltip_data = parse_tooltip(
            v.findtext("ns:Vehicle_Tool_Tip", namespaces=ns)
        )
        
        status_code = v.findtext("ns:Vehicle_Online_Status", namespaces=ns)
        
        status_map = {
            "1": "Online",
            "2": "Idle",
            "3": "Offline"
        }
        
        rows.append({
            "vehiculo": v.findtext("ns:Vehicle_Label", namespaces=ns),
            "hora_evento": v.findtext("ns:Event_Time", namespaces=ns),
            "evento": tooltip_data.get("Evento"),
            "latitud": float(v.findtext("ns:Vehicle_Latitude", namespaces=ns)),
            "longitud": float(v.findtext("ns:Vehicle_Longitude", namespaces=ns)),
            "estado_gps": tooltip_data.get("Estado GPS"),
            "estado_online": status_map.get(status_code, "Desconocido"),
            "kilometraje": float(tooltip_data.get("Kilometraje", 0)),
            "velocidad": float(tooltip_data.get("Velocidad", 0)),
            "satelites": int(tooltip_data.get("Satélites", 0)),
            "region": v.findtext("ns:REGION_NAME", namespaces=ns)
        })
    
    return pd.DataFrame(rows)

def detectar_alertas_velocidad(df, umbral=50):
    """Detecta vehículos con velocidad superior al umbral y los guarda en BD"""
    alertas = df[df['velocidad'] > umbral].copy()
    
    for _, alerta in alertas.iterrows():
        db.insertar_alerta(
            vehiculo=alerta['vehiculo'],
            velocidad=alerta['velocidad'],
            latitud=alerta['latitud'],
            longitud=alerta['longitud'],
            evento=alerta.get('evento', 'N/A'),
            umbral=umbral
        )

# ==================== INICIO AUTOMÁTICO DE GUARDADO ====================
# Esta función se ejecuta APENAS se levanta el servidor de Streamlit
# NO espera a que se renderice el dashboard

def iniciar_guardado_automatico():
    """Guarda automáticamente los datos de la API en la BD cada vez que se llama"""
    try:
        # Obtener datos desde la API (respeta cache de 65s si aplica)
        datos = obtener_datos_api()
        if datos is not None and not datos.empty:
            # Guardar en BD
            insertar_posiciones(datos)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            print(f"[{timestamp}] ✅ Datos guardados automáticamente en BD ({len(datos)} registros)")
            return True
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            print(f"[{timestamp}] ⚠️ API no disponible")
            return False
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        print(f"[{timestamp}] ❌ Error guardando datos: {e}")
        return False

# Ejecutar guardado automático SOLO una vez al inicio del servidor
if 'guardado_inicial' not in st.session_state:
    st.session_state.guardado_inicial = True
    iniciar_guardado_automatico()

# ==================== DATOS DE SEDES ====================

SEDES_EMPRESA = {
    'Barranquilla': (10.998112635869258, -74.80390214071542),
    'Bogotá': (4.622712983211501, -74.07517069061534),
    'Bucaramanga': (7.113322820901757, -73.11220738470941),
    'Cartagena': (10.394388449972752, -75.48626155078588),
    'Cali': (3.4199006005660775, -76.54521424495998),
    'Cúcuta': (7.885453423822413, -72.49784312668594),
    'Florencia': (1.6119228517796227, -75.6107601099816),
    'Ibagué': (4.43685951393222, -75.22219870673447),
    'Manizales': (5.066222549470782, -75.50921477151805),
    'Medellín': (6.2412493937293965, -75.58757801944702),
    'Mocoa': (1.1524235605207342, -76.64747761085188),
    'Neiva': (2.9298663267956453, -75.28165219092995),
    'Pasto': (1.2249440719835554, -77.28183211869232),
    'Pereira': (4.817491564263449, -75.69663948395733),
    'Popayán': (2.446338135646979, -76.60881407097398),
    'Santa Marta': (11.241062355233458, -74.19138557913598),
    'Sincelejo': (9.29862442698266, -75.393413396036),
    'Tunja': (5.532624029379286, -73.36060305203965),
    'Valledupar': (10.474422835897277, -73.25010596051824),
    'Villavicencio': (4.145116715785736, -73.64216602129447)
}

# ==================== FUNCIONES ====================

def generar_color_vehiculo(vehiculo_nombre):
    """Genera un color único, brillante y consistente para cada vehículo"""
    # Colores brillantes y saturados predefinidos
    colores_brillantes = [
        '#FF0000',  # Rojo brillante
        '#0000FF',  # Azul brillante
        '#00FF00',  # Verde brillante
        '#FF00FF',  # Magenta
        '#00FFFF',  # Cyan
        '#FF6600',  # Naranja
        '#9900FF',  # Púrpura
        '#FFFF00',  # Amarillo
        '#FF0099',  # Rosa fuerte
        '#00FF99',  # Verde agua
        '#FF3300',  # Rojo naranja
        '#0066FF',  # Azul real
        '#CC00FF',  # Violeta
        '#FF9900',  # Naranja dorado
        '#00CC00',  # Verde oscuro
        '#FF0066',  # Rosa rojo
        '#0099FF',  # Azul cielo
        '#FF6699',  # Rosa pastel oscuro
        '#99FF00',  # Lima
        '#6600FF',  # Índigo
    ]
    
    # Usar hash del nombre para seleccionar color consistente
    indice = hash(vehiculo_nombre) % len(colores_brillantes)
    return colores_brillantes[indice]

def get_sesion_actual():
    """Determina si estamos en sesión AM o PM"""
    hora_actual = datetime.now().time()
    mediodia = dt_time(12, 0, 0)
    return "AM" if hora_actual < mediodia else "PM"

@st.cache_data(ttl=65)
def obtener_datos_api(usuario, clave, empresa):
    """Obtiene los datos de la API (limitada a 1 consulta cada 60 segundos)"""
    
    url = "https://www.worldfleetlog.com/WebFleetStationServices/Online.asmx"
    
    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema"
               xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Header>
    <LoginInfo xmlns="http://tempuri.org/">
      <Username>{usuario}</Username>
      <Password>{clave}</Password>
      <Company>{empresa}</Company>
    </LoginInfo>
  </soap:Header>
  <soap:Body>
    <GetCarsInfo xmlns="http://tempuri.org/" />
  </soap:Body>
</soap:Envelope>"""
    
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': 'http://tempuri.org/GetCarsInfo'
    }
    
    try:
        response = requests.post(url, data=soap_body, headers=headers, timeout=30)
        
        if response.status_code == 200:
            df = parse_response(response.content)
            return df, None
        elif response.status_code == 500:
            return None, "⏳ API en cooldown (límite: 1 consulta cada 60 segundos). Espera unos segundos..."
        else:
            return None, f"Error {response.status_code}: {response.text[:200]}"
    
    except requests.exceptions.Timeout:
        return None, "⏱️ Timeout: La API tardó mucho en responder"
    except Exception as e:
        return None, f"Error de conexión: {str(e)}"

# ==================== VENTANA DE DESCARGA DE DATA ====================
@st.dialog("📥 Descarga de Data", width="large")
def ventana_descarga_data():
    """Ventana emergente para descargar datos filtrados de la base de datos"""
    st.markdown("### Filtros de Descarga")
    st.info("Selecciona los filtros para descargar los datos de la base de datos")
    
    # Obtener todos los datos disponibles
    df_total = db.obtener_todas_posiciones(dias=365)  # Último año
    
    if df_total.empty:
        st.warning("No hay datos disponibles en la base de datos")
        return
    
    # Asegurar que timestamp es datetime
    df_total['timestamp'] = pd.to_datetime(df_total['timestamp'])
    
    # Filtros
    col1, col2 = st.columns(2)
    
    with col1:
        # Filtro por fechas
        fecha_min = df_total['timestamp'].dt.date.min()
        fecha_max = df_total['timestamp'].dt.date.max()
        
        # Calcular fecha inicio por defecto (7 días atrás o fecha_min si es más reciente)
        fecha_inicio_default = max(fecha_min, fecha_max - pd.Timedelta(days=7))
        
        fecha_inicio = st.date_input(
            "Fecha inicio:",
            value=fecha_inicio_default,
            min_value=fecha_min,
            max_value=fecha_max
        )
        
        fecha_fin = st.date_input(
            "Fecha fin:",
            value=fecha_max,
            min_value=fecha_min,
            max_value=fecha_max
        )
    
    with col2:
        # Filtro por horas
        hora_inicio = st.time_input("Hora inicio:", value=dt_time(0, 0))
        hora_fin = st.time_input("Hora fin:", value=dt_time(23, 59))
    
    # Filtro por vehículo
    vehiculos_disponibles = ['Todos'] + sorted(df_total['vehiculo'].unique().tolist())
    vehiculo_filtro = st.multiselect(
        "Vehículos:",
        vehiculos_disponibles,
        default=['Todos']
    )
    
    # Filtro por estado
    estados_disponibles = ['Todos'] + sorted(df_total['estado_online'].unique().tolist())
    estado_filtro = st.multiselect(
        "Estados:",
        estados_disponibles,
        default=['Todos']
    )
    
    st.divider()
    
    # Aplicar filtros
    df_filtrado = df_total.copy()
    
    # Filtrar por fechas
    df_filtrado = df_filtrado[
        (df_filtrado['timestamp'].dt.date >= fecha_inicio) & 
        (df_filtrado['timestamp'].dt.date <= fecha_fin)
    ]
    
    # Filtrar por horas
    df_filtrado = df_filtrado[
        (df_filtrado['timestamp'].dt.time >= hora_inicio) & 
        (df_filtrado['timestamp'].dt.time <= hora_fin)
    ]
    
    # Filtrar por vehículo
    if 'Todos' not in vehiculo_filtro and len(vehiculo_filtro) > 0:
        df_filtrado = df_filtrado[df_filtrado['vehiculo'].isin(vehiculo_filtro)]
    
    # Filtrar por estado
    if 'Todos' not in estado_filtro and len(estado_filtro) > 0:
        df_filtrado = df_filtrado[df_filtrado['estado_online'].isin(estado_filtro)]
    
    # Mostrar estadísticas
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        st.metric("Registros encontrados", f"{len(df_filtrado):,}")
    with col_stat2:
        st.metric("Vehículos únicos", len(df_filtrado['vehiculo'].unique()))
    with col_stat3:
        tamaño_mb = len(df_filtrado) * 0.001  # Estimación aproximada
        st.metric("Tamaño estimado", f"{tamaño_mb:.2f} MB")
    
    # Vista previa
    if not df_filtrado.empty:
        with st.expander("👁️ Vista Previa (primeros 100 registros)", expanded=False):
            df_preview = df_filtrado.head(100).copy()
            df_preview['timestamp'] = df_preview['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
            st.dataframe(df_preview, use_container_width=True, height=300)
        
        st.divider()
        
        # Botones de descarga
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            # Descargar como CSV
            df_descarga = df_filtrado.copy()
            df_descarga['timestamp'] = df_descarga['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
            csv = df_descarga.to_csv(index=False).encode('utf-8-sig')
            
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name=f"data_flota_{fecha_inicio}_{fecha_fin}.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary"
            )
        
        with col_btn2:
            # Descargar como Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_descarga.to_excel(writer, index=False, sheet_name='Datos Flota')
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 Descargar Excel",
                data=excel_data,
                file_name=f"data_flota_{fecha_inicio}_{fecha_fin}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    else:
        st.warning("⚠️ No se encontraron registros con los filtros seleccionados")

# ==================== INTERFAZ ====================

st.title("🚗 Dashboard Para el Seguimiento de la Flota de La Ascension S.A.")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Credenciales ocultas (hardcodeadas)
    usuario = "wsascension"
    clave = "Ascension24!"
    empresa = "ASCENSION"
    
    # Solo mostrar nombre de la empresa
    st.info(f"🏢 Empresa: **{empresa}**")
    
    st.divider()
    
    auto_refresh = st.checkbox("🔄 Auto-actualizar cada 30 segundos", value=False)
    st.caption("💡 Usa el botón 'Actualizar Ahora' para refrescar manualmente")
    
    # Opción para pausar mientras se navega (activada por defecto)
    if auto_refresh:
        pausar_navegacion = st.checkbox("⏸️ Pausar durante navegación en mapa", value=True)
        st.caption("✓ Evita que el mapa se resetee mientras lo exploras")
    else:
        pausar_navegacion = False
    
    st.caption("⚠️ API limitada a 1 consulta cada 60 segundos")
    
    st.divider()
    
    st.subheader("⚙️ Alertas")
    umbral_velocidad = st.slider("Umbral de velocidad (km/h)", 30, 100, 50, 5)
    
    # Activar/desactivar alertas sonoras
    alertas_sonoras = st.checkbox("🔊 Alertas sonoras", value=True)
    if alertas_sonoras:
        st.caption("✓ Sonará cuando haya nuevas alertas de velocidad")
    
    st.divider()
    
    # Mostrar sesión actual
    sesion_actual = get_sesion_actual()
    st.info(f"📅 Sesión: **{sesion_actual}** ({datetime.now().strftime('%Y-%m-%d')})")
    st.caption("💡 Usa la pestaña 'Históricos' para ver datos de fechas anteriores")
    
    if st.button("🔄 Actualizar Ahora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    # Botón de descarga de data
    if st.button("📥 Descarga de Data", use_container_width=True, type="secondary"):
        ventana_descarga_data()
    
    st.divider()
    
    # Estadísticas de BD
    stats = db.obtener_estadisticas_sesion()
    st.metric("Registros en BD", stats['total_registros'])
    st.metric("Vehículos únicos", stats['total_vehiculos'])

# 1. PRIMERO: Cargar datos históricos de la BD (siempre disponibles)
# Cargar últimos 7 días por defecto para tener datos suficientes
@st.cache_data(ttl=10)  # Cache por 10 segundos
def cargar_datos_historicos(dias=7):
    return db.obtener_todas_posiciones(dias=dias)

df_historico = cargar_datos_historicos()

# 2. SEGUNDO: Intentar actualizar con datos de la API (solo si el usuario presiona actualizar)
# El guardado inicial ya se hizo al levantar el servidor
df_api, error_api = obtener_datos_api(usuario, clave, empresa)

# Si la API respondió correctamente, guardar en BD
if df_api is not None and not df_api.empty:
    registros_nuevos = db.insertar_posiciones(df_api)
    detectar_alertas_velocidad(df_api, umbral=umbral_velocidad)
    db.actualizar_estadisticas_sesion()
    
    # Limpiar cache para forzar recarga de datos frescos
    cargar_datos_historicos.clear()
    
    # Recargar datos históricos con los nuevos datos
    df_historico = cargar_datos_historicos()
    
    estado_api = "✅ API actualizada"
elif error_api:
    if "cooldown" in error_api or "500" in error_api:
        estado_api = f"⏳ {error_api}"
    else:
        estado_api = f"❌ {error_api}"
else:
    estado_api = "⚠️ Sin respuesta de API"

# SIEMPRE usar los últimos datos de la BD para el mapa
# Obtener último registro de cada vehículo para mostrar posición actual
if not df_historico.empty:
    df = df_historico.sort_values('timestamp').groupby('vehiculo').tail(1).reset_index(drop=True)
else:
    df = pd.DataFrame()

# Mostrar info
col_tiempo1, col_tiempo2, col_tiempo3 = st.columns([2, 2, 1])
with col_tiempo1:
    st.caption(f"⏰ Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with col_tiempo2:
    inicio_sesion = "08:00 AM" if sesion_actual == "AM" else "12:00 PM"
    st.caption(f"📊 Rastreo desde: {inicio_sesion}")
with col_tiempo3:
    if auto_refresh:
        st.caption("🟢 Auto-refresh activo")

# ==================== DASHBOARD POWER BI ====================
# El iframe se carga usando un contenedor estable para evitar recargas innecesarias
# Power BI se actualiza automáticamente desde Fabric, independientemente de Streamlit
if 'powerbi_loaded' not in st.session_state:
    st.session_state.powerbi_loaded = True

st.markdown("## 📊 Dashboard Flota Vehicular - METRICAS")
#st.caption("🔄 Este dashboard se actualiza automáticamente desde Microsoft Fabric")

# Iframe de Power BI embebido - PRINCIPAL (100% ancho x 950px)
powerbi_html = """
<iframe title="flota_Vehicular" 
        width="100%" 
        height="950" 
        src="https://app.powerbi.com/view?r=eyJrIjoiMDliYzY2M2UtMzRjYi00MDliLThlMzAtZjFkNjM4Y2I4MzMyIiwidCI6IjYwNjZiMGQ0LTRmYzgtNDMzNS05NjdiLWJmZDFmNzQ2Y2I0MSIsImMiOjR9" 
        frameborder="0" 
        allowFullScreen="true">
</iframe>
"""
components.html(powerbi_html, height=970, scrolling=True)

st.divider()
st.markdown("## 🗺️ Monitoreo en Tiempo Real")
st.divider()

# Mostrar estado de la API
if "cooldown" in estado_api or "500" in estado_api:
    st.warning(estado_api)
    st.info("📊 Mostrando datos de la base de datos")
elif "❌" in estado_api:
    st.warning(f"{estado_api} - Mostrando datos de BD")
elif "✅" in estado_api:
    st.success(estado_api, icon="✅")
# Si no hay datos ni en BD ni en API
if (df is None or df.empty) and df_historico.empty:
    st.warning("⚠️ No hay datos disponibles. Esperando primera actualización de la API...")
    st.stop()

# Si solo hay datos históricos, mostrar desde BD
if df.empty and not df_historico.empty:
    st.info("📊 Mostrando última posición conocida de cada vehículo desde la base de datos")
    df = df_historico.sort_values('timestamp').groupby('vehiculo').tail(1).reset_index(drop=True)

# MÉTRICAS
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Total Vehículos", len(df))
with col2:
    online = len(df[df['estado_online'] == 'Online'])
    st.metric("Online", online)
with col3:
    idle = len(df[df['estado_online'] == 'Idle'])
    st.metric("Idle", idle)
with col4:
    offline = len(df[df['estado_online'] == 'Offline'])
    st.metric("Offline", offline)
with col5:
    alertas_recientes = db.obtener_alertas_recientes(minutos=5)
    st.metric("⚠️ Alertas (5min)", len(alertas_recientes))

st.divider()

# ALERTAS
alertas_hora = db.obtener_alertas_recientes(minutos=60, solo_pendientes=True)

# Sistema de alertas sonoras
if alertas_sonoras and not alertas_hora.empty:
    # Inicializar contador de alertas previas
    if 'alertas_anteriores' not in st.session_state:
        st.session_state.alertas_anteriores = set()
    
    # Obtener IDs de alertas actuales
    alertas_actuales = set(alertas_hora['id'].tolist())
    
    # Detectar nuevas alertas
    nuevas_alertas = alertas_actuales - st.session_state.alertas_anteriores
    
    if len(nuevas_alertas) > 0:
        # Reproducir sonido de alerta
        st.markdown(f"""
        <audio autoplay>
            <source src="data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIGmi78eOaTRALUKfj7K1JEgxFmtvz1ImEPATGf9DTOmlxPG/h8duqYzUgCEyo6Oq0ZxoIVKfc69qBNAwYcrbs67tiIQYvic7z14g2Bxppvevlm1ETDlSo4+6uTRQMRZrb89OJfwTGgNHSOmlvPG/k8d2oYjQgB0yn6Ou1ZxoHVKfc6diBNAwXcrXs6rtiIQYuidDz1og1Bxppve3km08TDlSo4+6uTRQMRZrb89KJfwTGgNHSOWlvO2/k8d2oYjQfB0yo6Ou1aBkHU6fc6dmBMwwXcbXs6rtiIQYvit/y14o1Bxppu+3lm08TC1Om4u6tThQMRZvb89KJfwTGgNHSONlvO2/k8d2oYjQfB0yn6Ou0ZxkHVKfb6dmBMwwXcbXs6rtiIQYvit/y14o1Bxppue3lm08TC1On4u6tThQMRZvb89KJfwTGgNHSONlvO2/k8d2oYjQfB0yn6Ou0ZxkHVKfb6dmBMwwXcbXs6rtiIQYvit/y14o1Bxppue3lm08TC1On4u6tThQMRZvb89KJfwTGgNHSONlvO2/k8d2oYjQfB0yn6Ou0ZxkHVKfb6dmBMwwXcbXs6rtiIQYvit/y14o1Bxppue3lm08TC1On4u6tThQMRZvb89KJfwTGgNHSONlvO2/k8d2oYjQfB0yn6Ou0ZxkHVKfb6dmBMwwXcbXs6rtiIgYvit/y14o1Bxppue3lm08TC1On4u6tThQMRZvb89KJfwTGgNHSONlvO2/k8d2oYjQfB0yn6Ou0ZxkHVKfb6dmBMwwXcbXs6rtiIgYvit/y14o1Bxppue3lm08TC1On4u6tThQMRZvb89KJfwTGgNHSONlvO2/k8d2oYjQfB0yn6Ou0ZxkHVKfb6dmBMwwXcbXs6rtiIgYvit/y14o1Bxppue3lm08TC1On4u6tThQMRZvb89KJfwTGgNHSONlvO2/k8d2oYjQfB0yn6Ou0ZxkHVKfb6dmBMwwXcbXs6rtiIgYvit/y14o1Bxppue3lm08TC1On4u6tThQMRZvb89KJfwTGgNHSONlvO2/k8d2oYjQfB0yn6Ou0ZxkHVKfb6dmBMwwXcbXs6rtiIgYvit/y14o1Bxppue3lm08TC1On4u6tThQMRZvb89KJfwTGgNHSONlvO2/k8d2oYjQfB0yn6Ou0ZxkHVKfb6dmBMwwXcbXs6rtiIgYvit/y14o1Bxppue3lm08TC1On4u6tThQMRZvb89KJfwTGgNHSONlvO2/k8d2oYjQfB0yn6Ou0ZxkHVKfb6dmBMwwXcbXs6rtiIgYvit/y14o1Bxppue3lm08TC1On4u6tThQMRZvb89KJfwTGgNHSONlvO2/k8d2oYjQfB0yn6Ou0ZxkHVKfb6dmBMwwXcbXs6rtiIgY=" type="audio/wav">
        </audio>
        """, unsafe_allow_html=True)
    
    # Actualizar alertas anteriores
    st.session_state.alertas_anteriores = alertas_actuales

if not alertas_hora.empty:
    # Header con botón de descarga
    col_title, col_download = st.columns([4, 1])
    with col_title:
        st.markdown(f"🚨 **ALERTAS PENDIENTES DE VELOCIDAD** (Última hora: {len(alertas_hora)})")
    with col_download:
        # Preparar Excel para descarga
        buffer = BytesIO()
        df_descarga = alertas_hora[['timestamp', 'vehiculo', 'velocidad', 'umbral_configurado', 'evento', 'latitud', 'longitud']].copy()
        df_descarga.columns = ['Fecha/Hora', 'Vehículo', 'Velocidad (km/h)', 'Umbral (km/h)', 'Evento', 'Latitud', 'Longitud']
        df_descarga['Fecha/Hora'] = df_descarga['Fecha/Hora'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df_descarga.to_excel(buffer, index=False, sheet_name='Alertas')
        
        st.download_button(
            label="📥",
            data=buffer.getvalue(),
            file_name=f"alertas_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Descargar alertas en Excel"
        )
    
    with st.expander("Ver detalles de alertas pendientes", expanded=True):
        st.caption("⚠️ Haz clic en cada vehículo para ver sus alertas. Agrega comentario opcional y click en 'Atender'")
        
        # Agrupar alertas por vehículo
        vehiculos_con_alertas = alertas_hora.groupby('vehiculo')
        
        for vehiculo, alertas_vehiculo in vehiculos_con_alertas:
            # Mostrar cada vehículo como un expander colapsable
            num_alertas = len(alertas_vehiculo)
            
            # Determinar urgencia del vehículo según la alerta más reciente
            alerta_mas_reciente = alertas_vehiculo.iloc[0]
            tiempo_trans = (datetime.now() - alerta_mas_reciente['timestamp']).total_seconds()
            
            if tiempo_trans < 300:
                icono = "🔴"
            elif tiempo_trans < 900:
                icono = "🟠"
            else:
                icono = "🟡"
            
            with st.expander(f"{icono} **{vehiculo}** - {num_alertas} alerta{'s' if num_alertas > 1 else ''}", expanded=False):
                # Mostrar cada alerta del vehículo
                for idx, alerta in alertas_vehiculo.iterrows():
                    tiempo_trans = (datetime.now() - alerta['timestamp']).total_seconds()
                    
                    if tiempo_trans < 300:
                        color = "🔴"
                        urgencia = "URGENTE"
                    elif tiempo_trans < 900:
                        color = "🟠"
                        urgencia = "IMPORTANTE"
                    else:
                        color = "🟡"
                        urgencia = "ATENCIÓN"
                    
                    # Contenedor para cada alerta
                    with st.container():
                        col_info, col_accion = st.columns([4, 2])
                        
                        with col_info:
                            st.warning(
                                f"{color} **{urgencia}** | Velocidad: **{alerta['velocidad']:.0f} km/h** "
                                f"(Umbral: {alerta['umbral_configurado']:.0f} km/h) | "
                                f"{alerta['timestamp'].strftime('%H:%M:%S')} | {alerta['evento']}"
                            )
                        
                        with col_accion:
                            # Input para comentario
                            comentario = st.text_input(
                                "Comentario (opcional)", 
                                key=f"comentario_alerta_{alerta['id']}",
                                placeholder="Ej: Conductor notificado",
                                label_visibility="collapsed"
                            )
                            
                            # Botón para atender
                            if st.button("✅ Atender", key=f"atender_alerta_{alerta['id']}", width='stretch'):
                                db.marcar_alerta_atendida(alerta['id'], comentario)
                                st.success(f"✅ Alerta atendida")
                                time.sleep(0.5)
                                st.rerun()
                        
                        st.markdown("---")
else:
    st.success("✅ No hay alertas pendientes en la última hora")

# Mostrar alertas atendidas
with st.expander("📋 Historial de Alertas Atendidas (Últimos 7 días)", 
                 expanded=st.session_state.get('editando_alerta') is not None):
    alertas_atendidas = db.obtener_alertas_atendidas(dias=7)
    
    if not alertas_atendidas.empty:
        st.caption(f"Total de alertas atendidas: {len(alertas_atendidas)}")
        
        # Inicializar estado de edición si no existe
        if 'editando_alerta' not in st.session_state:
            st.session_state.editando_alerta = None
        
        # Encabezados primero
        col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 1.5, 2, 2, 3, 0.7, 0.7])
        with col1:
            st.caption("**Vehículo**")
        with col2:
            st.caption("**Velocidad**")
        with col3:
            st.caption("**Hora Alerta**")
        with col4:
            st.caption("**Hora Atención**")
        with col5:
            st.caption("**Comentario**")
        with col6:
            st.caption("**Editar**")
        with col7:
            st.caption("**Guardar**")
        
        st.markdown("---")
        
        # Mostrar cada alerta con botones de acción
        for idx, row in alertas_atendidas.iterrows():
            col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 1.5, 2, 2, 3, 0.7, 0.7])
            
            with col1:
                st.text(row['vehiculo'])
            with col2:
                st.text(f"{row['velocidad']:.0f} km/h")
            with col3:
                st.text(row['timestamp'].strftime('%Y-%m-%d %H:%M'))
            with col4:
                st.text(row['fecha_atencion'].strftime('%Y-%m-%d %H:%M'))
            with col5:
                # Si está en modo edición para esta fila
                if st.session_state.editando_alerta == row['id']:
                    nuevo_comentario = st.text_input(
                        "Comentario", 
                        value=row['comentario_atencion'] or "",
                        key=f"edit_comentario_{row['id']}",
                        label_visibility="collapsed"
                    )
                else:
                    st.text(row['comentario_atencion'] or "")
            with col6:
                # Botón para activar/desactivar edición
                if st.session_state.editando_alerta == row['id']:
                    if st.button("❌", key=f"cancel_{row['id']}", help="Cancelar edición"):
                        st.session_state.editando_alerta = None
                        st.rerun()
                else:
                    if st.button("✏️", key=f"edit_{row['id']}", help="Editar comentario"):
                        st.session_state.editando_alerta = row['id']
                        st.rerun()
            with col7:
                # Botón para guardar solo aparece si está editando
                if st.session_state.editando_alerta == row['id']:
                    if st.button("💾", key=f"save_{row['id']}", help="Guardar cambios"):
                        nuevo_comentario = st.session_state.get(f"edit_comentario_{row['id']}", "")
                        db.actualizar_comentario_alerta(row['id'], nuevo_comentario)
                        st.session_state.editando_alerta = None
                        st.success("✅ Comentario actualizado")
                        st.rerun()
    else:
        st.info("No hay alertas atendidas en los últimos 7 días")



st.divider()

# Coordenadas de enfoque por región (lat, lon, zoom)
coordenadas_regiones = {
    'Todas': (4.622748, -74.075227, 12),
    'Bogotá': (4.710989, -74.072092, 11),
    'Norte': (4.720000, -74.050000, 12),
    'Sur': (4.580000, -74.130000, 12),
    'Centro': (4.650000, -74.070000, 13),
    'Occidente': (4.680000, -74.150000, 12),
    'Usaquén': (4.740000, -74.030000, 13),
    'Suba': (4.750000, -74.080000, 13),
    'Engativá': (4.700000, -74.110000, 13),
    'Fontibón': (4.680000, -74.140000, 13),
    'Kennedy': (4.620000, -74.140000, 13),
    'Puente Aranda': (4.620000, -74.110000, 13),
    'Chapinero': (4.650000, -74.060000, 13),
    'Teusaquillo': (4.640000, -74.080000, 14),
 
}

# FILTROS - Diseño mejorado con más espacio
st.markdown("### 🔍 Filtros de Búsqueda")
col_filtro1, col_filtro2, col_filtro3 = st.columns(3)

with col_filtro1:
    estados_disponibles = ['Todos'] + sorted(df['estado_online'].dropna().unique().tolist())
    filtro_estado = st.selectbox("**Estado del Vehículo**", estados_disponibles)
    
    regiones_disponibles = ['Todas'] + sorted(df['region'].dropna().unique().tolist())
    filtro_region = st.selectbox("**Región**", regiones_disponibles)

with col_filtro2:
    eventos_disponibles = ['Todos'] + sorted(df['evento'].dropna().unique().tolist())
    filtro_evento = st.selectbox("**Evento**", eventos_disponibles)
    
    placas_disponibles = ['Todas'] + sorted(df['vehiculo'].dropna().unique().tolist())
    filtro_placa = st.selectbox("**Placa del Vehículo**", placas_disponibles)

with col_filtro3:
    # Selector de estilo de mapa
    estilos_mapa = {
        "🗺️ Calles (OSM)": "open-street-map",
        "🌍 Calles (Carto)": "carto-positron",
        "🌙 Oscuro": "carto-darkmatter",
        "🛰️ Satélite": "stamen-terrain"
    }
    estilo_seleccionado = st.selectbox("**Estilo de Mapa**", list(estilos_mapa.keys()))

# Aplicar filtros
df_filtrado = df.copy()
if filtro_estado != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['estado_online'] == filtro_estado]
if filtro_region != 'Todas':
    df_filtrado = df_filtrado[df_filtrado['region'] == filtro_region]
if filtro_evento != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['evento'] == filtro_evento]
if filtro_placa != 'Todas':
    df_filtrado = df_filtrado[df_filtrado['vehiculo'] == filtro_placa]

st.caption(f"Mostrando {len(df_filtrado)} de {len(df)} vehículos")

st.divider()

# MAPAS - Mantener pestaña activa después de cambios en filtros
# Inicializar la pestaña seleccionada en session_state si no existe
if 'tab_seleccionada' not in st.session_state:
    st.session_state.tab_seleccionada = 0  # 0 = Posición Actual, 1 = Históricos, 2 = Geocercas

# Crear selector de pestaña usando botones para tener control del estado
st.markdown("### 📊 Visualización de Datos")
col_tab1, col_tab2, col_tab3 = st.columns(3)
with col_tab1:
    if st.button("📍 Posición Actual", use_container_width=True, 
                 type="primary" if st.session_state.tab_seleccionada == 0 else "secondary",
                 key="btn_tab_posicion"):
        st.session_state.tab_seleccionada = 0
        st.rerun()

with col_tab2:
    if st.button("🛣️ Recorridos Históricos", use_container_width=True,
                 type="primary" if st.session_state.tab_seleccionada == 1 else "secondary",
                 key="btn_tab_historicos"):
        st.session_state.tab_seleccionada = 1
        st.rerun()

with col_tab3:
    if st.button("🔲 Geocerca", use_container_width=True,
                 type="primary" if st.session_state.tab_seleccionada == 2 else "secondary",
                 key="btn_tab_geocercas"):
        st.session_state.tab_seleccionada = 2
        st.rerun()

st.divider()

# Mostrar contenido según la pestaña seleccionada
if st.session_state.tab_seleccionada == 0:
    # TAB 1: Posición Actual
    st.subheader("Posición Actual de Vehículos")
    
    # Información de estados
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.markdown("🟢 **Online** - En movimiento")
    with col_info2:
        st.markdown("🟡 **Idle** - Detenido")
    with col_info3:
        st.markdown("🔴 **Offline** - Sin conexión")
    
    df_mapa = df_filtrado[['vehiculo', 'latitud', 'longitud', 'estado_online', 'velocidad', 'evento', 'timestamp']].copy()
    
    if not df_mapa.empty:
        # Selector de vehículo para hacer zoom
        col_selector1, col_selector2 = st.columns([3, 1])
        with col_selector1:
            vehiculo_zoom = st.selectbox(
                "🔍 Selecciona un vehículo para hacer zoom",
                options=['Ver todos'] + sorted(df_mapa['vehiculo'].tolist()),
                key="vehiculo_zoom_selector"
            )
        with col_selector2:
            if vehiculo_zoom != 'Ver todos':
                st.metric("Estado", df_mapa[df_mapa['vehiculo'] == vehiculo_zoom]['estado_online'].iloc[0])
        
        # Determinar centro y zoom del mapa
        # Prioridad: 1) Vehículo seleccionado, 2) Placa filtrada, 3) Región filtrada, 4) Base de operaciones
        if vehiculo_zoom != 'Ver todos':
            # Zoom en el vehículo seleccionado
            veh_data = df_mapa[df_mapa['vehiculo'] == vehiculo_zoom].iloc[0]
            center_lat = veh_data['latitud']
            center_lon = veh_data['longitud']
            zoom_level = 16
        elif filtro_placa != 'Todas' and not df_filtrado.empty:
            # Zoom en la placa filtrada
            placa_data = df_filtrado[df_filtrado['vehiculo'] == filtro_placa].iloc[0]
            center_lat = placa_data['latitud']
            center_lon = placa_data['longitud']
            zoom_level = 16
        elif filtro_region != 'Todas' and not df_filtrado.empty:
            # Calcular centro de la región basándose en los vehículos de esa región
            vehiculos_region = df_filtrado[df_filtrado['region'] == filtro_region]
            if not vehiculos_region.empty:
                center_lat = vehiculos_region['latitud'].mean()
                center_lon = vehiculos_region['longitud'].mean()
                zoom_level = 13
            else:
                center_lat = 4.622748079712874
                center_lon = -74.07522665861424
                zoom_level = 12
        else:
            # Vista general (Base de Operaciones)
            center_lat = 4.622748079712874
            center_lon = -74.07522665861424
            zoom_level = 12
        
        # Crear mapa Folium centrado en Bogotá (Base de Operaciones)
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom_level,
            tiles='OpenStreetMap' if estilo_seleccionado == "🗺️ Calles (OSM)" else 
                  'CartoDB positron' if estilo_seleccionado == "🌍 Calles (Carto)" else
                  'CartoDB dark_matter' if estilo_seleccionado == "🌙 Oscuro" else
                  'OpenStreetMap',
            control_scale=True
        )
        

        # Agregar marcador de Parqueadero Registrado
        folium.Marker(
            location=[4.623951727270638, -74.08158838073267],
            popup=folium.Popup(
                '<b>🅿️ PARQUEADERO REGISTRADO</b><br>La Ascensión S.A<br>Lat: 4.623952<br>Lon: -74.081588',
                max_width=300
            ),
            tooltip='🅿️ Parqueadero Registrado',
            icon=folium.Icon(color='blue', icon='car', prefix='fa')
        ).add_to(m)
        
        # Agregar marcadores de sedes de la empresa
        for ciudad, (lat, lon) in SEDES_EMPRESA.items():
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(
                    f'<b>🏢 SEDE {ciudad.upper()}</b><br>La Ascensión S.A<br>Lat: {lat:.6f}<br>Lon: {lon:.6f}',
                    max_width=300
                ),
                tooltip=f'🏢 Sede {ciudad}',
                icon=folium.Icon(color='purple', icon='building', prefix='fa')
            ).add_to(m)
        
        # Definir configuración de iconos por estado
        config_estados = {
            'Online': {'color': 'green', 'icon': 'play', 'prefix': 'fa'},
            'Idle': {'color': 'orange', 'icon': 'pause', 'prefix': 'fa'},
            'Offline': {'color': 'red', 'icon': 'times', 'prefix': 'fa'}
        }
        
        # Colores para las líneas de trayectoria
        colores_track = {
            'Online': 'green',
            'Idle': 'orange',
            'Offline': 'red'
        }
        
        # Agregar líneas de trayectoria reciente para cada vehículo
        # Mostrar últimos 10 puntos de cada vehículo para ver movimiento
        for vehiculo in df_mapa['vehiculo'].unique():
            # Obtener últimos 10 registros de este vehículo
            df_track = df_historico[df_historico['vehiculo'] == vehiculo].sort_values('timestamp').tail(10)
            
            if len(df_track) >= 2:  # Solo si hay al menos 2 puntos
                # Crear línea de trayectoria
                coordenadas_track = [[row['latitud'], row['longitud']] for _, row in df_track.iterrows()]
                estado_veh = df_mapa[df_mapa['vehiculo'] == vehiculo]['estado_online'].iloc[0]
                color_linea = colores_track.get(estado_veh, 'gray')
                
                folium.PolyLine(
                    coordenadas_track,
                    color=color_linea,
                    weight=3,
                    opacity=0.6,
                    tooltip=f'Trayectoria {vehiculo}'
                ).add_to(m)
                
                # Agregar marcadores pequeños en cada punto del recorrido con datos
                for idx, row in df_track.iterrows():
                    tooltip_track = f"""
                    {vehiculo}
                    🕐 {row['timestamp'].strftime('%H:%M:%S')}
                    ⚡ {row['velocidad']:.0f} km/h
                    📍 {row['evento']}
                    """
                    
                    # Marcador circular pequeño
                    folium.CircleMarker(
                        location=[row['latitud'], row['longitud']],
                        radius=3,
                        color=color_linea,
                        fill=True,
                        fillColor=color_linea,
                        fillOpacity=0.7,
                        weight=1,
                        tooltip=tooltip_track
                    ).add_to(m)
        
        # Agregar marcadores de vehículos
        for idx, row in df_mapa.iterrows():
            estado = row['estado_online']
            config = config_estados.get(estado, config_estados['Offline'])
            
            popup_html = f"""
            <div style='width: 250px; font-family: Arial;'>
                <h4 style='margin: 0; color: #333;'><b>🚗 {row['vehiculo']}</b></h4>
                <hr style='margin: 5px 0;'>
                <p style='margin: 5px 0;'><b>Estado:</b> {estado}</p>
                <p style='margin: 5px 0;'><b>Fecha:</b> {row['timestamp'].strftime('%d/%m/%Y %H:%M:%S')}</p>
                <p style='margin: 5px 0;'><b>Velocidad:</b> {row['velocidad']:.0f} km/h</p>
                <p style='margin: 5px 0;'><b>Evento:</b> {row['evento']}</p>
                <p style='margin: 5px 0; color: #666;'>Lat: {row['latitud']:.5f}<br>Lon: {row['longitud']:.5f}</p>
            </div>
            """
            
            folium.Marker(
                location=[row['latitud'], row['longitud']],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{row['vehiculo']} - {estado} - {row['timestamp'].strftime('%d/%m %H:%M:%S')}",
                icon=folium.Icon(
                    color=config['color'],
                    icon=config['icon'],
                    prefix=config['prefix']
                )
            ).add_to(m)
        
        # Mostrar el mapa en Streamlit con key estable para evitar parpadeo durante auto-refresh
        # Solo cambiar key cuando cambien filtros o vehículo, no cuando cambien los datos
        filtros_key = f"{filtro_estado}_{filtro_region}_{filtro_evento}_{filtro_placa}"
        if auto_refresh:
            # Durante auto-refresh, mantener key fijo para que el mapa no se resetee
            map_key = f"mapa_posicion_{vehiculo_zoom}_{filtros_key}_stable"
        else:
            # Sin auto-refresh, incluir datos para actualización normal
            map_key = f"mapa_posicion_{vehiculo_zoom}_{len(df_mapa)}_{filtros_key}"
        
        st_folium(m, width='stretch', height=900, returned_objects=[], key=map_key)
        
        # Tabla de datos debajo del mapa (minimizada)
        st.divider()
        
        with st.expander("📋 Ver Detalle de Vehículos", expanded=False):
            # Preparar datos para mostrar
            df_tabla = df_filtrado[[
                'vehiculo', 'estado_online', 'velocidad', 'kilometraje', 
                'evento', 'region', 'hora_evento', 'satelites'
            ]].copy()
            
            # Formatear columnas
            df_tabla['velocidad'] = df_tabla['velocidad'].apply(lambda x: f"{x:.0f} km/h")
            df_tabla['kilometraje'] = df_tabla['kilometraje'].apply(lambda x: f"{x:,.0f} km")
            
            # Renombrar columnas para mejor presentación
            df_tabla.columns = ['Vehículo', 'Estado', 'Velocidad', 'Kilometraje', 
                                'Evento', 'Región', 'Hora Evento', 'Satélites']
            
            # Mostrar tabla con colores
            st.dataframe(
                df_tabla,
                width='stretch',
                height=400,
                hide_index=True
            )
    else:
        st.info("No hay vehículos para mostrar")

elif st.session_state.tab_seleccionada == 1:
    # TAB 2: Recorridos Históricos
    st.subheader("🛣️ Recorridos Históricos")
    
    # Info de registros
    st.caption(f"📊 Total de registros en BD: {len(df_historico):,}")
    
    if not df_historico.empty:
        # Asegurar que timestamp es datetime
        if 'timestamp' in df_historico.columns:
            df_historico['timestamp'] = pd.to_datetime(df_historico['timestamp'])
        
        # FILTROS DE FECHA Y VISTA
        col_filtro1, col_filtro2, col_filtro3 = st.columns([2, 2, 2])
        
        with col_filtro1:
            vista_opcion = st.radio(
                "Vista de recorridos:",
                ["Todos los vehículos", "Un vehículo"],
                index=0,  # Por defecto "Todos los vehículos"
                horizontal=True,
                key="vista_recorridos"
            )
        
        # Obtener rango de fechas disponibles
        fecha_min = df_historico['timestamp'].dt.date.min()
        fecha_max = df_historico['timestamp'].dt.date.max()
        
        with col_filtro2:
            fecha_desde = st.date_input(
                "Desde:",
                value=fecha_max,  # Por defecto hoy
                min_value=fecha_min,
                max_value=fecha_max,
                key="fecha_desde_historico"
            )
        
        with col_filtro3:
            fecha_hasta = st.date_input(
                "Hasta:",
                value=fecha_max,  # Por defecto hoy
                min_value=fecha_min,
                max_value=fecha_max,
                key="fecha_hasta_historico"
            )
        
        # Validar que fecha_desde <= fecha_hasta
        if fecha_desde > fecha_hasta:
            st.error("⚠️ La fecha 'Desde' debe ser menor o igual a la fecha 'Hasta'")
            st.stop()
        
        # Filtrar datos por rango de fechas
        df_rango = df_historico[
            (df_historico['timestamp'].dt.date >= fecha_desde) & 
            (df_historico['timestamp'].dt.date <= fecha_hasta)
        ].copy()
        
        st.info(f"📅 Mostrando datos del **{fecha_desde.strftime('%d/%m/%Y')}** al **{fecha_hasta.strftime('%d/%m/%Y')}** ({len(df_rango):,} registros)")
        
        if df_rango.empty:
            st.warning("❌ No hay datos en el rango de fechas seleccionado")
        elif vista_opcion == "Un vehículo":
            # Obtener vehículos disponibles en el rango
            vehiculos_disponibles = sorted(df_rango['vehiculo'].unique().tolist())
            
            if len(vehiculos_disponibles) == 0:
                st.warning("No hay vehículos con datos en el rango seleccionado")
            else:
                vehiculo_seleccionado = st.selectbox(
                    "Selecciona un vehículo:", 
                    vehiculos_disponibles,
                    key="vehiculo_recorrido_historico"
                )
                
                if vehiculo_seleccionado:
                    # Filtrar datos por vehículo
                    df_recorrido = df_rango[
                        df_rango['vehiculo'] == vehiculo_seleccionado
                    ].sort_values('timestamp').reset_index(drop=True)
                    
                    # Debug: mostrar información del recorrido
                    if not df_recorrido.empty:
                        st.caption(f"📍 Puntos de recorrido para **{vehiculo_seleccionado}**: {len(df_recorrido)}")
                        st.caption(f"🕐 Desde {df_recorrido['timestamp'].min()} hasta {df_recorrido['timestamp'].max()}")
                        
                        # Mostrar distribución de estados
                        estados_count = df_recorrido['estado_online'].value_counts()
                        col_est1, col_est2, col_est3, col_est4 = st.columns(4)
                        with col_est1:
                            st.metric("🟢 Online", estados_count.get('Online', 0))
                        with col_est2:
                            st.metric("🟡 Idle", estados_count.get('Idle', 0))
                        with col_est3:
                            st.metric("🔴 Offline", estados_count.get('Offline', 0))
                        with col_est4:
                            distancia_recorrida = df_recorrido['kilometraje'].max() - df_recorrido['kilometraje'].min()
                            st.metric("📏 Distancia", f"{distancia_recorrida:.1f} km")
                    else:
                        st.warning(f"❌ No se encontraron datos para {vehiculo_seleccionado} en el rango seleccionado")
                    
                    if len(df_recorrido) >= 2:
                        # Crear mapa Folium para el recorrido
                        lat_center = df_recorrido['latitud'].mean()
                        lon_center = df_recorrido['longitud'].mean()
                        
                        # Calcular zoom apropiado
                        lat_range = df_recorrido['latitud'].max() - df_recorrido['latitud'].min()
                        lon_range = df_recorrido['longitud'].max() - df_recorrido['longitud'].min()
                        max_range = max(lat_range, lon_range)
                        
                        if max_range < 0.01:
                            zoom = 15
                        elif max_range < 0.05:
                            zoom = 13
                        elif max_range < 0.1:
                            zoom = 12
                        else:
                            zoom = 11
                        
                        m_recorrido = folium.Map(
                            location=[lat_center, lon_center],
                            zoom_start=zoom,
                            tiles='OpenStreetMap' if estilo_seleccionado == "🗺️ Calles (OSM)" else 
                                  'CartoDB positron' if estilo_seleccionado == "🌍 Calles (Carto)" else
                                  'CartoDB dark_matter' if estilo_seleccionado == "🌙 Oscuro" else
                                  'OpenStreetMap'
                        )
                        
                        # Agregar marcador de Base de Operaciones
                        folium.Marker(
                            location=[4.622748079712874, -74.07522665861424],
                            popup=folium.Popup(
                                '<b>🏠 BASE DE OPERACIONES</b><br>La Ascensión S.A',
                                max_width=250
                            ),
                            tooltip='🏠 Base',
                            icon=folium.Icon(color='red', icon='home', prefix='fa')
                        ).add_to(m_recorrido)
                        
                        # Agregar marcador de Parqueadero
                        folium.Marker(
                            location=[4.623951727270638, -74.08158838073267],
                            popup=folium.Popup(
                                '<b>🅿️ PARQUEADERO REGISTRADO</b><br>La Ascensión S.A',
                                max_width=250
                            ),
                            tooltip='🅿️ Parqueadero',
                            icon=folium.Icon(color='blue', icon='car', prefix='fa')
                        ).add_to(m_recorrido)
                        
                        # Agregar marcadores de sedes de la empresa
                        for ciudad, (lat, lon) in SEDES_EMPRESA.items():
                            folium.Marker(
                                location=[lat, lon],
                                popup=folium.Popup(
                                    f'<b>🏢 SEDE {ciudad.upper()}</b><br>La Ascensión S.A',
                                    max_width=250
                                ),
                                tooltip=f'🏢 Sede {ciudad}',
                                icon=folium.Icon(color='purple', icon='building', prefix='fa')
                            ).add_to(m_recorrido)
                        
                        # Colores por estado
                        colores_estado = {
                            'Online': 'green',
                            'Idle': 'orange',
                            'Offline': 'red'
                        }
                        
                        # Colores para diferentes días
                        colores_dias = ['#FF0000', '#00FF00', '#0000FF', '#FFA500', '#800080', 
                                       '#FF1493', '#00CED1', '#FFD700', '#FF4500', '#32CD32',
                                       '#8B0000', '#006400', '#00008B', '#FF8C00', '#4B0082']
                        
                        # Dibujar líneas separadas por día con diferentes colores
                        fechas_unicas = df_recorrido['timestamp'].dt.date.unique()
                        
                        for idx_dia, fecha_dia in enumerate(fechas_unicas):
                            df_dia = df_recorrido[df_recorrido['timestamp'].dt.date == fecha_dia]
                            color_dia = colores_dias[idx_dia % len(colores_dias)]
                            
                            coordenadas_dia = [[row['latitud'], row['longitud']] for _, row in df_dia.iterrows()]
                            fecha_str = fecha_dia.strftime('%d/%m/%Y')
                            hora_inicio = df_dia.iloc[0]['timestamp'].strftime('%H:%M')
                            hora_fin = df_dia.iloc[-1]['timestamp'].strftime('%H:%M')
                            
                            folium.PolyLine(
                                coordenadas_dia,
                                color=color_dia,
                                weight=4,
                                opacity=0.7,
                                tooltip=f'{vehiculo_seleccionado} | {fecha_str} | {hora_inicio} → {hora_fin}'
                            ).add_to(m_recorrido)
                        
                        # Agregar marcadores en puntos clave
                        for idx, row in df_recorrido.iterrows():
                            color = colores_estado.get(row['estado_online'], 'gray')
                            
                            popup_html = f"""
                            <div style='width: 250px;'>
                                <b>{vehiculo_seleccionado}</b><br>
                                <hr style='margin: 5px 0;'>
                                📅 {row['timestamp'].strftime('%d/%m/%Y')}<br>
                                🕐 {row['timestamp'].strftime('%H:%M:%S')}<br>
                                📍 Lat: {row['latitud']:.6f}<br>
                                📍 Lon: {row['longitud']:.6f}<br>
                                <hr style='margin: 5px 0;'>
                                Estado: {row['estado_online']}<br>
                                ⚡ Velocidad: {row['velocidad']:.0f} km/h<br>
                                📏 Km: {row['kilometraje']:.0f}
                            </div>
                            """
                            
                            tooltip_text = f"{row['timestamp'].strftime('%d/%m %H:%M')} | {row['velocidad']:.0f} km/h"
                            
                            folium.CircleMarker(
                                location=[row['latitud'], row['longitud']],
                                radius=5,
                                popup=folium.Popup(popup_html, max_width=250),
                                tooltip=tooltip_text,
                                color=color,
                                fill=True,
                                fillColor=color,
                                fillOpacity=0.7
                            ).add_to(m_recorrido)
                        
                        # Marcador de INICIO
                        folium.Marker(
                            location=[df_recorrido.iloc[0]['latitud'], df_recorrido.iloc[0]['longitud']],
                            popup=f"<b>🏁 INICIO</b><br>{df_recorrido.iloc[0]['timestamp'].strftime('%H:%M:%S')}<br>Km: {df_recorrido.iloc[0]['kilometraje']:.0f}",
                            tooltip='🏁 Inicio',
                            icon=folium.Icon(color='green', icon='play', prefix='fa')
                        ).add_to(m_recorrido)
                        
                        # Marcador de POSICIÓN ACTUAL
                        folium.Marker(
                            location=[df_recorrido.iloc[-1]['latitud'], df_recorrido.iloc[-1]['longitud']],
                            popup=f"<b>📍 ACTUAL</b><br>{df_recorrido.iloc[-1]['timestamp'].strftime('%H:%M:%S')}<br>Vel: {df_recorrido.iloc[-1]['velocidad']:.0f} km/h<br>Km: {df_recorrido.iloc[-1]['kilometraje']:.0f}",
                            tooltip='📍 Posición Actual',
                            icon=folium.Icon(color='red', icon='flag', prefix='fa')
                        ).add_to(m_recorrido)
                        
                        # Key único para evitar parpadeo durante auto-refresh
                        if auto_refresh:
                            map_key_recorrido = f"mapa_recorrido_{vehiculo_seleccionado}_stable"
                        else:
                            map_key_recorrido = f"mapa_recorrido_{vehiculo_seleccionado}_{len(df_recorrido)}"
                        st_folium(m_recorrido, width='stretch', height=850, returned_objects=[], key=map_key_recorrido)
                        
                        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                        with col_r1:
                            st.metric("Puntos", len(df_recorrido))
                        with col_r2:
                            st.metric("Vel. Promedio", f"{df_recorrido['velocidad'].mean():.1f} km/h")
                        with col_r3:
                            st.metric("Vel. Máxima", f"{df_recorrido['velocidad'].max():.1f} km/h")
                        with col_r4:
                            duracion = (df_recorrido['timestamp'].max() - df_recorrido['timestamp'].min()).total_seconds() / 3600
                            st.metric("Duración", f"{duracion:.2f} h")
                        
                        # Tabla de datos detallados (minimizada)
                        with st.expander("📊 Ver Datos Detallados del Recorrido", expanded=False):
                            df_tabla_recorrido = df_recorrido[[
                                'timestamp', 'vehiculo', 'estado_online', 'velocidad', 
                                'kilometraje', 'evento', 'latitud', 'longitud', 'satelites'
                            ]].copy()
                            df_tabla_recorrido['timestamp'] = df_tabla_recorrido['timestamp'].dt.strftime('%d/%m/%Y %H:%M:%S')
                            df_tabla_recorrido['velocidad'] = df_tabla_recorrido['velocidad'].apply(lambda x: f"{x:.0f} km/h")
                            df_tabla_recorrido['kilometraje'] = df_tabla_recorrido['kilometraje'].apply(lambda x: f"{x:,.0f} km")
                            df_tabla_recorrido.columns = ['Fecha/Hora', 'Vehículo', 'Estado', 'Velocidad', 
                                                          'Kilometraje', 'Evento', 'Latitud', 'Longitud', 'Satélites']
                            st.dataframe(df_tabla_recorrido, use_container_width=True, hide_index=True, height=400)
                    elif len(df_recorrido) == 1:
                        st.info(f"Solo hay un punto registrado para {vehiculo_seleccionado}. Se necesitan al menos 2 puntos para mostrar el recorrido.")
                    else:
                        st.warning(f"No hay datos de recorrido para {vehiculo_seleccionado}")
        
        else:  # Vista de todos los vehículos
            st.info(f"📊 Vista de todos los vehículos del {fecha_desde.strftime('%d/%m/%Y')} al {fecha_hasta.strftime('%d/%m/%Y')}")
            
            # Verificar cuántos vehículos tienen múltiples puntos
            vehiculos = df_rango['vehiculo'].unique()
            vehiculos_con_recorrido = []
            
            for vehiculo in vehiculos:
                df_veh_hist = df_rango[df_rango['vehiculo'] == vehiculo].sort_values('timestamp')
                if len(df_veh_hist) > 1:
                    vehiculos_con_recorrido.append(vehiculo)
            
            st.caption(f"Vehículos con recorrido: {len(vehiculos_con_recorrido)} de {len(vehiculos)}")
            
            if len(vehiculos_con_recorrido) == 0:
                st.warning("No hay vehículos con suficientes puntos para mostrar recorridos. Se necesitan al menos 2 registros por vehículo.")
            else:
                # Mostrar mensaje de carga
                with st.spinner(f'📍 Generando mapa con {len(vehiculos_con_recorrido)} vehículos y {len(df_rango):,} puntos...'):
                    # Crear mapa Folium para todos los vehículos
                    lat_center = df_rango['latitud'].mean()
                    lon_center = df_rango['longitud'].mean()
                
                # Calcular zoom apropiado basado en la dispersión de datos
                lat_range = df_rango['latitud'].max() - df_rango['latitud'].min()
                lon_range = df_rango['longitud'].max() - df_rango['longitud'].min()
                max_range = max(lat_range, lon_range)
                
                if max_range < 0.1:
                    zoom_inicial = 13
                elif max_range < 0.5:
                    zoom_inicial = 11
                elif max_range < 1.0:
                    zoom_inicial = 10
                else:
                    zoom_inicial = 8
                
                m_todos = folium.Map(
                    location=[lat_center, lon_center],
                    zoom_start=zoom_inicial,
                    tiles='OpenStreetMap' if estilo_seleccionado == "🗺️ Calles (OSM)" else 
                          'CartoDB positron' if estilo_seleccionado == "🌍 Calles (Carto)" else
                          'CartoDB dark_matter' if estilo_seleccionado == "🌙 Oscuro" else
                          'OpenStreetMap'
                )
                
                # Agregar marcador de Base de Operaciones
                folium.Marker(
                    location=[4.622748079712874, -74.07522665861424],
                    popup=folium.Popup(
                        '<b>🏠 BASE DE OPERACIONES</b><br>La Ascensión S.A',
                        max_width=250
                    ),
                    tooltip='🏠 Base',
                    icon=folium.Icon(color='red', icon='home', prefix='fa')
                ).add_to(m_todos)
                
                # Agregar marcador de Parqueadero
                folium.Marker(
                    location=[4.623951727270638, -74.08158838073267],
                    popup=folium.Popup(
                        '<b>🅿️ PARQUEADERO REGISTRADO</b><br>La Ascensión S.A',
                        max_width=250
                    ),
                    tooltip='🅿️ Parqueadero',
                    icon=folium.Icon(color='blue', icon='car', prefix='fa')
                ).add_to(m_todos)
                
                # Agregar marcadores de sedes de la empresa
                for ciudad, (lat, lon) in SEDES_EMPRESA.items():
                    folium.Marker(
                        location=[lat, lon],
                        popup=folium.Popup(
                            f'<b>🏢 SEDE {ciudad.upper()}</b><br>La Ascensión S.A',
                            max_width=250
                        ),
                        tooltip=f'🏢 Sede {ciudad}',
                        icon=folium.Icon(color='purple', icon='building', prefix='fa')
                    ).add_to(m_todos)
                
                for idx, vehiculo in enumerate(vehiculos_con_recorrido):
                    df_veh_hist = df_rango[df_rango['vehiculo'] == vehiculo].sort_values('timestamp')
                    
                    # Generar color único para este vehículo
                    color_vehiculo = generar_color_vehiculo(vehiculo)
                    
                    # Información de fechas para tooltip general
                    fecha_inicio = df_veh_hist.iloc[0]['timestamp'].strftime('%d/%m/%Y %H:%M')
                    fecha_fin = df_veh_hist.iloc[-1]['timestamp'].strftime('%d/%m/%Y %H:%M')
                    
                    # Dibujar toda la trayectoria del vehículo con su color único
                    coordenadas_completas = [[row['latitud'], row['longitud']] for _, row in df_veh_hist.iterrows()]
                    
                    folium.PolyLine(
                        coordenadas_completas,
                        color=color_vehiculo,
                        weight=4,
                        opacity=0.8,
                        tooltip=f'{vehiculo} | {fecha_inicio} → {fecha_fin}'
                    ).add_to(m_todos)
                    
                    # Agregar solo algunos puntos intermedios (cada 10 registros para no saturar)
                    # Esto evita agregar miles de marcadores que hacen lento el mapa
                    puntos_a_mostrar = df_veh_hist.iloc[::max(1, len(df_veh_hist) // 20)]  # Máximo 20 puntos por vehículo
                    for idx_punto, row in puntos_a_mostrar.iterrows():
                        tooltip_punto = f"{vehiculo} | {row['timestamp'].strftime('%d/%m %H:%M')} | {row['velocidad']:.0f} km/h"
                        
                        folium.CircleMarker(
                            location=[row['latitud'], row['longitud']],
                            radius=3,
                            tooltip=tooltip_punto,
                            color=color_vehiculo,
                            fill=True,
                            fillColor=color_vehiculo,
                            fillOpacity=0.7,
                            weight=1
                        ).add_to(m_todos)
                    
                    # Marcador inicial con icono
                    folium.Marker(
                        location=[df_veh_hist.iloc[0]['latitud'], df_veh_hist.iloc[0]['longitud']],
                        popup=f"<b>🏁 INICIO - {vehiculo}</b><br>{df_veh_hist.iloc[0]['timestamp'].strftime('%d/%m/%Y %H:%M:%S')}<br>Lat: {df_veh_hist.iloc[0]['latitud']:.6f}<br>Lon: {df_veh_hist.iloc[0]['longitud']:.6f}",
                        tooltip=f'🏁 {vehiculo} | Inicio: {fecha_inicio}',
                        icon=folium.Icon(color='green', icon='play', prefix='fa')
                    ).add_to(m_todos)
                    
                    # Marcador final con icono
                    folium.Marker(
                        location=[df_veh_hist.iloc[-1]['latitud'], df_veh_hist.iloc[-1]['longitud']],
                        popup=f"<b>🏁 FIN - {vehiculo}</b><br>{df_veh_hist.iloc[-1]['timestamp'].strftime('%d/%m/%Y %H:%M:%S')}<br>Vel: {df_veh_hist.iloc[-1]['velocidad']:.0f} km/h<br>Lat: {df_veh_hist.iloc[-1]['latitud']:.6f}<br>Lon: {df_veh_hist.iloc[-1]['longitud']:.6f}",
                        tooltip=f'🏁 {vehiculo} | Fin: {fecha_fin}',
                        icon=folium.Icon(color='red', icon='stop', prefix='fa')
                    ).add_to(m_todos)
                
                # Key único para evitar parpadeo durante auto-refresh
                if auto_refresh:
                    map_key_todos = f"mapa_todos_stable"
                else:
                    map_key_todos = f"mapa_todos_{fecha_desde}_{fecha_hasta}_{len(vehiculos_con_recorrido)}"
                
                # Renderizar el mapa
                st_folium(m_todos, width='stretch', height=850, returned_objects=[], key=map_key_todos)
                
                # Métricas del mapa
                col_g1, col_g2, col_g3 = st.columns(3)
                with col_g1:
                    st.metric("Vehículos Rastreados", len(vehiculos_con_recorrido))
                with col_g2:
                    st.metric("Total Puntos", len(df_rango))
                with col_g3:
                    st.metric("Vel. Promedio General", f"{df_rango['velocidad'].mean():.1f} km/h")
                
                # Tabla de datos detallados (minimizada)
                with st.expander("📊 Ver Datos Detallados de Todos los Recorridos", expanded=False):
                    df_tabla_todos = df_rango[[
                        'timestamp', 'vehiculo', 'estado_online', 'velocidad', 
                        'kilometraje', 'evento', 'latitud', 'longitud', 'satelites'
                    ]].copy()
                    df_tabla_todos['timestamp'] = df_tabla_todos['timestamp'].dt.strftime('%d/%m/%Y %H:%M:%S')
                    df_tabla_todos['velocidad'] = df_tabla_todos['velocidad'].apply(lambda x: f"{x:.0f} km/h")
                    df_tabla_todos['kilometraje'] = df_tabla_todos['kilometraje'].apply(lambda x: f"{x:,.0f} km")
                    df_tabla_todos = df_tabla_todos.sort_values('timestamp', ascending=False)
                    df_tabla_todos.columns = ['Fecha/Hora', 'Vehículo', 'Estado', 'Velocidad', 
                                              'Kilometraje', 'Evento', 'Latitud', 'Longitud', 'Satélites']
                    st.dataframe(df_tabla_todos, use_container_width=True, hide_index=True, height=400)
    else:
        st.info("No hay datos históricos disponibles")

elif st.session_state.tab_seleccionada == 2:
    # TAB 3: GEOCERCAS
    st.subheader("🔲 Gestión de Geocercas (Límites de Zonas)")
    
    # Obtener geocercas y asignaciones
    df_geocercas = db.obtener_geocercas_activas()
    df_asignaciones = db.obtener_asignaciones_geocercas()
    df_alertas_geo = db.obtener_alertas_geocerca_activas()
    
    # Mostrar estadísticas
    col_g1, col_g2, col_g3 = st.columns(3)
    with col_g1:
        st.metric("🔲 Geocercas Activas", len(df_geocercas))
    with col_g2:
        st.metric("🚗 Vehículos Asignados", len(df_asignaciones))
    with col_g3:
        st.metric("⚠️ Alertas Activas", len(df_alertas_geo))
    
    st.divider()
    
    # Sección 1: Vista de Asignaciones (Solo lectura)
    st.markdown("### 📌 Asignaciones Actuales de Vehículos")
    st.info("ℹ️ Para modificar asignaciones, dirígete a la sección de **Configuración**")
    
    with st.expander("📋 Ver Tabla de Asignaciones", expanded=False):
        if not df_asignaciones.empty:
            # Mostrar tabla de asignaciones
            df_asignaciones_display = df_asignaciones[['vehiculo', 'geocerca_nombre']].copy()
            df_asignaciones_display.columns = ['Vehículo', 'Geocerca Asignada']
            st.dataframe(df_asignaciones_display, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ No hay vehículos asignados a geocercas")
    
    st.divider()
    
    # Sección 2: Visualizar geocercas en el mapa
    st.markdown("### 🗺️ Mapa de Geocercas")
    
    # Crear mapa centrado en Colombia
    m_geocercas = folium.Map(
        location=[4.6, -74.1],  # Centro de Colombia
        zoom_start=6,
        tiles='OpenStreetMap'
    )
    
    # Dibujar todas las geocercas
    if not df_geocercas.empty:
        for _, geocerca in df_geocercas.iterrows():
            # Crear rectángulo para la geocerca
            bounds = [
                [geocerca['lat_min'], geocerca['lon_min']],
                [geocerca['lat_max'], geocerca['lon_max']]
            ]
            
            # Contar vehículos asignados
            vehiculos_asignados = df_asignaciones[df_asignaciones['geocerca_nombre'] == geocerca['nombre']]['vehiculo'].tolist()
            num_vehiculos = len(vehiculos_asignados)
            
            folium.Rectangle(
                bounds=bounds,
                color=geocerca['color'],
                fill=True,
                fillColor=geocerca['color'],
                fillOpacity=0.2,
                weight=3,
                popup=f"<b>{geocerca['nombre']}</b><br>{geocerca['descripcion']}<br>Vehículos: {num_vehiculos}<br><small>{', '.join(vehiculos_asignados) if vehiculos_asignados else 'Sin asignar'}</small>",
                tooltip=f"{geocerca['nombre']} ({num_vehiculos} vehículos)"
            ).add_to(m_geocercas)
            
            # Agregar marcador con el nombre
            centro_lat = (geocerca['lat_min'] + geocerca['lat_max']) / 2
            centro_lon = (geocerca['lon_min'] + geocerca['lon_max']) / 2
            
            folium.Marker(
                location=[centro_lat, centro_lon],
                popup=f"<b>{geocerca['nombre']}</b>",
                tooltip=geocerca['nombre'],
                icon=folium.DivIcon(html=f"""
                    <div style="
                        font-size: 14px; 
                        font-weight: bold; 
                        color: {geocerca['color']};
                        text-shadow: 1px 1px 2px white, -1px -1px 2px white;
                        white-space: nowrap;
                    ">{geocerca['nombre']}</div>
                """)
            ).add_to(m_geocercas)
    
    # Agregar posiciones actuales de vehículos asignados
    if not df.empty and not df_asignaciones.empty:
        for _, row in df.iterrows():
            if row['vehiculo'] in df_asignaciones['vehiculo'].values:
                # Obtener geocerca asignada
                asignacion = df_asignaciones[df_asignaciones['vehiculo'] == row['vehiculo']].iloc[0]
                
                # Verificar si está dentro o fuera
                lat_ok = asignacion['lat_min'] <= row['latitud'] <= asignacion['lat_max']
                lon_ok = asignacion['lon_min'] <= row['longitud'] <= asignacion['lon_max']
                dentro = lat_ok and lon_ok
                
                # Color según si está dentro o fuera
                color_marker = 'green' if dentro else 'red'
                icon_marker = 'ok-sign' if dentro else 'warning-sign'
                
                folium.Marker(
                    location=[row['latitud'], row['longitud']],
                    popup=f"<b>{row['vehiculo']}</b><br>Zona: {asignacion['geocerca_nombre']}<br>{'✅ DENTRO' if dentro else '⚠️ FUERA DE ZONA'}<br>Vel: {row['velocidad']:.0f} km/h",
                    tooltip=f"{row['vehiculo']} - {'✅ Dentro' if dentro else '⚠️ FUERA'} - {pd.Timestamp.now().strftime('%d/%m %H:%M')}",
                    icon=folium.Icon(color=color_marker, icon=icon_marker, prefix='glyphicon')
                ).add_to(m_geocercas)
    
    st_folium(m_geocercas, width='stretch', height=600, returned_objects=[], key="mapa_geocercas")
    
    st.divider()
    
    # Sección 3: Alertas de violación de geocercas
    st.markdown("### ⚠️ Alertas de Violación de Geocercas")
    
    if not df_alertas_geo.empty:
        st.warning(f"🚨 {len(df_alertas_geo)} alertas activas de vehículos fuera de zona")
        
        # Mostrar tabla de alertas
        df_alertas_display = df_alertas_geo[['timestamp', 'vehiculo', 'geocerca_nombre', 'latitud', 'longitud']].copy()
        df_alertas_display['timestamp'] = pd.to_datetime(df_alertas_display['timestamp']).dt.strftime('%d/%m/%Y %H:%M')
        df_alertas_display.columns = ['Fecha/Hora', 'Vehículo', 'Geocerca', 'Latitud', 'Longitud']
        
        st.dataframe(df_alertas_display, use_container_width=True, hide_index=True)
        
        # Atender alertas
        col_at1, col_at2 = st.columns([2, 1])
        with col_at1:
            alerta_seleccionada = st.selectbox(
                "Seleccionar alerta para atender:",
                df_alertas_geo['id'].tolist(),
                format_func=lambda x: f"ID {x} - {df_alertas_geo[df_alertas_geo['id']==x]['vehiculo'].iloc[0]} fuera de {df_alertas_geo[df_alertas_geo['id']==x]['geocerca_nombre'].iloc[0]}",
                key="alerta_geo_seleccionada"
            )
            
            comentario_atencion = st.text_input(
                "Comentario (opcional):",
                placeholder="Ej: Vehículo autorizado a salir de zona",
                key="comentario_alerta_geo"
            )
        
        with col_at2:
            st.write("")
            st.write("")
            if st.button("✅ Marcar como Atendida", type="primary", use_container_width=True):
                db.marcar_alerta_geocerca_atendida(alerta_seleccionada, comentario_atencion)
                st.success("✅ Alerta marcada como atendida")
                time.sleep(1)
                st.rerun()
    else:
        st.success("✅ No hay alertas de geocercas activas")

# AUTO-REFRESH con control de navegación
if auto_refresh:
    # Inicializar timestamp de última actualización si no existe
    if 'ultimo_refresh' not in st.session_state:
        st.session_state.ultimo_refresh = datetime.now()
    
    # Calcular tiempo transcurrido
    tiempo_transcurrido = (datetime.now() - st.session_state.ultimo_refresh).total_seconds()
    
    # Si está en modo pausa, NO hacer rerun automático
    if pausar_navegacion:
        # Actualizar timestamp para evitar que se acumule el tiempo
        st.session_state.ultimo_refresh = datetime.now()
        st.sidebar.info("⏸️ Auto-refresh pausado - Navega libremente")
        # NO hacer st.rerun() para que la página permanezca estática
    elif tiempo_transcurrido >= 60:
        # Modo normal: actualizar cada 60 segundos (sincronizado con límite de API)
        # Guardar datos automáticamente
        iniciar_guardado_automatico()
        st.session_state.ultimo_refresh = datetime.now()
        time.sleep(0.1)  # Pequeña pausa para estabilizar
        st.rerun()
    else:
        # Mostrar cuenta regresiva solo los últimos 10 segundos
        segundos_restantes = int(60 - tiempo_transcurrido)
        if segundos_restantes > 0 and segundos_restantes <= 10:
            st.sidebar.caption(f"⏱️ Próxima actualización en {segundos_restantes}s")
        # Esperar 1 segundo antes del próximo chequeo
        time.sleep(1)
        st.rerun()

# ==================== PIE DE PÁGINA ====================
st.markdown("---")

st.markdown("<h4 style='text-align: center;'>Ing. WILSON JAVIER ROCHA ORJUELA</h4>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-weight: bold;'>ANALISTA MEDIO DE DATOS</p>", unsafe_allow_html=True)
st.write("")

subcol1, subcol2, subcol3 = st.columns(3)

with subcol1:
    st.markdown("**Empresa**")
    st.write("La Ascensión S.A")
    st.write("Bogotá, Colombia")
    st.write("Cra. 21 No. 33-28 Teusaquillo")

with subcol2:
    st.markdown("**Contacto**")
    st.write("PBX: (60-1) 3389090 Ext. 1150")
    st.write("Cel: 311 566 29 50")
    st.markdown("[wilson.rocha@laascension.com](mailto:wilson.rocha@laascension.com)")

with subcol3:
    st.markdown("**Web**")
    st.markdown("[www.laascension.com](https://www.laascension.com)")

st.markdown("---")
st.markdown(f"<p style='text-align: center; color: #999; font-size: 0.9em;'>Dashboard de Seguimiento de Flota Vehicular © 2026</p>", unsafe_allow_html=True)
