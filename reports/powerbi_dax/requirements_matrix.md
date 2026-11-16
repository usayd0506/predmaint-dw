# DAX requirements matrix

**Wireframes examined:** `powerbi/PredMaint_Fixed_Project_New/PredMaint Report Wireframes.pdf` (7 pages, text extracted).  
**Semantic model:** `PredMaint_Fixed_Project_New` TMDL.  
**Create script:** `create_missing_measures.csx`  
**Corrections script (opt-in):** `proposed_measure_corrections.csx`

Status legend: **Existing** | **New** | **Correction-needed** | **Blocked**

---

## Page 1 — Executive Summary

| Visual | Measure | Status | DAX / formula | Sources | Dependencies | Folder | Format | Assumptions | Validation |
|---|---|---|---|---|---|---|---|---|---|
| KPI | Total Engines | Existing | `DISTINCTCOUNT(FactEngineHealth[engine_key])` | FactEngineHealth | — | — | `0` | One health row per test engine per run | Expect 100 |
| KPI | Critical Engines | Existing | Total Engines where risk=`Critical` | FactEngineHealth | Total Engines | — | `0` | Risk values Critical/Warning/Healthy | Expect 20 |
| KPI | At-Risk % | Existing | (Critical+Warning)/Total | FactEngineHealth | Total Engines | — | `%` | At-risk = Critical ∪ Warning | Expect 35% |
| KPI | Estimated Cost Avoided | Existing / Blocked | `BLANK()` | — | — | — | `0` | No estimation model | Stays blank |
| KPI | Labor Cost Saving % | Correction-needed | `(Greedy−GA)/Greedy` | FactSchedule via labor measures | GA/Greedy Labor Cost | 01/06 | `%` | Lower labor better | ~32.5% after correction |
| Risk Level Mix | Total Engines | Existing | by `risk_level` | FactEngineHealth | — | — | — | — | Stacks to 100 |
| Critical by Plant | Critical Engines | Existing | by DimPlant | FactEngineHealth→DimEngine→DimPlant | — | — | — | Plant via engine | Bars sum to Critical |
| Alerts by Severity | Total Alerts | Existing | by severity | FactAlert | — | — | — | — | Sum 43 |
| Headline | Headline Executive | Existing | text card | measures | Critical, Total | — | text | — | Readable sentence |
| Top 5 Lowest RUL | Min Predicted RUL, Lowest RUL Rank | Existing (+ soft correction) | MIN / RANKX | FactRULPrediction, DimEngine, DimPlant | Min Predicted RUL | — | — | Visual filters XGBoost | 5 rows, ascending RUL |

---

## Page 2 — Fleet Health & Risk

| Visual | Measure / column | Status | DAX / formula | Sources | Dependencies | Folder | Format | Assumptions | Validation |
|---|---|---|---|---|---|---|---|---|---|
| KPI | Avg Health Index | Existing | `AVERAGE(health_index)` | FactEngineHealth | — | — | `0.0` | — | ~30.8 |
| KPI | Avg Cycles Run | New | `AVERAGE(cycles_run)` | FactEngineHealth | — | 02 Fleet Health | `#,0.0` | — | Match SQL AVG |
| KPI | Avg Days Since Maintenance | New | AVERAGEX datediff(last_maintenance, DimDate[full_date]) | FactEngineHealth, DimDate | — | 02 | `#,0.0` | Snapshot = health date_key | ~35.3 days |
| KPI | Engines Never Maintained | New | Total Engines where last_maintenance blank | FactEngineHealth | Total Engines | 02 | `0` | — | 0 currently |
| Plant Risk Map | Critical Engines | Existing | sized by plant | DimPlant lat/long | Critical Engines | — | — | Map category set | 5 plants |
| Risk by Plant | Total Engines | Existing | stacked risk × plant | FactEngineHealth | — | — | — | — | — |
| Health Index Distribution | Total Engines | New columns needed | by Health Index Bin | FactEngineHealth | Bin columns | — | — | Bins 0-19…80-100 | Optional column script |
| Cycles vs Health | (columns) | Existing columns | scatter cycles × health | FactEngineHealth | — | — | — | One point per engine | 100 points |

Calculated columns (separate script): `Health Index Bin`, `Health Index Bin Sort`.

---

## Page 3 — Engine Watchlist

| Visual | Measure | Status | DAX / formula | Sources | Dependencies | Folder | Format | Assumptions | Validation |
|---|---|---|---|---|---|---|---|---|---|
| KPI | Engines RUL under 30 | New | DISTINCTCOUNT engines with predicted_rul &lt; 30 | FactRULPrediction, DimModel | Selected ML model | 03 | `0` | Default XGBoost; threshold 30 | Match SQL for XGB |
| KPI | Engines Prob over 70% | New | DISTINCTCOUNT failure_prob_30 &gt; 0.7 | FactRULPrediction | Selected ML model | 03 | `0` | Threshold 0.7 (rule R2) | Match SQL |
| KPI | Expected Failures 30d | New | `SUM(failure_prob_30)` | FactRULPrediction | Selected ML model | 03 | `#,0.00` | Expected count from probs | Between 0 and engine count |
| KPI | Avg Predicted RUL | New | AVERAGE predicted_rul | FactRULPrediction | Selected ML model | 03 | `#,0.0` | Default XGBoost | Match SQL |
| Watchlist table | Min Predicted RUL | Existing | — | FactRULPrediction | — | — | — | Slicer Model | Sorted ascending |
| RUL vs Prob scatter | (columns) | — | predicted_rul, failure_prob_30 | FactRULPrediction | — | — | — | One model | — |
| 10 lowest RUL | Min Predicted RUL | Existing | — | FactRULPrediction | — | — | — | — | Top 10 |
| Fail prob by plant | Avg Failure Prob 30d | New | AVERAGE failure_prob_30 | FactRULPrediction | Selected ML model | 03 | `%` | Via DimEngine→DimPlant | — |

**Model selection:** if exactly one of {XGBoost, LinearRegression} is filtered, use it; else XGBoost. GA/GREEDY DimModel members excluded.

---

## Page 4 — Alerts & Rules

| Visual | Measure | Status | DAX / formula | Sources | Dependencies | Folder | Format | Assumptions | Validation |
|---|---|---|---|---|---|---|---|---|---|
| KPI | Total Alerts | Existing | COUNTROWS(FactAlert) | FactAlert | — | — | `0` | — | 43 |
| KPI | Critical Alerts | New | Total Alerts where severity=`Critical` | FactAlert | Total Alerts | 04 | `0` | — | 20 |
| KPI | Engines With Alert | Existing | DISTINCTCOUNT engine_key | FactAlert | — | — | `0` | — | ≤43 |
| KPI | Alert Coverage % | New | Engines With Alert / Total Engines | FactAlert, FactEngineHealth | both | 04 | `%` | Cross-fact via measures only | — |
| Alerts by Severity | Total Alerts | Existing | — | FactAlert | — | — | — | Critical/High/Medium | 20/15/8 |
| Rule Hits R1–R6 | Rule Hits | New | COUNTROWS where rules_fired contains RuleCatalog[rule_id] | FactAlert, RuleCatalog | — | 04 | `0` | Delimited text match | Sum ≥ Total Alerts (multi-hit) |
| Recommended Actions | Total Alerts | Existing | by recommended_action | FactAlert | — | — | — | — | — |
| Alert Details | (columns) | — | — | FactAlert | — | — | — | — | — |
| Alerts by Plant | Total Alerts | Existing | via DimEngine→DimPlant | FactAlert | — | — | — | — | — |

---

## Page 5 — Maintenance & Cost

| Visual | Measure | Status | DAX / formula | Sources | Dependencies | Folder | Format | Assumptions | Validation |
|---|---|---|---|---|---|---|---|---|---|
| KPI | Total Maintenance Cost | Existing | SUM(maintenance_cost) | FactMaintenance | — | — | currency | — | Match SQL SUM |
| KPI | Work Orders | New | DISTINCTCOUNT(work_order_id) | FactMaintenance | — | 05 | `0` | Unique WO grain | 835 |
| KPI | Corrective Cost % | New | Cost of Repair+Replacement / Total | FactMaintenance | Total Maintenance Cost | 05 | `%` | Corrective = Repair∪Replacement | — |
| KPI | Avg Cost per Work Order | New | Total Cost / Work Orders | FactMaintenance | both | 05 | `$#,0.00` | — | — |
| KPI | Total Maintenance Hours | New | SUM(duration_hours) | FactMaintenance | — | 05 | `#,0.0` | — | Match SQL |
| Cost by month × type | Total Maintenance Cost | Existing | DimDate year_month × type | FactMaintenance, DimDate | — | — | — | Types: Inspection/Repair/Replacement | — |
| Avg cost per type | Avg Cost per Work Order | New | by maintenance_type | FactMaintenance | — | — | — | — | — |
| Top 10 technicians | Total Maintenance Cost | Existing | by DimTechnician | FactMaintenance | — | — | — | — | — |
| Plant × type matrix | Total Maintenance Cost | Existing | plant via engine | FactMaintenance | — | — | — | — | — |

---

## Page 6 — Smart Scheduling

| Visual | Measure | Status | DAX / formula | Sources | Dependencies | Folder | Format | Assumptions | Validation |
|---|---|---|---|---|---|---|---|---|---|
| KPI | Labor Cost Saving % | Correction-needed | see page 1 | FactSchedule | GA/Greedy Labor Cost | — | `%` | — | ~32.5% |
| KPI | Travel km Saved | New | Greedy Travel − GA Travel | FactModelMetric (GA/GREEDY) | helpers | 06 | `#,0.0` | Method metrics under DimModel labels | ~164.4 km |
| KPI | Fitness Improvement % | New | (Greedy−GA Fitness)/Greedy | FactModelMetric | helpers | 06 | `%` | Lower fitness better | ~24.9% |
| KPI | Technician Utilization % | New | GA hours / (Σ max_hours × weeks) | FactSchedule, DimTechnician, DimDate | Scheduled Hours | 06 | `%` | All 20 techs; weeks from GA date span | ~15% if 1 week |
| GA vs Greedy | GA Labor Cost, Greedy Labor Cost | Correction-needed | SUM est_cost by DimMethod | FactSchedule, DimMethod | — | 06 | currency | Both methods in FactSchedule (30+30) | 2355 vs 3490 |
| GA Convergence | (columns) | Existing table | generation, best_fitness | GA_Convergence | — | — | — | CSV-backed | Line chart |
| Hours by technician | Scheduled Hours | New | SUM slot_hours | FactSchedule | — | 06 | `#,0.0` | Slice method in visual | — |
| Tech × date matrix | Scheduled Jobs | New | SUM assignment_count | FactSchedule | — | 06 | `0` | — | — |

Helpers created: `GA Travel km`, `Greedy Travel km`, `GA Fitness`, `Greedy Fitness`.

---

## Page 7 — Model Performance

| Visual | Measure | Status | DAX / formula | Sources | Dependencies | Folder | Format | Assumptions | Validation |
|---|---|---|---|---|---|---|---|---|---|
| KPI | XGB RMSE | New | test_rmse_true for XGBoost | FactModelMetric, DimModel | — | 07 | `#,0.000` | Test split only | ~19.463 |
| KPI | LR RMSE | New | test_rmse_true for LinearRegression | FactModelMetric | — | 07 | `#,0.000` | Test split only | ~22.671 |
| KPI | NASA Improvement % | New | (LR NASA − XGB NASA) / LR NASA | FactModelMetric | — | 07 | `%` | Lower NASA better | ~45.1% |
| KPI | Model Recall | New | test_recall; default XGBoost | FactModelMetric | Selected ML model | 07 | `%` | Classification metric | XGB ~0.80 |
| RMSE & NASA by model | Model RMSE, Model NASA Score | New | test_rmse_true / test_nasa_score | FactModelMetric | — | 07 | — | Exclude GA/GREEDY members | 2 models |
| Precision/Recall/F1 | Model Precision, Model Recall, Model F1 | New | test_* metrics | FactModelMetric | — | 07 | `%` | Not CV metrics | — |
| Confusion matrix | TP, FP, FN, TN | New | metric rows tp/fp/fn/tn | FactModelMetric | Selected ML model | 07 | `0` | Real counts, not inferred | XGB: 20/6/5/69 |
| Metrics table | (columns) | — | metric_name × model | FactModelMetric | — | — | — | Filter ML models | — |
| SHAP | — | Blocked (image) | — | — | — | — | — | Not DAX | Image visual |

---

## Coverage summary

| Page | Covered by Existing/New/Correction | Blocked items |
|---|---|---|
| 1 Executive | Yes | Estimated Cost Avoided (non-blank) |
| 2 Fleet Health | Yes (bins via optional column script) | — |
| 3 Watchlist | Yes | — |
| 4 Alerts | Yes (Rule Hits via string match) | Ideal bridge table deferred |
| 5 Maintenance | Yes | — |
| 6 Scheduling | Yes | Prefer future FactMethodMetric |
| 7 Model Performance | Yes | SHAP image |

**All seven dashboard pages have measure coverage** for every DAX-capable KPI in the wireframes.
