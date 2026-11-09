import os
from pathlib import Path
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SYN = ROOT / "data" / "synthetic"
SQL_DIR = ROOT / "sql"

SERVER = os.getenv("DB_SERVER", "localhost")
DB = os.getenv("DB_NAME", "PredMaintDW")
DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")

ENGINE = create_engine(
    f"mssql+pyodbc://@{SERVER}/{DB}?driver={quote_plus(DRIVER)}"
    "&trusted_connection=yes&TrustServerCertificate=yes",
    fast_executemany=True,
)

SENSOR_COLS = (["engine_id", "cycle"]
               + [f"setting_{i}" for i in range(1, 4)]
               + [f"sensor_{i}" for i in range(1, 22)])
KEPT_SENSORS = [2, 3, 4, 7, 8, 9, 11, 12, 13, 14, 15, 17, 20, 21]   # dropped: 1,5,6,10,16,18,19
RUL_CAP = 125
FAIL_WINDOW = 30
