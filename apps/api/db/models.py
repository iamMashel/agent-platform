"""SQLAlchemy ORM models for agent run history."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, default="anonymous")
    input: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_used: Mapped[bool] = mapped_column(default=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    llm_provider: Mapped[str] = mapped_column(String(32), default="gemini")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
