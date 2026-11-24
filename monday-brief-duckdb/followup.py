from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from config import get_llm


class FollowUp(BaseModel):
    use_history: bool
    filters: str = Field(description="Filters to keep, e.g. region=Kowloon; month=10")
    metric: str = ""
    formula: str = ""
    note: str = ""


def resolve_followup(question: str, previous: dict | None) -> dict:
    if not previous:
        return {"use_history": False, "filters": "", "metric": "", "formula": "", "note": "new question"}
    system = (
        "Decide if the new question is a follow-up. "
        "If it is, keep previous filters and the previous metric and formula. "
        "Replace only the field the user changed. "
        "Example: previous region=Kowloon and column=sales; new question 'what about cost' "
        "keeps region=Kowloon and sets column=cost. "
        "If it is a new question, set use_history false and leave filters, metric, formula empty. "
        "Do not calculate."
    )
    result = get_llm(0).with_structured_output(FollowUp).invoke(
        [
            SystemMessage(content=system),
            HumanMessage(
                content=(
                    f"Previous question: {previous.get('question', '')}\n"
                    f"Previous filters: {previous.get('filters', '')}\n"
                    f"Previous metric: {previous.get('metric', '')}\n"
                    f"Previous formula: {previous.get('formula', '')}\n\n"
                    f"New question: {question}"
                )
            ),
        ]
    )
    return result.model_dump()