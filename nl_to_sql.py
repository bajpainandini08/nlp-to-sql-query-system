"""Schema-aware Gemini integration for NL-to-SQL."""
from __future__ import annotations

import json
import os
import re
from dotenv import load_dotenv

load_dotenv()


def generate_sql(question: str, schema_context: str) -> str:
    """Ask Gemini for one SQL query over the active `dataset` table."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. Add it to .env or Streamlit secrets."
        )

    from openai import OpenAI

    instructions = """You translate natural-language data questions into SQLite SQL.
Return exactly one JSON object with a single `sql` field. Use ONLY the table and quoted
column identifiers in the schema context. Its value must be a single read-only SELECT
statement (a WITH/CTE ending in SELECT is allowed). Never create, modify, attach, or
inspect a database. Do not use markdown. If the question cannot be answered from this
dataset, return a harmless SELECT with a clear literal message and LIMIT 1."""

    prompt = (
        f"Current dataset schema and limited metadata:\n{schema_context}\n\n"
        f"Question: {question}"
    )

    client = OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    response = client.chat.completions.create(
        model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    try:
        content = response.choices[0].message.content
        sql = json.loads(content or "")["sql"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise RuntimeError("Gemini returned an unreadable SQL response.") from error

    return normalize_sql(sql)


def normalize_sql(text: str) -> str:
    """Strip accidental fences without attempting to repair or invent SQL."""
    return re.sub(
        r"^\s*```(?:sql)?\s*|\s*```\s*$",
        "",
        text.strip(),
        flags=re.IGNORECASE,
    ).strip()