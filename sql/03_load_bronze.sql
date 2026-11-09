/*
This procedure loads data from the Staging Layer into the Bronze Layer.

The purpose of Bronze is to preserve raw data along with information
about when it was loaded and which source file it came from.

How it works:
1. Takes a source version as input to identify the dataset being loaded.
2. Generates a unique batch ID and loading timestamp.
3. Checks whether the source version has already been loaded to avoid duplicates.
4. Verifies that all six staging tables contain data.
5. Checks that sensor records belong to either the train or test dataset.
6. Copies records from the six staging tables into their corresponding Bronze tables.
7. Adds batch_id, load_ts, and source_file to every record.
8. Records the number of loaded rows and their status in ops.etl_log.
9. Compares staging and Bronze row counts for the current batch.
10. Commits all changes if successful, otherwise rolls back the transaction.

The procedure supports multiple batches without deleting previous Bronze data.
Each new source version is appended, while previously loaded versions are rejected.

Note: Duplicate prevention depends on the source version provided.
Different version names for identical data are not automatically detected.
*/


USE PredMaintDW;
GO

CREATE OR ALTER PROCEDURE bronze.usp_load_bronze
    @SourceVersion VARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @BatchId UNIQUEIDENTIFIER = NEWID();
    DECLARE @LoadTime DATETIME2 = SYSDATETIME();

    IF @SourceVersion IS NULL
       OR LTRIM(RTRIM(@SourceVersion)) = ''
    BEGIN
        THROW 50001, 'Source version is required.', 1;
    END;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- Stop if this source version is already loaded
        IF EXISTS (
            SELECT 1
            FROM ops.bronze_batch WITH (UPDLOCK, HOLDLOCK)
            WHERE source_version = @SourceVersion
        )
        BEGIN
            THROW 50002, 'This source version was already loaded.', 1;
        END;

        -- Check staging data
        IF NOT EXISTS (SELECT 1 FROM stg.sensors)
           OR NOT EXISTS (SELECT 1 FROM stg.rul_truth)
           OR NOT EXISTS (SELECT 1 FROM stg.plants)
           OR NOT EXISTS (SELECT 1 FROM stg.technicians)
           OR NOT EXISTS (SELECT 1 FROM stg.engine_master)
           OR NOT EXISTS (SELECT 1 FROM stg.maintenance)
        BEGIN
            THROW 50003, 'One or more staging tables are empty.', 1;
        END;

        -- Validate sensor split values
        IF EXISTS (
            SELECT 1
            FROM stg.sensors
            WHERE split IS NULL
               OR split NOT IN ('train', 'test')
        )
        BEGIN
            THROW 50004, 'Invalid sensor split found.', 1;
        END;

        -- Register the batch
        INSERT INTO ops.bronze_batch
            (batch_id, loaded_at, status, source_version)
        VALUES
            (@BatchId, @LoadTime, 'OK', @SourceVersion);

        -- Load sensor data
        INSERT INTO bronze.sensors
        SELECT s.*, @BatchId, @LoadTime,
            CASE
                WHEN s.split = 'train' THEN 'train_FD001.txt'
                ELSE 'test_FD001.txt'
            END
        FROM stg.sensors s;

        -- Load RUL truth
        INSERT INTO bronze.rul_truth
        SELECT r.*, @BatchId, @LoadTime, 'RUL_FD001.txt'
        FROM stg.rul_truth r;

        -- Load plants
        INSERT INTO bronze.plants
        SELECT p.*, @BatchId, @LoadTime, 'plants.csv'
        FROM stg.plants p;

        -- Load technicians
        INSERT INTO bronze.technicians
        SELECT t.*, @BatchId, @LoadTime, 'technicians.csv'
        FROM stg.technicians t;

        -- Load engine master
        INSERT INTO bronze.engine_master
        SELECT e.*, @BatchId, @LoadTime, 'engine_master.csv'
        FROM stg.engine_master e;

        -- Load maintenance
        INSERT INTO bronze.maintenance
        SELECT m.*, @BatchId, @LoadTime, 'maintenance_log.csv'
        FROM stg.maintenance m;

        -- Log row counts for this batch only
        INSERT INTO ops.etl_log
            (batch_id, step_name, rows_in, rows_out, status)
        VALUES
            (@BatchId, 'Bronze Sensors',
                (SELECT COUNT(*) FROM stg.sensors),
                (SELECT COUNT(*) FROM bronze.sensors
                 WHERE batch_id = @BatchId), 'OK'),

            (@BatchId, 'Bronze RUL Truth',
                (SELECT COUNT(*) FROM stg.rul_truth),
                (SELECT COUNT(*) FROM bronze.rul_truth
                 WHERE batch_id = @BatchId), 'OK'),

            (@BatchId, 'Bronze Plants',
                (SELECT COUNT(*) FROM stg.plants),
                (SELECT COUNT(*) FROM bronze.plants
                 WHERE batch_id = @BatchId), 'OK'),

            (@BatchId, 'Bronze Technicians',
                (SELECT COUNT(*) FROM stg.technicians),
                (SELECT COUNT(*) FROM bronze.technicians
                 WHERE batch_id = @BatchId), 'OK'),

            (@BatchId, 'Bronze Engine Master',
                (SELECT COUNT(*) FROM stg.engine_master),
                (SELECT COUNT(*) FROM bronze.engine_master
                 WHERE batch_id = @BatchId), 'OK'),

            (@BatchId, 'Bronze Maintenance',
                (SELECT COUNT(*) FROM stg.maintenance),
                (SELECT COUNT(*) FROM bronze.maintenance
                 WHERE batch_id = @BatchId), 'OK');

        -- Check this batch's row counts
        IF EXISTS (
            SELECT 1
            FROM ops.etl_log
            WHERE batch_id = @BatchId
              AND rows_in <> rows_out
        )
        BEGIN
            THROW 50005, 'Bronze row count mismatch.', 1;
        END;

        COMMIT TRANSACTION;

        SELECT @BatchId AS CompletedBatchId;
        PRINT 'Bronze layer loaded successfully.';

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        THROW;
    END CATCH
END;
GO


SELECT
    name
FROM sys.procedures
WHERE schema_id = SCHEMA_ID('bronze');

--verifying if bronze is , it should return 0 for each TableName

SELECT 'sensors' AS TableName, COUNT(*) AS TotalRows
FROM bronze.sensors
UNION ALL
SELECT 'rul_truth', COUNT(*) FROM bronze.rul_truth
UNION ALL
SELECT 'plants', COUNT(*) FROM bronze.plants
UNION ALL
SELECT 'technicians', COUNT(*) FROM bronze.technicians
UNION ALL
SELECT 'engine_master', COUNT(*) FROM bronze.engine_master
UNION ALL
SELECT 'maintenance', COUNT(*) FROM bronze.maintenance;

/*
SELECT split, COUNT(*) AS TotalRows
FROM stg.sensors
GROUP BY split;
*/


USE PredMaintDW;
GO

EXEC bronze.usp_load_bronze
    @SourceVersion = 'FD001_Synthetic_V1';


SELECT *
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'ops';

--Load Data from staging layer to the bronze layer
USE PredMaintDW;
GO

EXEC bronze.usp_load_bronze
    @SourceVersion = 'FD001_Synthetic_V1';


SELECT *
FROM ops.bronze_batch;

SELECT
    step_name,
    rows_in,
    rows_out,
    status
FROM ops.etl_log
ORDER BY log_id;



