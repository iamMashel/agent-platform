import time
import uuid
from typing import cast

import structlog
from fastapi import APIRouter, Depends, Request
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import settings
from apps.api.db.models import AgentRun
from apps.api.db.session import get_db
from apps.api.metrics import AGENT_RUNS, agent_run_duration_seconds
from apps.api.security import RequireApiKey, limiter
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
    session_id: str


@router.post("/run", response_model=AgentResponse, dependencies=[RequireApiKey])
@limiter.limit(settings.rate_limit)
async def run_agent(
    request: Request,
    body: AgentRequest,
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    AGENT_RUNS.inc()
    thread_id = body.session_id or str(uuid.uuid4())
    log.info(
        "agent.run.start", user_id=body.user_id, input_length=len(body.input), thread_id=thread_id
    )

    state = {
        "input": body.input,
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
            "user_id": body.user_id,
            "session_id": thread_id,
            "trace_name": "agent-workflow",
            "tags": [settings.environment, settings.llm_provider],
        }
        langfuse_handler = CallbackHandler(**lf_kwargs)  # type: ignore[arg-type]
        invoke_config["callbacks"] = [langfuse_handler]

    invoke_config.setdefault("configurable", {})["thread_id"] = thread_id

    start = time.perf_counter()
    result = _agent.invoke(cast(AgentState, state), config=cast(RunnableConfig, invoke_config))
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

    if langfuse_handler is not None:
        langfuse_handler.langfuse.flush()

    # Persist run to DB (best-effort — don't fail the response on DB error)
    try:
        db.add(
            AgentRun(
                session_id=thread_id,
                user_id=body.user_id,
                input=body.input,
                output=result.get("final_output"),
                tool_result=result.get("tool_result"),
                tool_used=tool_used,
                duration_ms=duration_ms,
                llm_provider=settings.llm_provider,
            )
        )
        await db.commit()
    except Exception as exc:
        log.warning("agent.run.db_write_failed", error=str(exc))

    return AgentResponse(
        input=body.input,
        output=result.get("final_output"),
        tool_result=result.get("tool_result"),
        duration_ms=duration_ms,
        session_id=thread_id,
    )
