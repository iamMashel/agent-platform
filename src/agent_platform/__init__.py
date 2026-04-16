"""Agent Platform — entry point for `uv run agent-platform`."""


def main() -> None:
    import uvicorn

    uvicorn.run(
        "apps.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_config=None,  # structlog handles logging
    )
