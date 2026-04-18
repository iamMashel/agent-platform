import operator
from typing import Annotated, TypedDict

# Each turn appends 2 strings ("User: ..." + "Assistant: ...").
# Sending the full history to every LLM call grows the prompt unboundedly.
# We keep only the most recent N turns in the prompt while the full history
# stays safely stored in the Postgres checkpoint.
_MAX_HISTORY_TURNS = 10


class AgentState(TypedDict):
    input: str
    messages: Annotated[list[str], operator.add]  # operator.add APPENDS across turns
    next_step: str | None
    tool_result: str | None
    final_output: str | None


def format_history(state: AgentState) -> str:
    msgs = state["messages"]
    if not msgs:
        return "(no prior messages)"
    recent = msgs[-(_MAX_HISTORY_TURNS * 2) :]
    return "\n".join(recent)
