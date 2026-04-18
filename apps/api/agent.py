import contextlib
import time
import uuid
from typing import Any, cast

import structlog
from fastapi import APIRouter, BackgroundTasks, Request
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from apps.api.config import settings
from apps.api.db.models import AgentRun
from apps.api.db.session import AsyncSessionLocal
from apps.api.metrics import AGENT_RUNS, agent_run_duration_seconds
from apps.api.security import RequireApiKey, limiter
from services.agent.graph.state import AgentState

router = APIRouter(prefix="/agent", tags=["agent"])
log = structlog.get_logger(__name__)

_LANGFUSE_TRACE_NAME = "agent-workflow"


class AgentRequest(BaseModel):
    input: str
    user_id: str = "anonymous"
    session_id: str | None = None


class AgentResponse(BaseModel):
    input: str
    output: str | None
    tool_result: str | None
    duration_ms: float
    session_id: str


async def _persist_run(run: AgentRun) -> None:
    try:
        async with AsyncSessionLocal() as session:
            session.add(run)
            await session.commit()
    except Exception as exc:
        log.warning("agent.run.db_write_failed", error=str(exc))


@router.post("/run", response_model=AgentResponse, dependencies=[RequireApiKey])
@limiter.limit(settings.rate_limit)
async def run_agent(
    request: Request,
    body: AgentRequest,
    background_tasks: BackgroundTasks,
) -> AgentResponse:
    AGENT_RUNS.inc()
    thread_id = body.session_id or str(uuid.uuid4())
    log.info(
        "agent.run.start", user_id=body.user_id, input_length=len(body.input), thread_id=thread_id
    )

    state: AgentState = {
        "input": body.input,
        "messages": [],
        "next_step": None,
        "tool_result": None,
        "final_output": None,
    }

    invoke_config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

    # ── Run agent ────────────────────────────────────────────────────────────
    # Use the single Langfuse client initialised at startup (app.state.langfuse).
    # CallbackHandler is created INSIDE start_as_current_observation so that the
    # active OTel span is already set when the handler builds its child spans —
    # this is what makes node/LLM observations appear nested under the root trace.
    lf_client: Any = getattr(request.app.state, "langfuse", None)

    start = time.perf_counter()
    result: dict[str, Any] = {}

    if lf_client is not None:
        with lf_client.start_as_current_observation(
            name=_LANGFUSE_TRACE_NAME,
            as_type="span",
            input={"user_message": body.input},
        ) as root_obs:
            with contextlib.suppress(Exception):
                lf_client.update_current_trace(
                    name=_LANGFUSE_TRACE_NAME,
                    user_id=body.user_id,
                    session_id=thread_id,
                    tags=[settings.environment, settings.llm_provider],
                    metadata={"thread_id": thread_id, "llm_provider": settings.llm_provider},
                )
            # Create CallbackHandler here, after the parent span is active,
            # so LangGraph node spans are captured as children of root_obs.
            with contextlib.suppress(Exception):
                from langfuse.langchain import CallbackHandler  # type: ignore[import-untyped]

                invoke_config["callbacks"] = [CallbackHandler()]

            result = await request.app.state.agent.ainvoke(
                cast(AgentState, state), config=invoke_config
            )
            with contextlib.suppress(Exception):
                root_obs.update(output=result.get("final_output"))
    else:
        result = await request.app.state.agent.ainvoke(
            cast(AgentState, state), config=invoke_config
        )

    duration = time.perf_counter() - start
    agent_run_duration_seconds.observe(duration)
    duration_ms = round(duration * 1000, 2)

    tool_used = result.get("tool_result") is not None
    log.info(
        "agent.run.complete",
        user_id=body.user_id,
        duration_ms=duration_ms,
        tool_used=tool_used,
        thread_id=thread_id,
    )

    if lf_client is not None:
        background_tasks.add_task(lf_client.flush)

    background_tasks.add_task(
        _persist_run,
        AgentRun(
            session_id=thread_id,
            user_id=body.user_id,
            input=body.input,
            output=result.get("final_output"),
            tool_result=result.get("tool_result"),
            tool_used=tool_used,
            duration_ms=duration_ms,
            llm_provider=settings.llm_provider,
        ),
    )

    return AgentResponse(
        input=body.input,
        output=result.get("final_output"),
        tool_result=result.get("tool_result"),
        duration_ms=duration_ms,
        session_id=thread_id,
    )
