"""Shared fixtures for the concierge tests."""

from __future__ import annotations

import pytest

from entertainment_concierge.agent import ConciergeAgent
from entertainment_concierge.inventory import BY_ID


def venue_dict(venue_id: str) -> dict:
    venue = dict(BY_ID[venue_id])
    if venue["available_dates"] is not None:
        venue["available_dates"] = list(venue["available_dates"])
    return venue


def clean_case() -> dict:
    """A clean private-dining case: V001 and V002 both satisfy it."""
    return {
        "id": "EC-T01",
        "category": "clean",
        "customer": "Acme Manufacturing Group",
        "request_text": "dinner for 12 with the Acme team next Thursday, somewhere private",
        "party_size": 12,
        "date": "2026-12-10",
        "occasion": "team dinner",
        "city": "New York",
        "kind": "private_dining",
        "private_required": True,
        "budget_usd": 6000,
        "venues": [venue_dict("V001"), venue_dict("V002")],
        "messages": [
            {
                "text": "Confirmed: The Alder Room is available on 2026-12-10.",
                "source": "V001",
                "asserts": {"available": ["2026-12-10"]},
            },
            {
                "text": "Our minimum spend for that evening is $3000.",
                "source": "V001",
                "asserts": {"minimum_spend_usd": 3000},
            },
        ],
        "claims": [
            {
                "text": "Finance approved a $6000 entertainment budget for this quarter.",
                "source": "budget-memo-001",
            }
        ],
        "required_evidence": ["V001:capacity", "V001:availability:2026-12-10"],
        "remediation_needed": [],
    }


@pytest.fixture
def agent() -> ConciergeAgent:
    return ConciergeAgent(mode="stub")
