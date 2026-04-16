from prometheus_client import Counter, Histogram

# --- HTTP layer ---
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# --- Agent layer ---
AGENT_RUNS = Counter("agent_runs_total", "Total agent workflow executions")

agent_run_duration_seconds = Histogram(
    "agent_run_duration_seconds",
    "Agent workflow run duration in seconds",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

# --- Tool layer ---
TOOL_EXECUTIONS = Counter(
    "tool_executions_total",
    "Total tool executions",
    ["tool_name"],
)
