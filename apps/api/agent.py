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

    # ── Langfuse v3 init ─────────────────────────────────────────────────────
    # Langfuse() sets up the OTel tracer provider.
    # CallbackHandler() attaches to the LangGraph invocation via the callbacks
    # list and automatically captures node spans, LLM generations (prompt +
    # output + tokens + latency), and tool calls.
    # update_current_trace() sets user/session metadata on the active trace.
    lf_client: Any = None
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        with contextlib.suppress(Exception):
            from langfuse import Langfuse  # type: ignore[import-untyped]
            from langfuse.langchain import CallbackHandler  # type: ignore[import-untyped]

            lf_client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
            invoke_config["callbacks"] = [CallbackHandler()]

    # ── Run agent ────────────────────────────────────────────────────────────
    start = time.perf_counter()
    result: dict[str, Any] = {}

    if lf_client is not None:
        # Wrap invocation in a root observation so user/session/tags are
        # attached to the trace and all child spans inherit the context.
        async with lf_client.start_as_current_observation(
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
