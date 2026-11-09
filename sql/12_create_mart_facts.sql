USE PredMaintDW;
GO

-- Grain: one engine per pipeline run
    CREATE TABLE mart.FactEngineHealth (
        health_fact_key BIGINT IDENTITY(1,1) PRIMARY KEY,
        run_key INT NOT NULL REFERENCES mart.DimRun(run_key),
        engine_key INT NOT NULL REFERENCES mart.DimEngine(engine_key),
        plant_key INT NOT NULL REFERENCES mart.DimPlant(plant_key),
        date_key INT NOT NULL REFERENCES mart.DimDate(date_key),
        cycles_run INT NOT NULL,
        last_maintenance DATE NULL,
        health_index DECIMAL(12,4) NOT NULL,
        degradation_stage VARCHAR(50) NOT NULL,
        risk_level VARCHAR(30) NOT NULL,
        CONSTRAINT UQ_FactEngineHealth UNIQUE (run_key, engine_key)
    );
GO

-- Grain: one engine, one ML model, per pipeline run
    CREATE TABLE mart.FactRULPrediction (
        prediction_fact_key BIGINT IDENTITY(1,1) PRIMARY KEY,
        run_key INT NOT NULL REFERENCES mart.DimRun(run_key),
        engine_key INT NOT NULL REFERENCES mart.DimEngine(engine_key),
        model_key INT NOT NULL REFERENCES mart.DimModel(model_key),
        date_key INT NULL REFERENCES mart.DimDate(date_key),
        predicted_at DATETIME2 NULL,
        predicted_rul FLOAT NOT NULL,
        failure_prob_30 FLOAT NOT NULL,
        CONSTRAINT UQ_FactRULPrediction UNIQUE (run_key, engine_key, model_key)
    );

GO

-- Grain: one alert per pipeline run

    CREATE TABLE mart.FactAlert (
        alert_fact_key BIGINT IDENTITY(1,1) PRIMARY KEY,
        run_key INT NOT NULL REFERENCES mart.DimRun(run_key),
        engine_key INT NOT NULL REFERENCES mart.DimEngine(engine_key),
        date_key INT NOT NULL REFERENCES mart.DimDate(date_key),
        alert_id INT NOT NULL,
        created_at DATETIME2 NOT NULL,
        severity VARCHAR(30) NOT NULL,
        recommended_action VARCHAR(MAX) NOT NULL,
        rules_fired VARCHAR(MAX) NOT NULL,
        alert_count INT NOT NULL DEFAULT 1,
        CONSTRAINT UQ_FactAlert UNIQUE (run_key, alert_id)
    );

GO

-- Grain: one cleaned Silver work order
    CREATE TABLE mart.FactMaintenance (
        maintenance_fact_key BIGINT IDENTITY(1,1) PRIMARY KEY,
        work_order_id INT NOT NULL UNIQUE,
        engine_key INT NOT NULL REFERENCES mart.DimEngine(engine_key),
        technician_key INT NOT NULL REFERENCES mart.DimTechnician(technician_key),
        date_key INT NOT NULL REFERENCES mart.DimDate(date_key),
        maintenance_type VARCHAR(50) NOT NULL,
        duration_hours DECIMAL(10,2) NOT NULL,
        maintenance_cost DECIMAL(14,2) NULL,
        is_imputed BIT NOT NULL,
        work_order_count INT NOT NULL DEFAULT 1
    );
GO

-- Grain: one scheduled assignment per pipeline run
    CREATE TABLE mart.FactSchedule (
        schedule_fact_key BIGINT IDENTITY(1,1) PRIMARY KEY,
        run_key INT NOT NULL REFERENCES mart.DimRun(run_key),
        engine_key INT NOT NULL REFERENCES mart.DimEngine(engine_key),
        technician_key INT NOT NULL REFERENCES mart.DimTechnician(technician_key),
        method_key INT NOT NULL REFERENCES mart.DimMethod(method_key),
        date_key INT NOT NULL REFERENCES mart.DimDate(date_key),
        schedule_id INT NOT NULL,
        slot_start DATETIME2 NOT NULL,
        slot_hours DECIMAL(10,2) NOT NULL,
        est_cost DECIMAL(14,2) NOT NULL,
        assignment_count INT NOT NULL DEFAULT 1,
        CONSTRAINT UQ_FactSchedule UNIQUE (run_key, schedule_id)
    );
GO

-- Grain: one metric name, one ML model, per pipeline run.
    CREATE TABLE mart.FactModelMetric (
        model_metric_fact_key BIGINT IDENTITY(1,1) PRIMARY KEY,
        run_key INT NOT NULL REFERENCES mart.DimRun(run_key),
        model_key INT NOT NULL REFERENCES mart.DimModel(model_key),
        metric_name VARCHAR(100) NOT NULL,
        metric_value FLOAT NOT NULL,
        CONSTRAINT UQ_FactModelMetric UNIQUE (run_key, model_key, metric_name)
    );
GO

-- Useful indexes for joins and Power BI filtering
IF NOT EXISTS (SELECT 1 
			   FROM sys.indexes 
			   WHERE object_id=OBJECT_ID('mart.FactEngineHealth') 
			   AND name='IX_FactEngineHealth_DatePlant'
			 )
    CREATE INDEX IX_FactEngineHealth_DatePlant ON mart.FactEngineHealth(date_key, plant_key);

IF NOT EXISTS (
		SELECT 1 
		FROM sys.indexes 
		WHERE object_id=OBJECT_ID('mart.FactRULPrediction') 
		AND name='IX_FactRULPrediction_Model'
		)
    CREATE INDEX IX_FactRULPrediction_Model ON mart.FactRULPrediction(model_key);

IF NOT EXISTS (
	SELECT 1 
	FROM sys.indexes 
	WHERE object_id=OBJECT_ID('mart.FactAlert') 
	AND name='IX_FactAlert_Date')

    CREATE INDEX IX_FactAlert_Date ON mart.FactAlert(date_key);

IF NOT EXISTS (
	SELECT 1 
	FROM sys.indexes 
	WHERE object_id=OBJECT_ID('mart.FactMaintenance') 
	AND name='IX_FactMaintenance_TechnicianDate')

    CREATE INDEX IX_FactMaintenance_TechnicianDate ON mart.FactMaintenance(technician_key, date_key);

IF NOT EXISTS (
	SELECT 1 
	FROM sys.indexes 
	WHERE object_id=OBJECT_ID('mart.FactSchedule') 
	AND name='IX_FactSchedule_MethodDate'
	)
    CREATE INDEX IX_FactSchedule_MethodDate ON mart.FactSchedule(method_key, date_key);
GO
