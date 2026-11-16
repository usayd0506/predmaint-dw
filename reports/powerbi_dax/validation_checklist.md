# Validation checklist

Use after running `create_missing_measures.csx` (and optionally `proposed_measure_corrections.csx`) against the open Desktop model. Compare card values to these SQL baselines from `USAYD-PC\SQLEXPRESS` / `PredMaintDW` (verified 2026-11-14).

## Pre-flight

- [ ] PBIP opened from `powerbi/PredMaint_Fixed_Project_New`
- [ ] Home → Refresh succeeded (mart Import + GA_Convergence CSV path reachable)
- [ ] `_Measures` table still present; `Column1` still present
- [ ] No duplicate measure names in `_Measures`
- [ ] Relationships unchanged (inactive plant paths remain inactive)

## Page 1 — Executive Summary

| Check | Expected (approx.) | Pass? |
|---|---|---|
| Total Engines | 100 | |
| Critical Engines | 20 | |
| At-Risk % | 35.00% (35/100) | |
| Estimated Cost Avoided | blank | |
| Labor Cost Saving % (after correction) | ≈ 32.52% = (3490.64−2355.36)/3490.64 | |
| Risk mix totals | Critical 20 + Warning 15 + Healthy 65 = 100 | |
| Alerts by severity | Critical 20, High 15, Medium 8 = 43 | |
| Top 5 Lowest RUL | XGBoost filter on; ascending RUL; 5 engines | |
| Headline Executive | “20 of 100 engines…” | |

## Page 2 — Fleet Health

| Check | Expected | Pass? |
|---|---|---|
| Avg Health Index | ≈ 30.8 | |
| Avg Cycles Run | matches `AVG(cycles_run)` | |
| Avg Days Since Maintenance | ≈ 35.3 | |
| Engines Never Maintained | 0 | |
| Plant map | 5 plants with lat/long; sized by Critical Engines | |
| Health bins (if columns created) | bins sort 0-19…80-100 | |
| Scatter | 100 points | |

SQL helper:

```sql
SELECT AVG(CAST(health_index AS float)), AVG(CAST(cycles_run AS float))
FROM mart.FactEngineHealth;

SELECT AVG(CAST(DATEDIFF(day, h.last_maintenance, d.full_date) AS float))
FROM mart.FactEngineHealth h
JOIN mart.DimDate d ON h.date_key = d.date_key;
```

## Page 3 — Watchlist

| Check | Expected | Pass? |
|---|---|---|
| Default model | XGBoost when Model slicer cleared | |
| Switching Model slicer to LinearRegression changes RUL KPIs | yes | |
| Engines RUL under 30 | DISTINCTCOUNT XGB rows with predicted_rul &lt; 30 | |
| Engines Prob over 70% | DISTINCTCOUNT XGB rows with failure_prob_30 &gt; 0.7 | |
| Expected Failures 30d | SUM(failure_prob_30) for XGB; not &gt; 100 | |
| No double count | 100 engines max per model, not 200 | |

```sql
SELECT COUNT(DISTINCT p.engine_key)
FROM mart.FactRULPrediction p
JOIN mart.DimModel m ON p.model_key = m.model_key
WHERE m.model_name = 'XGBoost' AND p.predicted_rul < 30;
```

## Page 4 — Alerts

| Check | Expected | Pass? |
|---|---|---|
| Total Alerts | 43 | |
| Critical Alerts | 20 | |
| Engines With Alert | DISTINCT engines in FactAlert | |
| Alert Coverage % | Engines With Alert / 100 | |
| Rule Hits R1–R6 | each rule ≥ 0; multi-rule alerts counted in multiple bars | |
| Rule Hits do not invent R7+ | only RuleCatalog members | |

```sql
SELECT severity, COUNT(*) FROM mart.FactAlert GROUP BY severity;
-- Sample multi-rule: SELECT rules_fired FROM mart.FactAlert WHERE rules_fired LIKE '%,%';
```

## Page 5 — Maintenance

| Check | Expected | Pass? |
|---|---|---|
| Work Orders | 835 | |
| Total Maintenance Cost | SQL SUM | |
| Total Maintenance Hours | SQL SUM duration_hours | |
| Corrective Cost % | (Repair+Replacement cost) / total | |
| Month axis | uses DimDate / year_month, not auto date | |
| No cost inflation | cost unchanged when unrelated slicers from other facts applied incorrectly | |

## Page 6 — Scheduling

| Check | Expected | Pass? |
|---|---|---|
| FactSchedule has both methods | GA 30 + GREEDY 30 | |
| GA Labor Cost (corrected) | 2355.36 | |
| Greedy Labor Cost (corrected) | 3490.64 | |
| Travel km Saved | ≈ 164.4 | |
| Fitness Improvement % | ≈ 24.87% | |
| GA Convergence | line over generations from GA_Convergence | |
| Technician Utilization % | GA hours 120 / (20×40×weeks); weeks from schedule date span | |
| Scheduled Hours / Jobs | respond to DimMethod slicer | |

```sql
SELECT m.method_name, SUM(s.est_cost), SUM(s.slot_hours), COUNT(*)
FROM mart.FactSchedule s
JOIN mart.DimMethod m ON s.method_key = m.method_key
GROUP BY m.method_name;
```

## Page 7 — Model Performance

| Check | Expected | Pass? |
|---|---|---|
| XGB RMSE | ≈ 19.463 (`test_rmse_true`) | |
| LR RMSE | ≈ 22.671 | |
| NASA Improvement % | ≈ (1328.47−729.11)/1328.47 ≈ 45.1% | |
| Model Recall (default) | XGB test_recall ≈ 0.80 | |
| Confusion XGB | TP 20, FP 6, FN 5, TN 69 | |
| Charts exclude GA/GREEDY as ML models | filter model_name to LR/XGB | |
| Do not use cv_* for these KPIs | test_* only | |
| SHAP | image visual (not measure) | |

## Regression / safety

- [ ] Re-running `create_missing_measures.csx` reports skips, creates 0 new duplicates
- [ ] Existing 14 measure names still present
- [ ] No relationships added/removed
- [ ] Report pages 2–7 still open (layout shells unchanged)
- [ ] Save PBIP / PBIX backup before and after script run
