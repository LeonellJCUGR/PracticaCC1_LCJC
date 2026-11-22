-- Inicialización idempotente de UNA instancia de SQL Server (docker compose).
-- Cada microservicio tiene su propio contenedor de SQL Server (database-per-service con
-- aislamiento físico); este mismo script se ejecuta una vez contra cada instancia.
--
-- Variables sqlcmd (las pasa el contenedor db-init-* con -v):
--   $(DB_NAME)       nombre de la base de datos      (catalog_db | booking_db)
--   $(APP_LOGIN)     login del microservicio          (catalog_app | booking_app)
--   $(APP_PASSWORD)  contraseña de ese login

SET NOCOUNT ON;

IF DB_ID(N'$(DB_NAME)') IS NULL
    CREATE DATABASE [$(DB_NAME)];
GO

IF SUSER_ID(N'$(APP_LOGIN)') IS NULL
    CREATE LOGIN [$(APP_LOGIN)] WITH PASSWORD = N'$(APP_PASSWORD)', DEFAULT_DATABASE = [$(DB_NAME)];
ELSE
    ALTER LOGIN [$(APP_LOGIN)] WITH PASSWORD = N'$(APP_PASSWORD)';
GO

USE [$(DB_NAME)];
IF USER_ID(N'$(APP_LOGIN)') IS NULL
    CREATE USER [$(APP_LOGIN)] FOR LOGIN [$(APP_LOGIN)];
-- Mínimo privilegio: leer/escribir datos y crear sus propias tablas. No es sysadmin ni db_owner.
ALTER ROLE db_datareader ADD MEMBER [$(APP_LOGIN)];
ALTER ROLE db_datawriter ADD MEMBER [$(APP_LOGIN)];
ALTER ROLE db_ddladmin   ADD MEMBER [$(APP_LOGIN)];
GO

PRINT 'Base de datos $(DB_NAME) lista para $(APP_LOGIN)';
