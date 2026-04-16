from typing import TypedDict, List, Optional


class AgentState(TypedDict):
    input: str
    messages: List[str]
    next_step: Optional[str]
    tool_result: Optional[str]
    final_output: Optional[str]