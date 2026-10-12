"""Generic chart recommendations based solely on query-result column types."""
from __future__ import annotations
import pandas as pd

def suggest_chart(frame: pd.DataFrame) -> tuple[str | None, str | None, str | None]:
    if frame.empty or len(frame.columns) < 2: return None, None, None
    numeric = frame.select_dtypes(include="number").columns.tolist()
    labels = [column for column in frame.columns if column not in numeric]
    if not numeric or not labels: return None, None, None
    x, y = labels[0], numeric[0]
    dates = pd.to_datetime(frame[x], errors="coerce")
    return ("line" if dates.notna().mean() >= 0.8 else "bar"), x, y
