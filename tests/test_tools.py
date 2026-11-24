"""Tests for the three allowlisted tools."""

from __future__ import annotations

import pytest

from entertainment_concierge.packet import case_from_dict, venue_from_dict
from entertainment_concierge.tools import (
    ALLOWED_TOOLS,
    booking_proposal,
    estimate_for,
    venue_message,
    venue_search,
)
from tests.conftest import clean_case, venue_dict


def test_allowed_tools_are_exactly_three() -> None:
    assert ALLOWED_TOOLS == ("venue_search", "booking_proposal", "venue_message")


def test_estimate_is_max_of_minimum_and_per_person() -> None:
    case = case_from_dict(clean_case())
    assert estimate_for(case.venues[0], 12) == 3000  # min 3000 vs 150*12=1800
    assert estimate_for(case.venues[1], 12) == 4000  # min 4000 vs 175*12=2100


def test_estimate_is_none_when_a_fact_is_unknown() -> None:
    assert estimate_for(venue_from_dict(venue_dict("V028")), 12) is None
    assert estimate_for(venue_from_dict(venue_dict("V027")), 30) is None


def test_venue_search_returns_matches_cheapest_first() -> None:
    case = case_from_dict(clean_case())
    matches = venue_search(case)
    assert [m.venue.id for m in matches] == ["V001", "V002"]
    assert [m.estimate_usd for m in matches] == [3000, 4000]


def test_venue_search_excludes_over_capacity() -> None:
    data = clean_case()
    data["party_size"] = 40
    case = case_from_dict(data)
    assert venue_search(case) == []


def test_venue_search_excludes_unavailable_date() -> None:
    data = clean_case()
    data["date"] = "2027-01-20"
    case = case_from_dict(data)
    assert venue_search(case) == []


def test_venue_search_excludes_over_budget() -> None:
    data = clean_case()
    data["budget_usd"] = 2000
    case = case_from_dict(data)
    assert venue_search(case) == []


def test_venue_search_excludes_unknown_facts() -> None:
    data = clean_case()
    data["venues"] = [venue_dict("V010")]  # capacity unknown
    data["party_size"] = 8
    data["budget_usd"] = 3000
    data["private_required"] = False
    case = case_from_dict(data)
    assert venue_search(case) == []


def test_venue_search_filters_city_kind_and_privacy() -> None:
    data = clean_case()
    data["venues"] = [venue_dict("V025"), venue_dict("V001")]
    case = case_from_dict(data)
    assert [m.venue.id for m in venue_search(case)] == ["V001"]
    data["city"] = "San Francisco"
    case = case_from_dict(data)
    assert [m.venue.id for m in venue_search(case)] == ["V025"]


def test_booking_proposal_is_a_draft_that_books_nothing() -> None:
    case = case_from_dict(clean_case())
    proposal = booking_proposal(case, "V001")
    assert proposal.status == "draft"
    assert proposal.venue_id == "V001"
    assert proposal.estimate_usd == 3000
    assert proposal.minimum_usd == 3000
    assert any("confirmation required" in term.lower() for term in proposal.terms)


def test_booking_proposal_refuses_non_matching_venue() -> None:
    case = case_from_dict(clean_case())
    with pytest.raises(ValueError, match="not a confirmed match"):
        booking_proposal(case, "V013")


def test_venue_message_is_a_draft_that_sends_nothing() -> None:
    case = case_from_dict(clean_case())
    for purpose in ("confirm_availability", "negotiate_minimum", "request_menu"):
        draft = venue_message(case, "V001", purpose)
        assert draft.sent is False
        assert draft.to_venue_id == "V001"
        assert "None" not in draft.body


def test_venue_message_refuses_unknown_purpose_and_venue() -> None:
    case = case_from_dict(clean_case())
    with pytest.raises(ValueError, match="unknown message purpose"):
        venue_message(case, "V001", "bribe_the_maitre_d")
    with pytest.raises(ValueError, match="unknown venue"):
        venue_message(case, "V999", "confirm_availability")


def test_read_case_validates_required_fields() -> None:
    data = clean_case()
    del data["budget_usd"]
    with pytest.raises(ValueError, match="missing required field"):
        case_from_dict(data)
