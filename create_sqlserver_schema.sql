-- Script para crear el esquema de base de datos en SQL Server
-- Base de datos: ciex
-- Tracking de Vehículos La Ascensión S.A.

USE ciex;
GO

-- Tabla de posiciones de vehículos
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[posiciones_vehiculos]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[posiciones_vehiculos] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [timestamp] DATETIME2 NOT NULL,
        [vehiculo] NVARCHAR(50) NOT NULL,
        [latitud] DECIMAL(10, 7) NOT NULL,
        [longitud] DECIMAL(10, 7) NOT NULL,
        [velocidad] DECIMAL(8, 2) DEFAULT 0,
        [kilometraje] DECIMAL(12, 2) DEFAULT 0,
        [estado_online] NVARCHAR(20),
        [estado_gps] NVARCHAR(50),
        [evento] NVARCHAR(100),
        [satelites] INT DEFAULT 0,
        [region] NVARCHAR(100),
        [hora_evento] NVARCHAR(50),
        [sesion_dia] NVARCHAR(10) NOT NULL,
        [fecha_registro] DATE NOT NULL,
        CONSTRAINT UQ_timestamp_vehiculo UNIQUE ([timestamp], [vehiculo])
    );

    -- Índices para consultas rápidas
    CREATE INDEX IX_posiciones_vehiculo ON [dbo].[posiciones_vehiculos]([vehiculo]);
    CREATE INDEX IX_posiciones_timestamp ON [dbo].[posiciones_vehiculos]([timestamp]);
    CREATE INDEX IX_posiciones_sesion ON [dbo].[posiciones_vehiculos]([sesion_dia], [fecha_registro]);
END
GO

-- Tabla de alertas de velocidad
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[alertas_velocidad]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[alertas_velocidad] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [timestamp] DATETIME2 NOT NULL,
        [vehiculo] NVARCHAR(50) NOT NULL,
        [velocidad] DECIMAL(8, 2) NOT NULL,
        [latitud] DECIMAL(10, 7) NOT NULL,
        [longitud] DECIMAL(10, 7) NOT NULL,
        [evento] NVARCHAR(100),
        [umbral_configurado] DECIMAL(8, 2) NOT NULL,
        [sesion_dia] NVARCHAR(10) NOT NULL,
        [fecha_registro] DATE NOT NULL,
        [atendida] BIT DEFAULT 0,
        [fecha_atencion] DATETIME2,
        [comentario_atencion] NVARCHAR(500)
    );

    CREATE INDEX IX_alertas_vehiculo ON [dbo].[alertas_velocidad]([vehiculo]);
    CREATE INDEX IX_alertas_timestamp ON [dbo].[alertas_velocidad]([timestamp]);
END
GO

-- Tabla de sesiones de tracking
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[sesiones_tracking]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[sesiones_tracking] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [fecha] DATE NOT NULL,
        [sesion] NVARCHAR(10) NOT NULL,
        [inicio_sesion] DATETIME2 NOT NULL,
        [fin_sesion] DATETIME2,
        [total_vehiculos] INT DEFAULT 0,
        [total_registros] INT DEFAULT 0,
        [total_alertas] INT DEFAULT 0,
        CONSTRAINT UQ_fecha_sesion UNIQUE ([fecha], [sesion])
    );
END
GO

-- Tabla de geocercas (zonas permitidas)
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[geocercas]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[geocercas] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [nombre] NVARCHAR(100) NOT NULL UNIQUE,
        [descripcion] NVARCHAR(500),
        [lat_min] DECIMAL(10, 7) NOT NULL,
        [lat_max] DECIMAL(10, 7) NOT NULL,
        [lon_min] DECIMAL(10, 7) NOT NULL,
        [lon_max] DECIMAL(10, 7) NOT NULL,
        [color] NVARCHAR(20) DEFAULT '#FF0000',
        [activa] BIT DEFAULT 1,
        [fecha_creacion] DATETIME2 DEFAULT GETDATE()
    );
END
GO

-- Tabla de asignación vehículo-geocerca
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[vehiculos_geocercas]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[vehiculos_geocercas] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [vehiculo] NVARCHAR(50) NOT NULL,
        [geocerca_id] INT NOT NULL,
        [fecha_asignacion] DATETIME2 DEFAULT GETDATE(),
        [activa] BIT DEFAULT 1,
        CONSTRAINT FK_vehiculos_geocercas_geocercas FOREIGN KEY ([geocerca_id])
            REFERENCES [dbo].[geocercas]([id]),
        CONSTRAINT UQ_vehiculo_geocerca UNIQUE ([vehiculo], [geocerca_id])
    );
END
GO

-- Tabla de alertas de geocerca
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[alertas_geocerca]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[alertas_geocerca] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [timestamp] DATETIME2 NOT NULL,
        [vehiculo] NVARCHAR(50) NOT NULL,
        [geocerca_nombre] NVARCHAR(100) NOT NULL,
        [latitud] DECIMAL(10, 7) NOT NULL,
        [longitud] DECIMAL(10, 7) NOT NULL,
        [tipo_violacion] NVARCHAR(20) DEFAULT 'SALIDA',
        [distancia_km] DECIMAL(10, 2),
        [atendida] BIT DEFAULT 0,
        [fecha_atencion] DATETIME2,
        [comentario_atencion] NVARCHAR(500)
    );

    CREATE INDEX IX_alertas_geocerca_vehiculo ON [dbo].[alertas_geocerca]([vehiculo]);
    CREATE INDEX IX_alertas_geocerca_timestamp ON [dbo].[alertas_geocerca]([timestamp]);
END
GO

PRINT 'Esquema de base de datos creado exitosamente en SQL Server';
PRINT 'Base de datos: ciex';
PRINT 'Tablas creadas:';
PRINT '  - posiciones_vehiculos';
PRINT '  - alertas_velocidad';
PRINT '  - sesiones_tracking';
PRINT '  - geocercas';
PRINT '  - vehiculos_geocercas';
PRINT '  - alertas_geocerca';
GO
