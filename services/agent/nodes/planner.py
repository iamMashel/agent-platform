from __future__ import annotations

import structlog

from services.agent.graph.state import AgentState, format_history
from services.agent.llm import get_llm

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """\
You are a planner agent. You have a conversation history and a new user message.

Conversation history:
{history}

New user message: {input}

Decide whether the user's request requires an external search or can be answered directly.
Respond with EXACTLY one of:
- "tool:search"   — if the user needs up-to-date or external information
- "final"         — if you can answer from knowledge or conversation history
"""


def planner_node(state: AgentState) -> dict[str, str | list[str] | None]:
    history = format_history(state)
    log.debug(
        "planner.start", input_length=len(state["input"]), history_turns=len(state["messages"])
    )

    llm = get_llm(temperature=0)
    prompt = _SYSTEM_PROMPT.format(history=history, input=state["input"])
    raw = llm.invoke(prompt).content
    response = (raw if isinstance(raw, str) else str(raw)).strip().lower()

    log.debug("planner.decision", next_step=response)
    return {"next_step": response, "messages": [f"User: {state['input']}"]}
