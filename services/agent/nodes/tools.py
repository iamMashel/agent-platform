from __future__ import annotations

import structlog

from apps.api.metrics import TOOL_EXECUTIONS
from services.agent.graph.state import AgentState
from services.agent.tools.search import search_tool

log = structlog.get_logger(__name__)


def tool_node(state: AgentState) -> dict[str, str | None]:
    query = state["input"]
    log.info("tool.execute", tool="search", query=query)
    TOOL_EXECUTIONS.labels(tool_name="search").inc()
    result = search_tool.invoke({"query": query})
    log.debug("tool.result", tool="search", result_length=len(result))
    return {"tool_result": result}
