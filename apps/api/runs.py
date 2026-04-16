"""Agent run history — read endpoints for stored runs."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
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
    created_at: str

    model_config = {"from_attributes": True}


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
    return [
        RunOut(
            id=r.id,
            session_id=r.session_id,
            user_id=r.user_id,
            input=r.input,
            output=r.output,
            tool_used=r.tool_used,
            duration_ms=r.duration_ms,
            llm_provider=r.llm_provider,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.get("/{run_id}", response_model=RunOut)
async def get_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> RunOut:
    row = await db.get(AgentRun, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunOut(
        id=row.id,
        session_id=row.session_id,
        user_id=row.user_id,
        input=row.input,
        output=row.output,
        tool_used=row.tool_used,
        duration_ms=row.duration_ms,
        llm_provider=row.llm_provider,
        created_at=row.created_at.isoformat(),
    )
