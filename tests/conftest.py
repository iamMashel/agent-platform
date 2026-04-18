"""Shared test fixtures.

Evals tests (tests/evals/) are marked with @pytest.mark.eval and require a real
GOOGLE_API_KEY. They are skipped automatically in CI when the key is the sentinel
value "test" (set by ci.yml).

All other tests use monkeypatched LLM nodes so no external API calls are made.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


class _MockLLM:
    """Deterministic LLM stub — returns predictable content based on prompt context."""

    def invoke(self, prompt: str, **_kwargs) -> MagicMock:
        resp = MagicMock()
        # Planner prompts contain "tool:search" or "final" decision cues
        if (
            "planner" in prompt.lower()
            or "tool:search" in prompt.lower()
            or "decide" in prompt.lower()
        ):
            resp.content = "final"
        else:
            resp.content = f"Mock response: {prompt[:60].strip()}"
        return resp


_mock = _MockLLM()


def _mock_get_llm(**_kwargs):
    return _mock


@pytest.fixture(autouse=True)
def mock_llm_nodes(monkeypatch, request):
    """Patch get_llm() in all node modules and the unified factory."""
    if "eval" in request.node.keywords:
        return

    monkeypatch.setattr("services.agent.nodes.planner.get_llm", _mock_get_llm)
    monkeypatch.setattr("services.agent.nodes.synthesizer.get_llm", _mock_get_llm)
    monkeypatch.setattr("services.agent.llm.get_llm", _mock_get_llm)
