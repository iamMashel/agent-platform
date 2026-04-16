from typing import TypedDict


class AgentState(TypedDict):
    input: str
    messages: list[str]
    next_step: str | None
    tool_result: str | None
    final_output: str | None
