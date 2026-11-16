# PredMaint project (fixed model + 7-page report, no DAX)

OPEN
1. Power BI Desktop > File > Options > Preview features: tick "Power BI Project (.pbip) save option" and the
   TMDL / enhanced report format options if listed. Restart Desktop.
2. File > Open report > Browse > PredMaint.pbip
3. Home > Refresh. The data paths are the ones from your file (F:\I.T Department\predmaint_powerbi_dataset\...).
   If the folder moved: Home > Transform data > Data source settings > Change source.
4. Add your DAX measures into the empty _Measures table (select it, then New measure).
5. File > Save as > .pbix when you want one file.

WHAT WAS FIXED
- All 5 facts now link to DimEngine as Many-to-One, Single direction, Active (they were inactive or 1:1 both ways).
- Extra plant paths set to inactive (DimTechnician and FactEngineHealth to DimPlant).
- Auto date/time off. DimDate marked as the date table (full_date). year_month is text so it sorts correctly.
- Sort-by-column set for month, weekday, risk level, degradation stage, severity, maintenance type, skill level.
- Keys and helper columns hidden, DimRun hidden, number/date formats and map data categories set.
- RuleCatalog (R1-R6) table added for the Rule Hits measure.
- Dark Espresso / Burnt Orange theme applied; 7 pages with sidebar and vertical page navigator.
