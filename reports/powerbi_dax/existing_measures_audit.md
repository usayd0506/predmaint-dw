# Existing measures audit

**Authoritative model:** `powerbi/PredMaint_Fixed_Project_New/Usyad Power Bi report.SemanticModel`  
**Inspected file:** `definition/tables/_Measures.tmdl`  
**Date inspected:** 2026-11-14

## Project path note

`powerbi/PredMaint_Fixed_Project` does **not** exist in the repository. The working PBIP is:

- `powerbi/PredMaint_Fixed_Project_New/` (SQL Import mart sources, 14 measures)
- `powerbi/PredMaint_Fixed_Project_old/` (empty `_Measures`, no DAX)

This audit treats **PredMaint_Fixed_Project_New** as authoritative. If Power BI Desktop has unsaved local edits beyond the checked-in TMDL, re-export/save the PBIP before running scripts.

## Inventory

| # | Measure | Present | Expression summary | Format | Verdict |
|---|---|---|---|---|---|
| 1 | Total Engines | Yes | `DISTINCTCOUNT(FactEngineHealth[engine_key])` | `0` | OK |
| 2 | Critical Engines | Yes | Total Engines where `risk_level = "Critical"` | `0` | OK |
| 3 | At-Risk % | Yes | Critical+Warning / Total Engines | `0.00%` | OK |
| 4 | Total Alerts | Yes | `COUNTROWS(FactAlert)` | `0` | OK |
| 5 | Engines With Alert | Yes | `DISTINCTCOUNT(FactAlert[engine_key])` | `0` | OK |
| 6 | Avg Health Index | Yes | `AVERAGE(FactEngineHealth[health_index])` | general | OK (prefer `0.0`) |
| 7 | Min Predicted RUL | Yes | `MIN(FactRULPrediction[predicted_rul])` | general | Soft issue — can mix models without filter |
| 8 | Total Maintenance Cost | Yes | `SUM(FactMaintenance[maintenance_cost])` | general | OK (prefer currency) |
| 9 | Estimated Cost Avoided | Yes | `BLANK()` | `0` | Intentional placeholder |
| 10 | Labor Cost Saving % | Yes | `(Greedy − GA) / Greedy` | **`0`** | Format wrong; depends on labor measures |
| 11 | GA Labor Cost | Yes | `AVERAGE(FactModelMetric)` where DimModel=`GA`, metric=`labor_cost` | general | **Correction needed** |
| 12 | Greedy Labor Cost | Yes | Same pattern for `GREEDY` | general | **Correction needed** |
| 13 | Headline Executive | Yes | Text from Critical/Total Engines | text | OK |
| 14 | Lowest RUL Rank | Yes | `RANKX` on Min Predicted RUL ASC dense | `0` | OK if RUL model is filtered |

### Not present (mentioned in prior context)

| Name | Status |
|---|---|
| Avg Cycles Run | **Present** (was the Desktop +1 of three) |
| Avg Days Since Maintenance | **Present** |
| Engines Never Maintained | **Present** |
| Generic measure named `Measure` | **Not present** in current TMDL — nothing to remove |
| `Column1` | Present on `_Measures` — keep as hidden placeholder |

**Existing measure count in semantic model: 17** (re-inspected after Desktop sync)

The three measures that closed the 14→17 gap (now present in saved `_Measures.tmdl`):

| Measure | Notes |
|---|---|
| Avg Cycles Run | `AVERAGE(FactEngineHealth[cycles_run])` |
| Avg Days Since Maintenance | AVERAGEX + LOOKUPVALUE snapshot date; guards `SnapshotDate >= last_maintenance` |
| Engines Never Maintained | `DISTINCTCOUNT` where `last_maintenance` blank |

**PBIP sync:** If Desktop ever shows more measures than the on-disk TMDL, **Save the PBIP** before running Tabular Editor scripts so skip-checks see the full inventory.

## Detailed issues

### 1. GA Labor Cost / Greedy Labor Cost (correction needed)

**Old DAX (GA):**

```dax
CALCULATE(
    AVERAGE(FactModelMetric[metric_value]),
    DimModel[model_name] = "GA",
    FactModelMetric[metric_name] = "labor_cost"
)
```

**Why incorrect semantically**

- `DimModel` is the ML model dimension (`LinearRegression`, `XGBoost`).
- `DimMethod` is the scheduling-algorithm dimension (`GA`, `GREEDY`).
- `ml/run_gold.py` appends scheduling comparison metrics into `gold.model_metrics` with `model_name` = `GA`/`GREEDY`, so DimModel was polluted and the measures return numbers by coincidence.

**Live verification (2026-11-14)**

| Source | GA | GREEDY |
|---|---:|---:|
| FactModelMetric `labor_cost` | 2355.36 | 3490.64 |
| FactSchedule `SUM(est_cost)` | 2355.36 | 3490.64 |

**Proposed DAX** — see `proposed_measure_corrections.csx`:

```dax
CALCULATE(
    SUM(FactSchedule[est_cost]),
    DimMethod[method_name] = "GA"   -- or "GREEDY"
)
```

**Affected visuals:** Executive Labor Saving % card; Smart Scheduling GA vs Greedy comparison.

### 2. Labor Cost Saving % format

Expression is fine once labor measures are corrected. Format string is currently `0` (integer). Should be `0.00%`.

### 3. Min Predicted RUL

Without a DimModel filter, `MIN` can evaluate across both XGBoost and LinearRegression rows (200 prediction rows for 100 engines). Executive Top-5 visual already filters `DimModel[model_name] = "XGBoost"`. Optional correction defaults to XGBoost when more than one ML model is in scope.

### 4. Estimated Cost Avoided

Remains `BLANK()`. No warehouse table or documented business formula supports a defensible avoided-cost estimate. Keep blank; do not invent.

## Objects inspected (not measures)

| Object | Action |
|---|---|
| `_Measures` table | Preserve |
| `Column1` | Preserve |
| Generic `Measure` | Not found — no action |
| Relationships | Preserved; inactive plant paths left inactive |

## Relationships relevant to measure correctness

Active many-to-one paths (single direction):

- All facts → DimEngine; DimEngine → DimPlant
- FactRULPrediction / FactModelMetric → DimModel
- FactSchedule → DimMethod
- Facts → DimDate / DimRun as applicable
- FactMaintenance / FactSchedule → DimTechnician

Inactive (preserve):

- DimTechnician → DimPlant
- FactEngineHealth → DimPlant (direct)

**Implication:** filters on one fact do not automatically propagate to another fact. Shared dimensions (DimEngine, DimDate, DimPlant via engine) are the safe cross-fact filter paths.
