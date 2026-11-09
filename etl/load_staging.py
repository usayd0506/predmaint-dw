import argparse
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import pyodbc
from sqlalchemy import create_engine


ROOT = Path(__file__).resolve().parents[1]
RAW_FOLDER = ROOT / "data" / "raw"
SYNTHETIC_FOLDER = ROOT / "data" / "synthetic"

SERVER = r".\SQLEXPRESS"
DATABASE = "PredMaintDW"
BATCH_SIZE = 1000

SENSOR_COLUMNS = (
    ["engine_id", "cycle"]
    + [f"setting_{number}" for number in range(1, 4)]
    + [f"sensor_{number}" for number in range(1, 22)]
)

TABLE_COLUMNS = {
    "sensors": ["split"] + SENSOR_COLUMNS,
    "rul_truth": ["engine_id", "true_rul"],
    "plants": [
        "plant_id", "plant_name", "city", "province", "country",
        "latitude", "longitude",
    ],
    "technicians": [
        "technician_id", "name", "plant_id", "skill_level",
        "hourly_rate", "max_hours_per_week",
    ],
    "engine_master": [
        "engine_uid", "engine_id", "split", "plant_id", "commission_date",
    ],
    "maintenance": [
        "work_order_id", "engine_uid", "work_date", "type",
        "technician_id", "duration_hours", "cost",
    ],
}

TABLE_LABELS = {
    "sensors": "Sensors",
    "rul_truth": "RUL Truth",
    "plants": "Plants",
    "technicians": "Technicians",
    "engine_master": "Engine Master",
    "maintenance": "Maintenance",
}


def create_database_engine():
    drivers = pyodbc.drivers()

    if "ODBC Driver 18 for SQL Server" in drivers:
        driver = "ODBC Driver 18 for SQL Server"
    elif "ODBC Driver 17 for SQL Server" in drivers:
        driver = "ODBC Driver 17 for SQL Server"
    else:
        raise RuntimeError("ODBC Driver 18 or 17 for SQL Server is required.")

    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        "Trusted_Connection=yes;"
        "Encrypt=no;"
        "TrustServerCertificate=yes;"
    )

    engine = create_engine(
        "mssql+pyodbc:///?odbc_connect=" + quote_plus(connection_string),
        fast_executemany=True,
    )
    return engine, driver


def check_source_files():
    source_files = [
        RAW_FOLDER / "train_FD001.txt",
        RAW_FOLDER / "test_FD001.txt",
        RAW_FOLDER / "RUL_FD001.txt",
        SYNTHETIC_FOLDER / "plants.csv",
        SYNTHETIC_FOLDER / "technicians.csv",
        SYNTHETIC_FOLDER / "engine_master.csv",
        SYNTHETIC_FOLDER / "maintenance_log.csv",
    ]

    missing_files = []
    for file_path in source_files:
        if not file_path.is_file():
            missing_files.append(str(file_path))

    if missing_files:
        raise FileNotFoundError("Missing source files: " + ", ".join(missing_files))


def read_sensor_file(file_path, split_name):
    data = pd.read_csv(file_path, sep=r"\s+", header=None)

    if data.shape[1] != len(SENSOR_COLUMNS):
        raise ValueError(
            f"{file_path.name} has {data.shape[1]} columns; "
            f"expected {len(SENSOR_COLUMNS)}."
        )

    data.columns = SENSOR_COLUMNS
    data.insert(0, "split", split_name)
    return data


def read_source_data():
    check_source_files()

    print("Reading training data...")
    train_data = read_sensor_file(RAW_FOLDER / "train_FD001.txt", "train")

    print("Reading testing data...")
    test_data = read_sensor_file(RAW_FOLDER / "test_FD001.txt", "test")
    sensors = pd.concat([train_data, test_data], ignore_index=True)

    rul_truth = pd.read_csv(
        RAW_FOLDER / "RUL_FD001.txt", sep=r"\s+", header=None
    )
    if rul_truth.shape[1] != 1:
        raise ValueError("RUL_FD001.txt must contain exactly one value column.")
    rul_truth.columns = ["true_rul"]
    rul_truth.insert(0, "engine_id", range(1, len(rul_truth) + 1))

    print("Reading synthetic data...")
    plants = pd.read_csv(SYNTHETIC_FOLDER / "plants.csv")
    technicians = pd.read_csv(SYNTHETIC_FOLDER / "technicians.csv")
    engine_master = pd.read_csv(SYNTHETIC_FOLDER / "engine_master.csv")
    maintenance = pd.read_csv(SYNTHETIC_FOLDER / "maintenance_log.csv")

    return {
        "sensors": sensors,
        "rul_truth": rul_truth,
        "plants": plants,
        "technicians": technicians,
        "engine_master": engine_master,
        "maintenance": maintenance,
    }


def inspect_database(engine):
    table_counts = {}
    database_columns = {}

    with engine.connect() as connection:
        database_name = connection.exec_driver_sql("SELECT DB_NAME();").scalar_one()
        if database_name != DATABASE:
            raise RuntimeError(
                f"Connected to {database_name}, but expected {DATABASE}."
            )

        print(f"Connected to {database_name} successfully.")

        for table_name in TABLE_COLUMNS:
            rows = connection.exec_driver_sql(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? "
                "ORDER BY ORDINAL_POSITION;",
                ("stg", table_name),
            ).fetchall()
            database_columns[table_name] = [row[0] for row in rows]
            table_counts[table_name] = connection.exec_driver_sql(
                f"SELECT COUNT(*) FROM stg.{table_name};"
            ).scalar_one()

    return database_columns, table_counts


def validate_columns(data, database_columns):
    for table_name in TABLE_COLUMNS:
        expected_columns = TABLE_COLUMNS[table_name]
        source_columns = list(data[table_name].columns)
        sql_columns = database_columns[table_name]

        if not sql_columns:
            raise ValueError(f"The table stg.{table_name} does not exist.")
        if source_columns != expected_columns:
            raise ValueError(
                f"Source columns for {table_name} do not match. "
                f"Found {source_columns}; expected {expected_columns}."
            )
        if sql_columns != expected_columns:
            raise ValueError(
                f"SQL columns for stg.{table_name} do not match. "
                f"Found {sql_columns}; expected {expected_columns}."
            )


def get_quality_results(data):
    train_rows = int((data["sensors"]["split"] == "train").sum())
    test_rows = int((data["sensors"]["split"] == "test").sum())
    duplicate_engine_uids = int(
        data["engine_master"]["engine_uid"].duplicated().sum()
    )

    duplicate_work_orders = data["maintenance"]["work_order_id"].duplicated(
        keep=False
    )
    duplicate_work_order_rows = int(duplicate_work_orders.sum())
    duplicate_work_order_ids = int(
        data["maintenance"].loc[
            duplicate_work_orders, "work_order_id"
        ].nunique()
    )
    missing_durations = int(data["maintenance"]["duration_hours"].isna().sum())

    if train_rows == 0 or test_rows == 0:
        raise ValueError("Both train and test sensor records are required.")
    if duplicate_engine_uids != 0:
        raise ValueError("engine_uid values in engine_master.csv must be unique.")

    return {
        "train_rows": train_rows,
        "test_rows": test_rows,
        "duplicate_engine_uids": duplicate_engine_uids,
        "missing_durations": missing_durations,
        "duplicate_work_order_rows": duplicate_work_order_rows,
        "duplicate_work_order_ids": duplicate_work_order_ids,
    }


def print_validation_results(data, table_counts, quality_results, driver):
    print(f"Using {driver}.")
    print("\nCurrent staging row counts:")
    for table_name in TABLE_COLUMNS:
        print(f"{TABLE_LABELS[table_name]}: {table_counts[table_name]} rows")

    print("\nValidated source row counts and planned inserts:")
    for table_name in TABLE_COLUMNS:
        print(f"{TABLE_LABELS[table_name]}: {len(data[table_name])} rows")

    print("\nSource checks:")
    print(f"Training sensor rows: {quality_results['train_rows']}")
    print(f"Testing sensor rows: {quality_results['test_rows']}")
    print(
        "Duplicate engine UIDs: "
        f"{quality_results['duplicate_engine_uids']}"
    )
    print(
        "Missing maintenance durations to preserve: "
        f"{quality_results['missing_durations']}"
    )
    print(
        "Duplicate maintenance work-order rows to preserve: "
        f"{quality_results['duplicate_work_order_rows']} "
        f"across {quality_results['duplicate_work_order_ids']} IDs"
    )


def check_staging_is_empty(table_counts):
    tables_with_data = []
    for table_name, row_count in table_counts.items():
        if row_count > 0:
            tables_with_data.append(f"stg.{table_name} ({row_count} rows)")

    if tables_with_data:
        raise RuntimeError(
            "Loading stopped because staging already contains data: "
            + ", ".join(tables_with_data)
        )


def load_data(engine, data, quality_results):
    with engine.begin() as connection:
        current_counts = {}
        for table_name in TABLE_COLUMNS:
            current_counts[table_name] = connection.exec_driver_sql(
                f"SELECT COUNT(*) FROM stg.{table_name};"
            ).scalar_one()
        check_staging_is_empty(current_counts)

        for table_name in TABLE_COLUMNS:
            print(f"Loading {TABLE_LABELS[table_name].lower()}...")
            data[table_name].to_sql(
                table_name,
                connection,
                schema="stg",
                if_exists="append",
                index=False,
                chunksize=BATCH_SIZE,
            )

        loaded_counts = {}
        for table_name in TABLE_COLUMNS:
            loaded_counts[table_name] = connection.exec_driver_sql(
                f"SELECT COUNT(*) FROM stg.{table_name};"
            ).scalar_one()
            if loaded_counts[table_name] != len(data[table_name]):
                raise RuntimeError(
                    f"Row count check failed for stg.{table_name}."
                )

        split_rows = dict(
            connection.exec_driver_sql(
                "SELECT split, COUNT(*) FROM stg.sensors GROUP BY split;"
            ).fetchall()
        )
        if split_rows.get("train", 0) != quality_results["train_rows"]:
            raise RuntimeError("Training sensor row verification failed.")
        if split_rows.get("test", 0) != quality_results["test_rows"]:
            raise RuntimeError("Testing sensor row verification failed.")

        duplicate_engine_uids = connection.exec_driver_sql(
            "SELECT COUNT(*) - COUNT(DISTINCT engine_uid) "
            "FROM stg.engine_master;"
        ).scalar_one()
        if duplicate_engine_uids != 0:
            raise RuntimeError("Engine UID uniqueness verification failed.")

        missing_durations = connection.exec_driver_sql(
            "SELECT COUNT(*) FROM stg.maintenance "
            "WHERE duration_hours IS NULL "
            "OR LTRIM(RTRIM(duration_hours)) = '';"
        ).scalar_one()
        if missing_durations != quality_results["missing_durations"]:
            raise RuntimeError("Missing duration verification failed.")

        duplicate_work_order_ids = connection.exec_driver_sql(
            "SELECT COUNT(*) FROM ("
            "SELECT work_order_id FROM stg.maintenance "
            "GROUP BY work_order_id HAVING COUNT(*) > 1"
            ") AS duplicates;"
        ).scalar_one()
        if duplicate_work_order_ids != quality_results["duplicate_work_order_ids"]:
            raise RuntimeError("Duplicate work-order verification failed.")

    print("\nData loaded successfully.")
    for table_name in TABLE_COLUMNS:
        print(f"{TABLE_LABELS[table_name]}: {loaded_counts[table_name]} rows")
    print(f"Training sensor rows: {split_rows['train']}")
    print(f"Testing sensor rows: {split_rows['test']}")
    print(f"Missing maintenance durations preserved: {missing_durations}")
    print(
        "Duplicate maintenance work-order IDs preserved: "
        f"{duplicate_work_order_ids}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Validate or load source data into the staging tables."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Insert the validated data into the empty staging tables.",
    )
    args = parser.parse_args()

    try:
        engine, driver = create_database_engine()
        database_columns, table_counts = inspect_database(engine)
        data = read_source_data()
        validate_columns(data, database_columns)
        quality_results = get_quality_results(data)
        print_validation_results(data, table_counts, quality_results, driver)
        check_staging_is_empty(table_counts)

        if args.apply:
            load_data(engine, data, quality_results)
        else:
            print("Validation completed. No database rows were inserted.")
            print("Run with --apply only after approval to load the data.")
    except Exception as error:
        raise SystemExit(f"\nStopped: {error}") from None


if __name__ == "__main__":
    main()
