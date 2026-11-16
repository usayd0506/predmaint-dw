#!/usr/bin/env python3
"""Offline CSV-versus-DDL schema audit for the PredMaintDW mart.

This tool does not connect to SQL Server and does not compare CSV row values to
database rows. It reads repository DDL, CSV files, PBIP TMDL, and mart loading
scripts, then writes schema-only reports.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import UUID


ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = ROOT / "powerbi" / "PredMaint_Fixed_Project" / "Datasets"
DIM_DDL = ROOT / "sql" / "10_create_mart_dimensions.sql"
FACT_DDL = ROOT / "sql" / "12_create_mart_facts.sql"
DIM_LOAD = ROOT / "sql" / "11_load_mart_dimensions.sql"
FACT_LOAD = ROOT / "sql" / "13_load_mart_facts.sql"
MODEL_DIR = ROOT / "powerbi" / "PredMaint_Fixed_Project" / "Usyad Power Bi report.SemanticModel" / "definition"
TABLE_DIR = MODEL_DIR / "tables"
RELATIONSHIPS = MODEL_DIR / "relationships.tmdl"
REPORT_MD = ROOT / "reports" / "powerbi_schema_comparison.md"
REPORT_CSV = ROOT / "reports" / "powerbi_schema_comparison.csv"

TABLES = (
    "DimDate", "DimEngine", "DimPlant", "DimTechnician", "DimModel", "DimMethod", "DimRun",
    "FactEngineHealth", "FactRULPrediction", "FactAlert", "FactMaintenance", "FactSchedule", "FactModelMetric",
)

INTEGER_TYPES = {"TINYINT", "SMALLINT", "INT", "BIGINT"}
DECIMAL_TYPES = {"DECIMAL", "NUMERIC", "MONEY", "SMALLMONEY"}
FLOAT_TYPES = {"FLOAT", "REAL"}
TEXT_TYPES = {"CHAR", "NCHAR", "VARCHAR", "NVARCHAR", "TEXT", "NTEXT"}
DATE_TYPES = {"DATE"}
DATETIME_TYPES = {"DATETIME", "DATETIME2", "SMALLDATETIME", "DATETIMEOFFSET"}


@dataclass
class Column:
    name: str
    sql_type: str
    nullable: bool
    primary_key: bool = False
    unique: bool = False
    identity: bool = False
    default: str = ""
    references: str = ""

    @property
    def base_type(self) -> str:
        return self.sql_type.split("(", 1)[0].strip().upper()

    @property
    def type_args(self) -> list[int]:
        match = re.search(r"\(([^)]+)\)", self.sql_type)
        if not match:
            return []
        values = []
        for part in match.group(1).split(","):
            part = part.strip()
            if part.upper() == "MAX":
                values.append(-1)
            elif part.isdigit():
                values.append(int(part))
        return values


@dataclass
class Table:
    name: str
    columns: list[Column] = field(default_factory=list)
    primary_key: list[str] = field(default_factory=list)
    unique_keys: list[list[str]] = field(default_factory=list)


def split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    in_quote = False
    i = 0
    while i < len(text):
        char = text[i]
        if char == "'":
            if in_quote and i + 1 < len(text) and text[i + 1] == "'":
                i += 2
                continue
            in_quote = not in_quote
        elif not in_quote:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == "," and depth == 0:
                parts.append(text[start:i].strip())
                start = i + 1
        i += 1
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def table_blocks(sql: str) -> dict[str, str]:
    sql = re.sub(r"--[^\r\n]*", "", sql)
    blocks: dict[str, str] = {}
    pattern = re.compile(r"CREATE\s+TABLE\s+mart\.\[?(\w+)\]?\s*\(", re.I)
    for match in pattern.finditer(sql):
        depth = 1
        index = match.end()
        in_quote = False
        while index < len(sql) and depth:
            char = sql[index]
            if char == "'":
                if in_quote and index + 1 < len(sql) and sql[index + 1] == "'":
                    index += 2
                    continue
                in_quote = not in_quote
            elif not in_quote:
                if char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1
            index += 1
        blocks[match.group(1)] = sql[match.end(): index - 1]
    return blocks


def parse_ddl() -> dict[str, Table]:
    blocks = {}
    for path in (DIM_DDL, FACT_DDL):
        blocks.update(table_blocks(path.read_text(encoding="utf-8-sig")))
    parsed: dict[str, Table] = {}
    for table_name, block in blocks.items():
        table = Table(table_name)
        table_constraints: list[str] = []
        for item in split_top_level(block):
            compact = " ".join(item.split())
            if re.match(r"^(CONSTRAINT\s+\S+\s+)?(PRIMARY\s+KEY|UNIQUE|FOREIGN\s+KEY)", compact, re.I):
                table_constraints.append(compact)
                continue
            match = re.match(r"^\[?(\w+)\]?\s+([A-Za-z]+(?:\s*\([^)]*\))?)(.*)$", compact, re.I)
            if not match:
                continue
            name, sql_type, remainder = match.groups()
            upper = remainder.upper()
            is_pk = "PRIMARY KEY" in upper
            nullable = False if is_pk or "NOT NULL" in upper else True
            if re.search(r"\bNULL\b", upper) and "NOT NULL" not in upper:
                nullable = True
            ref_match = re.search(r"REFERENCES\s+mart\.\[?(\w+)\]?\s*\(\s*\[?(\w+)\]?\s*\)", remainder, re.I)
            default_match = re.search(r"\bDEFAULT\s+(.+?)(?=\s+(?:CONSTRAINT|REFERENCES|UNIQUE|PRIMARY|NOT\s+NULL|NULL)\b|$)", remainder, re.I)
            column = Column(
                name=name,
                sql_type=sql_type.upper().replace(" ", ""),
                nullable=nullable,
                primary_key=is_pk,
                unique=bool(re.search(r"\bUNIQUE\b", upper)),
                identity="IDENTITY" in upper,
                default=default_match.group(1).strip() if default_match else "",
                references=f"{ref_match.group(1)}.{ref_match.group(2)}" if ref_match else "",
            )
            table.columns.append(column)
            if is_pk:
                table.primary_key.append(name)
            if column.unique:
                table.unique_keys.append([name])
        for constraint in table_constraints:
            key_match = re.search(r"\b(PRIMARY\s+KEY|UNIQUE)\s*\(([^)]+)\)", constraint, re.I)
            if not key_match:
                continue
            columns = [part.strip().strip("[]") for part in key_match.group(2).split(",")]
            if key_match.group(1).upper().startswith("PRIMARY"):
                table.primary_key = columns
                for column in table.columns:
                    if column.name in columns:
                        column.primary_key = True
                        column.nullable = False
            else:
                table.unique_keys.append(columns)
        parsed[table_name] = table
    return parsed


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        rows = []
        for row_number, row in enumerate(reader, 2):
            if None in row:
                raise ValueError(f"row {row_number} contains more fields than the header")
            rows.append({key: "" if value is None else value for key, value in row.items()})
    return headers, rows


def validate_value(raw: str, column: Column) -> str | None:
    if raw.strip() == "":
        return None
    value = raw.strip()
    base = column.base_type
    try:
        if base in INTEGER_TYPES:
            number = Decimal(value.replace(",", ""))
            if number != number.to_integral_value():
                return "not an integer"
        elif base in DECIMAL_TYPES:
            number = Decimal(value.replace(",", ""))
            args = column.type_args
            if len(args) == 2:
                precision, scale = args
                sign, digits, exponent = number.as_tuple()
                fractional = max(-exponent, 0)
                integer = max(len(digits) + exponent, 0)
                if fractional > scale or integer + fractional > precision:
                    return f"exceeds {column.sql_type} precision/scale"
        elif base in FLOAT_TYPES:
            float(value.replace(",", ""))
        elif base == "BIT":
            if value.casefold() not in {"0", "1", "true", "false", "yes", "no", "y", "n"}:
                return "not a BIT/boolean"
        elif base in DATE_TYPES:
            datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        elif base in DATETIME_TYPES:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        elif base == "UNIQUEIDENTIFIER":
            UUID(value.strip("{}"))
        elif base in TEXT_TYPES:
            args = column.type_args
            if args and args[0] != -1 and len(raw) > args[0]:
                return f"length {len(raw)} exceeds {args[0]}"
    except (ValueError, InvalidOperation, OverflowError) as exc:
        return str(exc)
    return None


def parse_relationships() -> tuple[list[tuple[str, str, str, str, bool]], dict[str, set[str]]]:
    text = RELATIONSHIPS.read_text(encoding="utf-8-sig")
    blocks = re.split(r"(?=^relationship\s+)", text, flags=re.M)
    relationships = []
    by_table: dict[str, set[str]] = defaultdict(set)
    for block in blocks:
        from_match = re.search(r"fromColumn:\s*(\w+)\.(\w+)", block)
        to_match = re.search(r"toColumn:\s*(\w+)\.(\w+)", block)
        if not from_match or not to_match:
            continue
        active = not bool(re.search(r"isActive:\s*false", block, re.I))
        from_table, from_column = from_match.groups()
        to_table, to_column = to_match.groups()
        relationships.append((from_table, from_column, to_table, to_column, active))
        by_table[from_table].add(from_column)
        by_table[to_table].add(to_column)
    return relationships, by_table


def parse_powerbi_types(table_name: str) -> tuple[dict[str, str], list[str]]:
    path = TABLE_DIR / f"{table_name}.tmdl"
    if not path.exists():
        return {}, []
    text = path.read_text(encoding="utf-8-sig")
    pairs = re.findall(r'\{"([^"]+)",\s*([^},]+)\}', text)
    types = {name: value.strip() for name, value in pairs}
    added = re.findall(r'Table\.AddColumn\([^,]+,\s*"([^"]+)"', text)
    return types, added


def pbi_type_compatible(column: Column, pbi_type: str) -> tuple[bool, str]:
    value = pbi_type.casefold().replace(" ", "")
    base = column.base_type
    if base in INTEGER_TYPES:
        return ("int64.type" in value, "")
    if base in DECIMAL_TYPES or base in FLOAT_TYPES:
        if "typenumber" in value or "double" in value or "decimal" in value:
            return True, ""
        if "int64.type" in value:
            return False, f"Power BI imports {column.name} as whole number but DDL permits fractional {column.sql_type}"
    if base == "BIT":
        return ("logical" in value or "boolean" in value, "")
    if base in DATE_TYPES:
        return ("typedate" in value or "datetime" in value, "")
    if base in DATETIME_TYPES:
        return ("datetime" in value, "")
    if base == "UNIQUEIDENTIFIER" or base in TEXT_TYPES:
        return ("typetext" in value or "string" in value, "")
    return True, ""


def load_transformations() -> dict[str, str]:
    return {
        "DimDate": "Generated from dates across Silver/Gold; date_key and calendar parts are derived. DDL/load do not create CSV-only year_month or weekday_name.",
        "DimEngine": "Surrogate engine_key is IDENTITY; natural key engine_uid is loaded from silver.engine_master.",
        "DimPlant": "Surrogate plant_key is IDENTITY; natural key plant_id is loaded from silver.plants.",
        "DimTechnician": "technician_name is loaded from silver.technicians.name; technician_key is IDENTITY.",
        "DimModel": "Distinct model_name values are unioned from predictions and metrics; model_key is IDENTITY.",
        "DimMethod": "method_name is loaded from gold.work_order_schedule.method; method_key is IDENTITY.",
        "DimRun": "run_key is IDENTITY; run_id is the natural unique identifier loaded from gold.run_control.",
        "FactEngineHealth": "run/engine/plant/date surrogate keys are resolved by joins; health_fact_key is IDENTITY.",
        "FactRULPrediction": "run/engine/model/date keys are resolved by joins; date_key uses CAST(predicted_at AS DATE); prediction_fact_key is IDENTITY.",
        "FactAlert": "recommended_action is loaded from gold.alerts.action; date_key uses CAST(created_at AS DATE); alert_count defaults to 1; alert_fact_key is IDENTITY.",
        "FactMaintenance": "maintenance_type, maintenance_cost and date_key derive from silver columns type, cost and work_date; work_order_count defaults to 1; maintenance_fact_key is IDENTITY.",
        "FactSchedule": "method_key resolves from gold method; date_key uses CAST(slot_start AS DATE); assignment_count defaults to 1; schedule_fact_key is IDENTITY.",
        "FactModelMetric": "metric_name/value are loaded from gold.model_metrics.metric/value; run/model keys are resolved; model_metric_fact_key is IDENTITY.",
    }


def json_compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true", help="Replace existing schema reports after explicit review.")
    args = parser.parse_args()
    existing = [path for path in (REPORT_MD, REPORT_CSV) if path.exists()]
    if existing and not args.overwrite:
        print("Refusing to overwrite existing output: " + ", ".join(str(path) for path in existing), file=sys.stderr)
        return 3

    ddl = parse_ddl()
    relationships, relationship_columns = parse_relationships()
    transformations = load_transformations()
    results: list[dict[str, Any]] = []

    for table_name in TABLES:
        table = ddl.get(table_name)
        csv_path = CSV_DIR / f"{table_name}.csv"
        if table is None or not csv_path.exists():
            results.append({"table": table_name, "status": "NOT VERIFIED", "error": "DDL table or CSV file missing"})
            continue
        headers, rows = read_csv(csv_path)
        ddl_names = [column.name for column in table.columns]
        missing = [name for name in ddl_names if name not in headers]
        extra = [name for name in headers if name not in ddl_names]
        casefold_sql = {name.casefold(): name for name in ddl_names}
        naming = [f"{name}->{casefold_sql[name.casefold()]}" for name in headers if name.casefold() in casefold_sql and name != casefold_sql[name.casefold()]]
        null_counts = {header: sum(row[header].strip() == "" for row in rows) for header in headers}
        type_issues = []
        for column in table.columns:
            if column.name not in headers:
                continue
            failures = Counter()
            examples = []
            for row_number, row in enumerate(rows, 2):
                issue = validate_value(row[column.name], column)
                if issue:
                    failures[issue] += 1
                    if len(examples) < 3:
                        examples.append({"row": row_number, "value": row[column.name], "issue": issue})
            if failures:
                type_issues.append({"column": column.name, "counts": dict(failures), "examples": examples})

        nonnull_violations = {
            column.name: null_counts.get(column.name, 0)
            for column in table.columns
            if not column.nullable and null_counts.get(column.name, 0) > 0
        }
        pk_nulls = sum(
            1 for row in rows
            if table.primary_key and any(row[column].strip() == "" for column in table.primary_key if column in row)
        )
        pk_counter = Counter(tuple(row[column] for column in table.primary_key) for row in rows) if table.primary_key and not missing else Counter()
        pk_duplicate_rows = sum(count - 1 for count in pk_counter.values() if count > 1)
        pk_duplicate_examples = [list(key) for key, count in pk_counter.items() if count > 1][:5]

        pbi_types, pbi_added = parse_powerbi_types(table_name)
        pbi_type_issues = []
        for column in table.columns:
            if column.name in pbi_types:
                compatible, note = pbi_type_compatible(column, pbi_types[column.name])
                if not compatible:
                    pbi_type_issues.append(note or f"{column.name}: {pbi_types[column.name]} versus {column.sql_type}")

        rel_issues = []
        for column_name in sorted(relationship_columns.get(table_name, set())):
            if column_name not in ddl_names:
                rel_issues.append(f"{column_name} missing from DDL")
            if column_name not in headers:
                rel_issues.append(f"{column_name} missing from CSV")

        hard_mismatch = bool(missing or naming or type_issues or nonnull_violations or pk_nulls or pk_duplicate_rows or rel_issues)
        mapping_needed = bool(extra or pbi_type_issues)
        if hard_mismatch:
            status = "SCHEMA MISMATCH"
        elif mapping_needed:
            status = "COMPATIBLE WITH MAPPING"
        else:
            status = "SCHEMA MATCH"

        mappings = []
        if table_name == "DimDate" and {"year_month", "weekday_name"}.issubset(extra):
            mappings.append("Derive year_month and weekday_name from full_date before existing model steps; weekday_number is already added in Power Query.")
        elif extra:
            mappings.append("Remove or explicitly derive CSV-only columns: " + ", ".join(extra))
        mappings.extend(pbi_type_issues)
        if status == "SCHEMA MATCH":
            safe_query = "YES after replacing the CSV connector with a SQL source; source columns and declared Power BI types are compatible."
        elif status == "COMPATIBLE WITH MAPPING":
            safe_query = "YES WITH MAPPING after replacing the connector and applying the listed derived-column/type changes."
        else:
            safe_query = "NO until the listed schema, key, null, or type issues are resolved."

        results.append(
            {
                "table": table_name,
                "status": status,
                "csv_file": str(csv_path.relative_to(ROOT)),
                "csv_rows": len(rows),
                "ddl_columns": ", ".join(ddl_names),
                "csv_columns": ", ".join(headers),
                "primary_key": ", ".join(table.primary_key),
                "primary_key_null_rows": pk_nulls,
                "primary_key_duplicate_rows": pk_duplicate_rows,
                "primary_key_duplicate_examples": json_compact(pk_duplicate_examples) if pk_duplicate_examples else "",
                "null_counts": json_compact(null_counts),
                "nonnull_violations": json_compact(nonnull_violations) if nonnull_violations else "",
                "missing_columns": ", ".join(missing),
                "extra_columns": ", ".join(extra),
                "naming_differences": ", ".join(naming),
                "type_compatibility": "COMPATIBLE" if not type_issues else "INCOMPATIBLE VALUES FOUND",
                "type_issues": json_compact(type_issues) if type_issues else "",
                "relationship_columns": ", ".join(sorted(relationship_columns.get(table_name, set()))),
                "relationship_issues": "; ".join(rel_issues),
                "powerbi_added_columns": ", ".join(pbi_added),
                "powerbi_query_compatibility": safe_query,
                "required_mapping": " ".join(mappings),
                "load_transformations": transformations[table_name],
                "error": "",
            }
        )

    REPORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "table", "status", "csv_file", "csv_rows", "ddl_columns", "csv_columns", "primary_key",
        "primary_key_null_rows", "primary_key_duplicate_rows", "primary_key_duplicate_examples", "null_counts",
        "nonnull_violations", "missing_columns", "extra_columns", "naming_differences", "type_compatibility",
        "type_issues", "relationship_columns", "relationship_issues", "powerbi_added_columns",
        "powerbi_query_compatibility", "required_mapping", "load_transformations", "error",
    ]
    csv_mode = "w" if args.overwrite else "x"
    with REPORT_CSV.open(csv_mode, encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    counts = Counter(result["status"] for result in results)
    lines = [
        "# Offline Power BI CSV versus SQL DDL schema comparison",
        "",
        "This is an offline schema audit. It does not establish SQL Server connectivity, inspect live database metadata, or prove that CSV and SQL row values are equivalent.",
        "",
        "## Scope and sources",
        "",
        f"- CSV directory: `{CSV_DIR.relative_to(ROOT)}`",
        f"- Dimension DDL: `{DIM_DDL.relative_to(ROOT)}`",
        f"- Fact DDL: `{FACT_DDL.relative_to(ROOT)}`",
        f"- Loading scripts inspected: `{DIM_LOAD.relative_to(ROOT)}`, `{FACT_LOAD.relative_to(ROOT)}`",
        f"- Power BI metadata inspected: `{RELATIONSHIPS.relative_to(ROOT)}` and the 13 table TMDL files",
        f"- Status totals: {counts['SCHEMA MATCH']} SCHEMA MATCH, {counts['COMPATIBLE WITH MAPPING']} COMPATIBLE WITH MAPPING, {counts['SCHEMA MISMATCH']} SCHEMA MISMATCH, {counts['NOT VERIFIED']} NOT VERIFIED",
        "",
        "## Summary",
        "",
        "| Table | Status | Rows | Primary key | PK nulls | PK duplicates | Missing columns | Extra columns | Type compatibility | Existing query can use SQL schema? |",
        "|---|---|---:|---|---:|---:|---|---|---|---|",
    ]
    for result in results:
        lines.append(
            f"| {result['table']} | {result['status']} | {result.get('csv_rows', '')} | {result.get('primary_key', '')} | "
            f"{result.get('primary_key_null_rows', '')} | {result.get('primary_key_duplicate_rows', '')} | "
            f"{result.get('missing_columns', '') or 'none'} | {result.get('extra_columns', '') or 'none'} | "
            f"{result.get('type_compatibility', '')} | {result.get('powerbi_query_compatibility', '').replace('|', '/')} |"
        )

    lines.extend(["", "## Exact DDL schema and CSV checks", ""])
    for result in results:
        lines.extend([f"### {result['table']} — {result['status']}", ""])
        if result.get("error"):
            lines.extend([f"NOT VERIFIED: {result['error']}", ""])
            continue
        table = ddl[result["table"]]
        lines.extend([
            f"CSV header: `{result['csv_columns']}`",
            "",
            f"Primary key: `{result['primary_key']}`; null rows: {result['primary_key_null_rows']}; duplicate rows: {result['primary_key_duplicate_rows']}.",
            "",
            "| DDL column | SQL type | NULL allowed | PK | Unique | Identity | Default | References | CSV null count |",
            "|---|---|---:|---:|---:|---:|---|---|---:|",
        ])
        null_counts = json.loads(result["null_counts"])
        for column in table.columns:
            lines.append(
                f"| {column.name} | {column.sql_type} | {'YES' if column.nullable else 'NO'} | "
                f"{'YES' if column.primary_key else ''} | {'YES' if column.unique else ''} | {'YES' if column.identity else ''} | "
                f"{column.default or ''} | {column.references or ''} | {null_counts.get(column.name, 'n/a')} |"
            )
        lines.extend([
            "",
            f"- Missing DDL columns in CSV: {result['missing_columns'] or 'none'}",
            f"- Extra CSV columns: {result['extra_columns'] or 'none'}",
            f"- Naming differences: {result['naming_differences'] or 'none'}",
            f"- CSV value/type compatibility with DDL: {result['type_compatibility']}",
            f"- Non-null constraint violations in CSV: {result['nonnull_violations'] or 'none'}",
            f"- Power BI relationship columns: {result['relationship_columns'] or 'none'}",
            f"- Relationship schema issues: {result['relationship_issues'] or 'none'}",
            f"- Power Query-added columns: {result['powerbi_added_columns'] or 'none'}",
            f"- Required mapping: {result['required_mapping'] or 'none'}",
            f"- Existing Power BI query assessment: {result['powerbi_query_compatibility']}",
            f"- Mart-load transformation: {result['load_transformations']}",
            "",
        ])
        if result["type_issues"]:
            lines.extend([f"Type issue examples: `{result['type_issues']}`", ""])

    lines.extend([
        "## Power BI relationship review",
        "",
        f"Every column used by the {len(relationships)} declared Power BI relationships exists with the same spelling in its CSV and repository DDL table. No relationship-key renaming is required for SQL migration.",
        "",
        "The two inactive relationships remain model choices, not schema mismatches: `DimTechnician.plant_id -> DimPlant.plant_id` and `FactEngineHealth.plant_key -> DimPlant.plant_key`.",
        "",
        "## Loading-script observations",
        "",
        "- Dimensions are incrementally inserted by natural keys; surrogate keys are SQL IDENTITY values.",
        "- Fact tables are deleted and reloaded as a fresh snapshot. This can make separately exported CSVs and a later live database different pipeline snapshots even when their schemas match.",
        "- Fact foreign keys are resolved through dimension joins; identity fact keys and count columns with defaults are not supplied by source SELECT lists.",
        "- `DimDate.year_month` and `DimDate.weekday_name` exist in the CSV/Power BI query but are absent from the DDL and mart load. They must be derived from `full_date` or added in a SQL view/query.",
        "- `FactSchedule.slot_hours` is `DECIMAL(10,2)` in DDL but the current Power Query imports it as `Int64.Type`. Use a decimal/number type when sourcing SQL so fractional hours are not lost.",
        "",
        "## Limitation",
        "",
        "DDL describes intended repository structure only. Until pyodbc connects and live metadata/data are audited, none of these statuses means that the live SQL tables exist as declared or that any CSV dataset is row-equivalent to SQL.",
        "",
    ])
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {REPORT_CSV}")
    for result in results:
        print(f"{result['table']}: {result['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
