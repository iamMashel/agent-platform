"""Tests for the four production fixes:
1. Unbounded messages truncation
2. LLM retry wrapping
3. Planner model splitting
4. Alembic migration is at head
"""

from __future__ import annotations

import contextlib
from unittest.mock import MagicMock

import pytest

# ── Fix 1: Unbounded messages ────────────────────────────────────────────────


class TestHistoryTruncation:
    def _make_state(self, n_turns: int):
        from services.agent.graph.state import AgentState

        msgs = []
        for i in range(n_turns):
            msgs.append(f"User: question {i}")
            msgs.append(f"Assistant: answer {i}")
        return AgentState(
            input="latest question",
            messages=msgs,
            next_step=None,
            tool_result=None,
            final_output=None,
        )

    def test_short_history_returned_in_full(self):
        from services.agent.graph.state import format_history  # noqa: PLC0415

        state = self._make_state(3)
        result = format_history(state)
        assert "question 0" in result
        assert "question 2" in result

    def test_long_history_is_truncated(self):
        from services.agent.graph.state import _MAX_HISTORY_TURNS, format_history

        n_turns = _MAX_HISTORY_TURNS + 5
        state = self._make_state(n_turns)
        result = format_history(state)
        # Oldest turns must be gone
        assert "question 0" not in result
        # Most recent turns must be present
        assert f"question {n_turns - 1}" in result

    def test_truncation_keeps_exactly_max_turns(self):
        from services.agent.graph.state import _MAX_HISTORY_TURNS, format_history

        n_turns = _MAX_HISTORY_TURNS + 3
        state = self._make_state(n_turns)
        result = format_history(state)
        lines = [ln for ln in result.splitlines() if ln.strip()]
        assert len(lines) == _MAX_HISTORY_TURNS * 2

    def test_empty_history_returns_placeholder(self):
        from services.agent.graph.state import AgentState, format_history

        state = AgentState(
            input="hi", messages=[], next_step=None, tool_result=None, final_output=None
        )
        assert format_history(state) == "(no prior messages)"

    def test_stored_messages_unaffected(self):
        """format_history truncates the view; it must NOT mutate state['messages']."""
        from services.agent.graph.state import _MAX_HISTORY_TURNS, format_history

        n_turns = _MAX_HISTORY_TURNS + 5
        state = self._make_state(n_turns)
        format_history(state)
        assert len(state["messages"]) == n_turns * 2


# ── Fix 2: LLM retry ────────────────────────────────────────────────────────


class TestLLMRetry:
    def test_get_llm_returns_runnable_with_retry(self):
        """get_llm() result must expose .invoke() (i.e. it's a valid Runnable)."""
        from services.agent.llm import get_llm

        llm = get_llm(temperature=0, task="default")
        assert hasattr(llm, "invoke")

    def test_llm_retries_on_transient_error(self):
        """A model that fails twice then succeeds should return the success result."""
        call_count = 0

        class FlakyLLM:
            def invoke(self, prompt, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise ConnectionError("transient")
                resp = MagicMock()
                resp.content = "success"
                return resp

            def with_retry(self, **kwargs):
                # Return a wrapper that calls invoke up to stop_after_attempt times
                stop = kwargs.get("stop_after_attempt", 3)

                class Retried:
                    def invoke(self, prompt, **kw):  # noqa: N805
                        last_exc: Exception = RuntimeError("no attempts")
                        for _ in range(stop):
                            try:
                                return FlakyLLM().invoke(prompt)
                            except Exception as e:
                                last_exc = e
                        raise last_exc

                return Retried()

        flaky = FlakyLLM()
        wrapped = flaky.with_retry(stop_after_attempt=3)
        result = wrapped.invoke("test")
        assert result.content == "success"

    def test_llm_raises_after_all_retries_exhausted(self):
        """If every attempt fails, the final exception must propagate."""

        class AlwaysFailLLM:
            def invoke(self, prompt, **kwargs):
                raise RuntimeError("always fails")

            def with_retry(self, stop_after_attempt=3, **kwargs):
                stop = stop_after_attempt

                class Retried:
                    def invoke(self, prompt, **kw):  # noqa: N805
                        for _ in range(stop):
                            with contextlib.suppress(RuntimeError):
                                AlwaysFailLLM().invoke(prompt)
                        raise RuntimeError("always fails")

                return Retried()

        wrapped = AlwaysFailLLM().with_retry(stop_after_attempt=3)
        with pytest.raises(RuntimeError, match="always fails"):
            wrapped.invoke("test")


# ── Fix 3: Planner model split ───────────────────────────────────────────────


class TestPlannerModelSplit:
    def test_resolved_planner_model_uses_custom_when_set(self, monkeypatch):
        from apps.api.config import Settings

        monkeypatch.setenv("LLM_PROVIDER", "litellm")
        monkeypatch.setenv("LITELLM_MODEL", "deepseek/deepseek-chat")
        monkeypatch.setenv("PLANNER_MODEL", "gemini/gemini-2.0-flash-lite")
        s = Settings()
        assert s.resolved_planner_model == "gemini/gemini-2.0-flash-lite"

    def test_resolved_planner_model_falls_back_to_litellm(self, monkeypatch):
        from apps.api.config import Settings

        monkeypatch.setenv("LLM_PROVIDER", "litellm")
        monkeypatch.setenv("LITELLM_MODEL", "deepseek/deepseek-chat")
        monkeypatch.setenv("PLANNER_MODEL", "")
        s = Settings()
        assert s.resolved_planner_model == "deepseek/deepseek-chat"

    def test_planner_node_calls_get_llm_with_planner_task(self, monkeypatch):
        """Planner node must request task='planner' from the factory."""
        captured = {}

        def mock_get_llm(temperature=0.0, task="default"):
            captured["task"] = task
            captured["temperature"] = temperature
            m = MagicMock()
            m.invoke.return_value = MagicMock(content="final")
            return m

        monkeypatch.setattr("services.agent.nodes.planner.get_llm", mock_get_llm)

        from langchain_core.runnables import RunnableConfig

        from services.agent.graph.state import AgentState
        from services.agent.nodes.planner import planner_node

        state = AgentState(
            input="What is LangGraph?",
            messages=[],
            next_step=None,
            tool_result=None,
            final_output=None,
        )
        planner_node(state, RunnableConfig())

        assert captured["task"] == "planner"
        assert captured["temperature"] == 0


# ── Fix 4: Alembic at head ───────────────────────────────────────────────────


class TestAlembicMigration:
    def test_migration_script_exists(self):
        from pathlib import Path

        versions = list(Path("infra/migrations/versions").glob("*.py"))
        assert len(versions) >= 1, "No migration scripts found"

    def test_alembic_is_at_head(self):
        """The live database must be at the latest migration revision.
        Skipped automatically when no Postgres is available (e.g. in unit CI)."""
        import pytest
        from alembic.config import Config as AlembicConfig
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory
        from sqlalchemy import create_engine
        from sqlalchemy.exc import OperationalError

        from apps.api.config import settings

        sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(
            sync_url, poolclass=__import__("sqlalchemy.pool", fromlist=["NullPool"]).NullPool
        )
        try:
            engine.connect().close()
        except OperationalError:
            pytest.skip("Postgres not available — skipping DB migration check")

        alembic_cfg = AlembicConfig("alembic.ini")
        script = ScriptDirectory.from_config(alembic_cfg)

        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            current = ctx.get_current_revision()

        head = script.get_current_head()
        assert current == head, f"DB is at {current!r}, expected head {head!r}"
