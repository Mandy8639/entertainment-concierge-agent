"""Live-mode safety tests: refusal paths only, no network calls."""

from __future__ import annotations

import pytest

from entertainment_concierge.agent import ConciergeAgent
from entertainment_concierge.reasoner import LiveReasoner
from tests.conftest import clean_case


def test_live_mode_refuses_without_key_even_when_gates_approved(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    agent = ConciergeAgent(mode="live")
    with pytest.raises(RuntimeError, match="no ANTHROPIC_API_KEY"):
        agent.run(clean_case(), approve_proposal=True, approve_payment=True)


def test_live_reasoner_default_model_is_haiku(tmp_path) -> None:
    reasoner = LiveReasoner(spend_path=str(tmp_path / "spend.json"))
    assert reasoner.model == "claude-haiku-4-5"
