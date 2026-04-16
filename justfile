# Agent Platform — task runner
# Install: cargo install just  OR  brew install just

# ── Dev ───────────────────────────────────────────────────────────────────────
dev:
    uv run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

dev-web:
    cd apps/web && npm run dev

# ── Quality ───────────────────────────────────────────────────────────────────
lint:
    uv run ruff check .

lint-fix:
    uv run ruff check --fix .

format:
    uv run ruff format .

format-check:
    uv run ruff format --check .

typecheck:
    uv run pyright

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
    uv run pytest tests/unit tests/integration -v

test-evals:
    uv run pytest tests/evals -v -m eval

test-cov:
    uv run pytest tests/unit tests/integration --cov=apps --cov=services --cov-report=term-missing

# ── CI gate (mirrors CI pipeline) ────────────────────────────────────────────
ci: lint format-check typecheck test

# ── Docker ───────────────────────────────────────────────────────────────────
up:
    docker compose up --build -d

down:
    docker compose down

logs:
    docker compose logs -f api

build:
    docker build -t agent-platform/api:local -f infra/docker/Dockerfile .

# ── Deps ─────────────────────────────────────────────────────────────────────
sync:
    uv sync --locked

add dep:
    uv add {{dep}}

add-dev dep:
    uv add --dev {{dep}}
