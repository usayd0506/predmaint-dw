// Tabular Editor 2 Advanced Scripting
// OPTIONAL — calculated columns for Fleet Health "Health index distribution"
// Not part of the default measure create script.
// Target table: FactEngineHealth

var tableName = "FactEngineHealth";
if (!Model.Tables.Contains(tableName))
{
    Error("Table '" + tableName + "' was not found. Aborting.");
    return;
}

var table = Model.Tables[tableName];
int created = 0;
int skipped = 0;

if (table.Columns.Contains("Health Index Bin"))
{
    Info("SKIP existing column: Health Index Bin");
    skipped++;
}
else
{
    var c = table.AddCalculatedColumn(
        "Health Index Bin",
        @"
SWITCH (
    TRUE (),
    FactEngineHealth[health_index] < 20, ""0-19"",
    FactEngineHealth[health_index] < 40, ""20-39"",
    FactEngineHealth[health_index] < 60, ""40-59"",
    FactEngineHealth[health_index] < 80, ""60-79"",
    ""80-100""
)
"
    );
    c.DisplayFolder = "Bins";
    Info("CREATE column: Health Index Bin");
    created++;
}

if (table.Columns.Contains("Health Index Bin Sort"))
{
    Info("SKIP existing column: Health Index Bin Sort");
    skipped++;
}
else
{
    var c = table.AddCalculatedColumn(
        "Health Index Bin Sort",
        @"
SWITCH (
    TRUE (),
    FactEngineHealth[health_index] < 20, 1,
    FactEngineHealth[health_index] < 40, 2,
    FactEngineHealth[health_index] < 60, 3,
    FactEngineHealth[health_index] < 80, 4,
    5
)
"
    );
    c.DisplayFolder = "Bins";
    c.IsHidden = true;
    Info("CREATE column: Health Index Bin Sort");
    created++;
}

if (table.Columns.Contains("Health Index Bin") && table.Columns.Contains("Health Index Bin Sort"))
{
    table.Columns["Health Index Bin"].SortByColumn = table.Columns["Health Index Bin Sort"];
    Info("Set SortByColumn: Health Index Bin <- Health Index Bin Sort");
}

Info("---- Column Summary ----");
Info("Created: " + created);
Info("Skipped: " + skipped);
