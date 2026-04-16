from services.agent.tools.mock_tool import search_tool
from apps.api.metrics import TOOL_EXECUTIONS


def tool_node(state):
    TOOL_EXECUTIONS.inc()
    query = state["input"]
    result = search_tool(query)

    return {"tool_result": result}