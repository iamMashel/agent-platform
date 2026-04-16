# ── Stage 1: dependency resolver ─────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Copy lockfile + manifest first for layer caching
COPY pyproject.toml uv.lock README.md ./

# Install only production deps into a virtualenv
RUN uv sync --locked --no-dev --no-install-project

# Copy source
COPY apps/ apps/
COPY services/ services/
COPY src/ src/

# Install the project itself
RUN uv sync --locked --no-dev

# ── Stage 2: lean runtime image ───────────────────────────────────────────────
FROM python:3.12-slim

LABEL org.opencontainers.image.title="agent-platform" \
      org.opencontainers.image.description="Production AI agent platform" \
      org.opencontainers.image.source="https://github.com/mashelodera/agent-platform"

WORKDIR /app

# Non-root user
RUN groupadd --system app && useradd --system --gid app app

# Copy built artefacts from builder
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

USER app

EXPOSE 8000

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--no-access-log"]
