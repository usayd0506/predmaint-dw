USE PredMaintDW;
GO

SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;


    INSERT INTO mart.DimPlant (
        plant_id, plant_name, city, province,
        country, latitude, longitude
    )
    SELECT
        p.plant_id,
        p.plant_name,
        p.city,
        p.province,
        p.country,
        p.latitude,
        p.longitude
    FROM silver.plants p
    WHERE NOT EXISTS (
        SELECT 1
        FROM mart.DimPlant d
        WHERE d.plant_id = p.plant_id
    );


    INSERT INTO mart.DimEngine (
        engine_uid, engine_id, split,
        plant_id, commission_date
    )
    SELECT
        e.engine_uid,
        e.engine_id,
        e.split,
        e.plant_id,
        e.commission_date
    FROM silver.engine_master e
    WHERE NOT EXISTS (
        SELECT 1
        FROM mart.DimEngine d
        WHERE d.engine_uid = e.engine_uid
    );


    INSERT INTO mart.DimTechnician (
        technician_id, technician_name, plant_id,
        skill_level, hourly_rate, max_hours_per_week
    )
    SELECT
        t.technician_id,
        t.name,
        t.plant_id,
        t.skill_level,
        t.hourly_rate,
        t.max_hours_per_week
    FROM silver.technicians t
    WHERE NOT EXISTS (
        SELECT 1
        FROM mart.DimTechnician d
        WHERE d.technician_id = t.technician_id
    );


    INSERT INTO mart.DimModel (model_name)
    SELECT m.model_name
    FROM (
        SELECT model_name FROM gold.ml_predictions
        UNION
        SELECT model_name FROM gold.model_metrics
    ) m
    WHERE NOT EXISTS (
        SELECT 1
        FROM mart.DimModel d
        WHERE d.model_name = m.model_name
    );


    INSERT INTO mart.DimMethod (method_name)
    SELECT DISTINCT s.method
    FROM gold.work_order_schedule s
    WHERE NOT EXISTS (
        SELECT 1
        FROM mart.DimMethod d
        WHERE d.method_name = s.method
    );


    INSERT INTO mart.DimRun (
        run_id, bronze_batch_id,
        source_version, created_at, status
    )
    SELECT
        r.run_id,
        r.bronze_batch_id,
        r.source_version,
        r.created_at,
        r.status
    FROM gold.run_control r
    WHERE NOT EXISTS (
        SELECT 1
        FROM mart.DimRun d
        WHERE d.run_id = r.run_id
    );


    -- 7. Load Date Dimension

    ;WITH SourceDates AS (
        SELECT work_date AS full_date
        FROM silver.maintenance

        UNION

        SELECT last_cycle_date
        FROM gold.engine_health

        UNION

        SELECT CAST(slot_start AS DATE)
        FROM gold.work_order_schedule

        UNION

        SELECT CAST(created_at AS DATE)
        FROM gold.alerts

        UNION

        SELECT CAST(predicted_at AS DATE)
        FROM gold.ml_predictions
        WHERE predicted_at IS NOT NULL

        UNION

        SELECT CAST(created_at AS DATE)
        FROM gold.run_control
    )
    INSERT INTO mart.DimDate (
        date_key, full_date, day_number,
        month_number, month_name,
        quarter_number, year_number
    )
    SELECT
        YEAR(full_date) * 10000
            + MONTH(full_date) * 100
            + DAY(full_date),
        full_date,
        DAY(full_date),
        MONTH(full_date),
        DATENAME(MONTH, full_date),
        DATEPART(QUARTER, full_date),
        YEAR(full_date)
    FROM SourceDates s
    WHERE full_date IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM mart.DimDate d
          WHERE d.full_date = s.full_date
      );

    COMMIT TRANSACTION;

    PRINT 'Data Mart dimensions loaded successfully.';

END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;
GO

--verification
SELECT 'DimPlant' AS Dimension, COUNT(*) AS Records
FROM mart.DimPlant

UNION ALL

SELECT 'DimEngine', COUNT(*)
FROM mart.DimEngine

UNION ALL

SELECT 'DimTechnician', COUNT(*)
FROM mart.DimTechnician

UNION ALL

SELECT 'DimModel', COUNT(*)
FROM mart.DimModel

UNION ALL

SELECT 'DimMethod', COUNT(*)
FROM mart.DimMethod

UNION ALL

SELECT 'DimRun', COUNT(*)
FROM mart.DimRun

UNION ALL

SELECT 'DimDate', COUNT(*)
FROM mart.DimDate;