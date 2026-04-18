from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from services.agent.graph.state import AgentState
from services.agent.nodes.planner import planner_node
from services.agent.nodes.synthesizer import synth_node
from services.agent.nodes.tools import tool_node


def _route(state: AgentState) -> str:
    next_step = (state.get("next_step") or "").strip().lower()
    return "tool" if next_step.startswith("tool:") else "synth"


def build_graph(checkpointer: Any = None) -> Any:
    """Build and compile the agent LangGraph workflow.

    Args:
        checkpointer: Optional LangGraph checkpointer for persistent memory.
                      Defaults to MemorySaver (in-process, suitable for dev/test).
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("tool", tool_node)
    graph.add_node("synth", synth_node)

    graph.set_entry_point("planner")
    graph.add_conditional_edges("planner", _route)
    graph.add_edge("tool", "synth")
    graph.add_edge("synth", END)

    return graph.compile(checkpointer=checkpointer)
