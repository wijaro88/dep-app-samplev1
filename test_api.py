"""
Script para probar la captura de datos de la API sin el dashboard
"""
import requests
from lxml import etree
import pandas as pd
from datetime import datetime
from db_manager import VehiculosDB

def parse_response(xml_content):
    """Parsea la respuesta XML y retorna un DataFrame"""
    try:
        root = etree.fromstring(xml_content)
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'
        }
        
        cars_info = root.xpath('//ns:GetCarsInfoResult/ns:CarInfo', namespaces=namespaces)
        
        if not cars_info:
            print("⚠️ No se encontraron datos de vehículos en la respuesta")
            return None
        
        datos = []
        for car in cars_info:
            dato = {
                'vehiculo': car.find('ns:Name', namespaces).text if car.find('ns:Name', namespaces) is not None else None,
                'latitud': float(car.find('ns:Latitude', namespaces).text) if car.find('ns:Latitude', namespaces) is not None else None,
                'longitud': float(car.find('ns:Longitude', namespaces).text) if car.find('ns:Longitude', namespaces) is not None else None,
                'velocidad': float(car.find('ns:Speed', namespaces).text) if car.find('ns:Speed', namespaces) is not None else 0,
                'direccion': car.find('ns:Address', namespaces).text if car.find('ns:Address', namespaces) is not None else "",
                'conductor': car.find('ns:Driver', namespaces).text if car.find('ns:Driver', namespaces) is not None else "",
                'evento': car.find('ns:LastEvent', namespaces).text if car.find('ns:LastEvent', namespaces) is not None else "",
            }
            datos.append(dato)
        
        return pd.DataFrame(datos)
    
    except Exception as e:
        print(f"❌ Error al parsear XML: {str(e)}")
        return None

def test_api_capture():
    """Prueba la captura de datos de la API"""
    print("="*60)
    print("PRUEBA DE CAPTURA DE DATOS DE LA API")
    print("="*60)
    print()
    
    usuario = "wsascension"
    clave = "Ascension24!"
    empresa = "ASCENSION"
    
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
    
    print(f"[{datetime.now()}] 🔍 Consultando API...")
    
    try:
        response = requests.post(url, data=soap_body, headers=headers, timeout=30)
        
        print(f"[{datetime.now()}] 📡 Código de respuesta: {response.status_code}")
        
        if response.status_code == 200:
            print(f"[{datetime.now()}] ✅ API respondió correctamente")
            
            df = parse_response(response.content)
            
            if df is not None and not df.empty:
                print(f"[{datetime.now()}] 📊 Datos obtenidos: {len(df)} vehículos")
                print()
                print("Vehículos detectados:")
                print("-" * 60)
                for idx, row in df.iterrows():
                    print(f"  {idx+1}. {row['vehiculo']}")
                    print(f"     Ubicación: ({row['latitud']}, {row['longitud']})")
                    print(f"     Velocidad: {row['velocidad']} km/h")
                    print(f"     Dirección: {row['direccion']}")
                    print()
                
                # Intentar guardar en base de datos
                print(f"[{datetime.now()}] 💾 Guardando en base de datos...")
                db = VehiculosDB()
                registros_nuevos = db.insertar_posiciones(df)
                print(f"[{datetime.now()}] ✅ {registros_nuevos} registros nuevos guardados")
                
            else:
                print(f"[{datetime.now()}] ⚠️ No se pudieron extraer datos del XML")
        else:
            print(f"[{datetime.now()}] ❌ API no disponible (código {response.status_code})")
            
    except requests.Timeout:
        print(f"[{datetime.now()}] ⏱️ Timeout: La API tardó mucho en responder")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Error: {str(e)}")
    
    print()
    print("="*60)
    print("PRUEBA FINALIZADA")
    print("="*60)

if __name__ == "__main__":
    test_api_capture()
