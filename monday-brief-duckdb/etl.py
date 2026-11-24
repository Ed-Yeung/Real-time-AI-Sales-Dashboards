import io
from pathlib import Path

import duckdb
import pandas as pd

from config import DB_PATH

REQUIRED = ("date", "region", "category", "sales", "cost", "units", "orders")
NUMBERS = ("sales", "cost", "units", "orders")


def clean_csv(raw: bytes) -> tuple[pd.DataFrame, dict]:
    frame = pd.read_csv(io.BytesIO(raw))
    read = int(len(frame))
    frame.columns = [str(name).strip().lower() for name in frame.columns]
    missing = [name for name in REQUIRED if name not in frame.columns]
    if missing:
        raise ValueError("Missing columns: " + ", ".join(missing))

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    for name in NUMBERS:
        frame[name] = pd.to_numeric(frame[name], errors="coerce")
    frame["region"] = frame["region"].astype("string").str.strip()
    frame["category"] = frame["category"].astype("string").str.strip()

    bad = (
        frame["date"].isna()
        | frame[list(NUMBERS)].isna().any(axis=1)
        | frame["region"].isna()
        | frame["region"].eq("")
        | frame["category"].isna()
        | frame["category"].eq("")
    )
    frame = frame.loc[~bad].copy()
    frame["year"] = frame["date"].dt.year.astype(int)
    frame["month"] = frame["date"].dt.month.astype(int)
    frame["weekday"] = frame["date"].dt.day_name()
    keep = ["date", "year", "month", "weekday", "region", "category", "sales", "cost", "units", "orders"]
    frame = frame[keep].drop_duplicates()
    kept = int(len(frame))
    return frame, {"read": read, "kept": kept, "deleted": read - kept}


def load_csv(raw: bytes) -> dict:
    frame, stats = clean_csv(raw)
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(DB_PATH)
    try:
        con.register("clean_sales", frame)
        con.execute("CREATE OR REPLACE TABLE sales AS SELECT * FROM clean_sales")
    finally:
        con.close()
    return stats
