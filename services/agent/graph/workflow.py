from langgraph.graph import StateGraph, END

from services.agent.graph.state import AgentState
from services.agent.nodes.planner import planner_node
from services.agent.nodes.tools import tool_node
from services.agent.nodes.synthesizer import synth_node


def build_graph():
    graph = StateGraph(AgentState)

    # nodes
    graph.add_node("planner", planner_node)
    graph.add_node("tool", tool_node)
    graph.add_node("synth", synth_node)

    # entry
    graph.set_entry_point("planner")

    # routing logic
    def route(state):
        if state["next_step"] and "tool" in state["next_step"]:
            return "tool"
        return "synth"

    graph.add_conditional_edges("planner", route)

    graph.add_edge("tool", "synth")
    graph.add_edge("synth", END)

    return graph.compile()
