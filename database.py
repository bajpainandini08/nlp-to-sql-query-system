"""Ephemeral SQLite database helpers for the active CSV dataset."""
from __future__ import annotations
import sqlite3
from pathlib import Path
import pandas as pd

TABLE_NAME = "dataset"

def create_dataset_database(frame: pd.DataFrame, db_path: Path) -> None:
    """Replace the session database with one generic table created from a dataframe."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    try:
        frame.to_sql(TABLE_NAME, connection, if_exists="replace", index=False)
    finally:
        connection.close()

def execute_read_only_query(db_path: Path, sql: str, max_rows: int = 1_000) -> pd.DataFrame:
    """Run a previously validated query and cap returned raw result sets."""
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        connection.execute("PRAGMA query_only = ON")
        connection.set_authorizer(_read_only_authorizer)
        cursor = connection.execute(sql)
        rows = cursor.fetchmany(max_rows + 1)
        result = pd.DataFrame(rows[:max_rows], columns=[item[0] for item in cursor.description])
        result.attrs["truncated"] = len(rows) > max_rows
        return result
    finally:
        connection.close()

def validate_query_against_database(db_path: Path, sql: str) -> tuple[bool, str]:
    """Use SQLite's compiler to catch invalid columns or functions before execution."""
    try:
        connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            connection.execute("PRAGMA query_only = ON")
            connection.execute("EXPLAIN QUERY PLAN " + sql)
        finally:
            connection.close()
        return True, "SQL references valid database objects."
    except sqlite3.Error as error:
        return False, f"SQL cannot run on the active dataset: {error}"

def _read_only_authorizer(action: int, arg1: str | None, arg2: str | None, db: str | None, source: str | None) -> int:
    allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}
    return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY
