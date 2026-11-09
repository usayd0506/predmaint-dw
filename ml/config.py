import pyodbc
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

SERVER = r"localhost\SQLEXPRESS"
DATABASE = "PredMaintDW"


def connect():
    drivers = pyodbc.drivers()
    driver = next((d for d in ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server") if d in drivers), None)
    if driver is None:
        raise RuntimeError("Install Microsoft ODBC Driver 17 or 18 for SQL Server")
    
    url = URL.create("mssql+pyodbc", host=SERVER, database=DATABASE,
                     query={"driver": driver, "trusted_connection": "yes", "TrustServerCertificate": "yes"})
    engine = create_engine(url, fast_executemany=True)

    
    with engine.connect() as conn:
        name = conn.execute(text("SELECT DB_NAME() ")).scalar_one()
        if name != DATABASE:
            raise RuntimeError(f"Incorrect database: {name}")
    print(f"Connected to {DATABASE} ({driver}).")
    return engine
