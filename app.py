"""Streamlit UI for the general-purpose Natural Language to SQL assistant."""
from __future__ import annotations
import hashlib
from pathlib import Path
import pandas as pd
import streamlit as st
from data_loader import DatasetInfo, example_questions, load_csv, schema_context
from database import create_dataset_database, execute_read_only_query, validate_query_against_database
from nl_to_sql import generate_sql
from query_validator import validate_sql
from visualization import suggest_chart

ROOT = Path(__file__).parent
SAMPLE_PATH = ROOT / "sales_data.csv"
st.set_page_config(page_title="AI Data Assistant", page_icon="🧠", layout="wide")

def activate_dataset(info: DatasetInfo, fingerprint: str) -> None:
    if st.session_state.get("fingerprint") == fingerprint: return
    db_path = ROOT / ".runtime" / f"{fingerprint}.db"
    create_dataset_database(info.frame, db_path)
    st.session_state.update(dataset=info, db_path=db_path, fingerprint=fingerprint, question="")

def explain_result(question: str, data: pd.DataFrame) -> str:
    if data.empty: return "The query completed, but no records matched the question."
    if len(data) == 1 and len(data.columns) == 1: return f"The query returned {data.iloc[0, 0]!s} for {data.columns[0]}."
    return f"The query returned {len(data):,} row(s) for your question. Review the table and chart for the result details."

st.title("🧠 AI-Powered Natural Language to SQL Data Assistant")
st.caption("Ask questions about a CSV in plain language. Your data stays local; only compact schema metadata is sent to the LLM.")

with st.sidebar:
    st.header("Dataset")
    source = st.radio("Choose a source", ["Use Sample Sales Dataset", "Upload Your Own CSV"])
    upload = st.file_uploader("Upload CSV", type=["csv"], disabled=source != "Upload Your Own CSV")
    try:
        if source == "Use Sample Sales Dataset":
            info = load_csv(SAMPLE_PATH, SAMPLE_PATH.name)
            fingerprint = hashlib.sha256(SAMPLE_PATH.read_bytes()).hexdigest()[:16]
        elif upload is not None:
            content = upload.getvalue()
            info = load_csv(upload, upload.name)
            fingerprint = hashlib.sha256(content).hexdigest()[:16]
        else:
            info = None
        if info: activate_dataset(info, fingerprint)
    except ValueError as error:
        st.error(str(error)); info = None
    if st.session_state.get("dataset"):
        active = st.session_state.dataset
        st.divider(); st.subheader("Dataset information")
        st.write(f"**{active.name}**")
        st.metric("Rows", f"{len(active.frame):,}")
        st.metric("Columns", len(active.frame.columns))

if not st.session_state.get("dataset"):
    st.info("Choose the bundled sample or upload a CSV to begin.")
    st.stop()
active: DatasetInfo = st.session_state.dataset

st.header("1. Dataset preview")
st.dataframe(active.schema, hide_index=True, use_container_width=True)
st.dataframe(active.frame.head(10), hide_index=True, use_container_width=True)

st.header("2. Ask a question")
examples = example_questions(active)
st.caption("Schema-derived examples")
for index, example in enumerate(examples):
    if st.button(example, key=f"example_{index}"): st.session_state.question = example
question = st.text_input("Question", placeholder="Ask something about the active dataset…", key="question")

if st.button("Generate SQL and run", type="primary", disabled=not question):
    try:
        with st.spinner("Generating schema-aware SQLite SQL…"):
            sql = generate_sql(question, schema_context(active))
        st.session_state.generated_sql = sql
        valid, message = validate_sql(sql)
        if not valid: st.error(message); st.stop()
        valid, message = validate_query_against_database(st.session_state.db_path, sql)
        if not valid: st.error(message); st.stop()
        st.session_state.result = execute_read_only_query(st.session_state.db_path, sql)
        st.session_state.validation_message = "SQL passed structural and database validation."
    except RuntimeError as error:
        st.error(str(error))
    except Exception as error:
        st.error(f"Request failed: {type(error).__name__}: {error}")

if "generated_sql" in st.session_state:
    st.header("3. Generated SQL")
    st.code(st.session_state.generated_sql, language="sql")
    st.success(st.session_state.get("validation_message", ""))
if "result" in st.session_state:
    result = st.session_state.result
    st.header("4. Results")
    st.dataframe(result, hide_index=True, use_container_width=True)
    if result.attrs.get("truncated"): st.warning("Only the first 1,000 rows are displayed. Aggregate queries are not changed by this display cap.")
    st.download_button("Download results as CSV", result.to_csv(index=False), "query_results.csv", "text/csv")
    chart, x, y = suggest_chart(result)
    if chart:
        st.header("5. Visualization")
        chosen = st.selectbox("Chart type", [chart, "bar" if chart == "line" else "line"], key="chart_type")
        chart_data = result[[x, y]].set_index(x)
        st.line_chart(chart_data) if chosen == "line" else st.bar_chart(chart_data)
    st.header("6. Explanation")
    st.write(explain_result(question, result))
