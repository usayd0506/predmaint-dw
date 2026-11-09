SELECT
    batch_id,
    source_version,
    status,
    loaded_at
FROM ops.bronze_batch
ORDER BY loaded_at DESC;

/*Create silver.plants where we want to have
clean and standardized values*/
CREATE TABLE silver.plants (
    plant_id INT PRIMARY KEY,
    plant_name VARCHAR(100),
    city VARCHAR(60),
    province VARCHAR(60),
    country VARCHAR(60),
    latitude FLOAT,
    longitude FLOAT
);
GO

/*silver.technicians*/

CREATE TABLE silver.technicians (
    technician_id INT PRIMARY KEY,
    name VARCHAR(100),
    plant_id INT,
    skill_level VARCHAR(20),
    hourly_rate FLOAT,
    max_hours_per_week INT
);
GO

--silver.engine_master

CREATE TABLE silver.engine_master (
    engine_uid INT PRIMARY KEY,
    engine_id INT,
    split VARCHAR(5),
    plant_id INT,
    commission_date DATE
);
GO

--silver.rul_truth

CREATE TABLE silver.rul_truth (
    engine_id INT PRIMARY KEY,
    true_rul INT NOT NULL
);
GO

--silver.maintenance

CREATE TABLE silver.maintenance (
    work_order_id INT PRIMARY KEY,
    engine_uid INT NOT NULL,
    work_date DATE,
    type VARCHAR(30),
    technician_id INT,
    duration_hours DECIMAL(8,2),
    cost DECIMAL(12,2),
    is_imputed BIT NOT NULL DEFAULT 0
);
GO

--silver.engine_cylce is our main silver table and it will store
/*It will store:
- Unique engine and cycle identifiers
- Operating conditions
- The 14 selected sensors
- Five-cycle rolling averages for those 14 sensors
- Actual RUL for each cycle
- Capped RUL


our implementation specification identifies these seven sensors as constant or near-constant in FD001:

1, 5, 6, 10, 16, 18, 19

Hence, we remove them from the Silver working feature set because they generally provide little useful information about engine degradation in this dataset. They remain intact in Bronze.

The 14 retained sensors are:

2, 3, 4, 7, 8, 9, 11, 12, 13, 14, 15, 17, 20, 21 where we'll take 5 cycle rolling average of each sensor
*/

CREATE TABLE silver.engine_cycles (
    engine_uid INT NOT NULL,
    engine_id INT NOT NULL,
    split VARCHAR(5) NOT NULL,
    cycle INT NOT NULL,
    cycle_date DATE NOT NULL,

    setting_1 FLOAT,
    setting_2 FLOAT,
    setting_3 FLOAT,

    s2 FLOAT,
    s3 FLOAT,
    s4 FLOAT,
    s7 FLOAT,
    s8 FLOAT,
    s9 FLOAT,
    s11 FLOAT,
    s12 FLOAT,
    s13 FLOAT,
    s14 FLOAT,
    s15 FLOAT,
    s17 FLOAT,
    s20 FLOAT,
    s21 FLOAT,

    s2_sm FLOAT,
    s3_sm FLOAT,
    s4_sm FLOAT,
    s7_sm FLOAT,
    s8_sm FLOAT,
    s9_sm FLOAT,
    s11_sm FLOAT,
    s12_sm FLOAT,
    s13_sm FLOAT,
    s14_sm FLOAT,
    s15_sm FLOAT,
    s17_sm FLOAT,
    s20_sm FLOAT,
    s21_sm FLOAT,

    rul INT NOT NULL,
    rul_capped INT NOT NULL,

    CONSTRAINT PK_engine_cycles
        PRIMARY KEY (engine_uid, cycle)
);
GO

