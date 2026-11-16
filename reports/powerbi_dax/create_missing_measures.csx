// Tabular Editor 2 Advanced Scripting
// PredMaintDW — create-only missing measures on _Measures
// Safe to re-run: skips names that already exist anywhere in the model;
// never overwrites expressions.
// Does NOT modify relationships, columns, tables, or existing measure DAX.
//
// Desktop / PBIP sync note (2026-11-14):
// Saved PBIP now contains 17 named measures on _Measures, including
// Avg Cycles Run, Avg Days Since Maintenance, and Engines Never Maintained.
// If Desktop still shows unsaved extras, Save the PBIP before running so
// skip checks see the full inventory.

var tableName = "_Measures";
if (!Model.Tables.Contains(tableName))
{
    Error("Table '" + tableName + "' was not found. Aborting. Create the measure table first.");
    return;
}

var table = Model.Tables[tableName];
int created = 0;
int skipped = 0;
int blocked = 0;

// True if any table already hosts a measure with this name (not only _Measures).
Func<string, bool> MeasureExistsAnywhere = (name) =>
{
    foreach (var t in Model.Tables)
    {
        if (t.Measures.Contains(name))
            return true;
    }
    return false;
};

Action<string, string, string, string> EnsureMeasure = (name, expression, displayFolder, formatString) =>
{
    if (MeasureExistsAnywhere(name))
    {
        Info("SKIP existing (model-wide): " + name);
        skipped++;
        return;
    }

    var m = table.AddMeasure(name, expression);
    if (!string.IsNullOrEmpty(displayFolder))
        m.DisplayFolder = displayFolder;
    if (!string.IsNullOrEmpty(formatString))
        m.FormatString = formatString;

    Info("CREATE: " + name);
    created++;
};

// ---------------------------------------------------------------------------
// Shared ML model selection
// - Respect exactly one selected ML model in {XGBoost, LinearRegression}.
// - If multiple ML models are in scope (KPI / both selected): default XGBoost
//   to avoid double-counting across FactRULPrediction rows.
// - If zero ML models are in scope (e.g. DimModel row is GA/GREEDY on a
//   comparison visual): return BLANK — do NOT fall through to XGBoost.
// ---------------------------------------------------------------------------

string SelectedMlModelPattern = @"
VAR FilteredML =
    CALCULATETABLE (
        VALUES ( DimModel[model_name] ),
        DimModel[model_name] IN { ""XGBoost"", ""LinearRegression"" }
    )
VAR ModelCount = COUNTROWS ( FilteredML )
VAR UseModel =
    IF (
        ModelCount = 0,
        BLANK (),
        IF (
            ModelCount = 1,
            MAXX ( FilteredML, DimModel[model_name] ),
            ""XGBoost""
        )
    )
RETURN
IF (
    ISBLANK ( UseModel ),
    BLANK (),
";

// ========== 02 Fleet Health ==========
// These three may already exist in Desktop/PBIP (the +3 that brought the
// inventory from 14 to 17). Create-only skip is intentional and required.
EnsureMeasure(
    "Avg Cycles Run",
    @"AVERAGE ( FactEngineHealth[cycles_run] )",
    "02 Fleet Health",
    "#,0.0"
);

EnsureMeasure(
    "Avg Days Since Maintenance",
    @"
AVERAGEX (
    FILTER (
        FactEngineHealth,
        NOT ISBLANK ( FactEngineHealth[last_maintenance] )
    ),
    VAR SnapshotDate =
        LOOKUPVALUE (
            DimDate[full_date],
            DimDate[date_key], FactEngineHealth[date_key]
        )
    RETURN
        IF (
            NOT ISBLANK ( SnapshotDate )
                && SnapshotDate >= FactEngineHealth[last_maintenance],
            DATEDIFF (
                FactEngineHealth[last_maintenance],
                SnapshotDate,
                DAY
            )
        )
)
",
    "02 Fleet Health",
    "#,0.0"
);

EnsureMeasure(
    "Engines Never Maintained",
    @"
CALCULATE (
    DISTINCTCOUNT ( FactEngineHealth[engine_key] ),
    ISBLANK ( FactEngineHealth[last_maintenance] )
)
",
    "02 Fleet Health",
    "0"
);

// ========== 03 Watchlist ==========
EnsureMeasure(
    "Avg Predicted RUL",
    SelectedMlModelPattern + @"
CALCULATE (
    AVERAGE ( FactRULPrediction[predicted_rul] ),
    DimModel[model_name] = UseModel
)
)
",
    "03 Watchlist",
    "#,0.0"
);

EnsureMeasure(
    "Avg Failure Prob 30d",
    SelectedMlModelPattern + @"
CALCULATE (
    AVERAGE ( FactRULPrediction[failure_prob_30] ),
    DimModel[model_name] = UseModel
)
)
",
    "03 Watchlist",
    "0.0%"
);

EnsureMeasure(
    "Engines RUL under 30",
    SelectedMlModelPattern + @"
CALCULATE (
    DISTINCTCOUNT ( FactRULPrediction[engine_key] ),
    FactRULPrediction[predicted_rul] < 30,
    DimModel[model_name] = UseModel
)
)
",
    "03 Watchlist",
    "0"
);

EnsureMeasure(
    "Engines Prob over 70%",
    SelectedMlModelPattern + @"
CALCULATE (
    DISTINCTCOUNT ( FactRULPrediction[engine_key] ),
    FactRULPrediction[failure_prob_30] > 0.7,
    DimModel[model_name] = UseModel
)
)
",
    "03 Watchlist",
    "0"
);

EnsureMeasure(
    "Expected Failures 30d",
    SelectedMlModelPattern + @"
CALCULATE (
    SUM ( FactRULPrediction[failure_prob_30] ),
    DimModel[model_name] = UseModel
)
)
",
    "03 Watchlist",
    "#,0.00"
);

// ========== 04 Alerts ==========
EnsureMeasure(
    "Critical Alerts",
    @"
CALCULATE (
    [Total Alerts],
    FactAlert[severity] = ""Critical""
)
",
    "04 Alerts",
    "0"
);

EnsureMeasure(
    "Alert Coverage %",
    @"
DIVIDE ( [Engines With Alert], [Total Engines], 0 )
",
    "04 Alerts",
    "0.00%"
);

// rules_fired is comma-delimited text such as "R3,R5,R6" (no spaces in live data).
// RuleCatalog[rule_id] values are R1..R6. Bound-token match avoids R1⊂R10 style errors.
EnsureMeasure(
    "Rule Hits",
    @"
VAR RuleId = SELECTEDVALUE ( RuleCatalog[rule_id] )
RETURN
IF (
    ISBLANK ( RuleId ),
    BLANK (),
    CALCULATE (
        COUNTROWS ( FactAlert ),
        FILTER (
            FactAlert,
            CONTAINSSTRING (
                "","" & SUBSTITUTE ( FactAlert[rules_fired], "" "", """" ) & "","",
                "","" & RuleId & "",""
            )
        )
    )
)
",
    "04 Alerts",
    "0"
);

// ========== 05 Maintenance ==========
EnsureMeasure(
    "Work Orders",
    @"
DISTINCTCOUNT ( FactMaintenance[work_order_id] )
",
    "05 Maintenance",
    "0"
);

EnsureMeasure(
    "Total Maintenance Hours",
    @"
SUM ( FactMaintenance[duration_hours] )
",
    "05 Maintenance",
    "#,0.0"
);

EnsureMeasure(
    "Avg Cost per Work Order",
    @"
DIVIDE ( [Total Maintenance Cost], [Work Orders], 0 )
",
    "05 Maintenance",
    "$#,0.00"
);

EnsureMeasure(
    "Corrective Cost %",
    @"
DIVIDE (
    CALCULATE (
        [Total Maintenance Cost],
        FactMaintenance[maintenance_type] IN { ""Repair"", ""Replacement"" }
    ),
    [Total Maintenance Cost],
    0
)
",
    "05 Maintenance",
    "0.00%"
);

// ========== 06 Scheduling ==========
EnsureMeasure(
    "GA Travel km",
    @"
CALCULATE (
    AVERAGE ( FactModelMetric[metric_value] ),
    DimModel[model_name] = ""GA"",
    FactModelMetric[metric_name] = ""travel_km""
)
",
    "06 Scheduling\\Helpers",
    "#,0.0"
);

EnsureMeasure(
    "Greedy Travel km",
    @"
CALCULATE (
    AVERAGE ( FactModelMetric[metric_value] ),
    DimModel[model_name] = ""GREEDY"",
    FactModelMetric[metric_name] = ""travel_km""
)
",
    "06 Scheduling\\Helpers",
    "#,0.0"
);

EnsureMeasure(
    "Travel km Saved",
    @"
[Greedy Travel km] - [GA Travel km]
",
    "06 Scheduling",
    "#,0.0"
);

EnsureMeasure(
    "GA Fitness",
    @"
CALCULATE (
    AVERAGE ( FactModelMetric[metric_value] ),
    DimModel[model_name] = ""GA"",
    FactModelMetric[metric_name] = ""fitness""
)
",
    "06 Scheduling\\Helpers",
    "#,0.0"
);

EnsureMeasure(
    "Greedy Fitness",
    @"
CALCULATE (
    AVERAGE ( FactModelMetric[metric_value] ),
    DimModel[model_name] = ""GREEDY"",
    FactModelMetric[metric_name] = ""fitness""
)
",
    "06 Scheduling\\Helpers",
    "#,0.0"
);

EnsureMeasure(
    "Fitness Improvement %",
    @"
DIVIDE (
    [Greedy Fitness] - [GA Fitness],
    [Greedy Fitness],
    0
)
",
    "06 Scheduling",
    "0.00%"
);

EnsureMeasure(
    "Scheduled Hours",
    @"
SUM ( FactSchedule[slot_hours] )
",
    "06 Scheduling",
    "#,0.0"
);

EnsureMeasure(
    "Scheduled Jobs",
    @"
SUM ( FactSchedule[assignment_count] )
",
    "06 Scheduling",
    "0"
);

// Technician Utilization % — FIXED period basis:
// Do NOT use MIN/MAX(DimDate[full_date]) under a DimMethod filter.
// Relationships are single-direction fact→DimDate, so that pattern spans the
// entire DimDate calendar (~1460 days). Period comes from FactSchedule[slot_start].
EnsureMeasure(
    "Technician Utilization %",
    @"
VAR ScheduledHrs =
    CALCULATE (
        [Scheduled Hours],
        DimMethod[method_name] = ""GA""
    )
VAR CapacityPerWeek =
    SUMX (
        ALL ( DimTechnician ),
        DimTechnician[max_hours_per_week]
    )
VAR MinSlot =
    CALCULATE (
        MIN ( FactSchedule[slot_start] ),
        DimMethod[method_name] = ""GA""
    )
VAR MaxSlot =
    CALCULATE (
        MAX ( FactSchedule[slot_start] ),
        DimMethod[method_name] = ""GA""
    )
VAR DaySpan =
    IF (
        ISBLANK ( MinSlot ) || ISBLANK ( MaxSlot ),
        BLANK (),
        DATEDIFF ( MinSlot, MaxSlot, DAY )
    )
VAR WeekCount =
    IF ( ISBLANK ( DaySpan ), BLANK (), MAX ( 1, INT ( DIVIDE ( DaySpan, 7 ) ) + 1 ) )
RETURN
DIVIDE ( ScheduledHrs, CapacityPerWeek * WeekCount, 0 )
",
    "06 Scheduling",
    "0.00%"
);

// ========== 07 Model Performance ==========
EnsureMeasure(
    "XGB RMSE",
    @"
CALCULATE (
    AVERAGE ( FactModelMetric[metric_value] ),
    DimModel[model_name] = ""XGBoost"",
    FactModelMetric[metric_name] = ""test_rmse_true""
)
",
    "07 Model Performance",
    "#,0.000"
);

EnsureMeasure(
    "LR RMSE",
    @"
CALCULATE (
    AVERAGE ( FactModelMetric[metric_value] ),
    DimModel[model_name] = ""LinearRegression"",
    FactModelMetric[metric_name] = ""test_rmse_true""
)
",
    "07 Model Performance",
    "#,0.000"
);

EnsureMeasure(
    "Model RMSE",
    SelectedMlModelPattern + @"
CALCULATE (
    AVERAGE ( FactModelMetric[metric_value] ),
    FactModelMetric[metric_name] = ""test_rmse_true"",
    DimModel[model_name] = UseModel
)
)
",
    "07 Model Performance",
    "#,0.000"
);

EnsureMeasure(
    "Model NASA Score",
    SelectedMlModelPattern + @"
CALCULATE (
    AVERAGE ( FactModelMetric[metric_value] ),
    FactModelMetric[metric_name] = ""test_nasa_score"",
    DimModel[model_name] = UseModel
)
)
",
    "07 Model Performance",
    "#,0.0"
);

EnsureMeasure(
    "Model Precision",
    SelectedMlModelPattern + @"
CALCULATE (
    AVERAGE ( FactModelMetric[metric_value] ),
    FactModelMetric[metric_name] = ""test_precision"",
    DimModel[model_name] = UseModel
)
)
",
    "07 Model Performance",
    "0.00%"
);

EnsureMeasure(
    "Model Recall",
    SelectedMlModelPattern + @"
CALCULATE (
    AVERAGE ( FactModelMetric[metric_value] ),
    FactModelMetric[metric_name] = ""test_recall"",
    DimModel[model_name] = UseModel
)
)
",
    "07 Model Performance",
    "0.00%"
);

EnsureMeasure(
    "Model F1",
    SelectedMlModelPattern + @"
CALCULATE (
    AVERAGE ( FactModelMetric[metric_value] ),
    FactModelMetric[metric_name] = ""test_f1"",
    DimModel[model_name] = UseModel
)
)
",
    "07 Model Performance",
    "0.00%"
);

EnsureMeasure(
    "NASA Improvement %",
    @"
VAR LrNasa =
    CALCULATE (
        AVERAGE ( FactModelMetric[metric_value] ),
        DimModel[model_name] = ""LinearRegression"",
        FactModelMetric[metric_name] = ""test_nasa_score""
    )
VAR XgbNasa =
    CALCULATE (
        AVERAGE ( FactModelMetric[metric_value] ),
        DimModel[model_name] = ""XGBoost"",
        FactModelMetric[metric_name] = ""test_nasa_score""
    )
RETURN
DIVIDE ( LrNasa - XgbNasa, LrNasa, 0 )
",
    "07 Model Performance",
    "0.00%"
);

EnsureMeasure(
    "TP",
    SelectedMlModelPattern + @"
CALCULATE (
    AVERAGE ( FactModelMetric[metric_value] ),
    FactModelMetric[metric_name] = ""tp"",
    DimModel[model_name] = UseModel
)
)
",
    "07 Model Performance\\Confusion",
    "0"
);

EnsureMeasure(
    "FP",
    SelectedMlModelPattern + @"
CALCULATE (
    AVERAGE ( FactModelMetric[metric_value] ),
    FactModelMetric[metric_name] = ""fp"",
    DimModel[model_name] = UseModel
)
)
",
    "07 Model Performance\\Confusion",
    "0"
);

EnsureMeasure(
    "FN",
    SelectedMlModelPattern + @"
CALCULATE (
    AVERAGE ( FactModelMetric[metric_value] ),
    FactModelMetric[metric_name] = ""fn"",
    DimModel[model_name] = UseModel
)
)
",
    "07 Model Performance\\Confusion",
    "0"
);

EnsureMeasure(
    "TN",
    SelectedMlModelPattern + @"
CALCULATE (
    AVERAGE ( FactModelMetric[metric_value] ),
    FactModelMetric[metric_name] = ""tn"",
    DimModel[model_name] = UseModel
)
)
",
    "07 Model Performance\\Confusion",
    "0"
);

Info("---- Summary ----");
Info("Created: " + created);
Info("Skipped (already existed, model-wide): " + skipped);
Info("Blocked (not attempted): " + blocked);
Info("Create-only script finished. Existing measure expressions were not changed.");
Info("Tip: Save the PBIP from Desktop before running if Desktop has measures not yet written to disk.");
