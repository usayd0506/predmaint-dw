/*
The Bronze Layer is used to preserve the original source data along with information about when, where, and how it entered the Data Warehouse.
*/
USE PredMaintDW;
GO

SELECT DB_NAME() AS CurrentDatabase;

SELECT 'sensors' AS TableName, COUNT(*) AS TotalRows
FROM stg.sensors

UNION ALL
SELECT 'rul_truth', COUNT(*) FROM stg.rul_truth

UNION ALL
SELECT 'plants', COUNT(*) FROM stg.plants

UNION ALL
SELECT 'technicians', COUNT(*) FROM stg.technicians

UNION ALL
SELECT 'engine_master', COUNT(*) FROM stg.engine_master

UNION ALL
SELECT 'maintenance', COUNT(*) FROM stg.maintenance;


/*
Check whether any Bronze tables already exist
*/
SELECT
    TABLE_SCHEMA,
    TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'bronze';

--this result should return an empty result

/*Creating all six Bronze tables*/

-- Bronze Sensors
IF OBJECT_ID('bronze.sensors', 'U') IS NULL
BEGIN
    SELECT TOP (0) *
    INTO bronze.sensors
    FROM stg.sensors;
END;
GO

-- Bronze RUL Truth
IF OBJECT_ID('bronze.rul_truth', 'U') IS NULL
BEGIN
    SELECT TOP (0) *
    INTO bronze.rul_truth
    FROM stg.rul_truth;
END;
GO

-- Bronze Plants
IF OBJECT_ID('bronze.plants', 'U') IS NULL
BEGIN
    SELECT TOP (0) *
    INTO bronze.plants
    FROM stg.plants;
END;
GO

-- Bronze Technicians
IF OBJECT_ID('bronze.technicians', 'U') IS NULL
BEGIN
    SELECT TOP (0) *
    INTO bronze.technicians
    FROM stg.technicians;
END;
GO

-- Bronze Engine Master
IF OBJECT_ID('bronze.engine_master', 'U') IS NULL
BEGIN
    SELECT TOP (0) *
    INTO bronze.engine_master
    FROM stg.engine_master;
END;
GO

-- Bronze Maintenance
IF OBJECT_ID('bronze.maintenance', 'U') IS NULL
BEGIN
    SELECT TOP (0) *
    INTO bronze.maintenance
    FROM stg.maintenance;
END;
GO

/*Check Created Tables in Bronze Layer*/
SELECT
    TABLE_SCHEMA,
    TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'bronze'
ORDER BY TABLE_NAME;

/*Now Add the Audit Columns*/

ALTER TABLE bronze.sensors
ADD batch_id UNIQUEIDENTIFIER NULL,
    load_ts DATETIME2 NULL,
    source_file VARCHAR(100) NULL;

ALTER TABLE bronze.rul_truth
ADD batch_id UNIQUEIDENTIFIER NULL,
    load_ts DATETIME2 NULL,
    source_file VARCHAR(100) NULL;

ALTER TABLE bronze.plants
ADD batch_id UNIQUEIDENTIFIER NULL,
    load_ts DATETIME2 NULL,
    source_file VARCHAR(100) NULL;

ALTER TABLE bronze.technicians
ADD batch_id UNIQUEIDENTIFIER NULL,
    load_ts DATETIME2 NULL,
    source_file VARCHAR(100) NULL;

ALTER TABLE bronze.engine_master
ADD batch_id UNIQUEIDENTIFIER NULL,
    load_ts DATETIME2 NULL,
    source_file VARCHAR(100) NULL;

ALTER TABLE bronze.maintenance
ADD batch_id UNIQUEIDENTIFIER NULL,
    load_ts DATETIME2 NULL,
    source_file VARCHAR(100) NULL;
GO
