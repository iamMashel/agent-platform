from __future__ import annotations

import structlog
from langchain_core.runnables import RunnableConfig

from apps.api.metrics import TOOL_EXECUTIONS
from services.agent.graph.state import AgentState
from services.agent.tools.search import search_tool

log = structlog.get_logger(__name__)


def tool_node(state: AgentState, config: RunnableConfig) -> dict[str, str | None]:
    # Planner may embed a refined query after the colon: "tool:search bitcoin price"
    # Fall back to the raw user input when no query is specified.
    next_step = state.get("next_step") or ""
    suffix = (
        next_step[len("tool:search") :].strip()
        if next_step.lower().startswith("tool:search")
        else ""
    )
    query = suffix if suffix else state["input"]
    log.info("tool.execute", tool="search", query=query)
    TOOL_EXECUTIONS.labels(tool_name="search").inc()
    result = search_tool.invoke({"query": query}, config=config)
    log.debug("tool.result", tool="search", result_length=len(result))
    return {"tool_result": result}
