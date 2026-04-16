import time
import uuid
from typing import cast

import structlog
from fastapi import APIRouter
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from apps.api.config import settings
from apps.api.metrics import AGENT_RUNS, agent_run_duration_seconds
from services.agent.graph.state import AgentState
from services.agent.graph.workflow import build_graph

router = APIRouter(prefix="/agent", tags=["agent"])
log = structlog.get_logger(__name__)

# Compiled graph (singleton)
_agent = build_graph()


class AgentRequest(BaseModel):
    input: str
    user_id: str = "anonymous"
    session_id: str | None = None


class AgentResponse(BaseModel):
    input: str
    output: str | None
    tool_result: str | None
    duration_ms: float


@router.post("/run", response_model=AgentResponse)
async def run_agent(request: AgentRequest) -> AgentResponse:
    AGENT_RUNS.inc()
    log.info("agent.run.start", user_id=request.user_id, input_length=len(request.input))

    state = {
        "input": request.input,
        "messages": [],
        "next_step": None,
        "tool_result": None,
        "final_output": None,
    }

    invoke_config: dict = {}

    # Langfuse tracing — one handler per request for isolated traces
    langfuse_handler = None
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        from langfuse.langchain import CallbackHandler  # type: ignore[import-untyped]

        lf_kwargs: dict[str, object] = {
            "public_key": settings.langfuse_public_key,
            "secret_key": settings.langfuse_secret_key,
            "host": settings.langfuse_host,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "trace_name": "agent-workflow",
            "tags": [settings.environment],
        }
        langfuse_handler = CallbackHandler(**lf_kwargs)  # type: ignore[arg-type]
        invoke_config["callbacks"] = [langfuse_handler]

    # MemorySaver checkpointer requires thread_id.
    # Use session_id for persistent cross-turn memory; fall back to a per-request UUID.
    thread_id = request.session_id or str(uuid.uuid4())
    invoke_config.setdefault("configurable", {})["thread_id"] = thread_id

    start = time.perf_counter()
    result = _agent.invoke(cast(AgentState, state), config=cast(RunnableConfig, invoke_config))
    duration = time.perf_counter() - start

    agent_run_duration_seconds.observe(duration)
    duration_ms = round(duration * 1000, 2)

    log.info(
        "agent.run.complete",
        user_id=request.user_id,
        duration_ms=duration_ms,
        tool_used=result.get("tool_result") is not None,
    )

    if langfuse_handler is not None:
        langfuse_handler.langfuse.flush()

    return AgentResponse(
        input=request.input,
        output=result.get("final_output"),
        tool_result=result.get("tool_result"),
        duration_ms=duration_ms,
    )
