"""End-to-end tests for the concierge agent."""

from __future__ import annotations

from entertainment_concierge.agent import ConciergeAgent
from tests.conftest import clean_case


def test_clean_case_proposes_books_and_pays_with_both_gates(agent) -> None:
    result = agent.run(clean_case(), approve_proposal=True, approve_payment=True)
    assert result.decision == "PROPOSE"
    assert result.proposal is not None
    assert result.proposal.venue_id == "V001"  # cheapest confirmed match
    assert result.proposal.status == "draft"
    assert result.draft is not None
    assert result.draft.sent is False
    assert result.published is True
    assert result.booked is True
    assert result.paid is True
    assert result.spend_usd == 0.0
    assert result.gates_checked == ["proposal", "payment"]
    assert result.provenance == ["V001", "budget-memo-001"]


def test_plan_is_the_three_allowlisted_tools(agent) -> None:
    assert agent.plan() == ["venue_search", "booking_proposal", "venue_message"]


def test_agent_rejects_unknown_mode() -> None:
    import pytest

    with pytest.raises(ValueError, match="unknown mode"):
        ConciergeAgent(mode="oracle")


def test_remediation_holds(agent) -> None:
    data = clean_case()
    data["remediation_needed"] = [
        "Saffron Cellar requires signed contract + 50% deposit — a human must complete this."
    ]
    result = agent.run(data, approve_proposal=True, approve_payment=True)
    assert result.decision == "HOLD"
    assert result.published is False
    assert result.booked is False


def test_live_agent_refuses_without_api_key(monkeypatch) -> None:
    import pytest

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    agent = ConciergeAgent(mode="live")
    with pytest.raises(RuntimeError, match="no ANTHROPIC_API_KEY"):
        agent.run(clean_case(), approve_proposal=True, approve_payment=True)
