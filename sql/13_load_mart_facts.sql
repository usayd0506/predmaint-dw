USE PredMaintDW;
GO
SET XACT_ABORT ON;
GO
BEGIN TRY
    BEGIN TRANSACTION;

    -- making sure shared dimension members exist before loading facts
    IF EXISTS (SELECT 1 FROM gold.engine_health g LEFT JOIN mart.DimRun r ON r.run_id=g.run_id WHERE r.run_key IS NULL)
        THROW 51001, 'Missing DimRun member(s). Rerun 08_load_mart_dimensions.sql.', 1;
    IF EXISTS (SELECT 1 FROM gold.ml_predictions g LEFT JOIN mart.DimModel m ON m.model_name=g.model_name WHERE m.model_key IS NULL)
        THROW 51002, 'Missing DimModel member(s). Rerun 08_load_mart_dimensions.sql.', 1;
    IF EXISTS (SELECT 1 FROM gold.work_order_schedule g LEFT JOIN mart.DimMethod m ON m.method_name=g.method WHERE m.method_key IS NULL)
        THROW 51003, 'Missing DimMethod member(s). Rerun 08_load_mart_dimensions.sql.', 1;

    -- Fresh snapshot refresh, get the latest transactions
    DELETE FROM mart.FactModelMetric;
    DELETE FROM mart.FactSchedule;
    DELETE FROM mart.FactMaintenance;
    DELETE FROM mart.FactAlert;
    DELETE FROM mart.FactRULPrediction;
    DELETE FROM mart.FactEngineHealth;

    INSERT INTO mart.FactEngineHealth (
        run_key, engine_key, plant_key, date_key, cycles_run,
        last_maintenance, health_index, degradation_stage, risk_level
    )
    SELECT
        r.run_key, e.engine_key, p.plant_key, d.date_key, g.cycles_run,
        g.last_maintenance, g.health_index, g.degradation_stage, g.risk_level
    FROM gold.engine_health g
    JOIN mart.DimRun r ON r.run_id = g.run_id
    JOIN mart.DimEngine e ON e.engine_uid = g.engine_uid
    JOIN mart.DimPlant p ON p.plant_id = g.plant_id
    JOIN mart.DimDate d ON d.full_date = g.last_cycle_date;

    INSERT INTO mart.FactRULPrediction (
        run_key, engine_key, model_key, date_key, predicted_at,
        predicted_rul, failure_prob_30
    )
    SELECT
        r.run_key, e.engine_key, m.model_key, d.date_key, g.predicted_at,
        g.predicted_rul, g.failure_prob_30
    FROM gold.ml_predictions g
    JOIN mart.DimRun r ON r.run_id = g.run_id
    JOIN mart.DimEngine e ON e.engine_uid = g.engine_uid
    JOIN mart.DimModel m ON m.model_name = g.model_name
    LEFT JOIN mart.DimDate d ON d.full_date = CAST(g.predicted_at AS DATE);

    INSERT INTO mart.FactAlert (
        run_key, engine_key, date_key, alert_id, created_at,
        severity, recommended_action, rules_fired
    )
    SELECT
        r.run_key, e.engine_key, d.date_key, g.alert_id, g.created_at,
        g.severity, g.action, g.rules_fired
    FROM gold.alerts g
    JOIN mart.DimRun r ON r.run_id = g.run_id
    JOIN mart.DimEngine e ON e.engine_uid = g.engine_uid
    JOIN mart.DimDate d ON d.full_date = CAST(g.created_at AS DATE);

    INSERT INTO mart.FactMaintenance (
        work_order_id, engine_key, technician_key, date_key,
        maintenance_type, duration_hours, maintenance_cost, is_imputed
    )
    SELECT
        s.work_order_id, e.engine_key, t.technician_key, d.date_key,
        s.type, s.duration_hours, s.cost, s.is_imputed
    FROM silver.maintenance s
    JOIN mart.DimEngine e ON e.engine_uid = s.engine_uid
    JOIN mart.DimTechnician t ON t.technician_id = s.technician_id
    JOIN mart.DimDate d ON d.full_date = s.work_date;

    INSERT INTO mart.FactSchedule (
        run_key, engine_key, technician_key, method_key, date_key,
        schedule_id, slot_start, slot_hours, est_cost
    )
    SELECT
        r.run_key, e.engine_key, t.technician_key, m.method_key, d.date_key,
        g.schedule_id, g.slot_start, g.slot_hours, g.est_cost
    FROM gold.work_order_schedule g
    JOIN mart.DimRun r ON r.run_id = g.run_id
    JOIN mart.DimEngine e ON e.engine_uid = g.engine_uid
    JOIN mart.DimTechnician t ON t.technician_id = g.technician_id
    JOIN mart.DimMethod m ON m.method_name = g.method
    JOIN mart.DimDate d ON d.full_date = CAST(g.slot_start AS DATE);

    INSERT INTO mart.FactModelMetric (
        run_key, model_key, metric_name, metric_value
    )
    SELECT
        r.run_key, m.model_key, g.metric, g.value
    FROM gold.model_metrics g
    JOIN mart.DimRun r ON r.run_id = g.run_id
    JOIN mart.DimModel m ON m.model_name = g.model_name;

    -- Detect missing dimensional matches
    IF (SELECT COUNT_BIG(*) FROM mart.FactEngineHealth) <> (SELECT COUNT_BIG(*) FROM gold.engine_health)
        THROW 51011, 'Engine health fact row count differs from Gold.', 1;
    IF (SELECT COUNT_BIG(*) FROM mart.FactRULPrediction) <> (SELECT COUNT_BIG(*) FROM gold.ml_predictions)
        THROW 51012, 'Prediction fact row count differs from Gold.', 1;
    IF (SELECT COUNT_BIG(*) FROM mart.FactAlert) <> (SELECT COUNT_BIG(*) FROM gold.alerts)
        THROW 51013, 'Alert fact row count differs from Gold.', 1;
    IF (SELECT COUNT_BIG(*) FROM mart.FactMaintenance) <> (SELECT COUNT_BIG(*) FROM silver.maintenance)
        THROW 51014, 'Maintenance fact row count differs from Silver.', 1;
    IF (SELECT COUNT_BIG(*) FROM mart.FactSchedule) <> (SELECT COUNT_BIG(*) FROM gold.work_order_schedule)
        THROW 51015, 'Schedule fact row count differs from Gold.', 1;
    IF (SELECT COUNT_BIG(*) FROM mart.FactModelMetric) <> (SELECT COUNT_BIG(*) FROM gold.model_metrics)
        THROW 51016, 'Model metric fact row count differs from Gold.', 1;

    -- Optional date should only be missing when source prediction timestamp is NULL
    IF EXISTS (SELECT 1 FROM mart.FactRULPrediction WHERE predicted_at IS NOT NULL AND date_key IS NULL)
        THROW 51017, 'Some non-null prediction timestamps are absent in DimDate.', 1;

    COMMIT TRANSACTION;
    PRINT 'All six mart fact tables loaded successfully.';
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO
