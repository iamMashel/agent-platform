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

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.environment)
    log.info("startup", app=settings.app_name, env=settings.environment, llm=settings.llm_provider)

    try:
        from apps.api.db.session import create_tables

        await create_tables()
    except Exception as exc:
        log.warning("db.init.skipped", reason=str(exc))

    yield

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
