# Predictive Maintenance Data Warehouse (SQL Server + SSMS, Medallion)

FAST-NUCES Karachi, Data Warehousing & BI. NASA C-MAPSS FD001.
Bazyl Sheikh (24K-2532), Umer Hafeez (24K-2519), Usayd Arsalan (24K-2553)

## Layers
stg -> bronze -> silver -> gold -> mart -> Power BI   (ops = ETL log)

## Setup
1. Install SQL Server (Developer/Express), SSMS, ODBC Driver 18.
2. `python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt`
3. Copy `.env.example` to `.env`, set DB_SERVER.
4. Put train_FD001.txt, test_FD001.txt, RUL_FD001.txt in `data/raw/`
   (source: NASA PCoE Prognostics Data Repository, "Turbofan Engine Degradation Simulation Data Set").
5. `python etl/generate_synthetic.py`  (writes data/synthetic/*.csv, seed 42)
6. In SSMS run sql/01 .. sql/06 in order (09 after the marts are loaded).
7. `python etl/run_pipeline.py`

## Run order and owners
See docs/TASKS.md.

## Conventions
- engine_uid = engine_id for train (1-100), 1000 + engine_id for test (1001-1100)
- All synthetic data is labelled synthetic; seed 42
- Power BI reads only from the mart schema
