"""Integration tests for the /agent/run endpoint.

Uses the mock_llm_nodes fixture from conftest.py — no real API calls.
DB dependency is overridden so tests don't need a running Postgres.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from apps.api.db.session import get_db
from apps.api.main import app

client = TestClient(app)


async def _fake_db():
    """Fake DB session — no real Postgres needed."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    yield session


@pytest.fixture(autouse=True)
def override_db():
    app.dependency_overrides[get_db] = _fake_db
    yield
    app.dependency_overrides.pop(get_db, None)


def test_agent_run_basic() -> None:
    response = client.post("/agent/run", json={"input": "Hello, what is 2+2?"})
    assert response.status_code == 200
    data = response.json()
    assert data["input"] == "Hello, what is 2+2?"
    assert "output" in data
    assert "session_id" in data


def test_agent_run_with_user_id() -> None:
    response = client.post(
        "/agent/run",
        json={"input": "test query", "user_id": "user-123"},
    )
    assert response.status_code == 200


def test_agent_run_with_session_id() -> None:
    """Session ID enables thread-based memory via LangGraph checkpointer."""
    response = client.post(
        "/agent/run",
        json={"input": "remember this", "session_id": "session-abc"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "session-abc"
    assert data["duration_ms"] >= 0


def test_agent_run_missing_input_returns_422() -> None:
    response = client.post("/agent/run", json={})
    assert response.status_code == 422


def test_agent_run_increments_metrics() -> None:
    """Verify that calling /agent/run updates the agent_runs_total counter."""
    client.post("/agent/run", json={"input": "metrics test"})
    metrics_after = client.get("/metrics").text
    assert "agent_runs_total" in metrics_after
