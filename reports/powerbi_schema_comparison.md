# Offline Power BI CSV versus SQL DDL schema comparison

This is an offline schema audit. It does not establish SQL Server connectivity, inspect live database metadata, or prove that CSV and SQL row values are equivalent.

## Scope and sources

- CSV directory: `powerbi\PredMaint_Fixed_Project\Datasets`
- Dimension DDL: `sql\10_create_mart_dimensions.sql`
- Fact DDL: `sql\12_create_mart_facts.sql`
- Loading scripts inspected: `sql\11_load_mart_dimensions.sql`, `sql\13_load_mart_facts.sql`
- Power BI metadata inspected: `powerbi\PredMaint_Fixed_Project\Usyad Power Bi report.SemanticModel\definition\relationships.tmdl` and the 13 table TMDL files
- Status totals: 11 SCHEMA MATCH, 2 COMPATIBLE WITH MAPPING, 0 SCHEMA MISMATCH, 0 NOT VERIFIED

## Summary

| Table | Status | Rows | Primary key | PK nulls | PK duplicates | Missing columns | Extra columns | Type compatibility | Existing query can use SQL schema? |
|---|---|---:|---|---:|---:|---|---|---|---|
| DimDate | COMPATIBLE WITH MAPPING | 1461 | date_key | 0 | 0 | none | year_month, weekday_name | COMPATIBLE | YES WITH MAPPING after replacing the connector and applying the listed derived-column/type changes. |
| DimEngine | SCHEMA MATCH | 200 | engine_key | 0 | 0 | none | none | COMPATIBLE | YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible. |
| DimPlant | SCHEMA MATCH | 5 | plant_key | 0 | 0 | none | none | COMPATIBLE | YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible. |
| DimTechnician | SCHEMA MATCH | 20 | technician_key | 0 | 0 | none | none | COMPATIBLE | YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible. |
| DimModel | SCHEMA MATCH | 4 | model_key | 0 | 0 | none | none | COMPATIBLE | YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible. |
| DimMethod | SCHEMA MATCH | 2 | method_key | 0 | 0 | none | none | COMPATIBLE | YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible. |
| DimRun | SCHEMA MATCH | 1 | run_key | 0 | 0 | none | none | COMPATIBLE | YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible. |
| FactEngineHealth | SCHEMA MATCH | 100 | health_fact_key | 0 | 0 | none | none | COMPATIBLE | YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible. |
| FactRULPrediction | SCHEMA MATCH | 200 | prediction_fact_key | 0 | 0 | none | none | COMPATIBLE | YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible. |
| FactAlert | SCHEMA MATCH | 43 | alert_fact_key | 0 | 0 | none | none | COMPATIBLE | YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible. |
| FactMaintenance | SCHEMA MATCH | 835 | maintenance_fact_key | 0 | 0 | none | none | COMPATIBLE | YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible. |
| FactSchedule | COMPATIBLE WITH MAPPING | 60 | schedule_fact_key | 0 | 0 | none | none | COMPATIBLE | YES WITH MAPPING after replacing the connector and applying the listed derived-column/type changes. |
| FactModelMetric | SCHEMA MATCH | 38 | model_metric_fact_key | 0 | 0 | none | none | COMPATIBLE | YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible. |

## Exact DDL schema and CSV checks

### DimDate — COMPATIBLE WITH MAPPING

CSV header: `date_key, full_date, day_number, month_number, month_name, quarter_number, year_number, year_month, weekday_name`

Primary key: `date_key`; null rows: 0; duplicate rows: 0.

| DDL column | SQL type | NULL allowed | PK | Unique | Identity | Default | References | CSV null count |
|---|---|---:|---:|---:|---:|---|---|---:|
| date_key | INT | NO | YES |  |  |  |  | 0 |
| full_date | DATE | NO |  | YES |  |  |  | 0 |
| day_number | INT | YES |  |  |  |  |  | 0 |
| month_number | INT | YES |  |  |  |  |  | 0 |
| month_name | VARCHAR(20) | YES |  |  |  |  |  | 0 |
| quarter_number | INT | YES |  |  |  |  |  | 0 |
| year_number | INT | YES |  |  |  |  |  | 0 |

- Missing DDL columns in CSV: none
- Extra CSV columns: year_month, weekday_name
- Naming differences: none
- CSV value/type compatibility with DDL: COMPATIBLE
- Non-null constraint violations in CSV: none
- Power BI relationship columns: date_key
- Relationship schema issues: none
- Power Query-added columns: weekday_number
- Required mapping: Derive year_month and weekday_name from full_date before existing model steps; weekday_number is already added in Power Query.
- Existing Power BI query assessment: YES WITH MAPPING after replacing the connector and applying the listed derived-column/type changes.
- Mart-load transformation: Generated from dates across Silver/Gold; date_key and calendar parts are derived. DDL/load do not create CSV-only year_month or weekday_name.

### DimEngine — SCHEMA MATCH

CSV header: `engine_key, engine_uid, engine_id, split, plant_id, commission_date`

Primary key: `engine_key`; null rows: 0; duplicate rows: 0.

| DDL column | SQL type | NULL allowed | PK | Unique | Identity | Default | References | CSV null count |
|---|---|---:|---:|---:|---:|---|---|---:|
| engine_key | INT | NO | YES |  | YES |  |  | 0 |
| engine_uid | INT | NO |  | YES |  |  |  | 0 |
| engine_id | INT | YES |  |  |  |  |  | 0 |
| split | VARCHAR(10) | YES |  |  |  |  |  | 0 |
| plant_id | INT | YES |  |  |  |  |  | 0 |
| commission_date | DATE | YES |  |  |  |  |  | 0 |

- Missing DDL columns in CSV: none
- Extra CSV columns: none
- Naming differences: none
- CSV value/type compatibility with DDL: COMPATIBLE
- Non-null constraint violations in CSV: none
- Power BI relationship columns: engine_key, plant_id
- Relationship schema issues: none
- Power Query-added columns: none
- Required mapping: none
- Existing Power BI query assessment: YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible.
- Mart-load transformation: Surrogate engine_key is IDENTITY; natural key engine_uid is loaded from silver.engine_master.

### DimPlant — SCHEMA MATCH

CSV header: `plant_key, plant_id, plant_name, city, province, country, latitude, longitude`

Primary key: `plant_key`; null rows: 0; duplicate rows: 0.

| DDL column | SQL type | NULL allowed | PK | Unique | Identity | Default | References | CSV null count |
|---|---|---:|---:|---:|---:|---|---|---:|
| plant_key | INT | NO | YES |  | YES |  |  | 0 |
| plant_id | INT | NO |  | YES |  |  |  | 0 |
| plant_name | VARCHAR(100) | YES |  |  |  |  |  | 0 |
| city | VARCHAR(100) | YES |  |  |  |  |  | 0 |
| province | VARCHAR(100) | YES |  |  |  |  |  | 0 |
| country | VARCHAR(100) | YES |  |  |  |  |  | 0 |
| latitude | FLOAT | YES |  |  |  |  |  | 0 |
| longitude | FLOAT | YES |  |  |  |  |  | 0 |

- Missing DDL columns in CSV: none
- Extra CSV columns: none
- Naming differences: none
- CSV value/type compatibility with DDL: COMPATIBLE
- Non-null constraint violations in CSV: none
- Power BI relationship columns: plant_id, plant_key
- Relationship schema issues: none
- Power Query-added columns: none
- Required mapping: none
- Existing Power BI query assessment: YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible.
- Mart-load transformation: Surrogate plant_key is IDENTITY; natural key plant_id is loaded from silver.plants.

### DimTechnician — SCHEMA MATCH

CSV header: `technician_key, technician_id, technician_name, plant_id, skill_level, hourly_rate, max_hours_per_week`

Primary key: `technician_key`; null rows: 0; duplicate rows: 0.

| DDL column | SQL type | NULL allowed | PK | Unique | Identity | Default | References | CSV null count |
|---|---|---:|---:|---:|---:|---|---|---:|
| technician_key | INT | NO | YES |  | YES |  |  | 0 |
| technician_id | INT | NO |  | YES |  |  |  | 0 |
| technician_name | VARCHAR(100) | YES |  |  |  |  |  | 0 |
| plant_id | INT | YES |  |  |  |  |  | 0 |
| skill_level | VARCHAR(30) | YES |  |  |  |  |  | 0 |
| hourly_rate | DECIMAL(12,2) | YES |  |  |  |  |  | 0 |
| max_hours_per_week | INT | YES |  |  |  |  |  | 0 |

- Missing DDL columns in CSV: none
- Extra CSV columns: none
- Naming differences: none
- CSV value/type compatibility with DDL: COMPATIBLE
- Non-null constraint violations in CSV: none
- Power BI relationship columns: plant_id, technician_key
- Relationship schema issues: none
- Power Query-added columns: skill_sort
- Required mapping: none
- Existing Power BI query assessment: YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible.
- Mart-load transformation: technician_name is loaded from silver.technicians.name; technician_key is IDENTITY.

### DimModel — SCHEMA MATCH

CSV header: `model_key, model_name`

Primary key: `model_key`; null rows: 0; duplicate rows: 0.

| DDL column | SQL type | NULL allowed | PK | Unique | Identity | Default | References | CSV null count |
|---|---|---:|---:|---:|---:|---|---|---:|
| model_key | INT | NO | YES |  | YES |  |  | 0 |
| model_name | VARCHAR(100) | NO |  | YES |  |  |  | 0 |

- Missing DDL columns in CSV: none
- Extra CSV columns: none
- Naming differences: none
- CSV value/type compatibility with DDL: COMPATIBLE
- Non-null constraint violations in CSV: none
- Power BI relationship columns: model_key
- Relationship schema issues: none
- Power Query-added columns: none
- Required mapping: none
- Existing Power BI query assessment: YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible.
- Mart-load transformation: Distinct model_name values are unioned from predictions and metrics; model_key is IDENTITY.

### DimMethod — SCHEMA MATCH

CSV header: `method_key, method_name`

Primary key: `method_key`; null rows: 0; duplicate rows: 0.

| DDL column | SQL type | NULL allowed | PK | Unique | Identity | Default | References | CSV null count |
|---|---|---:|---:|---:|---:|---|---|---:|
| method_key | INT | NO | YES |  | YES |  |  | 0 |
| method_name | VARCHAR(50) | NO |  | YES |  |  |  | 0 |

- Missing DDL columns in CSV: none
- Extra CSV columns: none
- Naming differences: none
- CSV value/type compatibility with DDL: COMPATIBLE
- Non-null constraint violations in CSV: none
- Power BI relationship columns: method_key
- Relationship schema issues: none
- Power Query-added columns: none
- Required mapping: none
- Existing Power BI query assessment: YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible.
- Mart-load transformation: method_name is loaded from gold.work_order_schedule.method; method_key is IDENTITY.

### DimRun — SCHEMA MATCH

CSV header: `run_key, run_id, bronze_batch_id, source_version, created_at, status`

Primary key: `run_key`; null rows: 0; duplicate rows: 0.

| DDL column | SQL type | NULL allowed | PK | Unique | Identity | Default | References | CSV null count |
|---|---|---:|---:|---:|---:|---|---|---:|
| run_key | INT | NO | YES |  | YES |  |  | 0 |
| run_id | UNIQUEIDENTIFIER | NO |  | YES |  |  |  | 0 |
| bronze_batch_id | UNIQUEIDENTIFIER | YES |  |  |  |  |  | 0 |
| source_version | VARCHAR(100) | YES |  |  |  |  |  | 0 |
| created_at | DATETIME | YES |  |  |  |  |  | 0 |
| status | VARCHAR(30) | YES |  |  |  |  |  | 0 |

- Missing DDL columns in CSV: none
- Extra CSV columns: none
- Naming differences: none
- CSV value/type compatibility with DDL: COMPATIBLE
- Non-null constraint violations in CSV: none
- Power BI relationship columns: run_key
- Relationship schema issues: none
- Power Query-added columns: none
- Required mapping: none
- Existing Power BI query assessment: YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible.
- Mart-load transformation: run_key is IDENTITY; run_id is the natural unique identifier loaded from gold.run_control.

### FactEngineHealth — SCHEMA MATCH

CSV header: `health_fact_key, run_key, engine_key, plant_key, date_key, cycles_run, last_maintenance, health_index, degradation_stage, risk_level`

Primary key: `health_fact_key`; null rows: 0; duplicate rows: 0.

| DDL column | SQL type | NULL allowed | PK | Unique | Identity | Default | References | CSV null count |
|---|---|---:|---:|---:|---:|---|---|---:|
| health_fact_key | BIGINT | NO | YES |  | YES |  |  | 0 |
| run_key | INT | NO |  |  |  |  | DimRun.run_key | 0 |
| engine_key | INT | NO |  |  |  |  | DimEngine.engine_key | 0 |
| plant_key | INT | NO |  |  |  |  | DimPlant.plant_key | 0 |
| date_key | INT | NO |  |  |  |  | DimDate.date_key | 0 |
| cycles_run | INT | NO |  |  |  |  |  | 0 |
| last_maintenance | DATE | YES |  |  |  |  |  | 0 |
| health_index | DECIMAL(12,4) | NO |  |  |  |  |  | 0 |
| degradation_stage | VARCHAR(50) | NO |  |  |  |  |  | 0 |
| risk_level | VARCHAR(30) | NO |  |  |  |  |  | 0 |

- Missing DDL columns in CSV: none
- Extra CSV columns: none
- Naming differences: none
- CSV value/type compatibility with DDL: COMPATIBLE
- Non-null constraint violations in CSV: none
- Power BI relationship columns: date_key, engine_key, plant_key, run_key
- Relationship schema issues: none
- Power Query-added columns: risk_sort, stage_sort
- Required mapping: none
- Existing Power BI query assessment: YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible.
- Mart-load transformation: run/engine/plant/date surrogate keys are resolved by joins; health_fact_key is IDENTITY.

### FactRULPrediction — SCHEMA MATCH

CSV header: `prediction_fact_key, run_key, engine_key, model_key, date_key, predicted_at, predicted_rul, failure_prob_30`

Primary key: `prediction_fact_key`; null rows: 0; duplicate rows: 0.

| DDL column | SQL type | NULL allowed | PK | Unique | Identity | Default | References | CSV null count |
|---|---|---:|---:|---:|---:|---|---|---:|
| prediction_fact_key | BIGINT | NO | YES |  | YES |  |  | 0 |
| run_key | INT | NO |  |  |  |  | DimRun.run_key | 0 |
| engine_key | INT | NO |  |  |  |  | DimEngine.engine_key | 0 |
| model_key | INT | NO |  |  |  |  | DimModel.model_key | 0 |
| date_key | INT | YES |  |  |  |  | DimDate.date_key | 0 |
| predicted_at | DATETIME | YES |  |  |  |  |  | 0 |
| predicted_rul | FLOAT | NO |  |  |  |  |  | 0 |
| failure_prob_30 | FLOAT | NO |  |  |  |  |  | 0 |

- Missing DDL columns in CSV: none
- Extra CSV columns: none
- Naming differences: none
- CSV value/type compatibility with DDL: COMPATIBLE
- Non-null constraint violations in CSV: none
- Power BI relationship columns: date_key, engine_key, model_key, run_key
- Relationship schema issues: none
- Power Query-added columns: none
- Required mapping: none
- Existing Power BI query assessment: YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible.
- Mart-load transformation: run/engine/model/date keys are resolved by joins; date_key uses CAST(predicted_at AS DATE); prediction_fact_key is IDENTITY.

### FactAlert — SCHEMA MATCH

CSV header: `alert_fact_key, run_key, engine_key, date_key, alert_id, created_at, severity, recommended_action, rules_fired, alert_count`

Primary key: `alert_fact_key`; null rows: 0; duplicate rows: 0.

| DDL column | SQL type | NULL allowed | PK | Unique | Identity | Default | References | CSV null count |
|---|---|---:|---:|---:|---:|---|---|---:|
| alert_fact_key | BIGINT | NO | YES |  | YES |  |  | 0 |
| run_key | INT | NO |  |  |  |  | DimRun.run_key | 0 |
| engine_key | INT | NO |  |  |  |  | DimEngine.engine_key | 0 |
| date_key | INT | NO |  |  |  |  | DimDate.date_key | 0 |
| alert_id | INT | NO |  |  |  |  |  | 0 |
| created_at | DATETIME | NO |  |  |  |  |  | 0 |
| severity | VARCHAR(30) | NO |  |  |  |  |  | 0 |
| recommended_action | VARCHAR(MAX) | NO |  |  |  |  |  | 0 |
| rules_fired | VARCHAR(MAX) | NO |  |  |  |  |  | 0 |
| alert_count | INT | NO |  |  |  | 1 |  | 0 |

- Missing DDL columns in CSV: none
- Extra CSV columns: none
- Naming differences: none
- CSV value/type compatibility with DDL: COMPATIBLE
- Non-null constraint violations in CSV: none
- Power BI relationship columns: date_key, engine_key, run_key
- Relationship schema issues: none
- Power Query-added columns: severity_sort
- Required mapping: none
- Existing Power BI query assessment: YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible.
- Mart-load transformation: recommended_action is loaded from gold.alerts.action; date_key uses CAST(created_at AS DATE); alert_count defaults to 1; alert_fact_key is IDENTITY.

### FactMaintenance — SCHEMA MATCH

CSV header: `maintenance_fact_key, work_order_id, engine_key, technician_key, date_key, maintenance_type, duration_hours, maintenance_cost, is_imputed, work_order_count`

Primary key: `maintenance_fact_key`; null rows: 0; duplicate rows: 0.

| DDL column | SQL type | NULL allowed | PK | Unique | Identity | Default | References | CSV null count |
|---|---|---:|---:|---:|---:|---|---|---:|
| maintenance_fact_key | BIGINT | NO | YES |  | YES |  |  | 0 |
| work_order_id | INT | NO |  | YES |  |  |  | 0 |
| engine_key | INT | NO |  |  |  |  | DimEngine.engine_key | 0 |
| technician_key | INT | NO |  |  |  |  | DimTechnician.technician_key | 0 |
| date_key | INT | NO |  |  |  |  | DimDate.date_key | 0 |
| maintenance_type | VARCHAR(50) | NO |  |  |  |  |  | 0 |
| duration_hours | DECIMAL(10,2) | NO |  |  |  |  |  | 0 |
| maintenance_cost | DECIMAL(14,2) | YES |  |  |  |  |  | 0 |
| is_imputed | BIT | NO |  |  |  |  |  | 0 |
| work_order_count | INT | NO |  |  |  | 1 |  | 0 |

- Missing DDL columns in CSV: none
- Extra CSV columns: none
- Naming differences: none
- CSV value/type compatibility with DDL: COMPATIBLE
- Non-null constraint violations in CSV: none
- Power BI relationship columns: date_key, engine_key, technician_key
- Relationship schema issues: none
- Power Query-added columns: type_sort
- Required mapping: none
- Existing Power BI query assessment: YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible.
- Mart-load transformation: maintenance_type, maintenance_cost and date_key derive from silver columns type, cost and work_date; work_order_count defaults to 1; maintenance_fact_key is IDENTITY.

### FactSchedule — COMPATIBLE WITH MAPPING

CSV header: `schedule_fact_key, run_key, engine_key, technician_key, method_key, date_key, schedule_id, slot_start, slot_hours, est_cost, assignment_count`

Primary key: `schedule_fact_key`; null rows: 0; duplicate rows: 0.

| DDL column | SQL type | NULL allowed | PK | Unique | Identity | Default | References | CSV null count |
|---|---|---:|---:|---:|---:|---|---|---:|
| schedule_fact_key | BIGINT | NO | YES |  | YES |  |  | 0 |
| run_key | INT | NO |  |  |  |  | DimRun.run_key | 0 |
| engine_key | INT | NO |  |  |  |  | DimEngine.engine_key | 0 |
| technician_key | INT | NO |  |  |  |  | DimTechnician.technician_key | 0 |
| method_key | INT | NO |  |  |  |  | DimMethod.method_key | 0 |
| date_key | INT | NO |  |  |  |  | DimDate.date_key | 0 |
| schedule_id | INT | NO |  |  |  |  |  | 0 |
| slot_start | DATETIME | NO |  |  |  |  |  | 0 |
| slot_hours | DECIMAL(10,2) | NO |  |  |  |  |  | 0 |
| est_cost | DECIMAL(14,2) | NO |  |  |  |  |  | 0 |
| assignment_count | INT | NO |  |  |  | 1 |  | 0 |

- Missing DDL columns in CSV: none
- Extra CSV columns: none
- Naming differences: none
- CSV value/type compatibility with DDL: COMPATIBLE
- Non-null constraint violations in CSV: none
- Power BI relationship columns: date_key, engine_key, method_key, run_key, technician_key
- Relationship schema issues: none
- Power Query-added columns: none
- Required mapping: Power BI imports slot_hours as whole number but DDL permits fractional DECIMAL(10,2)
- Existing Power BI query assessment: YES WITH MAPPING after replacing the connector and applying the listed derived-column/type changes.
- Mart-load transformation: method_key resolves from gold method; date_key uses CAST(slot_start AS DATE); assignment_count defaults to 1; schedule_fact_key is IDENTITY.

### FactModelMetric — SCHEMA MATCH

CSV header: `model_metric_fact_key, run_key, model_key, metric_name, metric_value`

Primary key: `model_metric_fact_key`; null rows: 0; duplicate rows: 0.

| DDL column | SQL type | NULL allowed | PK | Unique | Identity | Default | References | CSV null count |
|---|---|---:|---:|---:|---:|---|---|---:|
| model_metric_fact_key | BIGINT | NO | YES |  | YES |  |  | 0 |
| run_key | INT | NO |  |  |  |  | DimRun.run_key | 0 |
| model_key | INT | NO |  |  |  |  | DimModel.model_key | 0 |
| metric_name | VARCHAR(100) | NO |  |  |  |  |  | 0 |
| metric_value | FLOAT | NO |  |  |  |  |  | 0 |

- Missing DDL columns in CSV: none
- Extra CSV columns: none
- Naming differences: none
- CSV value/type compatibility with DDL: COMPATIBLE
- Non-null constraint violations in CSV: none
- Power BI relationship columns: model_key, run_key
- Relationship schema issues: none
- Power Query-added columns: none
- Required mapping: none
- Existing Power BI query assessment: YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible.
- Mart-load transformation: metric_name/value are loaded from gold.model_metrics.metric/value; run/model keys are resolved; model_metric_fact_key is IDENTITY.

## Power BI relationship review

Every column used by the 23 declared Power BI relationships exists with the same spelling in its CSV and repository DDL table. No relationship-key renaming is required for SQL migration.

The two inactive relationships remain model choices, not schema mismatches: `DimTechnician.plant_id -> DimPlant.plant_id` and `FactEngineHealth.plant_key -> DimPlant.plant_key`.

## Loading-script observations

- Dimensions are incrementally inserted by natural keys; surrogate keys are SQL IDENTITY values.
- Fact tables are deleted and reloaded as a fresh snapshot. This can make separately exported CSVs and a later live database different pipeline snapshots even when their schemas match.
- Fact foreign keys are resolved through dimension joins; identity fact keys and count columns with defaults are not supplied by source SELECT lists.
- `DimDate.year_month` and `DimDate.weekday_name` exist in the CSV/Power BI query but are absent from the DDL and mart load. They must be derived from `full_date` or added in a SQL view/query.
- `FactSchedule.slot_hours` is `DECIMAL(10,2)` in DDL but the current Power Query imports it as `Int64.Type`. Use a decimal/number type when sourcing SQL so fractional hours are not lost.

## Limitation

DDL describes intended repository structure only. Until pyodbc connects and live metadata/data are audited, none of these statuses means that the live SQL tables exist as declared or that any CSV dataset is row-equivalent to SQL.
