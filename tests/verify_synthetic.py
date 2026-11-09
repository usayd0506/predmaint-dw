"""Independent check of data/synthetic/*.csv. Run from project root:
    python tests/verify_synthetic.py
Does not depend on the generator code. Prints PASS/FAIL per check."""
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SYN, RAW = ROOT / "data" / "synthetic", ROOT / "data" / "raw"
fails = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + (f"  [{detail}]" if detail else ""))
    if not ok:
        fails.append(name)


plants = pd.read_csv(SYN / "plants.csv")
techs = pd.read_csv(SYN / "technicians.csv")
eng = pd.read_csv(SYN / "engine_master.csv", parse_dates=["commission_date"])
wo = pd.read_csv(SYN / "maintenance_log.csv")

# 1 columns exactly as the SQL staging tables expect
check("plants columns", list(plants.columns) == ["plant_id","plant_name","city","province","country","latitude","longitude"])
check("technicians columns", list(techs.columns) == ["technician_id","name","plant_id","skill_level","hourly_rate","max_hours_per_week"])
check("engine_master columns", list(eng.columns) == ["engine_uid","engine_id","split","plant_id","commission_date"])
check("maintenance columns", list(wo.columns) == ["work_order_id","engine_uid","work_date","type","technician_id","duration_hours","cost"])

# 2 row counts
check("5 plants / 20 technicians / 200 engines", (len(plants), len(techs), len(eng)) == (5, 20, 200), f"{len(plants)},{len(techs)},{len(eng)}")
check("maintenance rows 550-960", 550 <= len(wo) <= 960, str(len(wo)))

# 3 keys
check("engine_uid unique", eng.engine_uid.is_unique)
check("train uid = id, test uid = 1000 + id",
      ((eng.split == "train") & (eng.engine_uid == eng.engine_id)).sum() == 100
      and ((eng.split == "test") & (eng.engine_uid == 1000 + eng.engine_id)).sum() == 100)
check("work-order engines exist", wo.engine_uid.isin(eng.engine_uid).all())
check("work-order technicians exist", wo.technician_id.isin(techs.technician_id).all())
check("engine plants exist", eng.plant_id.isin(plants.plant_id).all())

# 4 domain rules
check("types valid", wo.type.isin(["Inspection","Repair","Replacement"]).all())
wo["work_date"] = pd.to_datetime(wo.work_date)
clean = wo.drop_duplicates()
rep = clean[clean.type == "Replacement"].merge(eng, on="engine_uid")
check("every train engine has exactly one Replacement",
      (rep[rep.split == "train"].groupby("engine_uid").size() == 1).all() and rep[rep.split == "train"].engine_uid.nunique() == 100)
check("no test engine has a Replacement", (rep.split == "test").sum() == 0)
insp = clean[clean.type == "Inspection"].groupby("engine_uid").size()
check("each engine has 2-5 inspections", insp.between(2, 5).all() and len(insp) == 200)
m = wo.merge(eng, on="engine_uid")
tp = techs.set_index("technician_id").plant_id
same = (m.technician_id.map(tp) == m.plant_id).mean()
check("same-plant technician share near 85%", 0.78 <= same <= 0.92, f"{same:.2f}")
check("no work before commission", (m.work_date >= m.commission_date).all())

# 5 dirty data present as intended
check("8 missing durations", wo.duration_hours.isna().sum() == 8, str(wo.duration_hours.isna().sum()))
check("3 duplicate rows", wo.duplicated().sum() == 3, str(wo.duplicated().sum()))

# 6 dates vs real NASA lifespans (only if raw files exist)
tr, te = RAW / "train_FD001.txt", RAW / "test_FD001.txt"
if tr.exists() and te.exists():
    last = {}
    for f, off in [(tr, 0), (te, 1000)]:
        t = pd.read_csv(f, sep=r"\s+", header=None, usecols=[0, 1])
        for eid, mx in t.groupby(0)[1].max().items():
            last[off + eid] = mx
    e2 = eng.set_index("engine_uid")
    end = pd.Series({u: e2.commission_date[u] + pd.Timedelta(days=int(last[u]) - 1) for u in e2.index})
    check("no work after the engine's last cycle date", (m.work_date <= m.engine_uid.map(end)).all())
    fail_day = rep[rep.split == "train"].set_index("engine_uid").work_date
    check("replacement falls on failure day", (fail_day == end[fail_day.index]).all())
else:
    print("SKIP  NASA files not in data/raw, lifespan checks not run")

print("\nALL CHECKS PASSED" if not fails else f"\n{len(fails)} FAILED: {fails}")
sys.exit(1 if fails else 0)
