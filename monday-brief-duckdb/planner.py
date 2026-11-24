import json
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from config import MAX_ROUNDS, get_llm
from state import AnalysisState

ChartType = Literal["bar", "line"]


class PlanStep(BaseModel):
    purpose: str = Field(description="What this one chart should show")
    columns: list[str] = Field(description="Exact column names used in this step")
    chart: ChartType
    instruction: str = Field(description="One concrete instruction for the coder")


class Plan(BaseModel):
    answerable: bool
    refusal: str = ""
    steps: list[PlanStep] = Field(default_factory=list)


SYSTEM = f"""You plan a short sales investigation for a store manager.
You receive one question and a dataset profile. The data lives in a DuckDB table named sales.

Rules:
- Use only columns that appear in the profile. Never invent columns.
- A ranking or "which is highest/lowest" question needs exactly 1 step.
- A "why" or "what changed" question needs 2 or 3 steps, never more than {MAX_ROUNDS}.
- Later steps must say to filter using the weakest or strongest group from the previous result.
- There is no week column. When the question says this week or last week, use this_week and last_week from the profile. Do not choose other dates.
- Profit margin means SUM(sales - cost) / SUM(sales), not the average of a ratio.
- If the question needs a field that is not in the profile (customer age, ads, weather, staff, rent), set answerable to false, leave steps empty, and say what is missing.
- Write purpose, refusal, and instruction in English.
"""


def planner_node(state: AnalysisState) -> dict:
    summary = state["data_summary"]
    known = set(summary["columns"])
    planner = get_llm(0).with_structured_output(Plan)
    plan = planner.invoke(
        [
            SystemMessage(content=SYSTEM),
            HumanMessage(
                content=(
                    f"Question: {state['question']}\n\n"
                    "Dataset profile:\n"
                    + json.dumps(summary, ensure_ascii=False, indent=2)
                )
            ),
        ]
    )

    if not plan.answerable:
        reason = plan.refusal or "This question cannot be answered from the sales file."
        print(f"[planner] refused: {reason}")
        return {"plan": [], "refused": reason}

    steps = []
    for step in plan.steps[:MAX_ROUNDS]:
        unknown = [column for column in step.columns if column not in known]
        if unknown:
            print(f"[planner] dropped step with unknown columns {unknown}")
            continue
        steps.append(step.model_dump())

    if not steps:
        reason = "The plan used columns that are not in the file."
        return {"plan": [], "refused": reason}

    print(f"[planner] {len(steps)} step(s)")
    for index, step in enumerate(steps, start=1):
        print(f"        {index}. {step['purpose']}")
    return {"plan": steps, "refused": None}
