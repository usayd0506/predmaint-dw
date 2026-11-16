# Live Power BI CSV versus PredMaintDW comparison

- Server: `USAYD-PC\SQLEXPRESS`
- Database: `PredMaintDW`
- Authentication: Windows (`USAYD-PC\USAYD`)
- ODBC driver used: `ODBC Driver 17 for SQL Server`
- Installed ODBC drivers: `SQL Server, ODBC Driver 17 for SQL Server, Oracle in XE, Microsoft Access Driver (*.mdb, *.accdb), Microsoft Excel Driver (*.xls, *.xlsx, *.xlsm, *.xlsb), Microsoft Access Text Driver (*.txt, *.csv), Microsoft Access dBASE Driver (*.dbf, *.ndx, *.mdx)`
- CSV directory: `powerbi\PredMaint_Fixed_Project\Datasets`
- Results: 9 PASS, 4 FAIL, 0 NOT VERIFIED

## Method

Live columns and primary keys were discovered from SQL Server `sys` metadata. Rows were matched by the discovered primary key, independent of source order. Integers, decimals, bits, dates, datetimes, and GUIDs were normalized to SQL-aware values. Decimal fields were compared exactly. SQL `float`/`real` fields used `math.isclose` with absolute and relative tolerances of `1e-9`. No aggregate checksum was used.

`DimDate` value comparison uses only its seven live SQL columns. CSV-only `year_month` and `weekday_name` were validated separately as derivations of `full_date`.

## Table summary

| Table | Status | SQL rows | CSV rows | SQL-only keys | CSV-only keys | Duplicate keys SQL/CSV | NULL mismatches | Changed rows | Foreign keys |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| DimDate | PASS | 1461 | 1461 | 0 | 0 | 0/0 | none | 0 | PASS |
| DimEngine | PASS | 200 | 200 | 0 | 0 | 0/0 | none | 0 | PASS |
| DimPlant | PASS | 5 | 5 | 0 | 0 | 0/0 | none | 0 | PASS |
| DimTechnician | PASS | 20 | 20 | 0 | 0 | 0/0 | none | 0 | PASS |
| DimModel | PASS | 4 | 4 | 0 | 0 | 0/0 | none | 0 | PASS |
| DimMethod | PASS | 2 | 2 | 0 | 0 | 0/0 | none | 0 | PASS |
| DimRun | FAIL | 1 | 1 | 0 | 0 | 0/0 | none | 1 | PASS |
| FactEngineHealth | PASS | 100 | 100 | 0 | 0 | 0/0 | none | 0 | PASS |
| FactRULPrediction | FAIL | 200 | 200 | 0 | 0 | 0/0 | none | 200 | PASS |
| FactAlert | FAIL | 43 | 43 | 0 | 0 | 0/0 | none | 43 | PASS |
| FactMaintenance | PASS | 835 | 835 | 0 | 0 | 0/0 | none | 0 | PASS |
| FactSchedule | FAIL | 60 | 60 | 0 | 0 | 0/0 | none | 4 | PASS |
| FactModelMetric | PASS | 38 | 38 | 0 | 0 | 0/0 | none | 0 | PASS |

## Per-table findings

### DimDate: PASS

Primary key: `date_key`. SQL/CSV rows: 1461/1461.
CSV-only documented columns: `year_month, weekday_name`.
CSV-only year_month mismatches=0; weekday_name mismatches=0. Compared values use only the seven SQL-backed columns.
No missing/extra primary keys, duplicate keys, NULL mismatches, or changed SQL-backed values were found.

### DimEngine: PASS

Primary key: `engine_key`. SQL/CSV rows: 200/200.
No missing/extra primary keys, duplicate keys, NULL mismatches, or changed SQL-backed values were found.

### DimPlant: PASS

Primary key: `plant_key`. SQL/CSV rows: 5/5.
No missing/extra primary keys, duplicate keys, NULL mismatches, or changed SQL-backed values were found.

### DimTechnician: PASS

Primary key: `technician_key`. SQL/CSV rows: 20/20.
No missing/extra primary keys, duplicate keys, NULL mismatches, or changed SQL-backed values were found.

### DimModel: PASS

Primary key: `model_key`. SQL/CSV rows: 4/4.
No missing/extra primary keys, duplicate keys, NULL mismatches, or changed SQL-backed values were found.

### DimMethod: PASS

Primary key: `method_key`. SQL/CSV rows: 2/2.
No missing/extra primary keys, duplicate keys, NULL mismatches, or changed SQL-backed values were found.

### DimRun: FAIL

Primary key: `run_key`. SQL/CSV rows: 1/1.
- Changed columns: `{"created_at":1}`
- Examples: `[{"key":[1],"differences":{"created_at":{"sql":"2026-11-08 21:31:13.404836","csv":"2026-11-08 21:31:13"}}}]`

### FactEngineHealth: PASS

Primary key: `health_fact_key`. SQL/CSV rows: 100/100.
No missing/extra primary keys, duplicate keys, NULL mismatches, or changed SQL-backed values were found.

### FactRULPrediction: FAIL

Primary key: `prediction_fact_key`. SQL/CSV rows: 200/200.
- Changed columns: `{"predicted_at":200}`
- Examples: `[{"key":[1],"differences":{"predicted_at":{"sql":"2026-11-08 21:31:13.505834","csv":"2026-11-08 21:31:13"}}},{"key":[10],"differences":{"predicted_at":{"sql":"2026-11-08 21:31:13.509910","csv":"2026-11-08 21:31:13"}}},{"key":[100],"differences":{"predicted_at":{"sql":"2026-11-08 21:31:13.509910","csv":"2026-11-08 21:31:13"}}},{"key":[101],"differences":{"predicted_at":{"sql":"2026-11-08 21:31:13.507833","csv":"2026-11-08 21:31:13"}}},{"key":[102],"differences":{"predicted_at":{"sql":"2026-11-08 21:31:13.511834","csv":"2026-11-08 21:31:13"}}}]`

### FactAlert: FAIL

Primary key: `alert_fact_key`. SQL/CSV rows: 43/43.
- Changed columns: `{"created_at":43}`
- Examples: `[{"key":[1],"differences":{"created_at":{"sql":"2026-11-08 21:31:13.542943","csv":"2026-11-08 21:31:13"}}},{"key":[10],"differences":{"created_at":{"sql":"2026-11-08 21:31:13.543959","csv":"2026-11-08 21:31:13"}}},{"key":[11],"differences":{"created_at":{"sql":"2026-11-08 21:31:13.543959","csv":"2026-11-08 21:31:13"}}},{"key":[12],"differences":{"created_at":{"sql":"2026-11-08 21:31:13.543959","csv":"2026-11-08 21:31:13"}}},{"key":[13],"differences":{"created_at":{"sql":"2026-11-08 21:31:13.543959","csv":"2026-11-08 21:31:13"}}}]`

### FactMaintenance: PASS

Primary key: `maintenance_fact_key`. SQL/CSV rows: 835/835.
No missing/extra primary keys, duplicate keys, NULL mismatches, or changed SQL-backed values were found.

### FactSchedule: FAIL

Primary key: `schedule_fact_key`. SQL/CSV rows: 60/60.
No current fractional values, so the present snapshot is not truncated; DDL is decimal(10,2), so SQL migration should still use type number.
- Changed columns: `{"slot_start":4}`
- Examples: `[{"key":[33],"differences":{"slot_start":{"sql":"2024-08-19 16:00:00","csv":"2024-08-19 15:59:59"}}},{"key":[54],"differences":{"slot_start":{"sql":"2024-08-19 16:00:00","csv":"2024-08-19 15:59:59"}}},{"key":[56],"differences":{"slot_start":{"sql":"2024-08-19 16:00:00","csv":"2024-08-19 15:59:59"}}},{"key":[58],"differences":{"slot_start":{"sql":"2024-08-20 16:00:00","csv":"2024-08-20 15:59:59"}}}]`

### FactModelMetric: PASS

Primary key: `model_metric_fact_key`. SQL/CSV rows: 38/38.
No missing/extra primary keys, duplicate keys, NULL mismatches, or changed SQL-backed values were found.

## Foreign-key validation

Discovered and checked 21 live fact foreign-key constraints against their referenced dimensions in both SQL and CSV data.

| Fact | Foreign key | Columns | Dimension | SQL orphans | CSV orphans |
|---|---|---|---|---:|---:|
| FactAlert | FK__FactAlert__date___1CBC4616 | date_key | DimDate(date_key) | 0 | 0 |
| FactAlert | FK__FactAlert__engin__1BC821DD | engine_key | DimEngine(engine_key) | 0 | 0 |
| FactAlert | FK__FactAlert__run_k__1AD3FDA4 | run_key | DimRun(run_key) | 0 | 0 |
| FactEngineHealth | FK__FactEngin__date___10566F31 | date_key | DimDate(date_key) | 0 | 0 |
| FactEngineHealth | FK__FactEngin__engin__0E6E26BF | engine_key | DimEngine(engine_key) | 0 | 0 |
| FactEngineHealth | FK__FactEngin__plant__0F624AF8 | plant_key | DimPlant(plant_key) | 0 | 0 |
| FactEngineHealth | FK__FactEngin__run_k__0D7A0286 | run_key | DimRun(run_key) | 0 | 0 |
| FactMaintenance | FK__FactMaint__date___236943A5 | date_key | DimDate(date_key) | 0 | 0 |
| FactMaintenance | FK__FactMaint__engin__2180FB33 | engine_key | DimEngine(engine_key) | 0 | 0 |
| FactMaintenance | FK__FactMaint__techn__22751F6C | technician_key | DimTechnician(technician_key) | 0 | 0 |
| FactModelMetric | FK__FactModel__model__31B762FC | model_key | DimModel(model_key) | 0 | 0 |
| FactModelMetric | FK__FactModel__run_k__30C33EC3 | run_key | DimRun(run_key) | 0 | 0 |
| FactRULPrediction | FK__FactRULPr__date___17036CC0 | date_key | DimDate(date_key) | 0 | 0 |
| FactRULPrediction | FK__FactRULPr__engin__151B244E | engine_key | DimEngine(engine_key) | 0 | 0 |
| FactRULPrediction | FK__FactRULPr__model__160F4887 | model_key | DimModel(model_key) | 0 | 0 |
| FactRULPrediction | FK__FactRULPr__run_k__14270015 | run_key | DimRun(run_key) | 0 | 0 |
| FactSchedule | FK__FactSched__date___2BFE89A6 | date_key | DimDate(date_key) | 0 | 0 |
| FactSchedule | FK__FactSched__engin__29221CFB | engine_key | DimEngine(engine_key) | 0 | 0 |
| FactSchedule | FK__FactSched__metho__2B0A656D | method_key | DimMethod(method_key) | 0 | 0 |
| FactSchedule | FK__FactSched__run_k__282DF8C2 | run_key | DimRun(run_key) | 0 | 0 |
| FactSchedule | FK__FactSched__techn__2A164134 | technician_key | DimTechnician(technician_key) | 0 | 0 |

## Power Query scheduling type

No current fractional values, so the present snapshot is not truncated; DDL is decimal(10,2), so SQL migration should still use type number.

## Connectivity diagnosis

The same ODBC 17 connection failed inside the restricted execution sandbox with SQLSTATE `08001` and SSPI/TLS credential errors. Running the identical SELECT-only connection outside that sandbox succeeded with Windows login shown above. No SQL Server security setting or installed software was changed.

## Limitation

PASS means the compared live snapshot and CSV are equal under the documented normalization and floating-point tolerances. It does not prove future ETL runs or later exports will remain equal.
