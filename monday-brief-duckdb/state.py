import operator
from typing import Annotated, Any, Optional, TypedDict


class AnalysisState(TypedDict):
    question: str
    db_path: str
    data_summary: dict[str, Any]
    plan: list[dict]
    refused: Optional[str]
    step_index: int
    generated_code: str
    error: Optional[str]
    retry_count: int
    rounds: Annotated[list, operator.add]
    insights: str


def initial_state(question: str, db_path: str) -> AnalysisState:
    return {
        "question": question.strip(),
        "db_path": db_path,
        "data_summary": {},
        "plan": [],
        "refused": None,
        "step_index": 0,
        "generated_code": "",
        "error": None,
        "retry_count": 0,
        "rounds": [],
        "insights": "",
    }
