from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest

from apps.api.agent import router as agent_router
from apps.api.config import settings
from apps.api.logging_config import configure_logging
from apps.api.middleware import ObservabilityMiddleware

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.environment)
    log.info("startup", app=settings.app_name, env=settings.environment)
    yield
    log.info("shutdown", app=settings.app_name)


app = FastAPI(
    title="Agent Platform",
    description="Production-grade AI agent platform with LangGraph orchestration",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(ObservabilityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name, "env": settings.environment}


@app.get("/metrics", tags=["ops"], response_class=PlainTextResponse)
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest().decode("utf-8"))
