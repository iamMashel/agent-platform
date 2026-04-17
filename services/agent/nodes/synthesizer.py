from __future__ import annotations

import structlog
from langchain_core.runnables import RunnableConfig

from services.agent.graph.state import AgentState, format_history
from services.agent.llm import get_llm

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """\
You are a helpful assistant. Use the conversation history and any tool result to answer the user.

Conversation history:
{history}

Tool result (if any): {tool_result}

User message: {input}

Provide a clear, concise answer.
"""


def synth_node(
    state: AgentState, config: RunnableConfig | None = None
) -> dict[str, str | list[str] | None]:
    history = format_history(state)
    log.debug("synth.start", has_tool_result=state.get("tool_result") is not None)

    llm = get_llm()
    prompt = _SYSTEM_PROMPT.format(
        history=history,
        tool_result=state.get("tool_result") or "N/A",
        input=state["input"],
    )
    raw = llm.invoke(prompt, config=config).content
    response = raw if isinstance(raw, str) else str(raw)

    log.debug("synth.complete", output_length=len(response))
    return {
        "final_output": response,
        "messages": [f"User: {state['input']}", f"Assistant: {response}"],
    }
