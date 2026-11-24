import pandas as pd
import plotly.io as pio
import streamlit as st

from config import DB_PATH
from data_io import DataLoadError, load_dataframe
from etl import load_csv
from explorer import profile_dataframe
from followup import resolve_followup
from graph import build_graph
from handbook import list_handbooks, match_handbook, save_handbook
from state import initial_state

st.set_page_config(page_title="Sales check", layout="wide", initial_sidebar_state="expanded")
st.markdown(
    """
    <style>
    :root { --accent: #0f6e6b; --ink: #1f2933; --muted: #667085; --line: #e6e8ec; }
    .stApp { background: #f6f7f9; color: var(--ink); }
    section[data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid var(--line); }
    section[data-testid="stSidebar"] h1 { font-size: 1.35rem; letter-spacing: -0.03em; }
    .stButton > button[kind="primary"] {
        background: var(--accent); border: 1px solid var(--accent); border-radius: 10px;
    }
    .stButton > button { border-radius: 10px; }
    div[data-testid="stChatMessage"] {
        background: #ffffff; border: 1px solid var(--line); border-radius: 14px;
        padding: 4px 8px; margin-bottom: 10px;
    }
    .stChatInput { border-radius: 14px; }
    .block-container { padding-top: 1.4rem; max-width: 980px; }
    </style>
    """,
    unsafe_allow_html=True,
)

EXAMPLES = [
    "Why is Kowloon down this week?",
    "Which category has the lowest profit margin?",
    "Which region grew the most?",
]


@st.cache_resource
def get_app():
    return build_graph()


def show_result(result: dict) -> None:
    if not result:
        return
    if result.get("refused"):
        st.warning(result["refused"])
    for item in result.get("rounds") or []:
        st.write(item["purpose"])
        if item.get("figure"):
            st.plotly_chart(pio.from_json(item["figure"]), use_container_width=True)
        if item.get("rows"):
            st.dataframe(item["rows"], hide_index=True, use_container_width=True)
        with st.expander("Code"):
            st.code(item.get("code") or "", language="python")
    if result.get("insights"):
        st.markdown(result["insights"])


if "chat" not in st.session_state:
    st.session_state["chat"] = []
if "etl" not in st.session_state:
    st.session_state["etl"] = None

with st.sidebar:
    st.markdown("### Sales check")
    st.caption("Ask about sales. Numbers come from the table.")
    if st.button("New chat", type="primary", use_container_width=True):
        st.session_state["chat"] = []
        st.rerun()

    st.subheader("Sources")
    st.caption(f"DuckDB: {DB_PATH}")
    books = list_handbooks()
    st.caption(f"Handbooks: {len(books)}")
    if books:
        for book in books:
            st.caption(f"PDF: {book.name}")
    else:
        st.caption("PDF: none")
    st.caption("Select one or more PDFs. Ctrl+click to pick several. New files are added, old files stay.")
    uploaded_pdfs = st.file_uploader("Upload handbook PDFs", type=["pdf"], accept_multiple_files=True)
    if uploaded_pdfs:
        token = "|".join(f"{item.name}:{item.size}" for item in uploaded_pdfs)
        if st.session_state.get("pdf_token") != token:
            for item in uploaded_pdfs:
                save_handbook(item.name, item.getvalue())
            st.session_state["pdf_token"] = token
            st.rerun()

    uploaded_csv = st.file_uploader("Upload sales CSV", type=["csv"])
    if uploaded_csv is not None:
        token = f"csv:{uploaded_csv.name}:{uploaded_csv.size}"
        if st.session_state.get("csv_token") != token:
            try:
                st.session_state["etl"] = load_csv(uploaded_csv.getvalue())
                st.session_state["csv_token"] = token
                st.session_state["etl_error"] = ""
            except Exception as exc:
                st.session_state["etl_error"] = str(exc)
            st.rerun()

try:
    frame = load_dataframe(DB_PATH)
    profile = profile_dataframe(frame)
except DataLoadError as exc:
    st.error("Upload a sales CSV in the sidebar first.")
    st.caption(str(exc))
    st.stop()

with st.sidebar:
    st.subheader("Data")
    etl = st.session_state.get("etl") or {}
    if etl:
        st.caption(f"Read {etl['read']:,}")
        st.caption(f"Kept {etl['kept']:,}")
        st.caption(f"Deleted {etl['deleted']:,}")
    if st.session_state.get("etl_error"):
        st.error(st.session_state["etl_error"])
    st.caption(f"Rows {profile['n_rows']:,}")
    st.caption(f"Columns {profile['n_cols']}")
    st.caption(f"Latest {profile.get('latest_date') or '—'}")
    this_week = " to ".join(profile.get("this_week") or [])
    last_week = " to ".join(profile.get("last_week") or [])
    st.caption(f"This week {this_week or '—'}")
    st.caption(f"Last week {last_week or '—'}")

for turn in st.session_state["chat"]:
    with st.chat_message("user"):
        st.write(turn["question"])
    with st.chat_message("assistant"):
        if turn.get("note"):
            st.caption(turn["note"])
        if turn.get("filters"):
            st.write(f"Filters: {turn['filters']}")
        if turn.get("formula"):
            st.write(f"Formula: {turn['formula']}")
        if turn.get("source"):
            st.caption(f"{turn['source']} p.{turn.get('page') or '?'}")
        if turn.get("quote") and not turn.get("result"):
            st.success(turn["quote"])
        show_result(turn.get("result") or {})

if not st.session_state["chat"]:
    st.markdown("#### Ask a question")
    st.caption("Try one of these")
    for example in EXAMPLES:
        st.markdown(f"- {example}")

asked = st.chat_input("Ask anything about your data")
if not asked:
    st.stop()

asked = asked.strip()
previous = st.session_state["chat"][-1] if st.session_state["chat"] else None
follow = resolve_followup(asked, previous)
question = asked
if follow["use_history"]:
    question = (
        f"{asked}\n"
        f"Keep filters: {follow['filters']}\n"
        f"Keep metric: {follow['metric']}\n"
        f"Keep formula: {follow['formula']}"
    )

if list_handbooks():
    match = match_handbook(question)
else:
    match = {
        "needs_definition": False,
        "found": False,
        "kind": "explore",
        "name": "",
        "formula": "",
        "quote": "",
    }

note = follow.get("note") or ""
if follow["use_history"]:
    note = f"Follow-up. {note}"
else:
    note = f"New question. {note}"

if match.get("conflict"):
    st.session_state["chat"].append({
        "question": asked,
        "filters": "",
        "metric": match.get("name") or "",
        "formula": "",
        "note": "Conflict. No calculation.",
        "quote": match.get("conflict_note") or "Two handbooks define this differently.",
        "source": "",
        "page": 0,
        "result": None,
    })
    st.rerun()

if match["kind"] == "document":
    st.session_state["chat"].append({
        "question": asked,
        "filters": "",
        "metric": "",
        "formula": "",
        "note": "document",
        "quote": match.get("quote") or "No matching sentence.",
        "result": None,
    })
    st.rerun()

if match.get("needs_definition") and match["found"] and match.get("formula"):
    question = f"{question}\nUse only this handbook formula: {match['formula']}"
    note = f"{note} Handbook formula."
elif match.get("needs_definition") and not match["found"]:
    question = (
        f"{question}\n"
        "This metric is not in the handbook. "
        "State the formula, the filters, and the groups in every step."
    )
    note = f"{note} Not in the handbook."

try:
    final = None
    with st.status("Investigating...", expanded=True) as status:
        for snap in get_app().stream(initial_state(question, DB_PATH), stream_mode="values"):
            final = snap
        status.update(label="Done", state="complete")
    st.session_state["chat"].append({
        "question": asked,
        "filters": follow.get("filters", ""),
        "metric": match.get("name") or follow.get("metric", ""),
        "formula": match.get("formula") or follow.get("formula", ""),
        "note": note,
        "quote": match.get("quote") or "",
        "result": final,
    })
    st.rerun()
except DataLoadError as exc:
    st.error(str(exc))
except Exception as exc:
    st.error(str(exc))
