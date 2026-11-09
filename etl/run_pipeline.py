"""One command, whole pipeline:  python -m etl.run_pipeline
Each step is logged to ops.etl_log. Add steps as you build them."""
import uuid
from sqlalchemy import text
from etl.config import ENGINE
from etl.logger import log_step, count
from etl import load_staging


def call_proc(proc, batch_id=None):
    with ENGINE.begin() as c:
        if batch_id is None:
            c.execute(text(f"EXEC {proc}"))
        else:
            c.execute(text(f"EXEC {proc} @batch_id = :b"), dict(b=str(batch_id)))


def step(batch_id, name, fn, count_in=None, count_out=None):
    try:
        fn()
        log_step(batch_id, name,
                 count(count_in) if count_in else None,
                 count(count_out) if count_out else None)
        print("OK  ", name)
    except Exception as e:                      # log and stop
        log_step(batch_id, name, status="FAIL", message=str(e))
        print("FAIL", name, e)
        raise


def main():
    b = uuid.uuid4()
    step(b, "stg load", load_staging.run, None, "stg.sensors")
    step(b, "bronze load", lambda: call_proc("bronze.usp_load_all", b), "stg.sensors", "bronze.sensors")
    # TODO: silver.usp_load_dimensions, silver.usp_load_engine_cycles
    # TODO: gold.usp_build_engine_health
    # TODO: ml.train_rul, ml.train_cls, ml.health_index, ml.expert_system, ml.ga_scheduler (each writes to gold)
    # TODO: mart.usp_load_* in dependency order
    print("batch", b)


if __name__ == "__main__":
    main()
