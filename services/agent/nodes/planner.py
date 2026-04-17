from __future__ import annotations

import structlog

from services.agent.graph.state import AgentState, format_history
from services.agent.llm import get_llm

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """\
You are a routing agent. Read the user message and output EXACTLY one token.

Conversation history:
{history}

User message: {input}

Output rules — one line only, no explanation:
- Output the exact string  tool:search  when the user asks about current events, live data, news, prices, sports scores, or any fact that may have changed recently.
- Output the exact string  final  when you can answer from your training knowledge or the conversation history above.

Your output:"""


def planner_node(state: AgentState) -> dict[str, str | None]:
    history = format_history(state)
    log.debug(
        "planner.start", input_length=len(state["input"]), history_turns=len(state["messages"])
    )

    llm = get_llm(temperature=0)
    prompt = _SYSTEM_PROMPT.format(history=history, input=state["input"])
    raw = llm.invoke(prompt).content
    # Take only the first non-empty line to avoid verbose LLM output
    first_line = next(
        (
            ln.strip()
            for ln in (raw if isinstance(raw, str) else str(raw)).splitlines()
            if ln.strip()
        ),
        "final",
    ).lower()

    log.debug("planner.decision", next_step=first_line)
    return {"next_step": first_line}
