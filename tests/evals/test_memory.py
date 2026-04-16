"""Memory retention eval — requires a real GOOGLE_API_KEY.

Tests that the LangGraph MemorySaver checkpointer correctly persists context
across invocations on the same thread_id.
"""

from __future__ import annotations

import os
from typing import cast

import pytest
from langchain_core.runnables import RunnableConfig

from services.agent.graph.state import AgentState

pytestmark = pytest.mark.eval


def _skip_without_real_key():
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key or key == "test":
        pytest.skip("Skipping eval: GOOGLE_API_KEY not set to a real value")


def test_agent_memory_retention() -> None:
    """Agent should recall facts stated in earlier turns of the same session."""
    _skip_without_real_key()

    from services.agent.graph.workflow import build_graph

    agent = build_graph()
    thread_id = "eval-memory-test-001"
    config = {"configurable": {"thread_id": thread_id}}

    base_state: dict = {
        "input": "",
        "messages": [],
        "next_step": None,
        "tool_result": None,
        "final_output": None,
    }

    # Turn 1 — inject a fact
    agent.invoke(
        cast(AgentState, {**base_state, "input": "My favourite colour is Crimson Red."}),
        config=cast(RunnableConfig, config),
    )

    # Turn 2 — test recall
    result = agent.invoke(
        cast(AgentState, {**base_state, "input": "What is my favourite colour?"}),
        config=cast(RunnableConfig, config),
    )

    output = (result.get("final_output") or "").lower()
    assert "crimson" in output, (
        f"Agent failed to recall context for thread {thread_id!r}. Got: {output!r}"
    )
