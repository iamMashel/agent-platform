from fastapi import APIRouter
from services.agent.graph.workflow import build_graph
from langfuse.langchain import CallbackHandler
from apps.api.metrics import AGENT_RUNS

router = APIRouter()
agent = build_graph()
langfuse_handler = CallbackHandler()


@router.post("/agent/run")
async def run_agent(payload: dict):
    state = {
        "input": payload["input"],
        "messages": [],
        "next_step": None,
        "tool_result": None,
        "final_output": None,
    }

    AGENT_RUNS.inc()
    result = agent.invoke(state, config={"callbacks": [langfuse_handler]})

    return {
        "input": payload["input"],
        "output": result["final_output"],
        "tool_result": result.get("tool_result"),
    }
