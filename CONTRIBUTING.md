# Contributing

## Branch naming

| Prefix       | When to use                                       |
|--------------|---------------------------------------------------|
| `feature/*`  | New functionality                                 |
| `fix/*`      | Bug fixes                                         |
| `chore/*`    | Dependencies, tooling, docs, config               |
| `hotfix/*`   | Urgent production fixes (branch from main)        |
| `release/*`  | Release prep (changelog, version bumps)           |

## Workflow

```bash
# 1. Start from a fresh main
git checkout main && git pull

# 2. Create a scoped branch
git checkout -b feature/my-feature

# 3. Work, commit often
git commit -m "feat: add X"   # see commit style below

# 4. Push and open a PR
git push -u origin feature/my-feature
```

## Commit style (Conventional Commits)

```
<type>(<scope>): <short description>
```

| Type       | When                                  |
|------------|---------------------------------------|
| `feat`     | New feature                           |
| `fix`      | Bug fix                               |
| `chore`    | Tooling, config, deps                 |
| `docs`     | Documentation only                    |
| `refactor` | Code change, no feature or fix        |
| `test`     | Adding or updating tests              |
| `ci`       | CI/CD changes                         |

Examples:

```
feat(agent): add session memory via LangGraph checkpointer
fix(metrics): correct histogram bucket boundaries
chore(deps): bump langfuse to 2.x
```

## Local quality gate

Before opening a PR, run:

```bash
just ci
```

This mirrors the CI pipeline:

```
ruff check → ruff format --check → pyright → pytest (unit + integration)
```

## Tests

- **Unit** (`tests/unit/`) — no external calls, runs instantly
- **Integration** (`tests/integration/`) — HTTP layer, LLM is mocked automatically
- **Evals** (`tests/evals/`) — requires a real `GOOGLE_API_KEY`, run with `just test-evals`

New behaviour requires new tests. PRs without tests for new code will be asked to add them.

## Adding a new LLM node

1. Create `services/agent/nodes/your_node.py`
2. Use `_get_llm()` lazy factory (see `planner.py`) — never instantiate at module level
3. Add the node to `services/agent/graph/workflow.py`
4. Add integration test in `tests/integration/`
5. Add eval fixture in `tests/evals/golden_dataset.json` if routing is affected

## Adding a new tool

1. Create `services/agent/tools/your_tool.py` using `@tool` from `langchain_core.tools`
2. Import and call it in `services/agent/nodes/tools.py`
3. Increment `TOOL_EXECUTIONS.labels(tool_name="your_tool")` for Prometheus tracking
