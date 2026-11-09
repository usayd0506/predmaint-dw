-- Create Database (PredMaintDw)
USE master;
GO

IF DB_ID('PredMaintDW') IS NULL
BEGIN
    CREATE DATABASE PredMaintDW;
END;
GO

USE PredMaintDW;
GO

SELECT DB_NAME() AS CurrentDatabase;

USE PredMaintDW;
GO

/*
Execute the schema creation script() the idea is that we will create schemas and store
relevant tables for them
*/

IF SCHEMA_ID('stg') IS NULL
    EXEC('CREATE SCHEMA stg');
GO

IF SCHEMA_ID('bronze') IS NULL
    EXEC('CREATE SCHEMA bronze');
GO

IF SCHEMA_ID('silver') IS NULL
    EXEC('CREATE SCHEMA silver');
GO

IF SCHEMA_ID('gold') IS NULL
    EXEC('CREATE SCHEMA gold');
GO

IF SCHEMA_ID('mart') IS NULL
    EXEC('CREATE SCHEMA mart');
GO

IF SCHEMA_ID('ops') IS NULL
    EXEC('CREATE SCHEMA ops');
GO

--Verify the schemas
SELECT name
FROM sys.schemas
WHERE name IN (
    'stg',
    'bronze',
    'silver',
    'gold',
    'mart',
    'ops'
)
ORDER BY name;

/* Essentially, we are using two types of Data, the details are as follows.

Raw NASA C-MAPSS data:
File	            Information

train_FD001.txt	    -Historical engine sensor measurements
test_FD001.txt	    -Partial engine histories for evaluation
RUL_FD001.txt	    -True remaining useful life of test engines

Each sensor record contains an engine ID, operating cycle, three operational settings and 21 sensor measurements.

Synthetic data is generated using python scripts:
File	I                  Information

plants.csv	               -Five industrial plant locations
technicians.csv	           -Approximately 20 technicians
engine_master.csv	       -200 engines linked to plants
maintenance_log.csv	       -Approximately 600–900 maintenance records
*/

--First we will create stg.sensors where both the training and test datasets will go
USE PredMaintDW;
GO

CREATE TABLE stg.sensors (
    split VARCHAR(5),
    engine_id INT,
    cycle INT,

    setting_1 FLOAT,
    setting_2 FLOAT,
    setting_3 FLOAT,

    sensor_1 FLOAT,
    sensor_2 FLOAT,
    sensor_3 FLOAT,
    sensor_4 FLOAT,
    sensor_5 FLOAT,
    sensor_6 FLOAT,
    sensor_7 FLOAT,
    sensor_8 FLOAT,
    sensor_9 FLOAT,
    sensor_10 FLOAT,
    sensor_11 FLOAT,
    sensor_12 FLOAT,
    sensor_13 FLOAT,
    sensor_14 FLOAT,
    sensor_15 FLOAT,
    sensor_16 FLOAT,
    sensor_17 FLOAT,
    sensor_18 FLOAT,
    sensor_19 FLOAT,
    sensor_20 FLOAT,
    sensor_21 FLOAT
);
GO

/*
This stores the true Remaining Useful Life (RUL) values from the NASA test dataset
The original RUL file contains a single value per test engine. When loading it, Python will assign the sequential engine_id values
*/

CREATE TABLE stg.rul_truth (
    engine_id INT,
    true_rul INT
);
GO
/*
This table identifies the geographical locations of the plants
latitude and longitude will be used for location-based analysis and a spatial index.
*/

CREATE TABLE stg.plants (
    plant_id INT,
    plant_name VARCHAR(100),
    city VARCHAR(60),
    province VARCHAR(60),
    country VARCHAR(60),
    latitude FLOAT,
    longitude FLOAT
);
GO

/*
Each technician belongs to a home plant and has a skill level
*/

CREATE TABLE stg.technicians (
    technician_id INT,
    name VARCHAR(100),
    plant_id INT,
    skill_level VARCHAR(20),
    hourly_rate FLOAT,
    max_hours_per_week INT
);
GO

/*
This table connects each engine to a plant
*/

CREATE TABLE stg.engine_master (
    engine_uid INT,
    engine_id INT,
    split VARCHAR(5),
    plant_id INT,
    commission_date DATE
);
GO

CREATE TABLE stg.maintenance (
    work_order_id INT,
    engine_uid INT,
    work_date VARCHAR(20),
    type VARCHAR(30),
    technician_id INT,
    duration_hours VARCHAR(20),
    cost VARCHAR(20)
);
GO
/*
Its purpose is to record the outcome of each ETL operation, including how many records were processed
*/

CREATE TABLE ops.etl_log (
    log_id INT IDENTITY(1,1) PRIMARY KEY,
    batch_id UNIQUEIDENTIFIER NOT NULL,
    step_name VARCHAR(100) NOT NULL,
    rows_in INT NULL,
    rows_out INT NULL,
    status VARCHAR(20) NOT NULL,
    message VARCHAR(500) NULL,
    logged_at DATETIME2 DEFAULT SYSDATETIME()
);
GO

USE PredMaintDW;
GO

IF OBJECT_ID('ops.bronze_batch', 'U') IS NULL
BEGIN
    CREATE TABLE ops.bronze_batch (
        batch_id UNIQUEIDENTIFIER PRIMARY KEY,
        loaded_at DATETIME2 DEFAULT SYSDATETIME(),
        status VARCHAR(20),
        source_version VARCHAR(100) UNIQUE
    );
END;
GO

--Verification
SELECT
    TABLE_SCHEMA,
    TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA IN ('stg', 'ops')
ORDER BY TABLE_SCHEMA, TABLE_NAME;



USE PredMaintDW;
GO

SELECT TOP 10 * FROM stg.sensors;
SELECT TOP 10 * FROM stg.plants;
SELECT TOP 10 * FROM stg.maintenance;


SELECT
    split,
    COUNT(*) AS TotalRows,
    COUNT(DISTINCT engine_id) AS TotalEngines
FROM stg.sensors
GROUP BY split;