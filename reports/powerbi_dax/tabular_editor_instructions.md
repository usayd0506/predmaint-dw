# Tabular Editor 2 — safe execution instructions

These steps apply the **create-only** script. Do **not** run corrections unless you explicitly approve them.

## 0. Backup first

1. Close any other editors on the PBIP if possible.
2. Copy the whole folder  
   `powerbi/PredMaint_Fixed_Project_New`  
   to a timestamped backup (e.g. `PredMaint_Fixed_Project_New_backup_YYYYMMDD`).
3. Optional: File → Save as `.pbix` backup from Power BI Desktop.

## 1. Install Tabular Editor 2

1. Download **Tabular Editor 2** (free) from the official Tabular Editor releases (TE2, not TE3).
2. Install or unzip the portable build.
3. Confirm you are on TE2: Help → About should show version **2.x**.

TE3-only APIs are not used in these scripts; still prefer TE2 as specified.

## 2. Open the model from Power BI Desktop (recommended)

1. Open  
   `powerbi/PredMaint_Fixed_Project_New/Usyad Power Bi report.pbip`  
   in **Power BI Desktop**.
2. Wait for the model to load.
3. Home → **Refresh** and confirm mart tables load from `USAYD-PC\SQLEXPRESS` / `PredMaintDW`.
4. External tools → **Tabular Editor** (if registered), **or** in TE2: File → Open → From DB → connect to the Desktop workspace instance shown in Desktop’s External Tools tooltip.

Alternative: In TE2, File → Open → File and open the `.SemanticModel` / database definition if your TE2 build supports PBIP/TMDL directly. Prefer the live Desktop connection so you can save back cleanly.

## 3. Verify `_Measures` before scripting

In TE2 tree:

- Tables → `_Measures` exists
- Measures currently listed (14): Total Engines, Critical Engines, At-Risk %, Total Alerts, Engines With Alert, Avg Health Index, Min Predicted RUL, Total Maintenance Cost, Estimated Cost Avoided, Labor Cost Saving %, GA Labor Cost, Greedy Labor Cost, Headline Executive, Lowest RUL Rank
- Column `Column1` present
- No measure literally named `Measure` (none expected)

## 4. Run the create-only script

1. TE2 → **Advanced Scripting** (C# script pane).
2. File → Open script (or paste)  
   `reports/powerbi_dax/create_missing_measures.csx`
3. Click **Run**.
4. Output should list `CREATE:` for missing names and `SKIP existing:` for the 14 already present.
5. Summary line: Created ≈ 36, Skipped = 14 (if none of the new names pre-exist).

**Do not** run `proposed_measure_corrections.csx` in this step.

## 5. Save back to Desktop / PBIP

1. TE2 → File → **Save** (writes into the connected model).
2. In Power BI Desktop, confirm new measures appear under `_Measures` display folders.
3. Desktop → File → **Save** the PBIP project.
4. Optional: refresh visuals on Executive Summary.

## 6. Optional — corrections (explicit approval only)

Only after reading `existing_measures_audit.md`:

1. Advanced Scripting → open `proposed_measure_corrections.csx`
2. Run once
3. Confirm Labor Cost Saving % shows as a percentage
4. Confirm GA/Greedy Labor Cost match FactSchedule sums
5. Save Desktop + PBIP

## 7. Optional — Health Index bins

1. Run `create_health_index_bin_columns.csx`
2. Save
3. Build the Fleet Health distribution visual on `Health Index Bin` + `[Total Engines]`

## 8. Rollback

If something is wrong:

1. Close Desktop **without** saving (if changes not yet saved), **or**
2. Restore the backup folder over `PredMaint_Fixed_Project_New`
3. Re-open the PBIP

TE2 create-only does not delete measures. Worst case for create-only: extra measures you can delete manually from `_Measures`. Corrections overwrite three/four expressions — restore from backup if needed.

## 9. What these scripts must never do

- Delete `_Measures` or `Column1`
- Change relationships
- Change Power Query / SQL sources
- Modify SQL Server
- Rebuild report pages

This pack only generates/updates DAX measure (and optional calculated column) objects inside the semantic model when you run the scripts yourself.
