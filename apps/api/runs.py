"""Agent run history — read endpoints for stored runs."""

from __future__ import annotations

import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_serializer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.models import AgentRun
from apps.api.db.session import get_db

router = APIRouter(prefix="/runs", tags=["runs"])
log = structlog.get_logger(__name__)


class RunOut(BaseModel):
    id: uuid.UUID
    session_id: str
    user_id: str
    input: str
    output: str | None
    tool_used: bool
    duration_ms: float
    llm_provider: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("created_at")
    def _serialize_created_at(self, v: datetime) -> str:
        return v.isoformat()


@router.get("", response_model=list[RunOut])
async def list_runs(
    user_id: str | None = Query(None),
    session_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[RunOut]:
    stmt = select(AgentRun).order_by(AgentRun.created_at.desc()).limit(limit)
    if user_id:
        stmt = stmt.where(AgentRun.user_id == user_id)
    if session_id:
        stmt = stmt.where(AgentRun.session_id == session_id)

    rows = (await db.execute(stmt)).scalars().all()
    return [RunOut.model_validate(r) for r in rows]


@router.get("/{run_id}", response_model=RunOut)
async def get_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> RunOut:
    row = await db.get(AgentRun, run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return RunOut.model_validate(row)
