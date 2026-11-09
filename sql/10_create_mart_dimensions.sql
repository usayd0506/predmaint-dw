USE PredMaintDW;
GO

IF SCHEMA_ID('mart') IS NULL
    EXEC('CREATE SCHEMA mart');
GO

CREATE TABLE mart.DimPlant (
      plant_key INT IDENTITY(1,1) PRIMARY KEY,
      plant_id INT NOT NULL UNIQUE,
      plant_name VARCHAR(100),
      city VARCHAR(100),
      province VARCHAR(100),
      country VARCHAR(100),
      latitude FLOAT,
      longitude FLOAT
    );
GO


CREATE TABLE mart.DimEngine (
    engine_key INT IDENTITY(1,1) PRIMARY KEY,
    engine_uid INT NOT NULL UNIQUE,
    engine_id INT,
    split VARCHAR(10),
    plant_id INT,
    commission_date DATE
);
GO


CREATE TABLE mart.DimTechnician (
    technician_key INT IDENTITY(1,1) PRIMARY KEY,
    technician_id INT NOT NULL UNIQUE,
    technician_name VARCHAR(100),
    plant_id INT,
    skill_level VARCHAR(30),
    hourly_rate DECIMAL(12,2),
    max_hours_per_week INT
);
GO


CREATE TABLE mart.DimModel (
     model_key INT IDENTITY(1,1) PRIMARY KEY,
     model_name VARCHAR(100) NOT NULL UNIQUE
 );
GO


CREATE TABLE mart.DimMethod (
      method_key INT IDENTITY(1,1) PRIMARY KEY,
      method_name VARCHAR(50) NOT NULL UNIQUE
);
GO

CREATE TABLE mart.DimRun (
    run_key INT IDENTITY(1,1) PRIMARY KEY,
    run_id UNIQUEIDENTIFIER NOT NULL UNIQUE,
    bronze_batch_id UNIQUEIDENTIFIER,
    source_version VARCHAR(100),
    created_at DATETIME2,
    status VARCHAR(30)
 );
GO

CREATE TABLE mart.DimDate (
     date_key INT PRIMARY KEY,
     full_date DATE NOT NULL UNIQUE,
     day_number INT,
     month_number INT,
	 month_name VARCHAR(20),
     quarter_number INT,
     year_number INT
);
GO

