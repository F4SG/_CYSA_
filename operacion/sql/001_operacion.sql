-- Migración idempotente del banco S2. Ejecutar dentro de CYSA_Control_S2 (SQL Server).
IF OBJECT_ID('control_planes','U') IS NULL
CREATE TABLE control_planes(
 id uniqueidentifier PRIMARY KEY, documento nvarchar(max) NOT NULL CHECK(ISJSON(documento)=1),
 validacion nvarchar(max) NOT NULL CHECK(ISJSON(validacion)=1),origen nvarchar(max) NOT NULL CHECK(ISJSON(origen)=1),
 estado nvarchar(30) NOT NULL,creado datetime2 NOT NULL DEFAULT SYSUTCDATETIME());
IF OBJECT_ID('control_decisiones','U') IS NULL
CREATE TABLE control_decisiones(
 solicitud_id uniqueidentifier PRIMARY KEY,plan_id uniqueidentifier NOT NULL UNIQUE REFERENCES control_planes(id),
 usuario nvarchar(200) NOT NULL,accion nvarchar(20) NOT NULL,motivo nvarchar(1000) NOT NULL,
 mfa nvarchar(max) NOT NULL CHECK(ISJSON(mfa)=1),creado datetime2 NOT NULL DEFAULT SYSUTCDATETIME());
IF OBJECT_ID('control_envios','U') IS NULL
CREATE TABLE control_envios(
 solicitud_id uniqueidentifier PRIMARY KEY REFERENCES control_decisiones(solicitud_id),
 payload nvarchar(max) NOT NULL CHECK(ISJSON(payload)=1),estado nvarchar(30) NOT NULL DEFAULT 'pendiente',
 intentos int NOT NULL DEFAULT 0,detalle nvarchar(500) NOT NULL DEFAULT '',actualizado datetime2 NOT NULL DEFAULT SYSUTCDATETIME());
IF OBJECT_ID('control_auditoria','U') IS NULL
CREATE TABLE control_auditoria(
 id bigint IDENTITY PRIMARY KEY,plan_id uniqueidentifier,usuario nvarchar(200) NOT NULL,
 operacion nvarchar(40) NOT NULL,motivo nvarchar(1000) NOT NULL,anterior nvarchar(max) NOT NULL,
 nuevo nvarchar(max) NOT NULL,creado datetime2 NOT NULL DEFAULT SYSUTCDATETIME());
IF OBJECT_ID('control_conteos','U') IS NULL
CREATE TABLE control_conteos(
 mensaje_id uniqueidentifier PRIMARY KEY,interseccion nvarchar(64) NOT NULL,acceso nvarchar(64) NOT NULL,
 carril nvarchar(64) NOT NULL,clase nvarchar(20) NOT NULL,cantidad int NOT NULL CHECK(cantidad>=0),
 inicio datetime2 NOT NULL,fin datetime2 NOT NULL,prueba bit NOT NULL,CHECK(fin>inicio));
IF OBJECT_ID('control_estados','U') IS NULL
CREATE TABLE control_estados(
 interseccion nvarchar(64) PRIMARY KEY,mensaje_id uniqueidentifier NOT NULL,fase_actual nvarchar(64) NOT NULL,
 plan_activo nvarchar(64) NOT NULL,estado_controlador nvarchar(20) NOT NULL,timestamp datetime2 NOT NULL,prueba bit NOT NULL);
