"""
Utilidades para manejo de zona horaria
"""
from datetime import datetime, timezone, timedelta

# Zona horaria Colombia/Ecuador/Perú (UTC-5)
TZ_OFFSET = timedelta(hours=-5)
TZ_NAME = "America/Bogota"

def get_local_now():
    """
    Obtiene la hora actual en zona horaria local (UTC-5)
    """
    utc_now = datetime.now(timezone.utc)
    local_now = utc_now + TZ_OFFSET
    return local_now.replace(tzinfo=None)

def utc_to_local(utc_dt):
    """
    Convierte un datetime UTC a hora local
    """
    if utc_dt is None:
        return None
    
    # Si no tiene timezone info, asumir que es UTC
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    
    local_dt = utc_dt + TZ_OFFSET
    return local_dt.replace(tzinfo=None)

def local_to_utc(local_dt):
    """
    Convierte un datetime local a UTC
    """
    if local_dt is None:
        return None
    
    # Si tiene timezone info, removerla primero
    if local_dt.tzinfo is not None:
        local_dt = local_dt.replace(tzinfo=None)
    
    utc_dt = local_dt - TZ_OFFSET
    return utc_dt
