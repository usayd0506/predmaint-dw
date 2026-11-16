#!/usr/bin/env python3
"""Read-only audit of Power BI CSV exports against PredMaintDW mart tables.

The script only issues SELECT statements.  It discovers columns, SQL data types,
primary keys, and unique indexes from SQL Server metadata instead of hard-coding
the mart schema.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

try:
    import pyodbc
except ImportError:  # handled as a reportable connectivity failure
    pyodbc = None

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TABLES = (
    "DimDate",
    "DimEngine",
    "DimPlant",
    "DimTechnician",
    "DimModel",
    "DimMethod",
    "DimRun",
    "FactEngineHealth",
    "FactRULPrediction",
    "FactAlert",
    "FactMaintenance",
    "FactSchedule",
    "FactModelMetric",
)
INTEGER_TYPES = {"tinyint", "smallint", "int", "bigint"}
DECIMAL_TYPES = {"decimal", "numeric", "money", "smallmoney"}
FLOAT_TYPES = {"float", "real"}
DATE_TYPES = {"date"}
DATETIME_TYPES = {"datetime", "datetime2", "smalldatetime", "datetimeoffset"}
TEXT_TYPES = {"char", "nchar", "varchar", "nvarchar", "text", "ntext"}
GUID_TYPES = {"uniqueidentifier"}
BIT_TYPES = {"bit"}
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class Column:
    name: str
    sql_type: str
    nullable: bool
    max_length: int | None
    precision: int | None
    scale: int | None
    ordinal: int

    @property
    def display_type(self) -> str:
        if self.sql_type in {"decimal", "numeric"}:
            return f"{self.sql_type}({self.precision},{self.scale})"
        if self.sql_type in {"varchar", "char", "nvarchar", "nchar"}:
            length = self.max_length
            if length == -1:
                suffix = "max"
            elif self.sql_type.startswith("n") and length is not None:
                suffix = str(length // 2)
            else:
                suffix = str(length)
            return f"{self.sql_type}({suffix})"
        return self.sql_type


@dataclass
class TableData:
    name: str
    columns: list[Column] = field(default_factory=list)
    primary_key: list[str] = field(default_factory=list)
    unique_keys: list[tuple[str, list[str]]] = field(default_factory=list)
    sql_rows: list[dict[str, Any]] = field(default_factory=list)
    csv_columns: list[str] = field(default_factory=list)
    csv_rows: list[dict[str, str]] = field(default_factory=list)
    csv_path: Path | None = None
    error: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv-dir",
        type=Path,
        default=ROOT / "data" / "powerbi_csv_reference",
        help="Directory containing one <mart table>.csv file per table.",
    )
    parser.add_argument("--server", default=None, help="SQL Server name; defaults to DB_SERVER or localhost.")
    parser.add_argument("--database", default=None, help="Database; defaults to DB_NAME or PredMaintDW.")
    parser.add_argument("--driver", default=None, help="ODBC driver; defaults to DB_DRIVER or ODBC Driver 18 for SQL Server.")
    parser.add_argument("--schema", default="mart", help="SQL schema to audit (default: mart).")
    parser.add_argument("--report-csv", type=Path, default=ROOT / "reports" / "powerbi_data_audit.csv")
    parser.add_argument("--report-md", type=Path, default=ROOT / "reports" / "powerbi_data_audit.md")
    parser.add_argument("--sample-limit", type=int, default=5, help="Maximum discrepancy examples per table.")
    parser.add_argument("--float-abs-tol", type=float, default=1e-9)
    parser.add_argument("--float-rel-tol", type=float, default=1e-9)
    return parser.parse_args()


def quote_identifier(value: str) -> str:
    if not IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"Unsafe SQL identifier: {value!r}")
    return f"[{value}]"


def load_environment() -> None:
    if load_dotenv is not None:
        load_dotenv(ROOT / ".env")


def connect(args: argparse.Namespace):
    if pyodbc is None:
        raise RuntimeError("pyodbc is not installed in this Python environment")
    load_environment()
    server = args.server or os.getenv("DB_SERVER", "localhost")
    database = args.database or os.getenv("DB_NAME", "PredMaintDW")
    requested_driver = args.driver or os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    installed = {name.casefold(): name for name in pyodbc.drivers()}
    driver = installed.get(requested_driver.casefold())
    if driver is None and args.driver is None:
        for candidate in ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "SQL Server"):
            driver = installed.get(candidate.casefold())
            if driver is not None:
                break
    if driver is None:
        raise RuntimeError(
            f"Configured ODBC driver {requested_driver!r} is not installed; "
            f"installed drivers: {sorted(installed.values())}"
        )
    connection_string = (
        f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};"
        "Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes;ApplicationIntent=ReadOnly;"
    )
    connection = pyodbc.connect(connection_string, timeout=10, autocommit=False)
    connection.timeout = 120
    cursor = connection.cursor()
    cursor.execute("SET NOCOUNT ON; SET TRANSACTION ISOLATION LEVEL READ COMMITTED;")
    db_name, login_name = cursor.execute("SELECT DB_NAME(), SUSER_SNAME()").fetchone()
    return connection, {
        "server": server,
        "database": str(db_name),
        "login": str(login_name),
        "driver": driver,
        "requested_driver": requested_driver,
    }


def discover_tables(connection, schema: str) -> dict[str, TableData]:
    cursor = connection.cursor()
    table_rows = cursor.execute(
        """
        SELECT t.name
        FROM sys.tables AS t
        JOIN sys.schemas AS s ON s.schema_id = t.schema_id
        WHERE s.name = ?
        ORDER BY t.name;
        """,
        schema,
    ).fetchall()
    existing = {str(row[0]).casefold(): str(row[0]) for row in table_rows}
    results: dict[str, TableData] = {}

    for expected in EXPECTED_TABLES:
        actual_name = existing.get(expected.casefold())
        data = TableData(name=expected)
        results[expected] = data
        if actual_name is None:
            data.error = f"SQL table {schema}.{expected} does not exist"
            continue

        column_rows = cursor.execute(
            """
            SELECT c.name, ty.name, c.is_nullable, c.max_length,
                   c.precision, c.scale, c.column_id
            FROM sys.columns AS c
            JOIN sys.types AS ty ON ty.user_type_id = c.user_type_id
            JOIN sys.tables AS t ON t.object_id = c.object_id
            JOIN sys.schemas AS s ON s.schema_id = t.schema_id
            WHERE s.name = ? AND t.name = ?
            ORDER BY c.column_id;
            """,
            schema,
            actual_name,
        ).fetchall()
        data.columns = [
            Column(
                name=str(r[0]),
                sql_type=str(r[1]).lower(),
                nullable=bool(r[2]),
                max_length=int(r[3]) if r[3] is not None else None,
                precision=int(r[4]) if r[4] is not None else None,
                scale=int(r[5]) if r[5] is not None else None,
                ordinal=int(r[6]),
            )
            for r in column_rows
        ]

        index_rows = cursor.execute(
            """
            SELECT i.name, i.is_primary_key, ic.key_ordinal, c.name
            FROM sys.indexes AS i
            JOIN sys.index_columns AS ic
              ON ic.object_id = i.object_id AND ic.index_id = i.index_id
            JOIN sys.columns AS c
              ON c.object_id = ic.object_id AND c.column_id = ic.column_id
            JOIN sys.tables AS t ON t.object_id = i.object_id
            JOIN sys.schemas AS s ON s.schema_id = t.schema_id
            WHERE s.name = ? AND t.name = ?
              AND i.is_unique = 1 AND i.is_hypothetical = 0
              AND ic.key_ordinal > 0
            ORDER BY i.index_id, ic.key_ordinal;
            """,
            schema,
            actual_name,
        ).fetchall()
        grouped: dict[tuple[str, bool], list[str]] = defaultdict(list)
        for index_name, is_pk, _ordinal, column_name in index_rows:
            grouped[(str(index_name), bool(is_pk))].append(str(column_name))
        for (index_name, is_pk), key_columns in grouped.items():
            if is_pk:
                data.primary_key = key_columns
            else:
                data.unique_keys.append((index_name, key_columns))

        select_columns = ", ".join(quote_identifier(c.name) for c in data.columns)
        sql = (
            f"SELECT {select_columns} FROM {quote_identifier(schema)}."
            f"{quote_identifier(actual_name)};"
        )
        rows = cursor.execute(sql).fetchall()
        names = [c.name for c in data.columns]
        data.sql_rows = [dict(zip(names, row)) for row in rows]
    return results


def find_csvs(csv_dir: Path) -> dict[str, Path]:
    if not csv_dir.is_dir():
        return {}
    return {path.stem.casefold(): path for path in csv_dir.glob("*.csv") if path.is_file()}


def read_csv_data(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                reader = csv.DictReader(handle)
                columns = list(reader.fieldnames or [])
                if not columns:
                    raise ValueError("CSV has no header row")
                rows = []
                for row_number, row in enumerate(reader, start=2):
                    if None in row:
                        raise ValueError(f"CSV row {row_number} has more fields than the header")
                    rows.append({str(k): "" if v is None else v for k, v in row.items()})
                return columns, rows
        except UnicodeDecodeError as exc:
            last_error = exc
    raise ValueError(f"Could not decode CSV: {last_error}")


def parse_date_text(value: str) -> date:
    text = value.strip()
    if "T" in text or " " in text:
        return parse_datetime_text(text).date()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return date.fromisoformat(text)


def parse_datetime_text(value: str) -> datetime:
    text = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %I:%M:%S %p",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError(f"unrecognized datetime {value!r}")


def normalize_value(value: Any, column: Column, source: str) -> Any:
    if source == "csv":
        if value is None or str(value).strip() == "":
            return None
        text = str(value).strip()
    else:
        if value is None:
            return None
        text = str(value).strip()

    sql_type = column.sql_type
    if sql_type in INTEGER_TYPES:
        decimal_value = Decimal(text.replace(",", ""))
        if decimal_value != decimal_value.to_integral_value():
            raise ValueError(f"not an integer: {value!r}")
        return int(decimal_value)
    if sql_type in DECIMAL_TYPES:
        return Decimal(text.replace(",", ""))
    if sql_type in FLOAT_TYPES:
        number = float(text.replace(",", ""))
        if not math.isfinite(number):
            raise ValueError(f"non-finite number: {value!r}")
        return number
    if sql_type in BIT_TYPES:
        if isinstance(value, bool):
            return value
        lowered = text.casefold()
        if lowered in {"1", "true", "yes", "y"}:
            return True
        if lowered in {"0", "false", "no", "n"}:
            return False
        raise ValueError(f"not a bit/boolean: {value!r}")
    if sql_type in DATE_TYPES:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return parse_date_text(text)
    if sql_type in DATETIME_TYPES:
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        return parse_datetime_text(text)
    if sql_type in GUID_TYPES:
        return text.strip("{}").lower()
    if sql_type in TEXT_TYPES:
        return str(value)
    if sql_type in {"binary", "varbinary", "image", "timestamp", "rowversion"}:
        if isinstance(value, bytes):
            return value.hex()
        return text.removeprefix("0x").lower()
    return value


def json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    return value


def values_equal(left: Any, right: Any, column: Column, abs_tol: float, rel_tol: float) -> bool:
    if left is None or right is None:
        return left is right
    if column.sql_type in FLOAT_TYPES:
        return math.isclose(float(left), float(right), abs_tol=abs_tol, rel_tol=rel_tol)
    return left == right


def soft_format_equal(left: Any, right: Any, column: Column) -> bool:
    if left is None or right is None:
        return left is right
    if column.sql_type in TEXT_TYPES:
        return str(left).strip().casefold() == str(right).strip().casefold()
    return False


def duplicate_summary(rows: list[dict[str, Any]], columns: list[str]) -> tuple[int, list[tuple[Any, ...]]]:
    if not columns:
        return 0, []
    counter = Counter(tuple(row.get(c) for c in columns) for row in rows)
    duplicate_count = sum(count - 1 for count in counter.values() if count > 1)
    examples = [key for key, count in counter.items() if count > 1][:5]
    return duplicate_count, examples


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=json_value, separators=(",", ":"))


def status_from_checks(checks: Iterable[str]) -> str:
    checks = list(checks)
    if any(value == "FAIL" for value in checks):
        return "FAIL"
    if any(value == "NOT VERIFIED" for value in checks):
        return "NOT VERIFIED"
    return "PASS"


def compare_table(data: TableData, args: argparse.Namespace) -> dict[str, Any]:
    result: dict[str, Any] = {
        "table": data.name,
        "status": "NOT VERIFIED",
        "csv_file": str(data.csv_path) if data.csv_path else "",
        "sql_table": f"{args.schema}.{data.name}",
        "primary_key": ", ".join(data.primary_key),
        "unique_keys": "; ".join(f"{name}({', '.join(cols)})" for name, cols in data.unique_keys),
        "sql_rows": len(data.sql_rows) if data.columns else "",
        "csv_rows": len(data.csv_rows) if data.csv_path else "",
        "column_status": "NOT VERIFIED",
        "type_status": "NOT VERIFIED",
        "row_count_status": "NOT VERIFIED",
        "null_status": "NOT VERIFIED",
        "duplicate_status": "NOT VERIFIED",
        "key_status": "NOT VERIFIED",
        "value_status": "NOT VERIFIED",
        "reference_status": "NOT VERIFIED",
        "cause": "",
        "missing_columns": "",
        "extra_columns": "",
        "type_issues": "",
        "null_issues": "",
        "duplicate_issues": "",
        "key_issues": "",
        "value_diff_count": "",
        "csv_only_count": "",
        "sql_only_count": "",
        "examples": "",
        "limitations": "",
        "error": data.error,
    }
    if data.error:
        causes = []
        if not data.columns:
            causes.append("SQL table unavailable")
        else:
            causes.append("CSV unreadable")
        if data.csv_path is None:
            causes.append("CSV file missing")
            result["error"] = (result["error"] + "; " if result["error"] else "") + f"No {data.name}.csv in {args.csv_dir}"
        result["cause"] = "; ".join(causes)
        return result
    if data.csv_path is None:
        result["cause"] = "CSV file missing"
        result["error"] = f"No {data.name}.csv in {args.csv_dir}"
        return result

    sql_names = [column.name for column in data.columns]
    sql_by_fold = {name.casefold(): name for name in sql_names}
    csv_by_fold = {name.casefold(): name for name in data.csv_columns}
    missing = [name for name in sql_names if name.casefold() not in csv_by_fold]
    extra = [name for name in data.csv_columns if name.casefold() not in sql_by_fold]
    case_mismatches = [
        (sql_name, csv_by_fold[sql_name.casefold()])
        for sql_name in sql_names
        if sql_name.casefold() in csv_by_fold and sql_name != csv_by_fold[sql_name.casefold()]
    ]
    result["missing_columns"] = ", ".join(missing)
    result["extra_columns"] = ", ".join(extra)
    result["column_status"] = "PASS" if not missing and not extra and not case_mismatches else "FAIL"

    common_columns = [column for column in data.columns if column.name.casefold() in csv_by_fold]
    normalized_sql: list[dict[str, Any]] = []
    normalized_csv: list[dict[str, Any]] = []
    type_issues: list[dict[str, Any]] = []
    for row in data.sql_rows:
        normalized_sql.append({column.name: normalize_value(row[column.name], column, "sql") for column in common_columns})
    for row_number, row in enumerate(data.csv_rows, start=2):
        normalized: dict[str, Any] = {}
        for column in common_columns:
            csv_name = csv_by_fold[column.name.casefold()]
            try:
                normalized[column.name] = normalize_value(row.get(csv_name), column, "csv")
            except (ValueError, TypeError, InvalidOperation, OverflowError) as exc:
                normalized[column.name] = ("__TYPE_ERROR__", row.get(csv_name))
                if len(type_issues) < args.sample_limit:
                    type_issues.append({"row": row_number, "column": column.name, "value": row.get(csv_name), "error": str(exc)})
        normalized_csv.append(normalized)
    result["type_status"] = "PASS" if not type_issues else "FAIL"
    result["type_issues"] = compact_json(type_issues) if type_issues else ""

    result["row_count_status"] = "PASS" if len(data.sql_rows) == len(data.csv_rows) else "FAIL"

    null_issues: list[dict[str, Any]] = []
    blank_ambiguities: list[str] = []
    for column in common_columns:
        sql_nulls = sum(row[column.name] is None for row in normalized_sql)
        csv_blanks = sum(row[column.name] is None for row in normalized_csv)
        sql_empty = sum(row[column.name] == "" for row in normalized_sql) if column.sql_type in TEXT_TYPES else 0
        if sql_nulls != csv_blanks:
            null_issues.append({"column": column.name, "sql_nulls": sql_nulls, "csv_blanks": csv_blanks, "sql_empty_strings": sql_empty})
        if column.sql_type in TEXT_TYPES and csv_blanks:
            blank_ambiguities.append(column.name)
    result["null_status"] = "PASS" if not null_issues else "FAIL"
    result["null_issues"] = compact_json(null_issues) if null_issues else ""

    full_columns = [column.name for column in common_columns]
    sql_full_dups, sql_full_examples = duplicate_summary(normalized_sql, full_columns)
    csv_full_dups, csv_full_examples = duplicate_summary(normalized_csv, full_columns)
    duplicate_issues: list[dict[str, Any]] = []
    if sql_full_dups or csv_full_dups:
        duplicate_issues.append({"key": "full row", "sql_duplicates": sql_full_dups, "csv_duplicates": csv_full_dups})
    key_issues: list[dict[str, Any]] = []
    keys_to_check = [("PRIMARY KEY", data.primary_key)] + data.unique_keys
    for key_name, key_columns in keys_to_check:
        if not key_columns:
            if key_name == "PRIMARY KEY":
                key_issues.append({"key": key_name, "issue": "No primary key discovered"})
            continue
        if any(column not in full_columns for column in key_columns):
            key_issues.append({"key": key_name, "columns": key_columns, "issue": "Key column missing from CSV"})
            continue
        sql_dups, _ = duplicate_summary(normalized_sql, key_columns)
        csv_dups, examples = duplicate_summary(normalized_csv, key_columns)
        if sql_dups or csv_dups:
            key_issues.append({"key": key_name, "columns": key_columns, "sql_duplicates": sql_dups, "csv_duplicates": csv_dups, "examples": examples[: args.sample_limit]})
    result["duplicate_status"] = "PASS" if not duplicate_issues else "FAIL"
    result["key_status"] = "PASS" if not key_issues else "FAIL"
    result["duplicate_issues"] = compact_json(duplicate_issues) if duplicate_issues else ""
    result["key_issues"] = compact_json(key_issues) if key_issues else ""

    examples: list[dict[str, Any]] = []
    value_diff_count = 0
    csv_only_count = 0
    sql_only_count = 0
    formatting_only = True
    can_key_compare = bool(data.primary_key) and all(column in full_columns for column in data.primary_key)
    if can_key_compare:
        sql_key_counts = Counter(tuple(row[c] for c in data.primary_key) for row in normalized_sql)
        csv_key_counts = Counter(tuple(row[c] for c in data.primary_key) for row in normalized_csv)
        if any(count > 1 for count in sql_key_counts.values()) or any(count > 1 for count in csv_key_counts.values()):
            can_key_compare = False

    if missing:
        result["value_status"] = "NOT VERIFIED"
        result["limitations"] = "Full-row comparison is unsupported because SQL columns are missing from the CSV."
    elif can_key_compare:
        sql_map = {tuple(row[c] for c in data.primary_key): row for row in normalized_sql}
        csv_map = {tuple(row[c] for c in data.primary_key): row for row in normalized_csv}
        sql_keys = set(sql_map)
        csv_keys = set(csv_map)
        csv_only_keys = sorted(csv_keys - sql_keys, key=repr)
        sql_only_keys = sorted(sql_keys - csv_keys, key=repr)
        csv_only_count = len(csv_only_keys)
        sql_only_count = len(sql_only_keys)
        for key in csv_only_keys[: args.sample_limit]:
            examples.append({"kind": "CSV only", "key": key})
        for key in sql_only_keys[: max(0, args.sample_limit - len(examples))]:
            examples.append({"kind": "SQL only", "key": key})
        for key in sorted(sql_keys & csv_keys, key=repr):
            differences = {}
            for column in data.columns:
                left = sql_map[key][column.name]
                right = csv_map[key][column.name]
                if not values_equal(left, right, column, args.float_abs_tol, args.float_rel_tol):
                    differences[column.name] = {"sql": left, "csv": right}
                    if not soft_format_equal(left, right, column):
                        formatting_only = False
            if differences:
                value_diff_count += 1
                if len(examples) < args.sample_limit:
                    examples.append({"kind": "value mismatch", "key": key, "columns": differences})
        result["value_status"] = "PASS" if value_diff_count == 0 and not csv_only_count and not sql_only_count else "FAIL"
    else:
        sql_counter = Counter(tuple(row[c.name] for c in data.columns) for row in normalized_sql)
        csv_counter = Counter(tuple(row[c.name] for c in data.columns) for row in normalized_csv)
        sql_only_count = sum((sql_counter - csv_counter).values())
        csv_only_count = sum((csv_counter - sql_counter).values())
        value_diff_count = max(sql_only_count, csv_only_count)
        result["value_status"] = "PASS" if not sql_only_count and not csv_only_count else "FAIL"
        result["limitations"] = "Primary-key comparison unavailable; used a full-row multiset comparison."

    if blank_ambiguities:
        note = "CSV blank fields cannot distinguish SQL NULL from an empty text value for: " + ", ".join(blank_ambiguities) + "."
        result["limitations"] = (result["limitations"] + " " + note).strip()

    result["value_diff_count"] = value_diff_count
    result["csv_only_count"] = csv_only_count
    result["sql_only_count"] = sql_only_count
    result["examples"] = compact_json(examples) if examples else ""

    causes: list[str] = []
    if missing or extra or case_mismatches:
        causes.append("schema mismatch")
    if len(data.sql_rows) != len(data.csv_rows) or csv_only_count or sql_only_count:
        causes.append("missing or extra records")
    if value_diff_count:
        causes.append("formatting only" if formatting_only else "actual value differences")
    if null_issues:
        causes.append("NULL/blank differences")
    if type_issues:
        causes.append("incompatible CSV values")
    if key_issues or duplicate_issues:
        causes.append("duplicate/key uniqueness differences")
    result["cause"] = "; ".join(causes) if causes else "equivalent after normalization"
    result["reference_status"] = "PASS"  # enhanced after all tables are loaded
    result["status"] = status_from_checks(
        result[name]
        for name in (
            "column_status",
            "type_status",
            "row_count_status",
            "null_status",
            "duplicate_status",
            "key_status",
            "value_status",
            "reference_status",
        )
    )
    return result


def normalized_lookup(data: TableData, key: str, label: str, source: str) -> dict[Any, Any]:
    columns = {column.name: column for column in data.columns}
    if key not in columns or label not in columns:
        return {}
    if source == "sql":
        rows = data.sql_rows
        return {normalize_value(row[key], columns[key], "sql"): normalize_value(row[label], columns[label], "sql") for row in rows}
    csv_by_fold = {name.casefold(): name for name in data.csv_columns}
    if key.casefold() not in csv_by_fold or label.casefold() not in csv_by_fold:
        return {}
    return {
        normalize_value(row[csv_by_fold[key.casefold()]], columns[key], "csv"):
        normalize_value(row[csv_by_fold[label.casefold()]], columns[label], "csv")
        for row in data.csv_rows
    }


def enhance_reference_checks(tables: dict[str, TableData], results: list[dict[str, Any]]) -> None:
    result_by_name = {result["table"]: result for result in results}
    specs = {
        "run_key": ("DimRun", "run_key", "run_id"),
        "model_key": ("DimModel", "model_key", "model_name"),
        "method_key": ("DimMethod", "method_key", "method_name"),
    }
    lookup_cache: dict[tuple[str, str], dict[Any, Any]] = {}
    for _column, (dimension, key, label) in specs.items():
        lookup_cache[(dimension, "sql")] = normalized_lookup(tables[dimension], key, label, "sql")
        lookup_cache[(dimension, "csv")] = normalized_lookup(tables[dimension], key, label, "csv")

    sql_run_ids = set(lookup_cache[("DimRun", "sql")].values())
    csv_run_ids = set(lookup_cache[("DimRun", "csv")].values())
    snapshot_diff = bool(sql_run_ids != csv_run_ids and sql_run_ids and csv_run_ids)

    for table_name, data in tables.items():
        result = result_by_name[table_name]
        if result["error"] or data.csv_path is None:
            continue
        applicable = [column for column in specs if any(c.name == column for c in data.columns)]
        if not applicable:
            result["reference_status"] = "PASS"
            continue
        issues = []
        sql_columns = {column.name: column for column in data.columns}
        csv_by_fold = {name.casefold(): name for name in data.csv_columns}
        for column_name in applicable:
            dimension, _key, _label = specs[column_name]
            sql_lookup = lookup_cache[(dimension, "sql")]
            csv_lookup = lookup_cache[(dimension, "csv")]
            if column_name.casefold() not in csv_by_fold or not sql_lookup or not csv_lookup:
                issues.append({"column": column_name, "issue": "reference comparison unavailable"})
                continue
            column = sql_columns[column_name]
            sql_values = {normalize_value(row[column_name], column, "sql") for row in data.sql_rows}
            csv_values = {normalize_value(row[csv_by_fold[column_name.casefold()]], column, "csv") for row in data.csv_rows if str(row[csv_by_fold[column_name.casefold()]]).strip()}
            sql_orphans = sorted((value for value in sql_values if value not in sql_lookup), key=repr)
            csv_orphans = sorted((value for value in csv_values if value not in csv_lookup), key=repr)
            sql_labels = {sql_lookup[value] for value in sql_values if value in sql_lookup}
            csv_labels = {csv_lookup[value] for value in csv_values if value in csv_lookup}
            if sql_orphans or csv_orphans or sql_labels != csv_labels:
                issues.append(
                    {
                        "column": column_name,
                        "sql_orphan_keys": sql_orphans[:5],
                        "csv_orphan_keys": csv_orphans[:5],
                        "sql_labels_only": sorted(sql_labels - csv_labels, key=repr)[:5],
                        "csv_labels_only": sorted(csv_labels - sql_labels, key=repr)[:5],
                    }
                )
        if issues:
            result["reference_status"] = "NOT VERIFIED" if any(i.get("issue") for i in issues) else "FAIL"
            result["key_issues"] = (result["key_issues"] + " " + compact_json({"reference_checks": issues})).strip()
            if snapshot_diff and any(issue["column"] == "run_key" for issue in issues):
                result["cause"] = (result["cause"] + "; different pipeline snapshot (run_id sets differ)").strip("; ")
        else:
            result["reference_status"] = "PASS"
        result["status"] = status_from_checks(
            result[name]
            for name in (
                "column_status", "type_status", "row_count_status", "null_status",
                "duplicate_status", "key_status", "value_status", "reference_status",
            )
        )


REPORT_FIELDS = (
    "table", "status", "csv_file", "sql_table", "primary_key", "unique_keys",
    "sql_rows", "csv_rows", "column_status", "type_status", "row_count_status",
    "null_status", "duplicate_status", "key_status", "value_status", "reference_status",
    "cause", "missing_columns", "extra_columns", "type_issues", "null_issues",
    "duplicate_issues", "key_issues", "value_diff_count", "csv_only_count",
    "sql_only_count", "examples", "limitations", "error",
)


def write_reports(
    args: argparse.Namespace,
    results: list[dict[str, Any]],
    tables: dict[str, TableData],
    connection_info: dict[str, str] | None,
    connection_error: str,
) -> None:
    args.report_csv.parent.mkdir(parents=True, exist_ok=True)
    args.report_md.parent.mkdir(parents=True, exist_ok=True)
    with args.report_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    counts = Counter(result["status"] for result in results)
    lines = [
        "# Power BI CSV to SQL Server audit",
        "",
        f"- CSV source: `{args.csv_dir.resolve()}`",
        f"- CSV directory: {'FOUND' if args.csv_dir.is_dir() else 'NOT FOUND'}",
        f"- SQL target: `{args.schema}` schema in `{(connection_info or {}).get('database', args.database or os.getenv('DB_NAME', 'PredMaintDW'))}`",
        f"- Connectivity: {'PASS' if connection_info else 'NOT VERIFIED'}",
    ]
    if connection_info:
        lines.extend(
            [
                f"- Server: `{connection_info['server']}`",
                f"- ODBC driver: `{connection_info['driver']}`",
                f"- Authentication: Windows (`{connection_info['login']}`)",
            ]
        )
    if connection_error:
        lines.append(f"- Connectivity error: `{connection_error}`")
    lines.extend(
        [
            f"- Result totals: {counts.get('PASS', 0)} PASS, {counts.get('FAIL', 0)} FAIL, {counts.get('NOT VERIFIED', 0)} NOT VERIFIED",
            "",
            "## Method",
            "",
            "The audit discovers live SQL columns, data types, primary keys, and unique indexes from `sys` metadata. "
            "It parses CSV values according to those SQL types, normalizes dates and booleans, compares decimal values exactly, "
            f"and compares floating-point values with absolute and relative tolerances of {args.float_abs_tol:g} and {args.float_rel_tol:g}. "
            "Rows are matched by the discovered primary key when it is present and unique; otherwise a full-row multiset comparison is used. "
            "No aggregate checksum is used.",
            "",
            "CSV blank fields are normalized to SQL NULL. When a text column contains blank CSV fields, CSV syntax cannot prove whether the source meant NULL or an empty string; that limitation is called out per table.",
            "",
            "## Summary",
            "",
            "| Table | Status | SQL rows | CSV rows | Columns | Types | Nulls | Keys | Values | Cause |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for result in results:
        cause = str(result["cause"]).replace("|", "\\|")
        lines.append(
            f"| {result['table']} | {result['status']} | {result['sql_rows']} | {result['csv_rows']} | "
            f"{result['column_status']} | {result['type_status']} | {result['null_status']} | "
            f"{result['key_status']} | {result['value_status']} | {cause} |"
        )

    lines.extend(["", "## Live SQL schemas and keys", ""])
    if not connection_info:
        lines.append("NOT VERIFIED because SQL Server connectivity was unavailable.")
    else:
        for name in EXPECTED_TABLES:
            data = tables[name]
            lines.extend([f"### {args.schema}.{name}", ""])
            if data.error:
                lines.extend([f"NOT VERIFIED: {data.error}", ""])
                continue
            lines.append(f"Primary key: `{', '.join(data.primary_key) if data.primary_key else 'NOT DISCOVERED'}`")
            if data.unique_keys:
                lines.append("Unique keys: " + "; ".join(f"`{idx}({', '.join(cols)})`" for idx, cols in data.unique_keys))
            else:
                lines.append("Unique keys: none beyond the primary key")
            lines.extend(["", "| Column | SQL type | Nullable |", "|---|---|---:|"])
            for column in data.columns:
                lines.append(f"| {column.name} | {column.display_type} | {'YES' if column.nullable else 'NO'} |")
            lines.append("")

    lines.extend(["## Per-table discrepancies", ""])
    for result in results:
        lines.extend([f"### {result['table']}: {result['status']}", "", f"Cause: {result['cause'] or 'not determined'}"])
        for label, field_name in (
            ("Missing SQL columns in CSV", "missing_columns"),
            ("Extra CSV columns", "extra_columns"),
            ("Type issues", "type_issues"),
            ("NULL/blank issues", "null_issues"),
            ("Duplicate issues", "duplicate_issues"),
            ("Key/reference issues", "key_issues"),
            ("Examples", "examples"),
            ("Limitations", "limitations"),
            ("Error", "error"),
        ):
            if result[field_name]:
                lines.append(f"- {label}: `{str(result[field_name]).replace('`', "'")}`")
        lines.append("")

    lines.extend(
        [
            "## Rerun",
            "",
            "From the repository root, using the configured `.env` values:",
            "",
            "```powershell",
            ".\\.venv\\Scripts\\python.exe tests\\compare_powerbi_csv_sql.py",
            "```",
            "",
            "To audit another export directory without changing any source files:",
            "",
            "```powershell",
            ".\\.venv\\Scripts\\python.exe tests\\compare_powerbi_csv_sql.py --csv-dir \"path\\to\\csv_exports\"",
            "```",
            "",
            "Exit code 0 means all 13 tables passed, 1 means at least one failed, and 2 means at least one comparison was not verified.",
            "",
        ]
    )
    args.report_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    tables = {name: TableData(name=name) for name in EXPECTED_TABLES}
    connection_info: dict[str, str] | None = None
    connection_error = ""
    connection = None
    try:
        connection, connection_info = connect(args)
        tables = discover_tables(connection, args.schema)
    except Exception as exc:  # a connectivity/metadata failure must still produce an audit report
        connection_error = f"{type(exc).__name__}: {exc}"
        for data in tables.values():
            data.error = connection_error
    finally:
        if connection is not None:
            connection.rollback()
            connection.close()

    csv_files = find_csvs(args.csv_dir)
    for name, data in tables.items():
        path = csv_files.get(name.casefold())
        if path is None:
            continue
        data.csv_path = path
        try:
            data.csv_columns, data.csv_rows = read_csv_data(path)
        except Exception as exc:
            data.error = (data.error + "; " if data.error else "") + f"CSV error: {type(exc).__name__}: {exc}"

    results = [compare_table(tables[name], args) for name in EXPECTED_TABLES]
    if connection_info:
        enhance_reference_checks(tables, results)
    write_reports(args, results, tables, connection_info, connection_error)
    print(f"Wrote {args.report_csv}")
    print(f"Wrote {args.report_md}")
    for result in results:
        print(f"{result['table']}: {result['status']} - {result['cause'] or result['error']}")
    if any(result["status"] == "FAIL" for result in results):
        return 1
    if any(result["status"] == "NOT VERIFIED" for result in results):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
