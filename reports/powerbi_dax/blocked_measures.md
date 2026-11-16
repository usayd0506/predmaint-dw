# Blocked / pending metrics

Items that are **not** included as real calculations in `create_missing_measures.csx` because source data or business assumptions are insufficient.

## Fully blocked (no inventing DAX)

| Metric | Page | Reason | Recommendation |
|---|---|---|---|
| Estimated Cost Avoided (non-blank) | Executive | Existing measure is `BLANK()`. No warehouse column, threshold table, or documented cost-avoidance model (failure cost × prevented failures, etc.). | Keep `BLANK()` until a documented estimation model and source table exist. |
| SHAP summary | Model Performance | Wireframe requires `shap_summary.png` image, not a DAX measure. | Add image visual in the report; optional `ml/shap_analysis.py` output. |

## Pending supporting objects (not measure-blocked if workaround used)

| Need | Page | Status | Notes |
|---|---|---|---|
| Health Index Bin / Health Index Bin Sort | Fleet Health | No calculated columns in TMDL | Optional script: `create_health_index_bin_columns.csx`. Distribution visual needs these columns. |
| Alert → Rule bridge table | Alerts | `FactAlert[rules_fired]` is comma-delimited (`R3,R5,R6`) | `Rule Hits` uses `CONTAINSSTRING` against `RuleCatalog`. Prefer a future `BridgeAlertRule` mart for cleaner counts. |
| Method metrics dimension purity | Smart Scheduling | Travel km / fitness stored under `DimModel` GA/GREEDY via gold pipeline | Create measures from `FactModelMetric` with documented smell, **or** add `mart.FactMethodMetric` keyed to `DimMethod`. Labor cost correction uses `FactSchedule` + `DimMethod` instead. |

## Assumptions that must remain explicit (measures created, not blocked)

| Measure | Assumption |
|---|---|
| Corrective Cost % | Corrective = `Repair` + `Replacement`; preventive = `Inspection` |
| Expected Failures 30d | Sum of `failure_prob_30` for the selected/default ML model (expected count) |
| Engines RUL under 30 / Prob over 70% | Thresholds match expert rules R1/R2 in `ml/run_gold.py` |
| Default ML model | XGBoost when no single ML model is selected (`ml/models.py` health path) |
| NASA Improvement % | Lower NASA score is better; improvement = `(LR − XGB) / LR` using `test_nasa_score` |
| Technician Utilization % | Denominator = all technicians × `max_hours_per_week` × weeks from `MIN/MAX(FactSchedule[slot_start])` for GA (not DimDate calendar); numerator = GA `slot_hours` |
| Travel km Saved / Fitness Improvement % | Read from `FactModelMetric` rows labeled GA/GREEDY (pipeline quirk) until a method-metric mart exists |

## Data observations that limit KPI drama (not blockers)

| Observation | Impact |
|---|---|
| `Engines Never Maintained` = 0 in current SQL | Measure is valid; KPI will show 0 |
| FactEngineHealth has 100 engines (test split), not 200 DimEngine members | `Total Engines` counts health-fact engines — correct for the dashboard snapshot |
| Confusion TP/FP/FN/TN exist as metric rows | Confusion matrix can use real counts; do **not** reverse-engineer from rounded % |
| CV metrics (`cv_*`) vs test metrics (`test_*`) | Model Performance KPIs use **test_** metrics only |
| Classifier vs regressor | RMSE/NASA = regression; Precision/Recall/F1/TP… = classification at RUL≤30 / prob≥0.5 |

## Recommended mart extension (future, out of scope for this script pack)

```text
mart.FactMethodMetric (run_key, method_key, metric_name, metric_value)
```

Populate from `docs/gold_results/ga_vs_greedy.csv` / scheduler comparison dict, and stop inserting GA/GREEDY into `gold.model_metrics` / `DimModel`.
