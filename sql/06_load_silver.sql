/*
A few design decisions are worth understanding:
- Silver is refreshed as a single selected snapshot. The six tables are deleted and repopulated within one transaction. Bronze remains unchanged.
- ROW_NUMBER() removes duplicate work orders before calculating median durations. This prevents duplicate source records from distorting the median.
- The rolling averages are calculated after duplicate sensor cycles have been removed.
- An is_imputed flag identifies maintenance durations that were replaced.
- The procedure records row counts in ops.etl_log, including legitimate reductions caused by deduplication.
*/

--checking for duplicates

SELECT
    work_order_id,
    COUNT(*) AS Occurrences
FROM bronze.maintenance
GROUP BY work_order_id
HAVING COUNT(*) > 1;

--Check source data conversion(identifies invalid dates, invalid costs, or invalid duration values)

SELECT
    work_order_id,
    work_date,
    duration_hours,
    cost
FROM bronze.maintenance
WHERE TRY_CONVERT(DATE, work_date) IS NULL
   OR TRY_CONVERT(DECIMAL(12,2), cost) IS NULL
   OR (
       NULLIF(LTRIM(RTRIM(duration_hours)), '') IS NOT NULL
       AND TRY_CONVERT(DECIMAL(8,2), duration_hours) IS NULL
   );

--check for all missing values in important sensors so that it is catered when we load them in silver
SELECT
    COUNT(*) AS TotalRows,
    COUNT(*) - COUNT(sensor_1) AS MissingSensor1,
    COUNT(*) - COUNT(sensor_2) AS MissingSensor2,
    COUNT(*) - COUNT(sensor_3) AS MissingSensor3,
    COUNT(*) - COUNT(sensor_4) AS MissingSensor4,
    COUNT(*) - COUNT(sensor_5) AS MissingSensor5,
    COUNT(*) - COUNT(sensor_6) AS MissingSensor6,
    COUNT(*) - COUNT(sensor_7) AS MissingSensor7,
    COUNT(*) - COUNT(sensor_8) AS MissingSensor8,
    COUNT(*) - COUNT(sensor_9) AS MissingSensor9,
    COUNT(*) - COUNT(sensor_10) AS MissingSensor10,
    COUNT(*) - COUNT(sensor_11) AS MissingSensor11,
    COUNT(*) - COUNT(sensor_12) AS MissingSensor12,
    COUNT(*) - COUNT(sensor_13) AS MissingSensor13,
    COUNT(*) - COUNT(sensor_14) AS MissingSensor14,
    COUNT(*) - COUNT(sensor_15) AS MissingSensor15,
    COUNT(*) - COUNT(sensor_16) AS MissingSensor16,
    COUNT(*) - COUNT(sensor_17) AS MissingSensor17,
    COUNT(*) - COUNT(sensor_18) AS MissingSensor18,
    COUNT(*) - COUNT(sensor_19) AS MissingSensor19,
    COUNT(*) - COUNT(sensor_20) AS MissingSensor20,
    COUNT(*) - COUNT(sensor_21) AS MissingSensor21
FROM bronze.sensors;


USE PredMaintDW;
GO

CREATE OR ALTER PROCEDURE silver.usp_load_silver
    @BatchId UNIQUEIDENTIFIER
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    -- Check the selected Bronze batch
    IF NOT EXISTS (
        SELECT 1
        FROM ops.bronze_batch
        WHERE batch_id = @BatchId
          AND status = 'OK'
    )
    BEGIN
        THROW 50010, 'Bronze batch not found or not successful.', 1;
    END;

    -- Check that the batch contains all six datasets
    IF NOT EXISTS (SELECT 1 FROM bronze.sensors WHERE batch_id = @BatchId)
       OR NOT EXISTS (SELECT 1 FROM bronze.rul_truth WHERE batch_id = @BatchId)
       OR NOT EXISTS (SELECT 1 FROM bronze.plants WHERE batch_id = @BatchId)
       OR NOT EXISTS (SELECT 1 FROM bronze.technicians WHERE batch_id = @BatchId)
       OR NOT EXISTS (SELECT 1 FROM bronze.engine_master WHERE batch_id = @BatchId)
       OR NOT EXISTS (SELECT 1 FROM bronze.maintenance WHERE batch_id = @BatchId)
    BEGIN
        THROW 50011, 'Selected batch has missing datasets.', 1;
    END;

    -- Check engine IDs and sensor cycles
    IF EXISTS (
        SELECT 1
        FROM bronze.engine_master
        WHERE batch_id = @BatchId
          AND (
              engine_uid IS NULL
              OR engine_id IS NULL
              OR plant_id IS NULL
              OR commission_date IS NULL
              OR split IS NULL
              OR split NOT IN ('train', 'test')
              OR engine_uid <>
                  CASE WHEN split = 'test'
                       THEN 1000 + engine_id
                       ELSE engine_id END
          )
    )
    BEGIN
        THROW 50012, 'Invalid engine master data.', 1;
    END;

    IF EXISTS (
        SELECT 1
        FROM bronze.sensors
        WHERE batch_id = @BatchId
          AND (engine_id IS NULL
               OR cycle IS NULL
               OR cycle < 1
               OR split IS NULL
               OR split NOT IN ('train', 'test'))
    )
    BEGIN
        THROW 50013, 'Invalid sensor IDs or cycles.', 1;
    END;

    -- Validate source dates and numeric maintenance values
    IF EXISTS (
        SELECT 1
        FROM bronze.maintenance
        WHERE batch_id = @BatchId
          AND (
              work_order_id IS NULL
              OR engine_uid IS NULL
              OR technician_id IS NULL
              OR TRY_CONVERT(DATE, work_date) IS NULL
              OR TRY_CONVERT(DECIMAL(12,2), cost) IS NULL
              OR TRY_CONVERT(DECIMAL(12,2), cost) < 0
              OR (
                  NULLIF(LTRIM(RTRIM(duration_hours)), '') IS NOT NULL
                  AND TRY_CONVERT(DECIMAL(8,2), duration_hours) IS NULL
              )
              OR TRY_CONVERT(DECIMAL(8,2), duration_hours) < 0
          )
    )
    BEGIN
        THROW 50014, 'Invalid maintenance dates or numeric values.', 1;
    END;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- Clear only the current Silver snapshot
        DELETE FROM silver.engine_cycles;
        DELETE FROM silver.maintenance;
        DELETE FROM silver.rul_truth;
        DELETE FROM silver.technicians;
        DELETE FROM silver.engine_master;
        DELETE FROM silver.plants;

        -- 1. Plants
        INSERT INTO silver.plants
        SELECT
            plant_id,
            LTRIM(RTRIM(plant_name)),
            LTRIM(RTRIM(city)),
            LTRIM(RTRIM(province)),
            UPPER(LTRIM(RTRIM(country))),
            latitude,
            longitude
        FROM bronze.plants
        WHERE batch_id = @BatchId;

        -- 2. Technicians
        INSERT INTO silver.technicians
        SELECT
            technician_id,
            LTRIM(RTRIM(name)),
            plant_id,
            CASE UPPER(LTRIM(RTRIM(skill_level)))
                WHEN 'JUNIOR' THEN 'Junior'
                WHEN 'MID' THEN 'Mid'
                WHEN 'SENIOR' THEN 'Senior'
            END,
            hourly_rate,
            max_hours_per_week
        FROM bronze.technicians
        WHERE batch_id = @BatchId;

        -- 3. Engine Master
        INSERT INTO silver.engine_master
        SELECT
            engine_uid,
            engine_id,
            split,
            plant_id,
            commission_date
        FROM bronze.engine_master
        WHERE batch_id = @BatchId;

        -- 4. RUL Truth
        INSERT INTO silver.rul_truth
        SELECT
            engine_id,
            true_rul
        FROM bronze.rul_truth
        WHERE batch_id = @BatchId;

        -- Check plant references
        IF EXISTS (
            SELECT 1
            FROM silver.technicians t
            LEFT JOIN silver.plants p
                ON t.plant_id = p.plant_id
            WHERE p.plant_id IS NULL
        )
        OR EXISTS (
            SELECT 1
            FROM silver.engine_master e
            LEFT JOIN silver.plants p
                ON e.plant_id = p.plant_id
            WHERE p.plant_id IS NULL
        )
        BEGIN
            THROW 50015, 'Invalid plant references.', 1;
        END;

        -- Check RUL truth values
        IF EXISTS (
            SELECT 1
            FROM silver.rul_truth
            WHERE true_rul IS NULL OR true_rul < 0
        )
        BEGIN
            THROW 50016, 'Invalid RUL truth values.', 1;
        END;

        -- Check that every test engine has RUL truth
        IF EXISTS (
            SELECT 1
            FROM silver.engine_master e
            LEFT JOIN silver.rul_truth r
                ON e.engine_id = r.engine_id
            WHERE e.split = 'test'
              AND r.engine_id IS NULL
        )
        BEGIN
            THROW 50017, 'Missing test engine RUL truth.', 1;
        END;

        -- Check that every sensor engine exists
        IF EXISTS (
            SELECT 1
            FROM bronze.sensors s
            LEFT JOIN silver.engine_master e
                ON s.engine_id = e.engine_id
               AND s.split = e.split
            WHERE s.batch_id = @BatchId
              AND e.engine_uid IS NULL
        )
        BEGIN
            THROW 50018, 'Sensor engine not found in master.', 1;
        END;

        -- Check maintenance references
        IF EXISTS (
            SELECT 1
            FROM bronze.maintenance m
            LEFT JOIN silver.engine_master e
                ON m.engine_uid = e.engine_uid
            LEFT JOIN silver.technicians t
                ON m.technician_id = t.technician_id
            WHERE m.batch_id = @BatchId
              AND (e.engine_uid IS NULL
                   OR t.technician_id IS NULL)
        )
        BEGIN
            THROW 50019, 'Invalid maintenance references.', 1;
        END;

        -- 5. Clean Maintenance
        ;WITH Dedup AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY work_order_id
                    ORDER BY
                        CASE WHEN duration_hours IS NULL
                             THEN 1 ELSE 0 END,
                        work_date DESC,
                        technician_id
                ) AS rn
            FROM bronze.maintenance
            WHERE batch_id = @BatchId
        ),
        Clean AS (
            SELECT
                work_order_id,
                engine_uid,
                TRY_CONVERT(DATE, work_date) AS work_date,
                CASE UPPER(LTRIM(RTRIM(type)))
                    WHEN 'INSPECTION' THEN 'Inspection'
                    WHEN 'REPAIR' THEN 'Repair'
                    WHEN 'REPLACEMENT' THEN 'Replacement'
                END AS type,
                technician_id,
                TRY_CONVERT(DECIMAL(8,2), duration_hours)
                    AS duration_hours,
                TRY_CONVERT(DECIMAL(12,2), cost) AS cost
            FROM Dedup
            WHERE rn = 1
        ),
        WithMedian AS (
            SELECT *,
                PERCENTILE_CONT(0.5)
                    WITHIN GROUP (ORDER BY duration_hours)
                    OVER (PARTITION BY type) AS median_duration
            FROM Clean
        )
        INSERT INTO silver.maintenance (
            work_order_id, engine_uid, work_date,
            type, technician_id, duration_hours,
            cost, is_imputed
        )
        SELECT
            work_order_id,
            engine_uid,
            work_date,
            type,
            technician_id,
            COALESCE(duration_hours, median_duration),
            cost,
            CASE WHEN duration_hours IS NULL THEN 1 ELSE 0 END
        FROM WithMedian;

        IF EXISTS (
            SELECT 1 FROM silver.maintenance
            WHERE duration_hours IS NULL OR type IS NULL
        )
        BEGIN
            THROW 50020, 'Maintenance cleaning is incomplete.', 1;
        END;

        -- 6. Clean sensor cycles and calculate RUL
        ;WITH Base AS (
            SELECT
                s.*,
                e.engine_uid,
                e.commission_date,
                MAX(s.cycle) OVER (
                    PARTITION BY s.split, s.engine_id
                ) AS max_cycle
            FROM bronze.sensors s
            JOIN silver.engine_master e
                ON s.engine_id = e.engine_id
               AND s.split = e.split
            WHERE s.batch_id = @BatchId
        ),
        Dedup AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY engine_uid, cycle
                    ORDER BY load_ts DESC, source_file
                ) AS rn
            FROM Base
        ),
        UniqueCycles AS (
            SELECT *
            FROM Dedup
            WHERE rn = 1
        ),
        Calculated AS (
            SELECT
                u.*,
                CASE
                    WHEN u.split = 'train'
                        THEN u.max_cycle - u.cycle
                    ELSE
                        u.max_cycle - u.cycle + r.true_rul
                END AS calculated_rul
            FROM UniqueCycles u
            LEFT JOIN silver.rul_truth r
                ON u.split = 'test'
               AND u.engine_id = r.engine_id
        )
        INSERT INTO silver.engine_cycles (
            engine_uid, engine_id, split, cycle, cycle_date,
            setting_1, setting_2, setting_3,
            s2, s3, s4, s7, s8, s9, s11, s12,
            s13, s14, s15, s17, s20, s21,
            s2_sm, s3_sm, s4_sm, s7_sm, s8_sm, s9_sm,
            s11_sm, s12_sm, s13_sm, s14_sm, s15_sm,
            s17_sm, s20_sm, s21_sm,
            rul, rul_capped
        )
        SELECT
            engine_uid,
            engine_id,
            split,
            cycle,
            DATEADD(DAY, cycle - 1, commission_date),

            setting_1,
            setting_2,
            setting_3,

            sensor_2,
            sensor_3,
            sensor_4,
            sensor_7,
            sensor_8,
            sensor_9,
            sensor_11,
            sensor_12,
            sensor_13,
            sensor_14,
            sensor_15,
            sensor_17,
            sensor_20,
            sensor_21,

            AVG(sensor_2) OVER (
                PARTITION BY engine_uid ORDER BY cycle
                ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
            ),
            AVG(sensor_3) OVER (
                PARTITION BY engine_uid ORDER BY cycle
                ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
            ),
            AVG(sensor_4) OVER (
                PARTITION BY engine_uid ORDER BY cycle
                ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
            ),
            AVG(sensor_7) OVER (
                PARTITION BY engine_uid ORDER BY cycle
                ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
            ),
            AVG(sensor_8) OVER (
                PARTITION BY engine_uid ORDER BY cycle
                ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
            ),
            AVG(sensor_9) OVER (
                PARTITION BY engine_uid ORDER BY cycle
                ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
            ),
            AVG(sensor_11) OVER (
                PARTITION BY engine_uid ORDER BY cycle
                ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
            ),
            AVG(sensor_12) OVER (
                PARTITION BY engine_uid ORDER BY cycle
                ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
            ),
            AVG(sensor_13) OVER (
                PARTITION BY engine_uid ORDER BY cycle
                ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
            ),
            AVG(sensor_14) OVER (
                PARTITION BY engine_uid ORDER BY cycle
                ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
            ),
            AVG(sensor_15) OVER (
                PARTITION BY engine_uid ORDER BY cycle
                ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
            ),
            AVG(sensor_17) OVER (
                PARTITION BY engine_uid ORDER BY cycle
                ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
            ),
            AVG(sensor_20) OVER (
                PARTITION BY engine_uid ORDER BY cycle
                ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
            ),
            AVG(sensor_21) OVER (
                PARTITION BY engine_uid ORDER BY cycle
                ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
            ),

            calculated_rul,
            CASE
                WHEN calculated_rul > 125 THEN 125
                ELSE calculated_rul
            END
        FROM Calculated;

        -- Record this Silver processing batch
        INSERT INTO ops.etl_log
            (batch_id, step_name, rows_in, rows_out, status)
        VALUES
            (@BatchId, 'Silver Sensors',
             (SELECT COUNT(*) FROM bronze.sensors
              WHERE batch_id = @BatchId),
             (SELECT COUNT(*) FROM silver.engine_cycles), 'OK'),

            (@BatchId, 'Silver Maintenance',
             (SELECT COUNT(*) FROM bronze.maintenance
              WHERE batch_id = @BatchId),
             (SELECT COUNT(*) FROM silver.maintenance), 'OK'),

            (@BatchId, 'Silver Plants',
             (SELECT COUNT(*) FROM bronze.plants
              WHERE batch_id = @BatchId),
             (SELECT COUNT(*) FROM silver.plants), 'OK'),

            (@BatchId, 'Silver Technicians',
             (SELECT COUNT(*) FROM bronze.technicians
              WHERE batch_id = @BatchId),
             (SELECT COUNT(*) FROM silver.technicians), 'OK'),

            (@BatchId, 'Silver Engine Master',
             (SELECT COUNT(*) FROM bronze.engine_master
              WHERE batch_id = @BatchId),
             (SELECT COUNT(*) FROM silver.engine_master), 'OK'),

            (@BatchId, 'Silver RUL Truth',
             (SELECT COUNT(*) FROM bronze.rul_truth
              WHERE batch_id = @BatchId),
             (SELECT COUNT(*) FROM silver.rul_truth), 'OK');

        COMMIT TRANSACTION;

        PRINT 'Silver layer loaded successfully.';

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        THROW;
    END CATCH
END;
GO


DECLARE @BatchId UNIQUEIDENTIFIER;

SELECT @BatchId = batch_id
FROM ops.bronze_batch
WHERE source_version = 'FD001_Synthetic_V1'
  AND status = 'OK';

IF @BatchId IS NULL
BEGIN
    THROW 50030, 'Selected Bronze batch not found', 1;
END;

EXEC silver.usp_load_silver @BatchId = @BatchId;