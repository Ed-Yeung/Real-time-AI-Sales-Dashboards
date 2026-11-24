import json

from langchain_core.messages import HumanMessage, SystemMessage

from config import get_llm
from state import AnalysisState

SYSTEM = """You write a short preliminary answer for a store manager.
Use only numbers that appear in the round results. Do not invent figures.
If the question was refused, repeat that reason and do not guess.

Use these four headings, in this order:
Finding
Evidence
Comparison
Limit

Say that this is an initial insight, not a formal performance number.
Mention which round each number came from.
"""


def writer_node(state: AnalysisState) -> dict:
    if state.get("refused"):
        text = (
            "Finding\n"
            f"{state['refused']}\n\n"
            "Evidence\nNo query was run.\n\n"
            "Comparison\nNothing to compare.\n\n"
            "Limit\nThe sales file does not contain the field this question needs."
        )
        return {"insights": text}

    payload = {
        "question": state["question"],
        "rounds": [
            {"round": item["round"], "purpose": item["purpose"], "rows": item["rows"]}
            for item in state["rounds"]
        ],
    }
    text = get_llm(0).invoke(
        [
            SystemMessage(content=SYSTEM),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False, indent=2)),
        ]
    )
    print("[writer] answer ready")
    return {"insights": text.content}
