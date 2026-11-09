"""Generate SYNTHETIC plants, technicians, engine_master and maintenance_log (seed 42).
Run from the project root:  python etl/generate_synthetic.py
All output is synthetic and must be labelled as such in the report."""
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "synthetic"
OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(42)

plants = pd.DataFrame([
    (1, "Karachi Hub",     "Karachi",   "Sindh",       "Pakistan", 24.8607, 67.0011),
    (2, "Lahore Works",    "Lahore",    "Punjab",      "Pakistan", 31.5204, 74.3587),
    (3, "Islamabad Base",  "Islamabad", "ICT",         "Pakistan", 33.6844, 73.0479),
    (4, "Faisalabad Yard", "Faisalabad","Punjab",      "Pakistan", 31.4504, 73.1350),
    (5, "Quetta Depot",    "Quetta",    "Balochistan", "Pakistan", 30.1798, 66.9750),
], columns=["plant_id","plant_name","city","province","country","latitude","longitude"])

rates = {"Junior": 15, "Mid": 25, "Senior": 40}
techs = []
for tid in range(1, 21):
    plant_id = (tid - 1) % 5 + 1
    skill = rng.choice(["Junior", "Mid", "Senior"], p=[0.35, 0.40, 0.25])
    techs.append((tid, f"Tech {tid:02d} (synthetic)", plant_id, skill,
                  round(rates[skill] * rng.uniform(0.9, 1.2), 2), 40))
techs = pd.DataFrame(techs, columns=["technician_id","name","plant_id","skill_level","hourly_rate","max_hours_per_week"])

# max cycle per train engine (from real data if present, otherwise random)
# max cycle per engine uid (real NASA lifespans if the files are present, otherwise random)
max_cycle = {}
for fname, off, lo, hi in [("train_FD001.txt", 0, 130, 360), ("test_FD001.txt", 1000, 31, 303)]:
    f = ROOT / "data" / "raw" / fname
    if f.exists():
        t = pd.read_csv(f, sep=r"\s+", header=None, usecols=[0, 1])
        max_cycle.update({off + int(k): int(v) for k, v in t.groupby(0)[1].max().items()})
    else:
        print(f"WARNING: {fname} not found in data/raw, using random lifespans")
        max_cycle.update({off + i: int(rng.integers(lo, hi)) for i in range(1, 101)})

rows = []
for split, offset in [("train", 0), ("test", 1000)]:
    for eid in range(1, 101):
        rows.append((offset + eid, eid, split, int(rng.integers(1, 6)),
                     pd.Timestamp("2023-01-01") + pd.Timedelta(days=int(rng.integers(0, 365)))))
engines = pd.DataFrame(rows, columns=["engine_uid","engine_id","split","plant_id","commission_date"])

dur = {"Inspection": (1, 3), "Repair": (4, 12), "Replacement": (12, 40)}
cost = {"Inspection": (150, 400), "Repair": (800, 3000), "Replacement": (5000, 15000)}
wo, wid = [], 1
for _, e in engines.iterrows():
    span = max_cycle[e.engine_uid]            # number of cycles; last cycle date = commission + span - 1 days
    last_day = span - 1
    events = [("Inspection", int(rng.integers(0, max(last_day, 1)))) for _ in range(int(rng.integers(2, 6)))]
    if e.split == "train":
        events.append(("Replacement", last_day))
        if rng.random() < 0.4:
            events.append(("Repair", int(rng.integers(int(last_day * 0.75), max(last_day, 1)))))
    elif rng.random() < 0.3:
        events.append(("Repair", int(rng.integers(0, max(last_day, 1)))))
    for typ, day in events:
        pool = techs[techs.plant_id == e.plant_id] if rng.random() < 0.85 else techs
        tech = pool.sample(1, random_state=int(rng.integers(0, 1_000_000))).iloc[0]
        wo.append((wid, e.engine_uid, (e.commission_date + pd.Timedelta(days=day)).strftime("%Y-%m-%d"),
                   typ, tech.technician_id,
                   round(rng.uniform(*dur[typ]), 1), round(rng.uniform(*cost[typ]), 2)))
        wid += 1
maint = pd.DataFrame(wo, columns=["work_order_id","engine_uid","work_date","type","technician_id","duration_hours","cost"])

# deliberate dirty data so Silver has real cleaning to do
maint["duration_hours"] = maint["duration_hours"].astype(object)
maint.loc[maint.sample(8, random_state=1).index, "duration_hours"] = None
maint = pd.concat([maint, maint.sample(3, random_state=2)], ignore_index=True)

plants.to_csv(OUT / "plants.csv", index=False)
techs.to_csv(OUT / "technicians.csv", index=False)
engines.to_csv(OUT / "engine_master.csv", index=False)
maint.to_csv(OUT / "maintenance_log.csv", index=False)
(OUT / "synthetic_data_readme.md").write_text(
    "# Synthetic data (NOT real)\nSeed 42. 5 plants, 20 technicians, 200 engines (100 train, 100 test).\n"
    "Maintenance: 2-5 inspections per engine, replacement at failure for train engines, "
    "85% same-plant technicians, 8 null durations and 3 duplicate rows injected on purpose.\n")
print({k: len(v) for k, v in dict(plants=plants, techs=techs, engines=engines, maint=maint).items()})
