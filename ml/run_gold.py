import argparse
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd
from sqlalchemy import text

from config import connect
from models import SENSORS, FEATURES, train_and_predict, health_scores
from scheduler import make_schedules

ROOT = Path(__file__).resolve().parent.parent

OUTPUT = ROOT / "docs" / "gold_results"


def read_inputs(engine):
    with engine.connect() as conn:

        batch = pd.read_sql(text("SELECT TOP (1) batch_id, source_version FROM ops.bronze_batch WHERE status='OK' ORDER BY loaded_at DESC"), conn)
        
        cycles = pd.read_sql(text("SELECT * FROM silver.engine_cycles"), conn)
        
        master = pd.read_sql(text("SELECT * FROM silver.engine_master"), conn)
        
        maintenance = pd.read_sql(text("SELECT * FROM silver.maintenance"), conn)
        
        plants = pd.read_sql(text("SELECT * FROM silver.plants"), conn)
        
        technicians = pd.read_sql(text("SELECT * FROM silver.technicians"), conn)
        
        limits = pd.read_sql(text("SELECT * FROM gold.risk_thresholds WHERE threshold_id = 1"), conn)
        
        existing = conn.execute(text("SELECT COUNT(*) FROM gold.run_control")).scalar_one()
        
        existing_health = conn.execute(text("SELECT COUNT(*) FROM gold.engine_health")).scalar_one()
    
    if len(batch) != 1 or len(limits) != 1:
        raise ValueError("Missing successful Bronze batch or risk thresholds")
    
    if any(x.empty for x in [cycles, master, maintenance, plants, technicians]):
        raise ValueError("Silver has empty required tables")
    
    if cycles.engine_uid.nunique() != 200 or len(cycles) != 33727:
        raise ValueError("Unexpected Silver engine-cycle population; inspect before running")
    
    if existing or existing_health:
        raise ValueError("Gold already contains a run. This initial loader refuses to overwrite it")
    
    # Guard against a mismatch between the Bronze batch and current Silver snapshot
    with engine.connect() as conn:
        bronze_count = conn.execute(text("SELECT COUNT(*) FROM bronze.sensors WHERE batch_id=:id"),
                                    {"id": str(batch.iloc[0].batch_id)}).scalar_one()
        
    if bronze_count != len(cycles):
        raise ValueError("Silver row count differs from the selected Bronze batch")
    
    return batch.iloc[0], cycles, master, maintenance, plants, technicians, limits.iloc[0]


def build_health(test, preds, train, master, maintenance, limits):

    health, baselines = health_scores(train, test, preds)

    reference = master[["engine_uid", "plant_id"]]

    health = health.merge(reference, on="engine_uid", validate="one_to_one")

    maintenance["work_date"] = pd.to_datetime(maintenance["work_date"])

    last = maintenance.groupby("engine_uid").work_date.max()

    health["last_maintenance"] = pd.to_datetime(health.engine_uid.map(last))

    health["cycle_date"] = pd.to_datetime(health.cycle_date)

    c_rul = float(limits.critical_rul)

    c_prob = float(limits.critical_probability)

    w_rul = float(limits.warning_rul)

    w_prob = float(limits.warning_probability)

    def risk(row):
        if row.predicted_rul < c_rul or row.failure_prob_30 > c_prob:
            return "Critical"
        
        if row.predicted_rul < w_rul or row.failure_prob_30 > w_prob:
            return "Warning"
        
        return "Healthy"
    
    health["risk_level"] = health.apply(risk, axis=1)
    return health, baselines


def generate_alerts(health, baselines):
    priorities = {"Medium": 1, "High": 2, "Critical": 3}

    rules = {
        "R1": ("Critical", "Immediate inspection"),
        "R2": ("Critical", "Ground engine and plan replacement"),
        "R3": ("High", "Inspect within seven days"),
        "R4": ("Medium", "Plan maintenance"),
        "R5": ("Medium", "Check temperature and pressure"),
        "R6": ("High", "Priority inspection")
    }

    alerts = []
    for row in health.itertuples():

        fired = set()
        if row.predicted_rul < 30 and row.health_index < 30:
            fired.add("R1")

        if row.failure_prob_30 > 0.7:
            fired.add("R2")

        if 30 <= row.predicted_rul <= 60:
            fired.add("R3")

        days_since = (row.cycle_date - row.last_maintenance).days if not pd.isna(row.last_maintenance) else 9999

        if row.degradation_stage == "Degrading" and days_since > 90:
            fired.add("R4")

        if (row.s4_sm > baselines["s4_sm"][0] + 2 * baselines["s4_sm"][1] or
                row.s11_sm > baselines["s11_sm"][0] + 2 * baselines["s11_sm"][1]):
            fired.add("R5")

        # Forward chaining: R6 fires when the derived facts R3 and R5 both exist.
        if "R3" in fired and "R5" in fired:
            fired.add("R6")

        if not fired:
            continue
        
        selected = sorted(fired, key=lambda r: (-priorities[rules[r][0]], r))[0]

        alerts.append({"engine_uid": int(row.engine_uid), "severity": rules[selected][0],
                       "action": rules[selected][1], "rules_fired": ",".join(sorted(fired))})
        
    return pd.DataFrame(alerts, columns=["engine_uid", "severity", "action", "rules_fired"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write derived Gold outputs to SQL Server")
    parser.add_argument("--quick", action="store_true", help="Shortened GA for debugging, not final reporting")
    args = parser.parse_args()
    engine = connect()
    batch, cycles, master, maintenance, plants, technicians, limits = read_inputs(engine)
    test, predictions, metrics, train = train_and_predict(cycles)
    health, baselines = build_health(test, predictions, train, master, maintenance, limits)
    alerts = generate_alerts(health, baselines)
    # The date is anchored to the simulated fleet's latest cycle date, NOT to the real calendar.
    # This is a retrospective scheduling demonstration, not real-world upcoming appointments.
    start = pd.Timestamp(health.cycle_date.max()).normalize() + timedelta(days=1)
    schedule, comparison, convergence, ga_stats = make_schedules(health, technicians, plants, start, args.quick)
    metrics.extend([("GA", "fitness_mean", ga_stats[0]), ("GA", "fitness_std", ga_stats[1])])
    for result in comparison:
        for key in ["fitness", "risk_penalty", "travel_km", "labor_cost", "overlaps", "overload_hours"]:
            metrics.append((result["method"], key, float(result[key])))
    print("Source version:", batch.source_version)
    print("Engine health records:", len(health), "Predictions:", len(predictions), "Alerts:", len(alerts))
    print("Scheduled rows:", len(schedule), "GA comparison:")
    print(pd.DataFrame(comparison).to_string(index=False))
    print(pd.DataFrame(metrics, columns=["model", "metric", "value"]).to_string(index=False))
    if not args.apply:
        print("DRY RUN: No database records changed. Run --apply after reviewing results.")
        return
    run_id = str(uuid4())
    # One transaction: either all Gold outputs are written or none are.
    with engine.begin() as conn:
        if conn.execute(text("SELECT COUNT(*) FROM gold.run_control")).scalar_one() != 0:
            raise RuntimeError("Gold is no longer empty. Cancelled before writing.")
        conn.execute(text("INSERT INTO gold.run_control (run_id, bronze_batch_id, source_version, status) "
                          "VALUES (:run_id, :batch_id, :source_version, 'OK')"),
                     {"run_id": run_id, "batch_id": str(batch.batch_id), "source_version": str(batch.source_version)})
        def write(table, df):
            if not df.empty:
                df.copy().to_sql(table, conn, schema="gold", if_exists="append", index=False, chunksize=500)
        health_out = health.rename(columns={"cycle": "cycles_run", "cycle_date": "last_cycle_date"})[
            ["engine_uid", "plant_id", "cycles_run", "last_cycle_date", "last_maintenance",
             "health_index", "degradation_stage", "risk_level"]].copy()
        health_out["run_id"] = run_id
        write("engine_health", health_out)
        predictions["run_id"] = run_id
        write("ml_predictions", predictions)
        metrics_out = pd.DataFrame(metrics, columns=["model_name", "metric", "value"])
        metrics_out["run_id"] = run_id
        write("model_metrics", metrics_out)
        alerts["run_id"] = run_id
        write("alerts", alerts)
        schedule["run_id"] = run_id
        write("work_order_schedule", schedule)
        for table, count in [("engine_health", len(health)), ("ml_predictions", len(predictions)),
                             ("alerts", len(alerts)), ("work_order_schedule", len(schedule))]:
            actual = conn.execute(text(f"SELECT COUNT(*) FROM gold.{table} WHERE run_id=:id"),
                                  {"id": run_id}).scalar_one()
            if actual != count:
                raise RuntimeError(f"Mismatch in gold.{table}: {actual} versus {count}")
        for step, count in [("Gold Engine Health",len(health)), ("Gold Predictions",len(predictions)),
                            ("Gold Alerts",len(alerts)), ("Gold Schedule",len(schedule))]:
            conn.execute(text("INSERT INTO ops.etl_log (batch_id, step_name, rows_in, rows_out, status, message) "
                              "VALUES (:id, :step, :a, :b, 'OK', :msg)"),
                         {"id": str(batch.batch_id), "step": step, "a": count, "b": count,
                          "msg": f"Gold run {run_id}"})
    OUTPUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(metrics, columns=["model", "metric", "value"]).to_csv(OUTPUT / "model_metrics.csv", index=False)
    pd.DataFrame(comparison).to_csv(OUTPUT / "ga_vs_greedy.csv", index=False)
    pd.DataFrame({"generation": range(1, len(convergence)+1), "best_fitness": convergence}).to_csv(
        OUTPUT / "ga_convergence.csv", index=False)
    print("Gold load committed. Run ID:", run_id)


if __name__ == "__main__":
    main()
