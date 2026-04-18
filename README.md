# Agent Platform

![CI](https://img.shields.io/github/actions/workflow/status/iamMashel/agent-platform/ci.yml?label=CI)
![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/github/license/iamMashel/agent-platform)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![Observability](https://img.shields.io/badge/observability-prometheus-orange)
![Tracing](https://img.shields.io/badge/tracing-langfuse-purple)

**Production-grade AI agent platform** built with FastAPI, LangGraph, Nuxt 3, Langfuse, and Prometheus.

> Building AI agents is easy. Operating them reliably in production is hard.  
> Agent Platform provides the missing engineering layer: orchestration, observability, evaluation pipelines, and deployment guardrails — with support for 100+ LLM providers via LiteLLM.

---

## Features

- **Multi-provider LLM support** via LiteLLM — swap between Gemini, DeepSeek, Claude, GPT-4o, Groq, Ollama, and 100+ more with a single env var change, zero code changes
- **Split planner model** — route the one-token routing decision to a cheap/fast model (`PLANNER_MODEL`) while keeping a capable model for synthesis; falls back to the same model if unset
- **LLM retry with jitter** — all LLM calls automatically retry up to 3× with exponential backoff and random jitter, handling transient rate-limit and network errors
- **FastAPI** production API with structured JSON logging and request-ID tracing
- **LangGraph** workflow: `planner → tool → synthesizer` state machine with persistent memory across turns
- **History truncation** — only the most recent 10 turns are sent to the LLM; full history is preserved in the Postgres checkpoint
- **DuckDuckGo search** — real web search with no API key required
- **Postgres** run history and LangGraph checkpoints — every agent run persisted for audit and replay; persistent multi-turn memory per session
- **Alembic** database migrations — schema changes are versioned and applied automatically at startup
- **Langfuse** LLM tracing — full trace context, node-level spans nested under a root trace per request
- **Prometheus + Grafana** — request rate, latency histograms (p50/p95/p99), agent run duration, tool execution counts
- **Nuxt 3 frontend** — dark-mode chat UI + live status dashboard with 120s request timeout and clear error messages
- **Docker Compose** 11-container stack — API, frontend, Redis, Postgres, Langfuse (web + worker + ClickHouse + MinIO), Prometheus, Grafana
- **uv** — fast, reproducible Python dependency management
- **Ruff + Pyright** — lint, format, and strict type checking
- **pytest** — unit, integration, and eval suites with automatic LLM mocking
- **GitHub Actions** — 6-job parallel CI (lint → typecheck → unit → integration → docker → frontend)
- **SlowAPI** — per-IP rate limiting on `/agent/run`
- **pre-commit** hooks

---

## Architecture

```
Browser / Client
      │
      ▼
  Nuxt 3 Frontend  (port 3002)
      │
      ▼
  FastAPI  ──────────────────────────────────┐
  /health  /metrics  /agent/run  /runs       │
      │                                      │
      ▼                                      │
  LangGraph Workflow                         │
  ┌─────────┐   tool?  ┌──────────┐         │
  │ planner │ ───────▶ │  tool    │  DuckDuckGo
  └────┬────┘          └────┬─────┘         │
       │ direct              │               │
       ▼                     ▼               │
  ┌─────────────────────────────┐           │
  │         synthesizer         │           │
  └─────────────┬───────────────┘           │
                │                           │
                ▼                           │
           final output                     │
                ├── Postgres (run history) ◀┘
                ├── Langfuse (LLM traces)
                └── Prometheus ◀── /metrics scrape
                         └── Grafana dashboards
```

---

## Quick Start

### Full stack with Docker Compose

```bash
git clone https://github.com/iamMashel/agent-platform.git
cd agent-platform
cp .env.example .env
# Set your LLM API key (see LLM Providers below)

docker compose up --build -d
```

| Service    | URL                        | Credentials  |
|------------|----------------------------|--------------|
| Frontend   | http://localhost:3002      |              |
| API Docs   | http://localhost:8000/docs |              |
| Grafana    | http://localhost:3001      | admin/admin  |
| Langfuse   | http://localhost:3010      |              |
| Prometheus | http://localhost:9090      |              |

### Local development (API only)

```bash
uv sync --locked
cp .env.example .env   # fill in your LLM API key

docker compose up agentdb redis -d  # only the backing services

just dev               # FastAPI with hot reload → http://localhost:8000/docs

cd apps/web && npm ci && npm run dev   # frontend → http://localhost:3000
```

---

## LLM Providers

Switch providers by editing two lines in `.env` — no code changes needed.

### Gemini (default)

```env
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_google_ai_api_key
GEMINI_MODEL=gemini-2.5-flash
```

Get a free key at https://aistudio.google.com/apikey

### LiteLLM — 100+ models

Set `LLM_PROVIDER=litellm` and pick any [LiteLLM-supported model string](https://docs.litellm.ai/docs/providers):

```env
LLM_PROVIDER=litellm

# DeepSeek
LITELLM_MODEL=deepseek/deepseek-chat
DEEPSEEK_API_KEY=sk-...

# Anthropic Claude
LITELLM_MODEL=anthropic/claude-opus-4-7
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI
LITELLM_MODEL=openai/gpt-4o
OPENAI_API_KEY=sk-...

# Groq (fast + free tier)
LITELLM_MODEL=groq/llama-3.1-8b-instant
GROQ_API_KEY=gsk_...

# Ollama (local, no API key)
LITELLM_MODEL=ollama/llama3.2
```

### OpenAI (direct)

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

### Groq (direct)

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.1-8b-instant
```

### Ollama (local)

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

After changing `.env`, restart the API:

```bash
docker compose up -d api
# or in local dev: just dev
```

---

## API Reference

| Method | Endpoint         | Description                           |
|--------|------------------|---------------------------------------|
| GET    | `/health`        | Health check — returns status + env   |
| GET    | `/metrics`       | Prometheus metrics (text format)      |
| POST   | `/agent/run`     | Execute the LangGraph agent workflow  |
| GET    | `/runs`          | List all agent runs from Postgres     |
| GET    | `/runs/{run_id}` | Get a single run by ID                |

### `POST /agent/run`

```json
{
  "input": "Search for the latest AI news",
  "user_id": "user-123",       
  "session_id": "session-abc"  
}
```

`session_id` enables persistent memory across turns via Redis + LangGraph checkpointing.

Response:

```json
{
  "input": "Search for the latest AI news",
  "output": "Here are the latest AI developments...",
  "tool_result": "1. ...\n2. ...\n3. ...",
  "duration_ms": 3421.5,
  "session_id": "session-abc"
}
```

`tool_result` is `null` when the planner routes directly without search.

---

## Repository Structure

```
agent-platform/
├── apps/
│   ├── api/                   # FastAPI application
│   │   ├── main.py            # App factory, lifespan, routes
│   │   ├── agent.py           # /agent/run endpoint
│   │   ├── config.py          # pydantic-settings (all env vars)
│   │   ├── logging_config.py  # structlog JSON configuration
│   │   ├── metrics.py         # Prometheus counters + histograms
│   │   ├── middleware.py      # Request timing + request-ID
│   │   ├── runs.py            # /runs endpoints
│   │   ├── security.py        # API key auth + SlowAPI rate limiter
│   │   └── db/                # SQLAlchemy models + async session
│   └── web/                   # Nuxt 3 frontend
│       └── app/
│           ├── pages/         # index.vue (chat), status.vue
│           ├── composables/   # useAgent.ts, useHealth.ts
│           └── layouts/       # default.vue (nav)
├── services/
│   └── agent/
│       ├── graph/             # LangGraph state + workflow
│       ├── nodes/             # planner, tool, synthesizer nodes
│       ├── tools/             # DuckDuckGo search tool
│       └── llm.py             # Unified LLM factory (all providers)
├── infra/
│   ├── docker/
│   │   └── Dockerfile         # Multistage Python build
│   ├── migrations/            # Alembic migration scripts
│   │   ├── env.py             # Migration env (excludes LangGraph tables)
│   │   └── versions/          # Versioned schema migrations
│   └── clickhouse/            # ClickHouse config (used by Langfuse)
├── monitoring/
│   ├── prometheus/            # prometheus.yml scrape config
│   └── grafana/               # Provisioned datasources + dashboards
├── tests/
│   ├── unit/                  # Fast, no external calls
│   ├── integration/           # HTTP layer tests, mocked LLM
│   └── evals/                 # LLM regression evals (real API key)
├── .github/
│   └── workflows/             # ci.yml (6-job parallel), eval.yml
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
└── justfile
```

---

## Development

```bash
just lint          # ruff check
just format        # ruff format
just typecheck     # pyright
just test          # unit + integration (mocked LLM, no external calls)
just test-evals    # LLM regression evals (requires real API key)
just ci            # full local CI gate
```

---

## Environment Variables

### LLM

| Variable           | Default            | Description                                    |
|--------------------|--------------------|------------------------------------------------|
| `LLM_PROVIDER`     | `gemini`           | `gemini` \| `openai` \| `ollama` \| `groq` \| `litellm` |
| `GOOGLE_API_KEY`   | —                  | Required if `LLM_PROVIDER=gemini`              |
| `GEMINI_MODEL`     | `gemini-2.5-flash` | Gemini model name                              |
| `OPENAI_API_KEY`   | —                  | Required if `LLM_PROVIDER=openai`              |
| `OPENAI_MODEL`     | `gpt-4o-mini`      | OpenAI model name                              |
| `GROQ_API_KEY`     | —                  | Required if `LLM_PROVIDER=groq`                |
| `GROQ_MODEL`       | `llama-3.1-8b-instant` | Groq model name                            |
| `OLLAMA_BASE_URL`  | `http://localhost:11434` | Ollama server URL                        |
| `OLLAMA_MODEL`     | `llama3.2`         | Ollama model name                              |
| `LITELLM_MODEL`    | `gemini/gemini-2.5-flash` | Any LiteLLM model string              |
| `PLANNER_MODEL`    | *(same as LITELLM_MODEL)* | Cheaper model for the one-token routing step; falls back to `LITELLM_MODEL` if blank |

Any API key supported by LiteLLM (`ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, etc.) is passed through automatically.

### Observability

| Variable              | Default                    | Description                   |
|-----------------------|----------------------------|-------------------------------|
| `LANGFUSE_PUBLIC_KEY` | —                          | Langfuse public key           |
| `LANGFUSE_SECRET_KEY` | —                          | Langfuse secret key           |
| `LANGFUSE_HOST`       | `http://localhost:3000`    | Langfuse host                 |

### Infrastructure

| Variable       | Default                                                   | Description         |
|----------------|-----------------------------------------------------------|---------------------|
| `REDIS_URL`    | `redis://localhost:6379/0`                                | Redis connection    |
| `DATABASE_URL` | `postgresql+asyncpg://agent:agent@localhost:5432/agent`  | Postgres connection |
| `ENVIRONMENT`  | `development`                                             | `development` \| `production` |
| `API_KEYS`     | —                                                         | Comma-separated valid API keys; empty = auth disabled |
| `RATE_LIMIT`   | `30/minute`                                               | Per-IP rate limit on `/agent/run` |

---

## Observability

### Prometheus metrics

| Metric                          | Type      | Description                        |
|---------------------------------|-----------|------------------------------------|
| `http_requests_total`           | Counter   | Requests by method/endpoint/status |
| `http_request_duration_seconds` | Histogram | Request latency (p50/p95/p99)      |
| `agent_runs_total`              | Counter   | Total agent workflow executions    |
| `agent_run_duration_seconds`    | Histogram | Agent workflow latency             |
| `tool_executions_total`         | Counter   | Tool calls by tool_name            |

### Grafana

Dashboards are auto-provisioned on container start. Open http://localhost:3001 (admin / admin).

### Langfuse

Full LLM traces with per-request handlers. Open http://localhost:3010. Create a project, paste the keys into `.env`, and restart the API.

---

## Tech Stack

| Layer         | Technology                                          |
|---------------|-----------------------------------------------------|
| API           | Python 3.12, FastAPI, Uvicorn                       |
| Orchestration | LangGraph, LangChain                                |
| LLM           | LiteLLM (100+ providers) · Gemini 2.5 Flash default |
| Search        | DuckDuckGo (no API key)                             |
| Memory        | LangGraph AsyncPostgresSaver (falls back to MemorySaver) |
| History       | Postgres + SQLAlchemy async + asyncpg + Alembic     |
| Tracing       | Langfuse                                            |
| Metrics       | Prometheus, Grafana                                 |
| Logging       | structlog (JSON in production)                      |
| Frontend      | Nuxt 3, Vue 3, Tailwind CSS                         |
| Config        | pydantic-settings                                   |
| Packaging     | uv, pyproject.toml                                  |
| Linting       | Ruff, Pyright                                       |
| Testing       | pytest, pytest-asyncio                              |
| CI/CD         | GitHub Actions (6-job parallel pipeline)            |
| Containers    | Docker multistage build, Docker Compose             |
| Rate limiting | SlowAPI (per-IP)                                    |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md).

## License

MIT — see [LICENSE](LICENSE).
