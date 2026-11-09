USE PredMaintDW;
GO


SELECT TOP (5) run_id, bronze_batch_id, source_version, status, created_at
FROM gold.run_control ORDER BY created_at DESC;

-- Gold expected: 100 test-engine health rows, 200 model predictions
SELECT 'engine_health' AS table_name, COUNT(*) AS row_count FROM gold.engine_health
UNION ALL SELECT 'ml_predictions', COUNT(*) FROM gold.ml_predictions
UNION ALL SELECT 'model_metrics', COUNT(*) FROM gold.model_metrics
UNION ALL SELECT 'alerts', COUNT(*) FROM gold.alerts
UNION ALL SELECT 'work_order_schedule', COUNT(*) FROM gold.work_order_schedule;

SELECT model_name, metric, value
FROM gold.model_metrics
WHERE run_id = (SELECT TOP (1) run_id FROM gold.run_control WHERE status='OK' ORDER BY created_at DESC)
ORDER BY model_name, metric;

SELECT risk_level, degradation_stage, COUNT(*) AS engines
FROM gold.engine_health GROUP BY risk_level, degradation_stage;

SELECT method, COUNT(*) AS scheduled, SUM(est_cost) AS total_labor_cost
FROM gold.work_order_schedule GROUP BY method;

-- Should be empty (also blocked by a UNIQUE constraint)
SELECT run_id, method, technician_id, slot_start, COUNT(*) AS overlaps
FROM gold.work_order_schedule
GROUP BY run_id, method, technician_id, slot_start
HAVING COUNT(*) > 1;

-- Alert rules should exist in gold.rule_catalog
SELECT TOP (10) engine_uid, severity, action, rules_fired
FROM gold.alerts ORDER BY alert_id DESC;
GO

SELECT COUNT(*) AS HealthRecords
FROM gold.engine_health;

SELECT COUNT(*) AS Predictions
FROM gold.ml_predictions;

SELECT COUNT(*) AS Alerts
FROM gold.alerts;

SELECT COUNT(*) AS ScheduleRecords
FROM gold.work_order_schedule;