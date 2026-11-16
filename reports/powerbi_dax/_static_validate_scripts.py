from pathlib import Path
import re

root = Path(__file__).resolve().parent
create = (root / "create_missing_measures.csx").read_text(encoding="utf-8")
corr = (root / "proposed_measure_corrections.csx").read_text(encoding="utf-8")
cols = (root / "create_health_index_bin_columns.csx").read_text(encoding="utf-8")

issues = []


def check(name, text, expect_add_measure=False):
    if name != "columns" and "_Measures" not in text:
        issues.append(f"{name}: missing _Measures reference")
    if "Contains(" not in text:
        issues.append(f"{name}: missing existence check Contains(")
    for bad in [
        "Delete(",
        ".Remove(",
        "DropMeasure",
        "Model.AddCalculationGroup",
        "CalculationGroup",
        "HybridTable",
        "EntityPartition",
    ]:
        if bad in text:
            issues.append(f"{name}: forbidden/TE3 pattern {bad}")
    if text.count("{") != text.count("}"):
        issues.append(
            f"{name}: unbalanced braces {text.count('{')}/{text.count('}')}"
        )
    if expect_add_measure and "AddMeasure" not in text:
        issues.append(f"{name}: missing AddMeasure")
    if "Error(" not in text:
        issues.append(f"{name}: missing Error() abort path")


check("create", create, True)
check("corrections", corr, False)
check("columns", cols, False)

names = re.findall(r'EnsureMeasure\(\s*"([^"]+)"', create)
dupes = sorted({n for n in names if names.count(n) > 1})
if dupes:
    issues.append(f"create: duplicate EnsureMeasure names: {dupes}")

existing = {
    "Total Engines",
    "Critical Engines",
    "At-Risk %",
    "Total Alerts",
    "Engines With Alert",
    "Avg Health Index",
    "Min Predicted RUL",
    "Total Maintenance Cost",
    "Estimated Cost Avoided",
    "Labor Cost Saving %",
    "GA Labor Cost",
    "Greedy Labor Cost",
    "Headline Executive",
    "Lowest RUL Rank",
}
overlap = sorted(set(names) & existing)
if overlap:
    issues.append(f"create: overlaps existing names (runtime skip only): {overlap}")

corr_names = re.findall(r'CorrectMeasure\(\s*"([^"]+)"', corr)

# Ensure create script does not assign Expression on existing measures
if "m.Expression" in create or ".Expression =" in create:
    issues.append("create: must not overwrite Expression")

print("STATIC_VALIDATION")
print("create_measure_count", len(names))
print("create_names:")
for n in names:
    print(" -", n)
print("correction_targets", corr_names)
print("issues_count", len(issues))
for i in issues:
    print("ISSUE:", i)

real = [i for i in issues if "overlaps existing" not in i]
print("RESULT:", "PASS" if not real else "FAIL")
