from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, generate_latest

app = FastAPI(title="Agent Platform")
request_count = Counter("http_requests_total", "Total HTTP requests")


@app.get("/health")
async def health() -> dict[str, str]:
    request_count.inc()
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest().decode("utf-8"))