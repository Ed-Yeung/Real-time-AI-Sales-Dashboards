import duckdb

from config import DB_PATH, SAMPLE_CSV


def connect(readonly: bool = True):
    return duckdb.connect(DB_PATH, read_only=readonly)


def build_database() -> int:
    con = duckdb.connect(DB_PATH)
    try:
        con.execute(
            "CREATE OR REPLACE TABLE sales AS SELECT * FROM read_csv_auto(?)",
            [SAMPLE_CSV],
        )
        count = con.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
    finally:
        con.close()
    return int(count)
