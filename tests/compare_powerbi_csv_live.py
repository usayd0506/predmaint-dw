#!/usr/bin/env python3
"""Compare the 13 Power BI CSV exports with live PredMaintDW mart tables.

The SQL connection uses Windows authentication and ApplicationIntent=ReadOnly.
Only SELECT statements and session-level SET statements are issued. No database
objects or source files are modified.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pyodbc

import compare_powerbi_csv_sql as base


ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = ROOT / "powerbi" / "PredMaint_Fixed_Project" / "Datasets"
REPORT_MD = ROOT / "reports" / "powerbi_live_data_comparison.md"
REPORT_CSV = ROOT / "reports" / "powerbi_live_data_comparison.csv"
SERVER = r"USAYD-PC\SQLEXPRESS"
DATABASE = "PredMaintDW"
DRIVER = "ODBC Driver 17 for SQL Server"
FLOAT_ABS_TOL = 1e-9
FLOAT_REL_TOL = 1e-9
SAMPLE_LIMIT = 5


@dataclass
class ForeignKey:
    name: str
    fact_table: str
    fact_columns: list[str]
    dimension_table: str
    dimension_columns: list[str]


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=base.json_value, separators=(",", ":"))


def output_guard() -> None:
    existing = [path for path in (REPORT_MD, REPORT_CSV) if path.exists()]
    if existing:
        raise FileExistsError("Refusing to overwrite existing reports: " + ", ".join(str(path) for path in existing))


def read_csvs(tables: dict[str, base.TableData]) -> None:
    files = base.find_csvs(CSV_DIR)
    for table_name, data in tables.items():
        path = files.get(table_name.casefold())
        if path is None:
            data.error = f"No {table_name}.csv in {CSV_DIR}"
            continue
        data.csv_path = path
        data.csv_columns, data.csv_rows = base.read_csv_data(path)


def normalize_tables(
    tables: dict[str, base.TableData],
) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
]:
    sql_normalized: dict[str, list[dict[str, Any]]] = {}
    csv_normalized: dict[str, list[dict[str, Any]]] = {}
    type_errors: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for table_name, data in tables.items():
        csv_by_fold = {name.casefold(): name for name in data.csv_columns}
        common = [column for column in data.columns if column.name.casefold() in csv_by_fold]
        sql_normalized[table_name] = [
            {column.name: base.normalize_value(row[column.name], column, "sql") for column in common}
            for row in data.sql_rows
        ]
        normalized_rows = []
        for row_number, row in enumerate(data.csv_rows, 2):
            normalized = {}
            for column in common:
                raw = row[csv_by_fold[column.name.casefold()]]
                try:
                    normalized[column.name] = base.normalize_value(raw, column, "csv")
                except (ValueError, TypeError, InvalidOperation, OverflowError) as exc:
                    normalized[column.name] = ("__TYPE_ERROR__", raw)
                    if len(type_errors[table_name]) < SAMPLE_LIMIT:
                        type_errors[table_name].append(
                            {"row": row_number, "column": column.name, "value": raw, "error": str(exc)}
                        )
            normalized_rows.append(normalized)
        csv_normalized[table_name] = normalized_rows
    return sql_normalized, csv_normalized, type_errors


def discover_foreign_keys(connection) -> list[ForeignKey]:
    rows = connection.cursor().execute(
        """
        SELECT fk.name, pt.name, pc.name, rt.name, rc.name, fkc.constraint_column_id
        FROM sys.foreign_keys AS fk
        JOIN sys.foreign_key_columns AS fkc ON fkc.constraint_object_id = fk.object_id
        JOIN sys.tables AS pt ON pt.object_id = fk.parent_object_id
        JOIN sys.schemas AS ps ON ps.schema_id = pt.schema_id
        JOIN sys.columns AS pc
          ON pc.object_id = fkc.parent_object_id AND pc.column_id = fkc.parent_column_id
        JOIN sys.tables AS rt ON rt.object_id = fk.referenced_object_id
        JOIN sys.schemas AS rs ON rs.schema_id = rt.schema_id
        JOIN sys.columns AS rc
          ON rc.object_id = fkc.referenced_object_id AND rc.column_id = fkc.referenced_column_id
        WHERE ps.name = 'mart' AND rs.name = 'mart' AND pt.name LIKE 'Fact%'
        ORDER BY fk.name, fkc.constraint_column_id;
        """
    ).fetchall()
    grouped: dict[tuple[str, str, str], list[tuple[int, str, str]]] = defaultdict(list)
    for fk_name, fact_table, fact_column, dimension_table, dimension_column, ordinal in rows:
        grouped[(str(fk_name), str(fact_table), str(dimension_table))].append(
            (int(ordinal), str(fact_column), str(dimension_column))
        )
    foreign_keys = []
    for (name, fact_table, dimension_table), columns in grouped.items():
        columns.sort()
        foreign_keys.append(
            ForeignKey(
                name=name,
                fact_table=fact_table,
                fact_columns=[item[1] for item in columns],
                dimension_table=dimension_table,
                dimension_columns=[item[2] for item in columns],
            )
        )
    return foreign_keys


def validate_foreign_keys(
    foreign_keys: list[ForeignKey],
    sql_rows: dict[str, list[dict[str, Any]]],
    csv_rows: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    per_table: dict[str, list[dict[str, Any]]] = defaultdict(list)
    details = []
    for fk in foreign_keys:
        sql_dimension_keys = {
            tuple(row[column] for column in fk.dimension_columns)
            for row in sql_rows[fk.dimension_table]
        }
        csv_dimension_keys = {
            tuple(row[column] for column in fk.dimension_columns)
            for row in csv_rows[fk.dimension_table]
        }
        sql_orphans = []
        csv_orphans = []
        for row in sql_rows[fk.fact_table]:
            key = tuple(row[column] for column in fk.fact_columns)
            if any(value is None for value in key):
                continue
            if key not in sql_dimension_keys:
                sql_orphans.append(key)
        for row in csv_rows[fk.fact_table]:
            key = tuple(row[column] for column in fk.fact_columns)
            if any(value is None for value in key):
                continue
            if key not in csv_dimension_keys:
                csv_orphans.append(key)
        detail = {
            "foreign_key": fk.name,
            "fact_columns": fk.fact_columns,
            "dimension": fk.dimension_table,
            "dimension_columns": fk.dimension_columns,
            "sql_orphans": len(sql_orphans),
            "csv_orphans": len(csv_orphans),
            "sql_examples": sql_orphans[:SAMPLE_LIMIT],
            "csv_examples": csv_orphans[:SAMPLE_LIMIT],
        }
        per_table[fk.fact_table].append(detail)
        details.append({"fact_table": fk.fact_table, **detail})
    return per_table, details


def compare_table(
    data: base.TableData,
    sql_rows: list[dict[str, Any]],
    csv_rows: list[dict[str, Any]],
    type_errors: list[dict[str, Any]],
    fk_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    result = {
        "table": data.name,
        "status": "NOT VERIFIED",
        "primary_key": ", ".join(data.primary_key),
        "sql_rows": len(data.sql_rows),
        "csv_rows": len(data.csv_rows),
        "missing_columns": "",
        "extra_columns": "",
        "csv_only_documentation_columns": "",
        "duplicate_sql_keys": "",
        "duplicate_csv_keys": "",
        "sql_only_keys": "",
        "csv_only_keys": "",
        "null_mismatch_columns": "",
        "changed_row_count": "",
        "changed_columns": "",
        "foreign_key_status": "NOT VERIFIED",
        "foreign_key_issues": "",
        "float_tolerance": f"abs={FLOAT_ABS_TOL:g}; rel={FLOAT_REL_TOL:g}",
        "dimdate_derived_columns": "",
        "slot_hours_fractional_sql": "",
        "slot_hours_fractional_csv": "",
        "slot_hours_power_query_risk": "",
        "examples": "",
        "error": data.error,
    }
    if data.error:
        return result

    sql_names = [column.name for column in data.columns]
    csv_names = data.csv_columns
    missing = [name for name in sql_names if name not in csv_names]
    extras = [name for name in csv_names if name not in sql_names]
    allowed_extras = [name for name in extras if data.name == "DimDate" and name in {"year_month", "weekday_name"}]
    unexpected_extras = [name for name in extras if name not in allowed_extras]
    result["missing_columns"] = ", ".join(missing)
    result["extra_columns"] = ", ".join(unexpected_extras)
    result["csv_only_documentation_columns"] = ", ".join(allowed_extras)

    common = [column for column in data.columns if column.name in csv_names]
    null_mismatches = []
    for column in common:
        sql_nulls = sum(row[column.name] is None for row in sql_rows)
        csv_nulls = sum(row[column.name] is None for row in csv_rows)
        if sql_nulls != csv_nulls:
            null_mismatches.append(f"{column.name}: SQL={sql_nulls}, CSV={csv_nulls}")
    result["null_mismatch_columns"] = "; ".join(null_mismatches)

    if not data.primary_key or any(column not in csv_names for column in data.primary_key):
        result["error"] = "Primary key unavailable in CSV"
        return result
    sql_key_counts = Counter(tuple(row[column] for column in data.primary_key) for row in sql_rows)
    csv_key_counts = Counter(tuple(row[column] for column in data.primary_key) for row in csv_rows)
    sql_duplicates = sum(count - 1 for count in sql_key_counts.values() if count > 1)
    csv_duplicates = sum(count - 1 for count in csv_key_counts.values() if count > 1)
    result["duplicate_sql_keys"] = sql_duplicates
    result["duplicate_csv_keys"] = csv_duplicates

    sql_map = {tuple(row[column] for column in data.primary_key): row for row in sql_rows}
    csv_map = {tuple(row[column] for column in data.primary_key): row for row in csv_rows}
    sql_keys = set(sql_map)
    csv_keys = set(csv_map)
    sql_only = sorted(sql_keys - csv_keys, key=repr)
    csv_only = sorted(csv_keys - sql_keys, key=repr)
    result["sql_only_keys"] = len(sql_only)
    result["csv_only_keys"] = len(csv_only)

    changed_rows = 0
    changed_column_counts: Counter[str] = Counter()
    examples = []
    for key in sorted(sql_keys & csv_keys, key=repr):
        differences = {}
        for column in common:
            left = sql_map[key][column.name]
            right = csv_map[key][column.name]
            if not base.values_equal(left, right, column, FLOAT_ABS_TOL, FLOAT_REL_TOL):
                changed_column_counts[column.name] += 1
                differences[column.name] = {"sql": left, "csv": right}
        if differences:
            changed_rows += 1
            if len(examples) < SAMPLE_LIMIT:
                examples.append({"key": key, "differences": differences})
    if sql_only and len(examples) < SAMPLE_LIMIT:
        examples.append({"sql_only_keys": sql_only[:SAMPLE_LIMIT]})
    if csv_only and len(examples) < SAMPLE_LIMIT:
        examples.append({"csv_only_keys": csv_only[:SAMPLE_LIMIT]})
    result["changed_row_count"] = changed_rows
    result["changed_columns"] = compact(dict(changed_column_counts)) if changed_column_counts else ""
    result["examples"] = compact(examples) if examples else ""

    fk_issues = [check for check in fk_checks if check["sql_orphans"] or check["csv_orphans"]]
    result["foreign_key_status"] = "PASS" if not fk_issues else "FAIL"
    result["foreign_key_issues"] = compact(fk_issues) if fk_issues else ""

    dimdate_issue = False
    if data.name == "DimDate":
        year_month_errors = 0
        weekday_errors = 0
        for normalized, raw in zip(csv_rows, data.csv_rows):
            full_date = normalized["full_date"]
            if raw.get("year_month") != full_date.strftime("%Y-%m"):
                year_month_errors += 1
            if raw.get("weekday_name") != full_date.strftime("%A"):
                weekday_errors += 1
        result["dimdate_derived_columns"] = (
            f"CSV-only year_month mismatches={year_month_errors}; "
            f"weekday_name mismatches={weekday_errors}. Compared values use only the seven SQL-backed columns."
        )
        dimdate_issue = bool(year_month_errors or weekday_errors)

    slot_risk = False
    if data.name == "FactSchedule":
        sql_fractional = [row["slot_hours"] for row in sql_rows if row["slot_hours"] is not None and Decimal(row["slot_hours"]) % 1 != 0]
        csv_fractional = [row["slot_hours"] for row in csv_rows if row["slot_hours"] is not None and Decimal(row["slot_hours"]) % 1 != 0]
        result["slot_hours_fractional_sql"] = len(sql_fractional)
        result["slot_hours_fractional_csv"] = len(csv_fractional)
        if sql_fractional:
            result["slot_hours_power_query_risk"] = (
                "FAIL: existing Int64.Type conversion would lose/reject fractional SQL values; "
                f"examples={compact(sql_fractional[:SAMPLE_LIMIT])}"
            )
            slot_risk = True
        else:
            result["slot_hours_power_query_risk"] = (
                "No current fractional values, so the present snapshot is not truncated; "
                "DDL is decimal(10,2), so SQL migration should still use type number."
            )

    failed = any(
        (
            missing,
            unexpected_extras,
            type_errors,
            null_mismatches,
            sql_duplicates,
            csv_duplicates,
            sql_only,
            csv_only,
            changed_rows,
            fk_issues,
            dimdate_issue,
            slot_risk,
            len(data.sql_rows) != len(data.csv_rows),
        )
    )
    result["status"] = "FAIL" if failed else "PASS"
    if type_errors:
        result["error"] = "CSV type errors: " + compact(type_errors)
    return result


FIELDS = (
    "table", "status", "primary_key", "sql_rows", "csv_rows", "missing_columns", "extra_columns",
    "csv_only_documentation_columns", "duplicate_sql_keys", "duplicate_csv_keys", "sql_only_keys",
    "csv_only_keys", "null_mismatch_columns", "changed_row_count", "changed_columns", "foreign_key_status",
    "foreign_key_issues", "float_tolerance", "dimdate_derived_columns", "slot_hours_fractional_sql",
    "slot_hours_fractional_csv", "slot_hours_power_query_risk", "examples", "error",
)


def write_reports(results, tables, connection_info, installed_drivers, foreign_keys, fk_details) -> None:
    REPORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_CSV.open("x", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)

    totals = Counter(result["status"] for result in results)
    lines = [
        "# Live Power BI CSV versus PredMaintDW comparison",
        "",
        f"- Server: `{connection_info['server']}`",
        f"- Database: `{connection_info['database']}`",
        f"- Authentication: Windows (`{connection_info['login']}`)",
        f"- ODBC driver used: `{connection_info['driver']}`",
        f"- Installed ODBC drivers: `{', '.join(installed_drivers)}`",
        f"- CSV directory: `{CSV_DIR.relative_to(ROOT)}`",
        f"- Results: {totals['PASS']} PASS, {totals['FAIL']} FAIL, {totals['NOT VERIFIED']} NOT VERIFIED",
        "",
        "## Method",
        "",
        "Live columns and primary keys were discovered from SQL Server `sys` metadata. Rows were matched by the discovered primary key, independent of source order. Integers, decimals, bits, dates, datetimes, and GUIDs were normalized to SQL-aware values. Decimal fields were compared exactly. SQL `float`/`real` fields used `math.isclose` with absolute and relative tolerances of `1e-9`. No aggregate checksum was used.",
        "",
        "`DimDate` value comparison uses only its seven live SQL columns. CSV-only `year_month` and `weekday_name` were validated separately as derivations of `full_date`.",
        "",
        "## Table summary",
        "",
        "| Table | Status | SQL rows | CSV rows | SQL-only keys | CSV-only keys | Duplicate keys SQL/CSV | NULL mismatches | Changed rows | Foreign keys |",
        "|---|---:|---:|---:|---:|---:|---:|---|---:|---:|",
    ]
    for result in results:
        lines.append(
            f"| {result['table']} | {result['status']} | {result['sql_rows']} | {result['csv_rows']} | "
            f"{result['sql_only_keys']} | {result['csv_only_keys']} | "
            f"{result['duplicate_sql_keys']}/{result['duplicate_csv_keys']} | "
            f"{result['null_mismatch_columns'] or 'none'} | {result['changed_row_count']} | "
            f"{result['foreign_key_status']} |"
        )

    lines.extend(["", "## Per-table findings", ""])
    for result in results:
        lines.extend([f"### {result['table']}: {result['status']}", ""])
        lines.append(f"Primary key: `{result['primary_key']}`. SQL/CSV rows: {result['sql_rows']}/{result['csv_rows']}.")
        if result["csv_only_documentation_columns"]:
            lines.append(f"CSV-only documented columns: `{result['csv_only_documentation_columns']}`.")
        if result["dimdate_derived_columns"]:
            lines.append(result["dimdate_derived_columns"])
        if result["slot_hours_power_query_risk"]:
            lines.append(result["slot_hours_power_query_risk"])
        for label, field in (
            ("Missing columns", "missing_columns"), ("Unexpected extra columns", "extra_columns"),
            ("NULL mismatches", "null_mismatch_columns"), ("Changed columns", "changed_columns"),
            ("Foreign-key issues", "foreign_key_issues"), ("Examples", "examples"), ("Error", "error"),
        ):
            if result[field]:
                lines.append(f"- {label}: `{result[field]}`")
        if result["status"] == "PASS":
            lines.append("No missing/extra primary keys, duplicate keys, NULL mismatches, or changed SQL-backed values were found.")
        lines.append("")

    lines.extend([
        "## Foreign-key validation",
        "",
        f"Discovered and checked {len(foreign_keys)} live fact foreign-key constraints against their referenced dimensions in both SQL and CSV data.",
        "",
        "| Fact | Foreign key | Columns | Dimension | SQL orphans | CSV orphans |",
        "|---|---|---|---|---:|---:|",
    ])
    for detail in fk_details:
        lines.append(
            f"| {detail['fact_table']} | {detail['foreign_key']} | {', '.join(detail['fact_columns'])} | "
            f"{detail['dimension']}({', '.join(detail['dimension_columns'])}) | "
            f"{detail['sql_orphans']} | {detail['csv_orphans']} |"
        )

    lines.extend([
        "",
        "## Power Query scheduling type",
        "",
        next(result["slot_hours_power_query_risk"] for result in results if result["table"] == "FactSchedule"),
        "",
        "## Connectivity diagnosis",
        "",
        "The same ODBC 17 connection failed inside the restricted execution sandbox with SQLSTATE `08001` and SSPI/TLS credential errors. Running the identical SELECT-only connection outside that sandbox succeeded with Windows login shown above. No SQL Server security setting or installed software was changed.",
        "",
        "## Limitation",
        "",
        "PASS means the compared live snapshot and CSV are equal under the documented normalization and floating-point tolerances. It does not prove future ETL runs or later exports will remain equal.",
        "",
    ])
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    try:
        output_guard()
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 3

    installed_drivers = pyodbc.drivers()
    args = SimpleNamespace(server=SERVER, database=DATABASE, driver=DRIVER, schema="mart")
    connection = None
    try:
        connection, connection_info = base.connect(args)
        tables = base.discover_tables(connection, "mart")
        read_csvs(tables)
        sql_rows, csv_rows, type_errors = normalize_tables(tables)
        foreign_keys = discover_foreign_keys(connection)
        fk_per_table, fk_details = validate_foreign_keys(foreign_keys, sql_rows, csv_rows)
        results = [
            compare_table(
                tables[table_name], sql_rows[table_name], csv_rows[table_name],
                type_errors[table_name], fk_per_table.get(table_name, []),
            )
            for table_name in base.EXPECTED_TABLES
        ]
        connection.rollback()
        connection.close()
        connection = None
        write_reports(results, tables, connection_info, installed_drivers, foreign_keys, fk_details)
        print(f"Wrote {REPORT_MD}")
        print(f"Wrote {REPORT_CSV}")
        for result in results:
            print(f"{result['table']}: {result['status']}")
        if any(result["status"] == "FAIL" for result in results):
            return 1
        if any(result["status"] == "NOT VERIFIED" for result in results):
            return 2
        return 0
    except Exception as exc:
        if connection is not None:
            connection.rollback()
            connection.close()
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
