"""Dedicated read-only SQL validation for the one-table analytics database."""
from __future__ import annotations
import re
import sqlglot
from sqlglot import exp

FORBIDDEN_TOKENS = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|ATTACH|DETACH|PRAGMA|VACUUM|REPLACE|LOAD_EXTENSION)\b|--|/\*", re.IGNORECASE)

def validate_sql(sql: str, allowed_table: str = "dataset") -> tuple[bool, str]:
    """Allow exactly one SQLite SELECT/CTE query using only the active table."""
    statement = sql.strip()
    if not statement: return False, "No SQL was generated."
    if FORBIDDEN_TOKENS.search(statement): return False, "Unsafe SQL keyword or comment syntax was rejected."
    if ";" in statement.rstrip().rstrip(";"): return False, "Only one SQL statement is allowed."
    try: expressions = sqlglot.parse(statement, read="sqlite")
    except sqlglot.errors.ParseError: return False, "Generated SQL is not valid SQLite syntax."
    if len(expressions) != 1 or expressions[0] is None: return False, "Only one SQL statement is allowed."
    tree = expressions[0]
    if not isinstance(tree, exp.Query): return False, "Only read-only SELECT queries are allowed."
    tables = {table.name.lower() for table in tree.find_all(exp.Table)}
    if tables and not tables.issubset({allowed_table.lower()}): return False, "SQL may only query the active dataset table."
    return True, "Read-only SQL passed structural validation."
