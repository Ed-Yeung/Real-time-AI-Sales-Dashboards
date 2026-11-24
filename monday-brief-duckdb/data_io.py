import duckdb
import pandas as pd


class DataLoadError(Exception):
    pass


def load_dataframe(db_path: str) -> pd.DataFrame:
    try:
        con = duckdb.connect(db_path, read_only=True)
        try:
            frame = con.execute("SELECT * FROM sales").df()
        finally:
            con.close()
    except Exception as exc:
        raise DataLoadError(f"Unable to read the sales table: {exc}") from exc
    if frame.shape[0] == 0 or frame.shape[1] == 0:
        raise DataLoadError("The sales table has no rows or no columns.")
    return frame
