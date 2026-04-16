from __future__ import annotations

import os

import structlog

from services.agent.graph.state import AgentState

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """\
You are a planner agent. Decide whether the user's request requires an external search \
or can be answered directly.

Respond with EXACTLY one of:
- "tool:search"   — if the user needs up-to-date or external information
- "final"         — if the user's request can be answered from your own knowledge

User input: {input}
"""


def _get_llm():
    """Lazy LLM factory — avoids import-time side effects for tests."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    from apps.api.config import settings

    if settings.google_api_key:
        os.environ["GOOGLE_API_KEY"] = settings.google_api_key

    return ChatGoogleGenerativeAI(model=settings.gemini_model, temperature=0)


def planner_node(state: AgentState) -> dict[str, str | None]:
    log.debug("planner.start", input_length=len(state["input"]))
    llm = _get_llm()
    prompt = _SYSTEM_PROMPT.format(input=state["input"])
    raw = llm.invoke(prompt).content
    response = (raw if isinstance(raw, str) else str(raw)).strip().lower()
    log.debug("planner.decision", next_step=response)
    return {"next_step": response}
