"""
Módulo para gestión de base de datos del tracking de vehículos
"""
import sqlite3
from datetime import datetime, time as dt_time
import pandas as pd
import os
import time

DB_PATH = os.path.join(os.path.dirname(__file__), 'vehiculos_tracking.db')

class VehiculosDB:
    """Clase para gestionar la base de datos de vehículos"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self._asegurar_db_existe()
    
    def _get_connection(self):
        """Obtiene una conexión a la base de datos con timeout y configuración optimizada"""
        conn = sqlite3.connect(self.db_path, timeout=60.0, check_same_thread=False)
        conn.execute("PRAGMA busy_timeout = 60000")  # 60 segundos
        return conn
    
    def _asegurar_db_existe(self):
        """Asegura que la base de datos existe"""
        if not os.path.exists(self.db_path):
            from init_database import crear_base_datos
            crear_base_datos()
    
    def _get_sesion_actual(self):
        """Determina si estamos en sesión AM o PM"""
        hora_actual = datetime.now().time()
        mediodia = dt_time(12, 0, 0)
        
        if hora_actual < mediodia:
            return "AM"
        else:
            return "PM"
    
    def insertar_posiciones(self, df):
        """
        Inserta posiciones de vehículos en la base de datos
        
        Args:
            df: DataFrame con las columnas: vehiculo, latitud, longitud, velocidad, etc.
        """
        max_reintentos = 5
        for intento in range(max_reintentos):
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                timestamp = datetime.now()
                sesion = self._get_sesion_actual()
                fecha = timestamp.date()
                
                registros_insertados = 0
                alertas_geocerca = 0
                
                for _, row in df.iterrows():
                    try:
                        cursor.execute('''
                        INSERT OR IGNORE INTO posiciones_vehiculos 
                        (timestamp, vehiculo, latitud, longitud, velocidad, kilometraje,
                         estado_online, estado_gps, evento, satelites, region, hora_evento,
                         sesion_dia, fecha_registro)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            timestamp,
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
                            sesion,
                            fecha
                        ))
                        
                        if cursor.rowcount > 0:
                            registros_insertados += 1
                            
                            # Verificar geocerca
                            dentro, nombre_geocerca = self.verificar_geocerca(
                                row['vehiculo'], 
                                row['latitud'], 
                                row['longitud']
                            )
                            
                            if not dentro and nombre_geocerca:
                                # Vehículo fuera de su geocerca - registrar alerta
                                alerta_id = self.registrar_alerta_geocerca(
                                    timestamp,
                                    row['vehiculo'],
                                    nombre_geocerca,
                                    row['latitud'],
                                    row['longitud']
                                )
                                if alerta_id:
                                    alertas_geocerca += 1
                            
                    except sqlite3.IntegrityError:
                        # Registro duplicado - ignorar silenciosamente
                        pass
                    except Exception as e:
                        # Solo imprimir si no es un error de bloqueo
                        if "locked" not in str(e).lower():
                            print(f"Error insertando registro para {row['vehiculo']}: {e}")
                
                conn.commit()
                conn.close()
                
                return registros_insertados, alertas_geocerca
                
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and intento < max_reintentos - 1:
                    time.sleep(0.5 * (intento + 1))  # Espera exponencial
                    continue
                else:
                    if intento == max_reintentos - 1:
                        print(f"⚠️ No se pudo insertar después de {max_reintentos} intentos")
                    return 0, 0
            except Exception as e:
                print(f"Error inesperado en insertar_posiciones: {e}")
                return 0, 0
    
    def insertar_alerta(self, vehiculo, velocidad, latitud, longitud, evento, umbral):
        """Inserta una alerta de velocidad"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        timestamp = datetime.now()
        sesion = self._get_sesion_actual()
        fecha = timestamp.date()
        
        cursor.execute('''
        INSERT INTO alertas_velocidad 
        (timestamp, vehiculo, velocidad, latitud, longitud, evento, 
         umbral_configurado, sesion_dia, fecha_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp, vehiculo, velocidad, latitud, longitud, 
            evento, umbral, sesion, fecha
        ))
        
        conn.commit()
        conn.close()
    
    def obtener_posiciones_sesion_actual(self):
        """Obtiene todas las posiciones de la sesión actual (AM o PM)"""
        conn = self._get_connection()
        
        sesion = self._get_sesion_actual()
        fecha = datetime.now().date()
        
        query = '''
        SELECT * FROM posiciones_vehiculos
        WHERE sesion_dia = ? AND fecha_registro = ?
        ORDER BY timestamp
        '''
        
        df = pd.read_sql_query(query, conn, params=(sesion, fecha))
        conn.close()
        
        # Convertir timestamp a datetime
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    def obtener_todas_posiciones(self, dias=30):
        """Obtiene todas las posiciones de los últimos N días"""
        conn = self._get_connection()
        
        fecha_limite = (datetime.now() - pd.Timedelta(days=dias)).date()
        
        query = '''
        SELECT * FROM posiciones_vehiculos
        WHERE fecha_registro >= ?
        ORDER BY timestamp DESC
        '''
        
        df = pd.read_sql_query(query, conn, params=(fecha_limite,))
        conn.close()
        
        # Convertir timestamp a datetime
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    def obtener_recorrido_vehiculo(self, vehiculo, sesion=None, fecha=None):
        """Obtiene el recorrido de un vehículo específico"""
        conn = self._get_connection()
        
        if sesion is None:
            sesion = self._get_sesion_actual()
        if fecha is None:
            fecha = datetime.now().date()
        
        query = '''
        SELECT * FROM posiciones_vehiculos
        WHERE vehiculo = ? AND sesion_dia = ? AND fecha_registro = ?
        ORDER BY timestamp
        '''
        
        df = pd.read_sql_query(query, conn, params=(vehiculo, sesion, fecha))
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    def obtener_alertas_recientes(self, minutos=60, solo_pendientes=True):
        """Obtiene alertas de los últimos X minutos"""
        conn = self._get_connection()
        
        tiempo_limite = datetime.now() - pd.Timedelta(minutes=minutos)
        
        if solo_pendientes:
            query = '''
            SELECT * FROM alertas_velocidad
            WHERE timestamp >= ? AND (atendida = 0 OR atendida IS NULL)
            ORDER BY timestamp DESC
            LIMIT 50
            '''
        else:
            query = '''
            SELECT * FROM alertas_velocidad
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT 50
            '''
        
        df = pd.read_sql_query(query, conn, params=(tiempo_limite,))
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            if 'fecha_atencion' in df.columns:
                df['fecha_atencion'] = pd.to_datetime(df['fecha_atencion'])
        
        return df
    
    def obtener_estadisticas_sesion(self):
        """Obtiene estadísticas de la sesión actual"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        sesion = self._get_sesion_actual()
        fecha = datetime.now().date()
        
        # Total de registros
        cursor.execute('''
        SELECT COUNT(*) FROM posiciones_vehiculos
        WHERE sesion_dia = ? AND fecha_registro = ?
        ''', (sesion, fecha))
        total_registros = cursor.fetchone()[0]
        
        # Total de vehículos únicos
        cursor.execute('''
        SELECT COUNT(DISTINCT vehiculo) FROM posiciones_vehiculos
        WHERE sesion_dia = ? AND fecha_registro = ?
        ''', (sesion, fecha))
        total_vehiculos = cursor.fetchone()[0]
        
        # Total de alertas
        cursor.execute('''
        SELECT COUNT(*) FROM alertas_velocidad
        WHERE sesion_dia = ? AND fecha_registro = ?
        ''', (sesion, fecha))
        total_alertas = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_registros': total_registros,
            'total_vehiculos': total_vehiculos,
            'total_alertas': total_alertas,
            'sesion': sesion,
            'fecha': fecha
        }
    
    def registrar_sesion(self):
        """Registra el inicio de una sesión con retry logic"""
        sesion = self._get_sesion_actual()
        fecha = datetime.now().date()
        timestamp = datetime.now()
        
        # Retry logic con exponential backoff
        max_intentos = 3
        espera_base = 1  # segundos
        
        for intento in range(max_intentos):
            try:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                cursor = conn.cursor()
                
                cursor.execute('''
                INSERT OR IGNORE INTO sesiones_tracking 
                (fecha, sesion, inicio_sesion)
                VALUES (?, ?, ?)
                ''', (fecha, sesion, timestamp))
                
                conn.commit()
                conn.close()
                return  # Éxito, salir
                
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and intento < max_intentos - 1:
                    # Database is locked, esperar y reintentar
                    espera = espera_base * (2 ** intento)  # Exponential backoff
                    print(f"Base de datos bloqueada, reintentando en {espera}s... (intento {intento + 1}/{max_intentos})")
                    time.sleep(espera)
                else:
                    print(f"Error al registrar sesión: {e}")
                    break
            except Exception as e:
                print(f"Error al registrar sesión: {e}")
                break
    
    def actualizar_estadisticas_sesion(self):
        """Actualiza las estadísticas de la sesión actual"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = self.obtener_estadisticas_sesion()
        
        cursor.execute('''
        UPDATE sesiones_tracking
        SET total_vehiculos = ?,
            total_registros = ?,
            total_alertas = ?,
            fin_sesion = ?
        WHERE fecha = ? AND sesion = ?
        ''', (
            stats['total_vehiculos'],
            stats['total_registros'],
            stats['total_alertas'],
            datetime.now(),
            stats['fecha'],
            stats['sesion']
        ))
        
        conn.commit()
        conn.close()
    
    def obtener_vehiculos_activos(self):
        """Obtiene lista de vehículos con datos en la sesión actual"""
        conn = self._get_connection()
        
        sesion = self._get_sesion_actual()
        fecha = datetime.now().date()
        
        query = '''
        SELECT DISTINCT vehiculo 
        FROM posiciones_vehiculos
        WHERE sesion_dia = ? AND fecha_registro = ?
        ORDER BY vehiculo
        '''
        
        cursor = conn.cursor()
        cursor.execute(query, (sesion, fecha))
        vehiculos = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return vehiculos
    
    def marcar_alerta_atendida(self, alerta_id, comentario=""):
        """Marca una alerta como atendida con comentario"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        fecha_atencion = datetime.now()
        
        cursor.execute('''
        UPDATE alertas_velocidad
        SET atendida = 1,
            fecha_atencion = ?,
            comentario_atencion = ?
        WHERE id = ?
        ''', (fecha_atencion, comentario, alerta_id))
        
        conn.commit()
        conn.close()
    
    def actualizar_comentario_alerta(self, alerta_id, comentario):
        """Actualiza el comentario de una alerta atendida"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE alertas_velocidad
        SET comentario_atencion = ?
        WHERE id = ?
        ''', (comentario, alerta_id))
        
        conn.commit()
        conn.close()
    
    def obtener_alertas_atendidas(self, dias=7):
        """Obtiene alertas atendidas de los últimos X días"""
        conn = self._get_connection()
        
        fecha_limite = (datetime.now() - pd.Timedelta(days=dias)).date()
        
        query = '''
        SELECT * FROM alertas_velocidad
        WHERE atendida = 1 AND fecha_registro >= ?
        ORDER BY fecha_atencion DESC
        '''
        
        df = pd.read_sql_query(query, conn, params=(fecha_limite,))
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['fecha_atencion'] = pd.to_datetime(df['fecha_atencion'])
        
        return df    
    # ============ MÉTODOS DE GEOCERCAS ============
    
    def crear_geocerca(self, nombre, descripcion, lat_min, lat_max, lon_min, lon_max, color='#FF0000'):
        """Crea una nueva geocerca"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO geocercas (nombre, descripcion, lat_min, lat_max, lon_min, lon_max, color)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (nombre, descripcion, lat_min, lat_max, lon_min, lon_max, color))
            
            conn.commit()
            geocerca_id = cursor.lastrowid
            conn.close()
            return geocerca_id
        except sqlite3.IntegrityError:
            conn.close()
            return None
    
    def obtener_geocercas_activas(self):
        """Obtiene todas las geocercas activas"""
        conn = self._get_connection()
        df = pd.read_sql_query('''
        SELECT * FROM geocercas WHERE activa = 1
        ORDER BY nombre
        ''', conn)
        conn.close()
        return df
    
    def asignar_vehiculo_geocerca(self, vehiculo, geocerca_id):
        """Asigna un vehículo a una geocerca"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT OR REPLACE INTO vehiculos_geocercas (vehiculo, geocerca_id, activa)
            VALUES (?, ?, 1)
            ''', (vehiculo, geocerca_id))
            
            conn.commit()
            conn.close()
            return True
        except:
            conn.close()
            return False
    
    def obtener_asignaciones_geocercas(self):
        """Obtiene todas las asignaciones activas vehículo-geocerca"""
        conn = self._get_connection()
        df = pd.read_sql_query('''
        SELECT vg.vehiculo, g.nombre as geocerca_nombre, 
               g.lat_min, g.lat_max, g.lon_min, g.lon_max, g.color
        FROM vehiculos_geocercas vg
        INNER JOIN geocercas g ON vg.geocerca_id = g.id
        WHERE vg.activa = 1 AND g.activa = 1
        ''', conn)
        conn.close()
        return df
    
    def verificar_geocerca(self, vehiculo, latitud, longitud):
        """Verifica si un vehículo está dentro de su geocerca asignada
        Retorna: (dentro_geocerca: bool, nombre_geocerca: str o None)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Obtener geocerca asignada al vehículo
        cursor.execute('''
        SELECT g.nombre, g.lat_min, g.lat_max, g.lon_min, g.lon_max
        FROM vehiculos_geocercas vg
        INNER JOIN geocercas g ON vg.geocerca_id = g.id
        WHERE vg.vehiculo = ? AND vg.activa = 1 AND g.activa = 1
        LIMIT 1
        ''', (vehiculo,))
        
        resultado = cursor.fetchone()
        conn.close()
        
        if not resultado:
            # No tiene geocerca asignada
            return True, None
        
        nombre, lat_min, lat_max, lon_min, lon_max = resultado
        
        # Verificar si está dentro de los límites
        dentro = (lat_min <= latitud <= lat_max) and (lon_min <= longitud <= lon_max)
        
        return dentro, nombre
    
    def registrar_alerta_geocerca(self, timestamp, vehiculo, geocerca_nombre, latitud, longitud):
        """Registra una alerta de violación de geocerca"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Evitar duplicados de la misma alerta en los últimos 5 minutos
        cursor.execute('''
        SELECT id FROM alertas_geocerca
        WHERE vehiculo = ? 
        AND geocerca_nombre = ?
        AND datetime(timestamp) >= datetime(?, '-5 minutes')
        AND atendida = 0
        ''', (vehiculo, geocerca_nombre, timestamp))
        
        if cursor.fetchone():
            conn.close()
            return None
        
        cursor.execute('''
        INSERT INTO alertas_geocerca 
        (timestamp, vehiculo, geocerca_nombre, latitud, longitud, tipo_violacion)
        VALUES (?, ?, ?, ?, ?, 'SALIDA')
        ''', (timestamp, vehiculo, geocerca_nombre, latitud, longitud))
        
        conn.commit()
        alerta_id = cursor.lastrowid
        conn.close()
        
        return alerta_id
    
    def obtener_alertas_geocerca_activas(self):
        """Obtiene alertas de geocerca no atendidas"""
        conn = self._get_connection()
        df = pd.read_sql_query('''
        SELECT * FROM alertas_geocerca
        WHERE atendida = 0
        ORDER BY timestamp DESC
        ''', conn)
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    def marcar_alerta_geocerca_atendida(self, alerta_id, comentario=''):
        """Marca una alerta de geocerca como atendida"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        fecha_atencion = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
        UPDATE alertas_geocerca
        SET atendida = 1,
            fecha_atencion = ?,
            comentario_atencion = ?
        WHERE id = ?
        ''', (fecha_atencion, comentario, alerta_id))
        
        conn.commit()
        conn.close()