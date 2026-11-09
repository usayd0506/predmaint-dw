-- Run in SSMS after the pipeline. Every query should return 0 rows / the expected value.
SELECT engine_uid, cycle, COUNT(*) c FROM silver.engine_cycles GROUP BY engine_uid, cycle HAVING COUNT(*) > 1;
SELECT COUNT(*) AS train_last_cycle_rul_not_zero FROM (
  SELECT engine_uid, MIN(rul) r FROM silver.engine_cycles WHERE split='train' GROUP BY engine_uid) x WHERE r <> 0;
SELECT a.rules_fired FROM gold.alerts a WHERE a.rules_fired = '' OR a.rules_fired IS NULL;
SELECT step_name, rows_in, rows_out, status FROM ops.etl_log ORDER BY log_id DESC;
