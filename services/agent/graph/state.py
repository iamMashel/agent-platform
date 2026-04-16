import operator
from typing import Annotated, TypedDict


class AgentState(TypedDict):
    input: str
    messages: Annotated[list[str], operator.add]  # operator.add APPENDS across turns
    next_step: str | None
    tool_result: str | None
    final_output: str | None


def format_history(state: AgentState) -> str:
    return "\n".join(state["messages"]) if state["messages"] else "(no prior messages)"
