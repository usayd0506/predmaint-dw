--Now we are going to verify and validate our data
USE PredMaintDW;
GO

SELECT
    'Sensors' AS TableName,
    (SELECT COUNT(*) FROM stg.sensors) AS StagingRows,
    (SELECT COUNT(*) FROM bronze.sensors) AS BronzeRows

UNION ALL
SELECT 'RUL Truth',
    (SELECT COUNT(*) FROM stg.rul_truth),
    (SELECT COUNT(*) FROM bronze.rul_truth)

UNION ALL
SELECT 'Plants',
    (SELECT COUNT(*) FROM stg.plants),
    (SELECT COUNT(*) FROM bronze.plants)

UNION ALL
SELECT 'Technicians',
    (SELECT COUNT(*) FROM stg.technicians),
    (SELECT COUNT(*) FROM bronze.technicians)

UNION ALL
SELECT 'Engine Master',
    (SELECT COUNT(*) FROM stg.engine_master),
    (SELECT COUNT(*) FROM bronze.engine_master)

UNION ALL
SELECT 'Maintenance',
    (SELECT COUNT(*) FROM stg.maintenance),
    (SELECT COUNT(*) FROM bronze.maintenance);

--Data lineage: We can trace records back to their original files.
SELECT
    source_file,
    COUNT(*) AS TotalRows
FROM bronze.sensors
GROUP BY source_file;

--Verify the batch ID
SELECT
    batch_id,
    COUNT(*) AS TotalRows
FROM bronze.sensors
GROUP BY batch_id;


--verify the metadata across all six tables:
SELECT
    batch_id,
    step_name,
    rows_in,
    rows_out,
    status,
    logged_at
FROM ops.etl_log
WHERE step_name LIKE 'Bronze%'
ORDER BY log_id;

--verifying if the missing audit values exist(if any), we should see 0 as expected result
SELECT COUNT(*) AS MissingAuditValues
FROM bronze.sensors
WHERE batch_id IS NULL
   OR load_ts IS NULL
   OR source_file IS NULL;
--the query returns a 0 hence there are no missing audit values

--Since all of our validation checks are passed, we must make audit columns
--mandatory now


-- Bronze Sensors
ALTER TABLE bronze.sensors
ALTER COLUMN batch_id UNIQUEIDENTIFIER NOT NULL;

ALTER TABLE bronze.sensors
ALTER COLUMN load_ts DATETIME2 NOT NULL;

ALTER TABLE bronze.sensors
ALTER COLUMN source_file VARCHAR(100) NOT NULL;


-- Bronze RUL Truth
ALTER TABLE bronze.rul_truth
ALTER COLUMN batch_id UNIQUEIDENTIFIER NOT NULL;

ALTER TABLE bronze.rul_truth
ALTER COLUMN load_ts DATETIME2 NOT NULL;

ALTER TABLE bronze.rul_truth
ALTER COLUMN source_file VARCHAR(100) NOT NULL;


-- Bronze Plants
ALTER TABLE bronze.plants
ALTER COLUMN batch_id UNIQUEIDENTIFIER NOT NULL;

ALTER TABLE bronze.plants
ALTER COLUMN load_ts DATETIME2 NOT NULL;

ALTER TABLE bronze.plants
ALTER COLUMN source_file VARCHAR(100) NOT NULL;


-- Bronze Technicians
ALTER TABLE bronze.technicians
ALTER COLUMN batch_id UNIQUEIDENTIFIER NOT NULL;

ALTER TABLE bronze.technicians
ALTER COLUMN load_ts DATETIME2 NOT NULL;

ALTER TABLE bronze.technicians
ALTER COLUMN source_file VARCHAR(100) NOT NULL;


-- Bronze Engine Master
ALTER TABLE bronze.engine_master
ALTER COLUMN batch_id UNIQUEIDENTIFIER NOT NULL;

ALTER TABLE bronze.engine_master
ALTER COLUMN load_ts DATETIME2 NOT NULL;

ALTER TABLE bronze.engine_master
ALTER COLUMN source_file VARCHAR(100) NOT NULL;


-- Bronze Maintenance
ALTER TABLE bronze.maintenance
ALTER COLUMN batch_id UNIQUEIDENTIFIER NOT NULL;

ALTER TABLE bronze.maintenance
ALTER COLUMN load_ts DATETIME2 NOT NULL;

ALTER TABLE bronze.maintenance
ALTER COLUMN source_file VARCHAR(100) NOT NULL;

GO

