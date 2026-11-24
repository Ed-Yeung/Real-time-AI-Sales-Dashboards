from langgraph.graph import END, START, StateGraph

from coder import coder_node
from config import MAX_CODE_ATTEMPTS, MAX_ROUNDS
from explorer import explorer_node
from planner import planner_node
from state import AnalysisState
from writer import writer_node


def route_after_planner(state: AnalysisState) -> str:
    if state.get("refused") or not state.get("plan"):
        return "writer"
    return "coder"


def route_after_coder(state: AnalysisState) -> str:
    if state.get("error") and state["retry_count"] < MAX_CODE_ATTEMPTS:
        return "retry"
    finished = state["step_index"] + 1
    if state.get("error"):
        return "writer"
    if finished < len(state["plan"]) and finished < MAX_ROUNDS:
        return "next"
    return "writer"


def advance_node(state: AnalysisState) -> dict:
    return {
        "step_index": state["step_index"] + 1,
        "error": None,
        "retry_count": 0,
        "generated_code": "",
    }


def build_graph():
    builder = StateGraph(AnalysisState)
    builder.add_node("explorer", explorer_node)
    builder.add_node("planner", planner_node)
    builder.add_node("coder", coder_node)
    builder.add_node("advance", advance_node)
    builder.add_node("writer", writer_node)

    builder.add_edge(START, "explorer")
    builder.add_edge("explorer", "planner")
    builder.add_conditional_edges(
        "planner",
        route_after_planner,
        {"coder": "coder", "writer": "writer"},
    )
    builder.add_conditional_edges(
        "coder",
        route_after_coder,
        {"retry": "coder", "next": "advance", "writer": "writer"},
    )
    builder.add_edge("advance", "coder")
    builder.add_edge("writer", END)
    return builder.compile()


if __name__ == "__main__":
    print(build_graph().get_graph().draw_mermaid())
