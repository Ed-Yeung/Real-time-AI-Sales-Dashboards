import json

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from execute import run_generated_code
from state import AnalysisState
from config import get_llm


class GeneratedCode(BaseModel):
    code: str = Field(description="One complete Python script. No markdown.")


SYSTEM = """You write one Python script for one analysis step.

The script must:
- Open the database with duckdb.connect(sys.argv[1], read_only=True). The path is already in sys.argv[1].
- Run one SELECT against the table named sales, then call .df() to get a pandas DataFrame.
- Use plotly.express for the chart.
- Follow the current step only. Do not add extra charts.
- If previous results are provided, use them to choose the filter named in the step.
- Save one chart with fig.write_json("fig0.json", engine="json").
- Save the rows behind that chart as result.json, a JSON list of objects.
- Use only columns from the profile.
- When the step says this week or last week, filter the date column with this_week and last_week from the profile. Do not choose other dates.
- Profit margin is SUM(sales - cost) / SUM(sales). Do not average a row-level ratio.

Do not call fig.show(). Do not read a CSV. Do not use pandas.read_csv.
Do not use INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, COPY, or ATTACH.
Do not use the network, and do not read or write any other files.
"""


def _prompt(state: AnalysisState) -> str:
    step = state["plan"][state["step_index"]]
    prior = [
        {"purpose": item["purpose"], "rows": item["rows"]}
        for item in state["rounds"]
    ]
    return (
        "PROFILE:\n"
        + json.dumps(state["data_summary"], ensure_ascii=False, indent=2)
        + "\n\nCURRENT STEP:\n"
        + json.dumps(step, ensure_ascii=False, indent=2)
        + "\n\nPREVIOUS RESULTS:\n"
        + json.dumps(prior, ensure_ascii=False, indent=2)
        + (
            "\n\nPREVIOUS CODE FAILED. Fix it and return the full script.\n"
            + state["generated_code"]
            + "\nERROR:\n"
            + (state["error"] or "")
            if state["error"]
            else "\n\nWrite the script."
        )
    )


def coder_node(state: AnalysisState) -> dict:
    step = state["plan"][state["step_index"]]
    attempt = state["retry_count"] + 1
    print(f"[coder] step {state['step_index'] + 1}, attempt {attempt}")

    coder = get_llm(0).with_structured_output(GeneratedCode)
    generated = coder.invoke(
        [SystemMessage(content=SYSTEM), HumanMessage(content=_prompt(state))]
    )
    result = run_generated_code(generated.code, state["db_path"])
    if not result.success:
        print(f"[coder] failed: {result.stderr[:200]}")
        return {
            "generated_code": generated.code,
            "error": result.stderr[-2000:],
            "retry_count": attempt,
        }

    print(f"[coder] ok, {len(result.records)} rows")
    return {
        "generated_code": generated.code,
        "error": None,
        "retry_count": attempt,
        "rounds": [
            {
                "round": state["step_index"] + 1,
                "purpose": step["purpose"],
                "code": generated.code,
                "figure": result.figure_json,
                "rows": result.records,
            }
        ],
    }
