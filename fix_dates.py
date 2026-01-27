import re

with open('db_manager_sqlserver.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Agregar función auxiliar después de _get_sesion_actual
old_method = '''    def _get_sesion_actual(self):
        """Determina si estamos en sesión AM o PM"""
        hora_actual = datetime.now().time()
        mediodia = dt_time(12, 0, 0)
        return "AM" if hora_actual < mediodia else "PM"'''

new_method = '''    def _get_sesion_actual(self):
        """Determina si estamos en sesión AM o PM"""
        hora_actual = datetime.now().time()
        mediodia = dt_time(12, 0, 0)
        return "AM" if hora_actual < mediodia else "PM"
    
    def _to_sql_date(self, fecha):
        """Convierte fecha Python a string compatible con SQL Server antiguo"""
        if isinstance(fecha, str):
            return fecha
        return fecha.strftime('%Y-%m-%d') if fecha else None'''

content = content.replace(old_method, new_method)

# Reemplazar todas las asignaciones de fecha
replacements = [
    ('fecha = timestamp.date()', 'fecha = self._to_sql_date(timestamp.date())'),
    ('fecha = datetime.now().date()', 'fecha = self._to_sql_date(datetime.now().date())'),
    ('fecha_limite = (datetime.now() - pd.Timedelta(days=dias)).date()', 
     'fecha_limite = self._to_sql_date((datetime.now() - pd.Timedelta(days=dias)).date())'),
]

for old, new in replacements:
    content = content.replace(old, new)

with open('db_manager_sqlserver.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ Archivo actualizado con conversiones de fecha')
