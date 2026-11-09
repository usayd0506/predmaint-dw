from sqlalchemy import text
from etl.config import ENGINE


def log_step(batch_id, step, rows_in=None, rows_out=None, status="OK", message=None):
    with ENGINE.begin() as c:
        c.execute(text(
            "INSERT INTO ops.etl_log (batch_id, step_name, rows_in, rows_out, status, message) "
            "VALUES (:b, :s, :ri, :ro, :st, :m)"),
            dict(b=str(batch_id), s=step, ri=rows_in, ro=rows_out, st=status, m=(message or "")[:500]))


def count(table):
    with ENGINE.connect() as c:
        return c.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
