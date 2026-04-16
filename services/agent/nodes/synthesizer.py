from __future__ import annotations

import os

import structlog

from services.agent.graph.state import AgentState

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """\
You are a helpful assistant. Produce a clear, concise answer for the user.

User input: {input}
Tool result: {tool_result}
"""


def _get_llm():
    """Lazy LLM factory — avoids import-time side effects for tests."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    from apps.api.config import settings

    if settings.google_api_key:
        os.environ["GOOGLE_API_KEY"] = settings.google_api_key

    return ChatGoogleGenerativeAI(model=settings.gemini_model)


def synth_node(state: AgentState) -> dict[str, str | None]:
    log.debug("synth.start", has_tool_result=state.get("tool_result") is not None)
    llm = _get_llm()
    prompt = _SYSTEM_PROMPT.format(
        input=state["input"],
        tool_result=state.get("tool_result") or "N/A",
    )
    raw = llm.invoke(prompt).content
    response = raw if isinstance(raw, str) else str(raw)
    log.debug("synth.complete", output_length=len(response))
    return {"final_output": response}
