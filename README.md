# Agent Platform

![CI](https://img.shields.io/github/actions/workflow/status/iamMashel/agent-platform/ci.yml?label=CI)
![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/github/license/iamMashel/agent-platform)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![Observability](https://img.shields.io/badge/observability-prometheus-orange)
![Tracing](https://img.shields.io/badge/tracing-langfuse-purple)

**Production-grade AI agent platform** built with FastAPI, LangGraph, Nuxt 3, Langfuse, and Prometheus.

> Building AI agents is easy. Operating them reliably in production is hard.  
> Agent Platform provides the missing engineering layer: orchestration, observability, evaluation pipelines, and deployment guardrails in a single modern backend platform.

---

## Features

- **FastAPI** production API with structured JSON logging and request-ID tracing
- **LangGraph** workflow: `planner → tool → synthesizer` state machine with persistent memory
- **Langfuse** LLM tracing — full trace context, per-request handlers, generation-level spans
- **Prometheus + Grafana** — request rate, latency histograms (p50/p95/p99), agent run duration, error rate
- **Nuxt 3 frontend** — dark-mode chat UI + live status dashboard
- **Docker Compose** stack — API, frontend, Langfuse, Postgres, Prometheus, Grafana
- **uv** — fast, reproducible Python dependency management
- **Ruff + Pyright** — lint, format, and strict type checking
- **pytest** — unit, integration, and eval suites with automatic LLM mocking
- **GitHub Actions** — multi-job CI (lint → typecheck → unit → integration → docker → frontend)
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
  /health  /metrics  /agent/run              │
      │                                      │
      ▼                                      │
  LangGraph Workflow                         │
  ┌─────────┐   tool?  ┌──────────┐         │
  │ planner │ ───────▶ │  tool    │         │
  └────┬────┘          └────┬─────┘         │
       │ direct              │               │
       ▼                     ▼               │
  ┌─────────────────────────────┐           │
  │         synthesizer         │           │
  └─────────────┬───────────────┘           │
                │                           │
                ▼                           │
           final output                     │
                                            │
  Langfuse  ◀─────────────────────────────-┘
  Prometheus ◀── /metrics scrape
  Grafana    ◀── dashboards
```

---

## Quick Start

### Local development

```bash
# 1. Clone and enter
git clone https://github.com/iamMashel/agent-platform.git
cd agent-platform

# 2. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Sync dependencies
uv sync --locked

# 4. Configure environment
cp .env.example .env
# Add your GOOGLE_API_KEY to .env

# 5. Start API
just dev
# → http://localhost:8000/docs

# 6. Start frontend (separate terminal)
cd apps/web && npm ci && npm run dev
# → http://localhost:3000
```

### Full stack with Docker Compose

```bash
cp .env.example .env
# Add your GOOGLE_API_KEY

docker compose up --build -d
```

| Service    | URL                          |
|------------|------------------------------|
| API        | http://localhost:8000        |
| API Docs   | http://localhost:8000/docs   |
| Frontend   | http://localhost:3002        |
| Langfuse   | http://localhost:3010        |
| Grafana    | http://localhost:3001        |
| Prometheus | http://localhost:9090        |

---

## API Reference

| Method | Endpoint      | Description                           |
|--------|---------------|---------------------------------------|
| GET    | `/health`     | Health check — returns status + env   |
| GET    | `/metrics`    | Prometheus metrics (text format)      |
| POST   | `/agent/run`  | Execute the LangGraph agent workflow  |

### `POST /agent/run`

```json
{
  "input": "Search for the latest AI news",
  "user_id": "user-123",       // optional
  "session_id": "session-abc"  // optional — enables memory across turns
}
```

Response:

```json
{
  "input": "Search for the latest AI news",
  "output": "Here are the latest AI developments...",
  "tool_result": "[MOCK SEARCH RESULT for 'Search for the latest AI news']",
  "duration_ms": 842.5
}
```

---

## Repository Structure

```
agent-platform/
├── apps/
│   ├── api/                   # FastAPI application
│   │   ├── main.py            # App factory, lifespan, routes
│   │   ├── agent.py           # /agent/run endpoint
│   │   ├── config.py          # pydantic-settings
│   │   ├── logging_config.py  # structlog JSON configuration
│   │   ├── metrics.py         # Prometheus counters + histograms
│   │   └── middleware.py      # Request timing + request-ID
│   └── web/                   # Nuxt 3 frontend
│       └── app/
│           ├── pages/         # index.vue (chat), status.vue
│           ├── composables/   # useAgent.ts, useHealth.ts
│           └── layouts/       # default.vue (nav)
├── services/
│   └── agent/
│       ├── graph/             # LangGraph state + workflow
│       ├── nodes/             # planner, tool, synthesizer nodes
│       └── tools/             # mock_tool (swap for real APIs)
├── infra/
│   └── docker/
│       └── Dockerfile         # Multistage Python build
├── monitoring/
│   ├── prometheus/            # prometheus.yml scrape config
│   └── grafana/               # Provisioned datasources + dashboards
├── tests/
│   ├── unit/                  # Fast, no external calls
│   ├── integration/           # HTTP layer tests, mocked LLM
│   └── evals/                 # LLM regression evals (real API key)
├── .github/
│   └── workflows/             # ci.yml (multi-job), eval.yml
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
just test          # unit + integration (mocked LLM)
just test-evals    # LLM regression evals (requires real API key)
just ci            # full local CI gate
```

---

## Environment Variables

| Variable              | Required | Description                              |
|-----------------------|----------|------------------------------------------|
| `GOOGLE_API_KEY`      | Yes      | Google AI Studio API key                 |
| `GEMINI_MODEL`        | No       | Gemini model name (default: gemini-2.5-flash) |
| `LANGFUSE_PUBLIC_KEY` | No       | Langfuse public key for LLM tracing      |
| `LANGFUSE_SECRET_KEY` | No       | Langfuse secret key                      |
| `LANGFUSE_HOST`       | No       | Langfuse host (default: localhost:3010 in Docker)  |
| `ENVIRONMENT`         | No       | `development` or `production`            |

Copy `.env.example` → `.env` and fill in values.

---

## Observability

### Prometheus metrics

| Metric                                  | Type      | Description                         |
|-----------------------------------------|-----------|-------------------------------------|
| `http_requests_total`                   | Counter   | Requests by method/endpoint/status  |
| `http_request_duration_seconds`         | Histogram | Request latency (p50/p95/p99)       |
| `agent_runs_total`                      | Counter   | Total agent workflow executions     |
| `agent_run_duration_seconds`            | Histogram | Agent workflow latency              |
| `tool_executions_total`                 | Counter   | Tool calls by tool_name             |

### Grafana

Dashboards are auto-provisioned. Open http://localhost:3001 (admin / admin).

### Langfuse

Full LLM traces with per-request handlers. Open http://localhost:3010.

---

## Tech Stack

| Layer         | Technology                            |
|---------------|---------------------------------------|
| API           | Python 3.12, FastAPI, Uvicorn         |
| Orchestration | LangGraph, LangChain                  |
| LLM           | Gemini 2.0 Flash (via langchain-google-genai) |
| Tracing       | Langfuse                              |
| Metrics       | Prometheus, Grafana                   |
| Logging       | structlog (JSON in production)        |
| Frontend      | Nuxt 3, Vue 3, Tailwind CSS           |
| Config        | pydantic-settings                     |
| Packaging     | uv, pyproject.toml                    |
| Linting       | Ruff, Pyright                         |
| Testing       | pytest, pytest-asyncio                |
| CI/CD         | GitHub Actions (multi-job)            |
| Containers    | Docker multistage, Docker Compose     |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md).

## License

MIT — see [LICENSE](LICENSE).
