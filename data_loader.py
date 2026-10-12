"""Generic CSV loading, cleaning, metadata, and prompt-context utilities."""
from __future__ import annotations
import re
from dataclasses import dataclass
import pandas as pd

MAX_ROWS = 200_000

@dataclass
class DatasetInfo:
    name: str
    frame: pd.DataFrame
    original_to_safe: dict[str, str]
    schema: pd.DataFrame

def load_csv(source: object, name: str) -> DatasetInfo:
    """Load CSV, reject unusable files, and make database-safe unique column names."""
    try: frame = pd.read_csv(source)
    except Exception as error: raise ValueError("Could not read this file as a CSV.") from error
    if frame.empty or not len(frame.columns): raise ValueError("The CSV must contain at least one column and one data row.")
    if len(frame) > MAX_ROWS: raise ValueError(f"This prototype supports up to {MAX_ROWS:,} rows per dataset.")
    if frame.columns.isna().any(): raise ValueError("CSV headers cannot be empty.")
    original_names = [str(column).strip() for column in frame.columns]
    if any(not column for column in original_names): raise ValueError("CSV headers cannot be blank.")
    safe_names = _safe_columns(original_names)
    frame.columns = safe_names
    frame = _infer_dates(frame)
    schema = pd.DataFrame({"Column": original_names, "SQL column": safe_names, "Detected type": [_sqlite_type(frame[column]) for column in safe_names], "Missing values": [int(frame[column].isna().sum()) for column in safe_names], "Unique values": [int(frame[column].nunique(dropna=True)) for column in safe_names]})
    return DatasetInfo(name=name, frame=frame, original_to_safe=dict(zip(original_names, safe_names)), schema=schema)

def schema_context(info: DatasetInfo) -> str:
    """Build compact metadata only—never send the complete CSV to the LLM."""
    lines = ["Table: dataset"]
    for _, item in info.schema.iterrows():
        safe = item["SQL column"]
        samples = [str(value) for value in info.frame[safe].dropna().drop_duplicates().head(5).tolist()]
        lines.append(f'- "{safe}" (original: "{item["Column"]}", type: {item["Detected type"]}, samples: {samples})')
    return "\n".join(lines)

def example_questions(info: DatasetInfo) -> list[str]:
    """Offer generic, schema-derived prompts without business-domain rules."""
    schema = info.schema
    numeric = schema[schema["Detected type"].isin(["INTEGER", "REAL"])]["Column"].tolist()
    non_identifier = [column for column in numeric if not re.search(r"(^id$|_id$|^id_)", column, re.IGNORECASE)]
    numeric = non_identifier or numeric
    categorical = schema[(schema["Detected type"] == "TEXT") & (schema["Unique values"] > 1)]["Column"].tolist()
    prompts = ["How many rows are in this dataset?"]
    if numeric: prompts.append(f"What is the average {numeric[0]}?")
    if categorical: prompts.append(f"How many records are there for each {categorical[0]}?")
    if numeric and categorical: prompts.append(f"What is the total {numeric[0]} by {categorical[0]}?")
    return prompts[:4]

def _safe_columns(columns: list[str]) -> list[str]:
    used, result = set(), []
    for index, name in enumerate(columns, start=1):
        base = re.sub(r"[^a-zA-Z0-9_]", "_", name).strip("_") or f"column_{index}"
        if base[0].isdigit(): base = "column_" + base
        candidate, suffix = base, 2
        while candidate.lower() in used:
            candidate, suffix = f"{base}_{suffix}", suffix + 1
        used.add(candidate.lower()); result.append(candidate)
    return result

def _infer_dates(frame: pd.DataFrame) -> pd.DataFrame:
    for column in frame.select_dtypes(include="object"):
        parsed = pd.to_datetime(frame[column], errors="coerce")
        if parsed.notna().mean() >= 0.9: frame[column] = parsed.dt.strftime("%Y-%m-%d")
    return frame

def _sqlite_type(series: pd.Series) -> str:
    if pd.api.types.is_integer_dtype(series): return "INTEGER"
    if pd.api.types.is_numeric_dtype(series): return "REAL"
    if pd.to_datetime(series, errors="coerce").notna().mean() >= 0.9: return "DATE/TEXT"
    return "TEXT"
