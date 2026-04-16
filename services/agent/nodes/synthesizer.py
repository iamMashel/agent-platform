from __future__ import annotations

import structlog

from services.agent.graph.state import AgentState

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """\
You are a helpful assistant. Use the conversation history and any tool result to answer the user.

Conversation history:
{history}

Tool result (if any): {tool_result}

User message: {input}

Provide a clear, concise answer.
"""


def _get_llm():
    """Lazy LLM factory — avoids import-time side effects for tests."""
    from services.agent.llm import get_llm

    return get_llm()


def synth_node(state: AgentState) -> dict[str, str | list[str] | None]:
    history = "\n".join(state["messages"]) if state["messages"] else "(no prior messages)"
    log.debug("synth.start", has_tool_result=state.get("tool_result") is not None)

    llm = _get_llm()
    prompt = _SYSTEM_PROMPT.format(
        history=history,
        tool_result=state.get("tool_result") or "N/A",
        input=state["input"],
    )
    raw = llm.invoke(prompt).content
    response = raw if isinstance(raw, str) else str(raw)

    log.debug("synth.complete", output_length=len(response))
    # Append the assistant turn so it's available in the next session
    return {"final_output": response, "messages": [f"Assistant: {response}"]}
