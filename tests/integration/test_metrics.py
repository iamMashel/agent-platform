"""Integration tests verifying Prometheus metrics are correctly emitted."""

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_metrics_endpoint_returns_200() -> None:
    response = client.get("/metrics")
    assert response.status_code == 200


def test_metrics_content_type_is_text() -> None:
    response = client.get("/metrics")
    assert "text/plain" in response.headers["content-type"]


def test_http_requests_counter_present() -> None:
    client.get("/health")
    metrics = client.get("/metrics").text
    assert "http_requests_total" in metrics


def test_agent_runs_counter_present() -> None:
    metrics = client.get("/metrics").text
    assert "agent_runs_total" in metrics


def test_histogram_buckets_present() -> None:
    metrics = client.get("/metrics").text
    assert "http_request_duration_seconds_bucket" in metrics
