from prometheus_client import Counter

AGENT_RUNS = Counter("agent_runs_total", "Total agent workflow executions")
TOOL_EXECUTIONS = Counter("tool_executions_total", "Total tool executions initialized by the agent")
