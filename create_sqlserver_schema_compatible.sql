-- Schema SQL Server 2014 compatible
USE ciex;

-- Tabla de posiciones de vehículos
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'posiciones_vehiculos') AND type in (N'U'))
CREATE TABLE posiciones_vehiculos (
    id INT IDENTITY(1,1) PRIMARY KEY,
    timestamp DATETIME2 NOT NULL,
    vehiculo NVARCHAR(50) NOT NULL,
    latitud DECIMAL(10,7) NOT NULL,
    longitud DECIMAL(10,7) NOT NULL,
    velocidad DECIMAL(5,2) DEFAULT 0,
    kilometraje DECIMAL(10,2) DEFAULT 0,
    estado_online NVARCHAR(20),
    estado_gps NVARCHAR(20),
    evento NVARCHAR(100),
    satelites INT DEFAULT 0,
    region NVARCHAR(100),
    hora_evento NVARCHAR(20),
    sesion_dia NVARCHAR(2) DEFAULT 'AM',
    fecha_registro DATE NOT NULL
);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_posiciones_timestamp')
CREATE INDEX idx_posiciones_timestamp ON posiciones_vehiculos(timestamp);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_posiciones_vehiculo')
CREATE INDEX idx_posiciones_vehiculo ON posiciones_vehiculos(vehiculo);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_posiciones_sesion')
CREATE INDEX idx_posiciones_sesion ON posiciones_vehiculos(sesion_dia, fecha_registro);

-- Tabla de alertas de velocidad
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'alertas_velocidad') AND type in (N'U'))
CREATE TABLE alertas_velocidad (
    id INT IDENTITY(1,1) PRIMARY KEY,
    timestamp DATETIME2 NOT NULL,
    vehiculo NVARCHAR(50) NOT NULL,
    velocidad DECIMAL(5,2) NOT NULL,
    latitud DECIMAL(10,7) NOT NULL,
    longitud DECIMAL(10,7) NOT NULL,
    evento NVARCHAR(100),
    umbral_configurado DECIMAL(5,2),
    sesion_dia NVARCHAR(2) DEFAULT 'AM',
    fecha_registro DATE NOT NULL,
    atendida BIT DEFAULT 0,
    fecha_atencion DATETIME2 NULL,
    comentario_atencion NVARCHAR(500)
);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_alertas_timestamp')
CREATE INDEX idx_alertas_timestamp ON alertas_velocidad(timestamp);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_alertas_atendida')
CREATE INDEX idx_alertas_atendida ON alertas_velocidad(atendida);

-- Tabla de sesiones de tracking
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'sesiones_tracking') AND type in (N'U'))
CREATE TABLE sesiones_tracking (
    id INT IDENTITY(1,1) PRIMARY KEY,
    fecha DATE NOT NULL,
    sesion NVARCHAR(2) NOT NULL,
    inicio_sesion DATETIME2,
    fin_sesion DATETIME2,
    total_vehiculos INT DEFAULT 0,
    total_registros INT DEFAULT 0,
    total_alertas INT DEFAULT 0,
    CONSTRAINT unique_fecha_sesion UNIQUE (fecha, sesion)
);

-- Tabla de geocercas
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'geocercas') AND type in (N'U'))
CREATE TABLE geocercas (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nombre NVARCHAR(100) NOT NULL UNIQUE,
    descripcion NVARCHAR(500),
    lat_min DECIMAL(10,7) NOT NULL,
    lat_max DECIMAL(10,7) NOT NULL,
    lon_min DECIMAL(10,7) NOT NULL,
    lon_max DECIMAL(10,7) NOT NULL,
    color NVARCHAR(20) DEFAULT '#FF0000',
    activa BIT DEFAULT 1,
    fecha_creacion DATETIME2 DEFAULT GETDATE()
);

-- Tabla de asignación de vehículos a geocercas
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'vehiculos_geocercas') AND type in (N'U'))
CREATE TABLE vehiculos_geocercas (
    id INT IDENTITY(1,1) PRIMARY KEY,
    vehiculo NVARCHAR(50) NOT NULL,
    geocerca_id INT NOT NULL,
    activa BIT DEFAULT 1,
    fecha_asignacion DATETIME2 DEFAULT GETDATE(),
    FOREIGN KEY (geocerca_id) REFERENCES geocercas(id),
    CONSTRAINT unique_vehiculo_geocerca UNIQUE (vehiculo, geocerca_id)
);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_vehiculo_geocerca')
CREATE INDEX idx_vehiculo_geocerca ON vehiculos_geocercas(vehiculo);

-- Tabla de alertas de geocerca
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'alertas_geocerca') AND type in (N'U'))
CREATE TABLE alertas_geocerca (
    id INT IDENTITY(1,1) PRIMARY KEY,
    timestamp DATETIME2 NOT NULL,
    vehiculo NVARCHAR(50) NOT NULL,
    geocerca_nombre NVARCHAR(100) NOT NULL,
    latitud DECIMAL(10,7) NOT NULL,
    longitud DECIMAL(10,7) NOT NULL,
    tipo_violacion NVARCHAR(20) DEFAULT 'SALIDA',
    atendida BIT DEFAULT 0,
    fecha_atencion DATETIME2 NULL,
    comentario_atencion NVARCHAR(500)
);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_alertas_geo_timestamp')
CREATE INDEX idx_alertas_geo_timestamp ON alertas_geocerca(timestamp);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_alertas_geo_atendida')
CREATE INDEX idx_alertas_geo_atendida ON alertas_geocerca(atendida);

PRINT ' Esquema creado exitosamente';
