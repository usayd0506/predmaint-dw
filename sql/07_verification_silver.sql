
SELECT 'Engine Cycles' AS TableName,
       COUNT(*) AS TotalRows
FROM silver.engine_cycles

UNION ALL
SELECT 'RUL Truth', COUNT(*) FROM silver.rul_truth

UNION ALL
SELECT 'Plants', COUNT(*) FROM silver.plants

UNION ALL
SELECT 'Technicians', COUNT(*) FROM silver.technicians

UNION ALL
SELECT 'Engine Master', COUNT(*) FROM silver.engine_master

UNION ALL
SELECT 'Maintenance', COUNT(*) FROM silver.maintenance;

--verifying duplicates are gone
SELECT
    work_order_id,
    COUNT(*) AS TotalRows
FROM silver.maintenance
GROUP BY work_order_id
HAVING COUNT(*) > 1;

--verifying uniqueness of each sensor cycle
SELECT
    engine_uid,
    cycle,
    COUNT(*) AS TotalRows
FROM silver.engine_cycles
GROUP BY engine_uid, cycle
HAVING COUNT(*) > 1;

--Verify imputed maintenance durations
SELECT
    COUNT(*) AS ImputedRecords
FROM silver.maintenance
WHERE is_imputed = 1;

SELECT
    work_order_id,
    type,
    duration_hours,
    is_imputed
FROM silver.maintenance
WHERE is_imputed = 1;



WITH LastCycles AS (
    SELECT
        engine_uid,
        MAX(cycle) AS last_cycle
    FROM silver.engine_cycles
    WHERE split = 'train'
    GROUP BY engine_uid
)
SELECT
    e.engine_uid,
    e.cycle,
    e.rul
FROM silver.engine_cycles e
JOIN LastCycles l
    ON e.engine_uid = l.engine_uid
   AND e.cycle = l.last_cycle;

--Check the last cycle of every test engine

WITH LastCycles AS (
    SELECT
        engine_uid,
        MAX(cycle) AS last_cycle
    FROM silver.engine_cycles
    WHERE split = 'test'
    GROUP BY engine_uid
)

--Verify smoothed sensors
SELECT TOP 15
    engine_uid,
    cycle,
    s2,
    s2_sm,
    rul,
    rul_capped
FROM silver.engine_cycles
WHERE engine_uid = 1
ORDER BY cycle;

--Verify the ETL logs

SELECT
    batch_id,
    step_name,
    rows_in,
    rows_out,
    status,
    logged_at
FROM ops.etl_log
WHERE step_name LIKE 'Silver%'
ORDER BY log_id DESC;
