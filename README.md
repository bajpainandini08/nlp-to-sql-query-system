# AI-Powered Natural Language to SQL Data Assistant

Ask questions about any CSV in plain language. The app uses an LLM to generate SQLite SQL from the **currently loaded schema**, validates it as read-only, runs it locally, and shows results, charts, and a CSV download.

## Overview

Writing SQL is a barrier to exploring data. This project turns a question into SQL while remaining dataset-independent: bundled `sales_data.csv` is only a demonstration. Upload employee, survey, inventory, finance, student, or other CSV data without source-code changes.

`CSV → inspection/normalization → temporary SQLite table (dataset) → schema-aware LLM → SQL validator → local query → results/chart`

The LLM receives the question plus compact schema metadata—types and up to five sample values per column—not the full dataset. Queries execute only in a local session database.

## Features

- Sample CSV and arbitrary CSV upload
- Dynamic row/column counts, types, missing values, unique values, and preview
- Database-safe unique column names while retaining original labels
- Google Gemini API with native structured JSON output
- Schema-driven SQL generation; no sales-specific rules or fixed questions
- Structural validator, database compilation validation, SQLite read-only authorizer, and 1,000-row display cap
- Generic bar/line chart recommendation and CSV result download

## SQL safety and privacy

Only one `SELECT` query (including safe CTEs) against `dataset` is allowed. The validator rejects writes, DDL, `PRAGMA`, `ATTACH`, comments, multiple statements, and unsafe commands. SQLite uses read-only/query-only mode plus an authorizer. Invalid columns are caught during SQLite compilation before execution. The result cap affects returned rows only, not aggregate calculations.

Do not upload sensitive data unless you accept compact metadata being sent to the configured LLM provider. The full uploaded CSV is never sent to the API or stored permanently by the application.

## Project structure

```text
app.py                 Streamlit interface and orchestration
data_loader.py         Generic CSV loading, cleaning, schema metadata
database.py            Session SQLite creation and read-only execution
nl_to_sql.py           Gemini API SQL generation
query_validator.py     Dedicated SQL safety validation
visualization.py       Generic result chart selection
sales_data.csv         Demonstration dataset
tests/test_core.py     Non-LLM integration and safety tests
```

## Installation and run

```powershell
cd "C:\Users\nbajp\Documents\Codex\2026-09-20\so\outputs\nl-to-sql-query-system"
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and set GEMINI_API_KEY to your Google AI Studio key
python -m streamlit run app.py
```

Set `GEMINI_API_KEY` in `.env` and never commit it. `GEMINI_MODEL` is optional and defaults to `gemini-3.7-flash`; choose a model available to your Google AI Studio account. The implementation uses Gemini's native API and requests structured JSON containing only a SQL field.

## Usage

Choose **Use Sample Sales Dataset** or **Upload Your Own CSV**. Review the live schema, select a schema-derived example or ask a question, then choose **Generate SQL and run**. An employee CSV can answer “What is the average salary by department?” because the LLM receives that active schema rather than a sales schema.

## Testing

```powershell
python -m unittest discover -s tests -v
```

Tests do not call or fake an LLM. They verify the real sample CSV, three analytics queries, an unrelated employee dataset, generic visualization recommendation, unsafe SQL rejection, and invalid-column handling. A Gemini API key is required for interactive LLM generation.

## Deploy to Streamlit Community Cloud

1. Push this folder to GitHub, including `sales_data.csv` but excluding `.env`.
2. Create an app in Streamlit Community Cloud and select `app.py`.
3. Add `GEMINI_API_KEY="..."` and optionally `GEMINI_MODEL="..."` in **Settings → Secrets**.
4. Deploy. The sample is bundled; uploaded CSVs are session-only.

## Limitations and improvements

CSV formats Pandas cannot parse and datasets above 200,000 rows are rejected. LLM output can be semantically imperfect, so generated SQL is shown and always checked before execution. Production improvements include authentication, stronger semantic validation, audit logging, user-controlled limits, and additional read-only databases.
