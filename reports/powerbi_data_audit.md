# Power BI CSV to SQL Server audit

- CSV source: `D:\Users\DANIYAL ARSALAN\Desktop\predmaint-dw\data\powerbi_csv_reference`
- CSV directory: NOT FOUND
- SQL target: `mart` schema in `PredMaintDW`
- Connectivity: NOT VERIFIED
- Connectivity error: `OperationalError: ('08001', '[08001] [Microsoft][ODBC Driver 17 for SQL Server]Encryption not supported on the client. (21) (SQLDriverConnect); [08001] [Microsoft][ODBC Driver 17 for SQL Server]SSL Provider: No credentials are available in the security package\r\n (-2146893042); [08001] [Microsoft][ODBC Driver 17 for SQL Server]Client unable to establish connection (21); [08001] [Microsoft][ODBC Driver 17 for SQL Server]A network-related or instance-specific error has occurred while establishing a connection to SQL Server. Server is not found or not accessible. Check if instance name is correct and if SQL Server is configured to allow remote connections. For more information see SQL Server Books Online. (-2146893042)')`
- Result totals: 0 PASS, 0 FAIL, 13 NOT VERIFIED

## Method

The audit discovers live SQL columns, data types, primary keys, and unique indexes from `sys` metadata. It parses CSV values according to those SQL types, normalizes dates and booleans, compares decimal values exactly, and compares floating-point values with absolute and relative tolerances of 1e-09 and 1e-09. Rows are matched by the discovered primary key when it is present and unique; otherwise a full-row multiset comparison is used. No aggregate checksum is used.

CSV blank fields are normalized to SQL NULL. When a text column contains blank CSV fields, CSV syntax cannot prove whether the source meant NULL or an empty string; that limitation is called out per table.

## Summary

| Table | Status | SQL rows | CSV rows | Columns | Types | Nulls | Keys | Values | Cause |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| DimDate | NOT VERIFIED |  |  | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | SQL table unavailable; CSV file missing |
| DimEngine | NOT VERIFIED |  |  | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | SQL table unavailable; CSV file missing |
| DimPlant | NOT VERIFIED |  |  | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | SQL table unavailable; CSV file missing |
| DimTechnician | NOT VERIFIED |  |  | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | SQL table unavailable; CSV file missing |
| DimModel | NOT VERIFIED |  |  | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | SQL table unavailable; CSV file missing |
| DimMethod | NOT VERIFIED |  |  | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | SQL table unavailable; CSV file missing |
| DimRun | NOT VERIFIED |  |  | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | SQL table unavailable; CSV file missing |
| FactEngineHealth | NOT VERIFIED |  |  | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | SQL table unavailable; CSV file missing |
| FactRULPrediction | NOT VERIFIED |  |  | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | SQL table unavailable; CSV file missing |
| FactAlert | NOT VERIFIED |  |  | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | SQL table unavailable; CSV file missing |
| FactMaintenance | NOT VERIFIED |  |  | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | SQL table unavailable; CSV file missing |
| FactSchedule | NOT VERIFIED |  |  | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | SQL table unavailable; CSV file missing |
| FactModelMetric | NOT VERIFIED |  |  | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | SQL table unavailable; CSV file missing |

## Live SQL schemas and keys

NOT VERIFIED because SQL Server connectivity was unavailable.
## Per-table discrepancies

### DimDate: NOT VERIFIED

Cause: SQL table unavailable; CSV file missing
- Error: `OperationalError: ('08001', '[08001] [Microsoft][ODBC Driver 17 for SQL Server]Encryption not supported on the client. (21) (SQLDriverConnect); [08001] [Microsoft][ODBC Driver 17 for SQL Server]SSL Provider: No credentials are available in the security package\r\n (-2146893042); [08001] [Microsoft][ODBC Driver 17 for SQL Server]Client unable to establish connection (21); [08001] [Microsoft][ODBC Driver 17 for SQL Server]A network-related or instance-specific error has occurred while establishing a connection to SQL Server. Server is not found or not accessible. Check if instance name is correct and if SQL Server is configured to allow remote connections. For more information see SQL Server Books Online. (-2146893042)'); No DimDate.csv in D:\Users\DANIYAL ARSALAN\Desktop\predmaint-dw\data\powerbi_csv_reference`

### DimEngine: NOT VERIFIED

Cause: SQL table unavailable; CSV file missing
- Error: `OperationalError: ('08001', '[08001] [Microsoft][ODBC Driver 17 for SQL Server]Encryption not supported on the client. (21) (SQLDriverConnect); [08001] [Microsoft][ODBC Driver 17 for SQL Server]SSL Provider: No credentials are available in the security package\r\n (-2146893042); [08001] [Microsoft][ODBC Driver 17 for SQL Server]Client unable to establish connection (21); [08001] [Microsoft][ODBC Driver 17 for SQL Server]A network-related or instance-specific error has occurred while establishing a connection to SQL Server. Server is not found or not accessible. Check if instance name is correct and if SQL Server is configured to allow remote connections. For more information see SQL Server Books Online. (-2146893042)'); No DimEngine.csv in D:\Users\DANIYAL ARSALAN\Desktop\predmaint-dw\data\powerbi_csv_reference`

### DimPlant: NOT VERIFIED

Cause: SQL table unavailable; CSV file missing
- Error: `OperationalError: ('08001', '[08001] [Microsoft][ODBC Driver 17 for SQL Server]Encryption not supported on the client. (21) (SQLDriverConnect); [08001] [Microsoft][ODBC Driver 17 for SQL Server]SSL Provider: No credentials are available in the security package\r\n (-2146893042); [08001] [Microsoft][ODBC Driver 17 for SQL Server]Client unable to establish connection (21); [08001] [Microsoft][ODBC Driver 17 for SQL Server]A network-related or instance-specific error has occurred while establishing a connection to SQL Server. Server is not found or not accessible. Check if instance name is correct and if SQL Server is configured to allow remote connections. For more information see SQL Server Books Online. (-2146893042)'); No DimPlant.csv in D:\Users\DANIYAL ARSALAN\Desktop\predmaint-dw\data\powerbi_csv_reference`

### DimTechnician: NOT VERIFIED

Cause: SQL table unavailable; CSV file missing
- Error: `OperationalError: ('08001', '[08001] [Microsoft][ODBC Driver 17 for SQL Server]Encryption not supported on the client. (21) (SQLDriverConnect); [08001] [Microsoft][ODBC Driver 17 for SQL Server]SSL Provider: No credentials are available in the security package\r\n (-2146893042); [08001] [Microsoft][ODBC Driver 17 for SQL Server]Client unable to establish connection (21); [08001] [Microsoft][ODBC Driver 17 for SQL Server]A network-related or instance-specific error has occurred while establishing a connection to SQL Server. Server is not found or not accessible. Check if instance name is correct and if SQL Server is configured to allow remote connections. For more information see SQL Server Books Online. (-2146893042)'); No DimTechnician.csv in D:\Users\DANIYAL ARSALAN\Desktop\predmaint-dw\data\powerbi_csv_reference`

### DimModel: NOT VERIFIED

Cause: SQL table unavailable; CSV file missing
- Error: `OperationalError: ('08001', '[08001] [Microsoft][ODBC Driver 17 for SQL Server]Encryption not supported on the client. (21) (SQLDriverConnect); [08001] [Microsoft][ODBC Driver 17 for SQL Server]SSL Provider: No credentials are available in the security package\r\n (-2146893042); [08001] [Microsoft][ODBC Driver 17 for SQL Server]Client unable to establish connection (21); [08001] [Microsoft][ODBC Driver 17 for SQL Server]A network-related or instance-specific error has occurred while establishing a connection to SQL Server. Server is not found or not accessible. Check if instance name is correct and if SQL Server is configured to allow remote connections. For more information see SQL Server Books Online. (-2146893042)'); No DimModel.csv in D:\Users\DANIYAL ARSALAN\Desktop\predmaint-dw\data\powerbi_csv_reference`

### DimMethod: NOT VERIFIED

Cause: SQL table unavailable; CSV file missing
- Error: `OperationalError: ('08001', '[08001] [Microsoft][ODBC Driver 17 for SQL Server]Encryption not supported on the client. (21) (SQLDriverConnect); [08001] [Microsoft][ODBC Driver 17 for SQL Server]SSL Provider: No credentials are available in the security package\r\n (-2146893042); [08001] [Microsoft][ODBC Driver 17 for SQL Server]Client unable to establish connection (21); [08001] [Microsoft][ODBC Driver 17 for SQL Server]A network-related or instance-specific error has occurred while establishing a connection to SQL Server. Server is not found or not accessible. Check if instance name is correct and if SQL Server is configured to allow remote connections. For more information see SQL Server Books Online. (-2146893042)'); No DimMethod.csv in D:\Users\DANIYAL ARSALAN\Desktop\predmaint-dw\data\powerbi_csv_reference`

### DimRun: NOT VERIFIED

Cause: SQL table unavailable; CSV file missing
- Error: `OperationalError: ('08001', '[08001] [Microsoft][ODBC Driver 17 for SQL Server]Encryption not supported on the client. (21) (SQLDriverConnect); [08001] [Microsoft][ODBC Driver 17 for SQL Server]SSL Provider: No credentials are available in the security package\r\n (-2146893042); [08001] [Microsoft][ODBC Driver 17 for SQL Server]Client unable to establish connection (21); [08001] [Microsoft][ODBC Driver 17 for SQL Server]A network-related or instance-specific error has occurred while establishing a connection to SQL Server. Server is not found or not accessible. Check if instance name is correct and if SQL Server is configured to allow remote connections. For more information see SQL Server Books Online. (-2146893042)'); No DimRun.csv in D:\Users\DANIYAL ARSALAN\Desktop\predmaint-dw\data\powerbi_csv_reference`

### FactEngineHealth: NOT VERIFIED

Cause: SQL table unavailable; CSV file missing
- Error: `OperationalError: ('08001', '[08001] [Microsoft][ODBC Driver 17 for SQL Server]Encryption not supported on the client. (21) (SQLDriverConnect); [08001] [Microsoft][ODBC Driver 17 for SQL Server]SSL Provider: No credentials are available in the security package\r\n (-2146893042); [08001] [Microsoft][ODBC Driver 17 for SQL Server]Client unable to establish connection (21); [08001] [Microsoft][ODBC Driver 17 for SQL Server]A network-related or instance-specific error has occurred while establishing a connection to SQL Server. Server is not found or not accessible. Check if instance name is correct and if SQL Server is configured to allow remote connections. For more information see SQL Server Books Online. (-2146893042)'); No FactEngineHealth.csv in D:\Users\DANIYAL ARSALAN\Desktop\predmaint-dw\data\powerbi_csv_reference`

### FactRULPrediction: NOT VERIFIED

Cause: SQL table unavailable; CSV file missing
- Error: `OperationalError: ('08001', '[08001] [Microsoft][ODBC Driver 17 for SQL Server]Encryption not supported on the client. (21) (SQLDriverConnect); [08001] [Microsoft][ODBC Driver 17 for SQL Server]SSL Provider: No credentials are available in the security package\r\n (-2146893042); [08001] [Microsoft][ODBC Driver 17 for SQL Server]Client unable to establish connection (21); [08001] [Microsoft][ODBC Driver 17 for SQL Server]A network-related or instance-specific error has occurred while establishing a connection to SQL Server. Server is not found or not accessible. Check if instance name is correct and if SQL Server is configured to allow remote connections. For more information see SQL Server Books Online. (-2146893042)'); No FactRULPrediction.csv in D:\Users\DANIYAL ARSALAN\Desktop\predmaint-dw\data\powerbi_csv_reference`

### FactAlert: NOT VERIFIED

Cause: SQL table unavailable; CSV file missing
- Error: `OperationalError: ('08001', '[08001] [Microsoft][ODBC Driver 17 for SQL Server]Encryption not supported on the client. (21) (SQLDriverConnect); [08001] [Microsoft][ODBC Driver 17 for SQL Server]SSL Provider: No credentials are available in the security package\r\n (-2146893042); [08001] [Microsoft][ODBC Driver 17 for SQL Server]Client unable to establish connection (21); [08001] [Microsoft][ODBC Driver 17 for SQL Server]A network-related or instance-specific error has occurred while establishing a connection to SQL Server. Server is not found or not accessible. Check if instance name is correct and if SQL Server is configured to allow remote connections. For more information see SQL Server Books Online. (-2146893042)'); No FactAlert.csv in D:\Users\DANIYAL ARSALAN\Desktop\predmaint-dw\data\powerbi_csv_reference`

### FactMaintenance: NOT VERIFIED

Cause: SQL table unavailable; CSV file missing
- Error: `OperationalError: ('08001', '[08001] [Microsoft][ODBC Driver 17 for SQL Server]Encryption not supported on the client. (21) (SQLDriverConnect); [08001] [Microsoft][ODBC Driver 17 for SQL Server]SSL Provider: No credentials are available in the security package\r\n (-2146893042); [08001] [Microsoft][ODBC Driver 17 for SQL Server]Client unable to establish connection (21); [08001] [Microsoft][ODBC Driver 17 for SQL Server]A network-related or instance-specific error has occurred while establishing a connection to SQL Server. Server is not found or not accessible. Check if instance name is correct and if SQL Server is configured to allow remote connections. For more information see SQL Server Books Online. (-2146893042)'); No FactMaintenance.csv in D:\Users\DANIYAL ARSALAN\Desktop\predmaint-dw\data\powerbi_csv_reference`

### FactSchedule: NOT VERIFIED

Cause: SQL table unavailable; CSV file missing
- Error: `OperationalError: ('08001', '[08001] [Microsoft][ODBC Driver 17 for SQL Server]Encryption not supported on the client. (21) (SQLDriverConnect); [08001] [Microsoft][ODBC Driver 17 for SQL Server]SSL Provider: No credentials are available in the security package\r\n (-2146893042); [08001] [Microsoft][ODBC Driver 17 for SQL Server]Client unable to establish connection (21); [08001] [Microsoft][ODBC Driver 17 for SQL Server]A network-related or instance-specific error has occurred while establishing a connection to SQL Server. Server is not found or not accessible. Check if instance name is correct and if SQL Server is configured to allow remote connections. For more information see SQL Server Books Online. (-2146893042)'); No FactSchedule.csv in D:\Users\DANIYAL ARSALAN\Desktop\predmaint-dw\data\powerbi_csv_reference`

### FactModelMetric: NOT VERIFIED

Cause: SQL table unavailable; CSV file missing
- Error: `OperationalError: ('08001', '[08001] [Microsoft][ODBC Driver 17 for SQL Server]Encryption not supported on the client. (21) (SQLDriverConnect); [08001] [Microsoft][ODBC Driver 17 for SQL Server]SSL Provider: No credentials are available in the security package\r\n (-2146893042); [08001] [Microsoft][ODBC Driver 17 for SQL Server]Client unable to establish connection (21); [08001] [Microsoft][ODBC Driver 17 for SQL Server]A network-related or instance-specific error has occurred while establishing a connection to SQL Server. Server is not found or not accessible. Check if instance name is correct and if SQL Server is configured to allow remote connections. For more information see SQL Server Books Online. (-2146893042)'); No FactModelMetric.csv in D:\Users\DANIYAL ARSALAN\Desktop\predmaint-dw\data\powerbi_csv_reference`

## Rerun

From the repository root, using the configured `.env` values:

```powershell
.\.venv\Scripts\python.exe tests\compare_powerbi_csv_sql.py
```

To audit another export directory without changing any source files:

```powershell
.\.venv\Scripts\python.exe tests\compare_powerbi_csv_sql.py --csv-dir "path\to\csv_exports"
```

Exit code 0 means all 13 tables passed, 1 means at least one failed, and 2 means at least one comparison was not verified.
