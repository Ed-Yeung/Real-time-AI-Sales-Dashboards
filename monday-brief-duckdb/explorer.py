import warnings

import pandas as pd

from data_io import load_dataframe
from state import AnalysisState


def comparison_windows(frame: pd.DataFrame, date_column: str) -> dict:
    latest = pd.to_datetime(frame[date_column], errors="coerce").max()
    if pd.isna(latest):
        return {}
    this_end = latest.normalize()
    this_start = this_end - pd.Timedelta(days=6)
    last_end = this_start - pd.Timedelta(days=1)
    last_start = last_end - pd.Timedelta(days=6)
    as_text = lambda day: day.strftime("%Y-%m-%d")
    return {
        "latest_date": as_text(this_end),
        "this_week": [as_text(this_start), as_text(this_end)],
        "last_week": [as_text(last_start), as_text(last_end)],
    }


def profile_dataframe(frame: pd.DataFrame) -> dict:
    numeric = frame.select_dtypes(include="number").columns.tolist()
    other = [column for column in frame.columns if column not in numeric]
    dates, categories = [], []
    for column in other:
        sample = frame[column].dropna().head(200)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parsed = pd.to_datetime(sample, errors="coerce")
        if len(sample) and parsed.notna().mean() >= 0.8:
            dates.append(column)
        else:
            categories.append(column)

    preview = {}
    for column in categories:
        preview[column] = frame[column].value_counts().head(8).index.astype(str).tolist()

    date_column = "date" if "date" in dates else (dates[0] if dates else None)
    windows = comparison_windows(frame, date_column) if date_column else {}

    return {
        "n_rows": int(frame.shape[0]),
        "n_cols": int(frame.shape[1]),
        "columns": frame.columns.tolist(),
        "numerical_columns": numeric,
        "categorical_columns": categories,
        "datetime_columns": dates,
        "categorical_preview": preview,
        "table": "sales",
        **windows,
    }


def explorer_node(state: AnalysisState) -> dict:
    summary = profile_dataframe(load_dataframe(state["db_path"]))
    print(
        f"[explorer] {summary['n_rows']} rows, latest {summary.get('latest_date')}, "
        f"this week {summary.get('this_week')}"
    )
    return {"data_summary": summary}
