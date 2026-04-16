from __future__ import annotations

import os

import structlog

from services.agent.graph.state import AgentState

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


def _get_llm():
    """Lazy LLM factory — avoids import-time side effects for tests."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    from apps.api.config import settings

    if settings.google_api_key:
        os.environ["GOOGLE_API_KEY"] = settings.google_api_key

    return ChatGoogleGenerativeAI(model=settings.gemini_model, temperature=0)


def planner_node(state: AgentState) -> dict[str, str | list[str] | None]:
    history = "\n".join(state["messages"]) if state["messages"] else "(no prior messages)"
    log.debug(
        "planner.start", input_length=len(state["input"]), history_turns=len(state["messages"])
    )

    llm = _get_llm()
    prompt = _SYSTEM_PROMPT.format(history=history, input=state["input"])
    raw = llm.invoke(prompt).content
    response = (raw if isinstance(raw, str) else str(raw)).strip().lower()

    log.debug("planner.decision", next_step=response)
    # Append the user turn to messages so it persists across turns
    return {"next_step": response, "messages": [f"User: {state['input']}"]}
