import operator
from typing import Annotated, TypedDict


class AgentState(TypedDict):
    input: str
    # Annotated with operator.add so LangGraph APPENDS across turns (enables memory)
    messages: Annotated[list[str], operator.add]
    next_step: str | None
    tool_result: str | None
    final_output: str | None
