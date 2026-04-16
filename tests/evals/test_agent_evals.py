"""Offline regression evals — require a real GOOGLE_API_KEY.

These tests are marked with @pytest.mark.eval and are automatically skipped
when GOOGLE_API_KEY == "test" (the CI sentinel value).
"""

from __future__ import annotations

import json
import os
from typing import cast

import pytest

from services.agent.graph.state import AgentState

pytestmark = pytest.mark.eval


def _skip_without_real_key():
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key or key == "test":
        pytest.skip("Skipping eval: GOOGLE_API_KEY not set to a real value")


def load_golden_dataset() -> list[dict]:
    with open("tests/evals/golden_dataset.json") as f:
        return json.load(f)


@pytest.mark.parametrize("case", load_golden_dataset())
def test_agent_planner_routing(case: dict) -> None:
    """Verify the planner routes correctly for known input patterns."""
    _skip_without_real_key()

    from services.agent.graph.workflow import build_graph

    agent = build_graph()
    state = {
        "input": case["input"],
        "messages": [],
        "next_step": None,
        "tool_result": None,
        "final_output": None,
    }

    result = agent.invoke(cast(AgentState, state))

    assert result["next_step"] is not None, "Planner did not set next_step"

    if case["expected_next_step"] == "tool":
        assert "tool" in result["next_step"].lower(), (
            f"Expected tool routing but got: {result['next_step']!r}"
        )
    else:
        assert "tool" not in result["next_step"].lower(), (
            f"Expected direct answer but got tool routing: {result['next_step']!r}"
        )
