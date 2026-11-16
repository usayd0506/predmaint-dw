// Tabular Editor 2 Advanced Scripting
// PredMaintDW — OPTIONAL corrections to EXISTING measures
// Run ONLY after reviewing reports/powerbi_dax/existing_measures_audit.md
// and explicitly approving these changes.
//
// This script OVERWRITES expressions / format strings for named measures.
// It does not create new measures and does not touch relationships.

var tableName = "_Measures";
if (!Model.Tables.Contains(tableName))
{
    Error("Table '" + tableName + "' was not found. Aborting.");
    return;
}

var table = Model.Tables[tableName];
int updated = 0;
int missing = 0;

Action<string, string, string, string> CorrectMeasure = (name, expression, displayFolder, formatString) =>
{
    if (!table.Measures.Contains(name))
    {
        Info("MISSING (cannot correct): " + name);
        missing++;
        return;
    }

    var m = table.Measures[name];
    m.Expression = expression;
    if (!string.IsNullOrEmpty(displayFolder))
        m.DisplayFolder = displayFolder;
    if (!string.IsNullOrEmpty(formatString))
        m.FormatString = formatString;

    Info("UPDATED: " + name);
    updated++;
};

// ---------------------------------------------------------------------------
// 1) GA Labor Cost / Greedy Labor Cost
// OLD: FactModelMetric + DimModel[model_name] = "GA"|"GREEDY"
// WHY WRONG: DimModel is the ML model dimension. Scheduling algorithms belong
//            in DimMethod. Labor figures were only visible under DimModel
//            because gold.model_metrics incorrectly stores method summaries
//            with model_name = GA/GREEDY.
// NEW: SUM(FactSchedule[est_cost]) filtered by DimMethod.
// JUSTIFICATION: scheduler.py sets est_cost = hourly_rate * SLOT_HOURS per
//                assignment. Live SQL confirms SUM(est_cost) matches the
//                FactModelMetric labor_cost scalars exactly (GA 2355.36,
//                GREEDY 3490.64).
// AFFECTED VISUALS: Executive "Labor Cost Saving %"; Smart Scheduling
//                   "GA vs Greedy" and any card using these measures.
// ---------------------------------------------------------------------------

CorrectMeasure(
    "GA Labor Cost",
    @"
CALCULATE (
    SUM ( FactSchedule[est_cost] ),
    DimMethod[method_name] = ""GA""
)
",
    "06 Scheduling",
    "$#,0.00"
);

CorrectMeasure(
    "Greedy Labor Cost",
    @"
CALCULATE (
    SUM ( FactSchedule[est_cost] ),
    DimMethod[method_name] = ""GREEDY""
)
",
    "06 Scheduling",
    "$#,0.00"
);

// ---------------------------------------------------------------------------
// 2) Labor Cost Saving %
// OLD formatString: "0" (integer, not percent)
// Expression is already DIVIDE([Greedy Labor Cost] - [GA Labor Cost], ...)
// Keep expression; fix format and folder only.
// ---------------------------------------------------------------------------

CorrectMeasure(
    "Labor Cost Saving %",
    @"
DIVIDE (
    [Greedy Labor Cost] - [GA Labor Cost],
    [Greedy Labor Cost],
    0
)
",
    "01 Executive\\06 Scheduling",
    "0.00%"
);

// ---------------------------------------------------------------------------
// 3) Min Predicted RUL — optional default to XGBoost when multiple ML models
//    are in scope (prevents accidental averaging/min across models).
// AFFECTED VISUALS: Executive Top 5 (already filters XGBoost); Watchlist
//                   tables/bars that bind [Min Predicted RUL].
// ---------------------------------------------------------------------------

CorrectMeasure(
    "Min Predicted RUL",
    @"
VAR FilteredML =
    CALCULATETABLE (
        VALUES ( DimModel[model_name] ),
        DimModel[model_name] IN { ""XGBoost"", ""LinearRegression"" }
    )
VAR ModelCount = COUNTROWS ( FilteredML )
VAR UseModel =
    IF (
        ModelCount = 1,
        SELECTEDVALUE ( DimModel[model_name] ),
        ""XGBoost""
    )
RETURN
CALCULATE (
    MIN ( FactRULPrediction[predicted_rul] ),
    DimModel[model_name] = UseModel
)
",
    "01 Executive\\03 Watchlist",
    "#,0.0"
);

// ---------------------------------------------------------------------------
// 4) Estimated Cost Avoided — intentionally LEFT AS BLANK()
// No defensible estimation model is documented in the warehouse.
// Do not invent a formula here. See blocked_measures.md.
// ---------------------------------------------------------------------------

Info("---- Correction Summary ----");
Info("Updated: " + updated);
Info("Missing targets: " + missing);
Info("Estimated Cost Avoided was NOT changed (remains BLANK by design).");
