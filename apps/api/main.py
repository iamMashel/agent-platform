import contextlib
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from apps.api.agent import router as agent_router
from apps.api.config import settings
from apps.api.logging_config import configure_logging
from apps.api.middleware import ObservabilityMiddleware
from apps.api.runs import router as runs_router
from apps.api.security import limiter
from services.agent.graph.workflow import build_graph

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.environment)
    log.info("startup", app=settings.app_name, env=settings.environment, llm=settings.llm_provider)

    try:
        import asyncio

        from alembic import command as alembic_command
        from alembic.config import Config as AlembicConfig

        alembic_cfg = AlembicConfig("alembic.ini")
        await asyncio.to_thread(alembic_command.upgrade, alembic_cfg, "head")
        log.info("db.migrations.applied")
    except Exception as exc:
        log.warning("db.migrations.skipped", reason=str(exc))

    # Initialize Langfuse once at startup so the OTel tracer provider is set up
    # exactly once. Re-creating Langfuse() per request resets the OTel context
    # and breaks parent-span propagation for child observations.
    app.state.langfuse = None
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        with contextlib.suppress(Exception):
            from langfuse import Langfuse  # type: ignore[import-untyped]

            app.state.langfuse = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
            log.info("tracing.backend", backend="langfuse", host=settings.langfuse_host)

    # Build agent graph with Postgres checkpointer for persistent memory.
    # Uses the same agentdb already running; falls back to MemorySaver if unavailable.
    # AsyncPostgresSaver uses psycopg3 connection format (no +asyncpg prefix).
    pg_conn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    try:
        from langgraph.checkpoint.postgres.aio import (
            AsyncPostgresSaver,  # type: ignore[import-untyped]
        )

        checkpointer_ctx = AsyncPostgresSaver.from_conn_string(pg_conn)
        checkpointer = await checkpointer_ctx.__aenter__()
        await checkpointer.setup()
        app.state.agent = build_graph(checkpointer=checkpointer)
        app.state.checkpointer_ctx = checkpointer_ctx
        log.info("memory.backend", backend="postgres")
    except Exception as exc:
        log.warning("memory.postgres.unavailable", error=str(exc), fallback="MemorySaver")
        app.state.agent = build_graph()
        app.state.checkpointer_ctx = None

    yield

    lf = getattr(app.state, "langfuse", None)
    if lf is not None:
        with contextlib.suppress(Exception):
            lf.flush()

    ctx = getattr(app.state, "checkpointer_ctx", None)
    if ctx is not None:
        try:  # noqa: SIM105
            await ctx.__aexit__(None, None, None)
        except Exception:
            pass

    try:
        from apps.api.db.session import close_engine

        await close_engine()
    except Exception:
        pass

    log.info("shutdown", app=settings.app_name)


app = FastAPI(
    title="Agent Platform",
    description="Production-grade AI agent platform with LangGraph orchestration",
    version="0.2.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.add_middleware(SlowAPIMiddleware)
app.add_middleware(ObservabilityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)
app.include_router(runs_router)


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.environment,
        "llm": settings.llm_provider,
    }


@app.get("/metrics", tags=["ops"], response_class=PlainTextResponse)
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest().decode("utf-8"))
