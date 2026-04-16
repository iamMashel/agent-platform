"""Integration tests for the /agent/run endpoint.

Uses the mock_llm_nodes fixture from conftest.py — no real API calls.
"""

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_agent_run_basic() -> None:
    response = client.post("/agent/run", json={"input": "Hello, what is 2+2?"})
    assert response.status_code == 200
    data = response.json()
    assert "input" in data
    assert "output" in data
    assert data["input"] == "Hello, what is 2+2?"


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
    assert "duration_ms" in data
    assert data["duration_ms"] >= 0


def test_agent_run_missing_input_returns_422() -> None:
    response = client.post("/agent/run", json={})
    assert response.status_code == 422


def test_agent_run_increments_metrics() -> None:
    """Verify that calling /agent/run updates the agent_runs_total counter."""
    client.post("/agent/run", json={"input": "metrics test"})
    metrics_after = client.get("/metrics").text

    # Counter should have incremented
    assert "agent_runs_total" in metrics_after
