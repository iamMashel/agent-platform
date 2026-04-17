import contextlib
import time
import uuid
from datetime import UTC, datetime
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
_GRAPH_NODE_NAMES = {"planner", "tool", "synth"}


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


def _prompt_text(llm_input: Any) -> str:
    """Extract the human-readable prompt string from LangChain LLM input."""
    with contextlib.suppress(Exception):
        msgs = llm_input.get("messages", [[]])
        if msgs and msgs[0]:
            return str(getattr(msgs[0][-1], "content", msgs[0][-1]))[:2000]
    return str(llm_input)[:2000]


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

    # ── Langfuse init ────────────────────────────────────────────────────────
    lf_client = None
    lf_trace = None
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        with contextlib.suppress(Exception):
            from langfuse import Langfuse  # type: ignore[import-untyped]

            lf_client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
            lf_trace = lf_client.trace(
                name=_LANGFUSE_TRACE_NAME,
                user_id=body.user_id,
                session_id=thread_id,
                tags=[settings.environment, settings.llm_provider],
                input={"user_message": body.input},
                metadata={"thread_id": thread_id, "llm_provider": settings.llm_provider},
            )

    # ── Stream graph events → collect result + build Langfuse trace ──────────
    # Keyed by LangGraph run_id so we can match start/end pairs.
    _node_spans: dict[str, Any] = {}
    _gen_start: dict[str, datetime] = {}
    _gen_parent: dict[str, Any] = {}  # run_id → parent span (or None)
    result: dict[str, Any] = {}

    start = time.perf_counter()

    async for ev in request.app.state.agent.astream_events(
        cast(AgentState, state), config=invoke_config, version="v2"
    ):
        kind: str = ev["event"]
        name: str = ev.get("name", "")
        run_id: str = str(ev.get("run_id", ""))
        parent_run_id: str = str(ev.get("parent_run_id") or "")
        data: dict[str, Any] = ev.get("data", {})

        # ── Node start ───────────────────────────────────────────────────────
        if kind == "on_chain_start" and name in _GRAPH_NODE_NAMES and lf_trace:
            with contextlib.suppress(Exception):
                _node_spans[run_id] = lf_trace.span(
                    name=name,
                    input=data.get("input"),
                    start_time=datetime.now(tz=UTC),
                    metadata={"node": name},
                )

        # ── Node end ─────────────────────────────────────────────────────────
        elif kind == "on_chain_end" and name in _GRAPH_NODE_NAMES and lf_trace:
            span = _node_spans.pop(run_id, None)
            with contextlib.suppress(Exception):
                if span:
                    span.end(
                        output=data.get("output"),
                        end_time=datetime.now(tz=UTC),
                    )

        # ── LLM call start ───────────────────────────────────────────────────
        elif kind == "on_chat_model_start":
            _gen_start[run_id] = datetime.now(tz=UTC)
            _gen_parent[run_id] = _node_spans.get(parent_run_id)

        # ── LLM call end — captures prompt, output, tokens, latency ─────────
        elif kind == "on_chat_model_end" and lf_trace:
            gen_start = _gen_start.pop(run_id, None)
            parent_span = _gen_parent.pop(run_id, None)
            if gen_start is None:
                continue

            ai_msg = data.get("output")
            text_out = str(getattr(ai_msg, "content", "")) if ai_msg else ""
            usage_meta: dict[str, int] = getattr(ai_msg, "usage_metadata", None) or {}

            with contextlib.suppress(Exception):
                gen_kwargs: dict[str, Any] = {
                    "name": f"{name}-generation",
                    "model": name,  # model class / deployment name
                    "input": _prompt_text(data.get("input")),
                    "output": text_out,
                    "start_time": gen_start,
                    "end_time": datetime.now(tz=UTC),
                    "usage": {
                        "input": usage_meta.get("input_tokens", 0),
                        "output": usage_meta.get("output_tokens", 0),
                        "total": usage_meta.get("total_tokens", 0),
                    },
                }
                if parent_span is not None:
                    parent_span.generation(**gen_kwargs)
                else:
                    lf_trace.generation(**gen_kwargs)

        # ── Tool call start ──────────────────────────────────────────────────
        elif kind == "on_tool_start" and lf_trace:
            parent_span = _node_spans.get(parent_run_id)
            with contextlib.suppress(Exception):
                span_kwargs: dict[str, Any] = {
                    "name": f"tool:{name}",
                    "input": data.get("input"),
                    "start_time": datetime.now(tz=UTC),
                    "metadata": {"tool": name},
                }
                _node_spans[run_id] = (
                    parent_span.span(**span_kwargs) if parent_span else lf_trace.span(**span_kwargs)
                )

        # ── Tool call end ────────────────────────────────────────────────────
        elif kind == "on_tool_end" and lf_trace:
            span = _node_spans.pop(run_id, None)
            with contextlib.suppress(Exception):
                if span:
                    span.end(
                        output=data.get("output"),
                        end_time=datetime.now(tz=UTC),
                    )

        # ── Graph end — grab final state ─────────────────────────────────────
        elif kind == "on_chain_end":
            output = data.get("output", {})
            if isinstance(output, dict) and "final_output" in output:
                result = output

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

    # ── Finalise Langfuse trace ──────────────────────────────────────────────
    if lf_trace is not None:
        with contextlib.suppress(Exception):
            lf_trace.update(
                output=result.get("final_output"),
                metadata={
                    "duration_ms": duration_ms,
                    "tool_used": tool_used,
                    "llm_provider": settings.llm_provider,
                },
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
