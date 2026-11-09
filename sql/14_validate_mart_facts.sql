USE PredMaintDW;
GO
SELECT 'FactEngineHealth' AS fact_table, COUNT(*) AS rows_loaded FROM mart.FactEngineHealth
UNION ALL SELECT 'FactRULPrediction', COUNT(*) FROM mart.FactRULPrediction
UNION ALL SELECT 'FactAlert', COUNT(*) FROM mart.FactAlert
UNION ALL SELECT 'FactMaintenance', COUNT(*) FROM mart.FactMaintenance
UNION ALL SELECT 'FactSchedule', COUNT(*) FROM mart.FactSchedule
UNION ALL SELECT 'FactModelMetric', COUNT(*) FROM mart.FactModelMetric;
GO

SELECT 'Engine health' AS source_name, (SELECT COUNT(*) FROM gold.engine_health) AS source_rows,
       (SELECT COUNT(*) FROM mart.FactEngineHealth) AS mart_rows
UNION ALL SELECT 'RUL predictions', (SELECT COUNT(*) FROM gold.ml_predictions), (SELECT COUNT(*) FROM mart.FactRULPrediction)
UNION ALL SELECT 'Alerts', (SELECT COUNT(*) FROM gold.alerts), (SELECT COUNT(*) FROM mart.FactAlert)
UNION ALL SELECT 'Maintenance', (SELECT COUNT(*) FROM silver.maintenance), (SELECT COUNT(*) FROM mart.FactMaintenance)
UNION ALL SELECT 'Schedule', (SELECT COUNT(*) FROM gold.work_order_schedule), (SELECT COUNT(*) FROM mart.FactSchedule)
UNION ALL SELECT 'Model metrics', (SELECT COUNT(*) FROM gold.model_metrics), (SELECT COUNT(*) FROM mart.FactModelMetric);
GO

SELECT model_name, COUNT(*) AS prediction_records, AVG(predicted_rul) AS avg_predicted_rul,
       AVG(failure_prob_30) AS avg_failure_probability
FROM mart.FactRULPrediction f
JOIN mart.DimModel m ON f.model_key=m.model_key
GROUP BY model_name;
GO

SELECT p.plant_name, COUNT(*) AS engines,
       AVG(f.health_index) AS avg_health_index
FROM mart.FactEngineHealth f
JOIN mart.DimPlant p ON p.plant_key=f.plant_key
GROUP BY p.plant_name;
GO

SELECT m.method_name, COUNT(*) AS scheduled_jobs,
       SUM(f.slot_hours) AS total_hours, SUM(f.est_cost) AS total_estimated_cost
FROM mart.FactSchedule f
JOIN mart.DimMethod m ON m.method_key=f.method_key
GROUP BY m.method_name;
GO

SELECT maintenance_type, COUNT(*) AS jobs,
       SUM(CASE WHEN is_imputed = 1 THEN 1 ELSE 0 END) AS imputed_jobs,
       AVG(duration_hours) AS avg_duration_hours
FROM mart.FactMaintenance
GROUP BY maintenance_type;
GO


