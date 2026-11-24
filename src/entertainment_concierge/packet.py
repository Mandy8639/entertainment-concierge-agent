"""Booking case: the single input to the agent.

A case is a synthetic booking request: a one-sentence request parsed into
party size, date, occasion and constraints, a shortlist of candidate venues
drawn from the inventory, messages from venues, and claims about the booking.
Every message and claim carries a provenance source; a claim without a source
is unsourced by construction and the guardrail treats it as fabrication.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Venue:
    """One candidate venue, with facts copied from the inventory.

    ``capacity``, ``minimum_spend_usd``, ``price_per_person_usd`` and
    ``available_dates`` are None when that fact is unknown (missing
    evidence, G3). ``requires`` names a pre-booking step a human must
    complete before any hold (remediation).
    """

    id: str
    name: str
    kind: str
    city: str
    capacity: int | None
    minimum_spend_usd: int | None
    price_per_person_usd: int | None
    available_dates: list[str] | None
    private: bool
    requires: str | None = None


@dataclass(frozen=True)
class VenueMessage:
    """One message from a venue. ``source`` is the venue id it came from.

    ``asserts`` holds machine-readable facts the message claims (e.g. a
    minimum or a date). The guardrail compares them against the inventory:
    an assert that contradicts the inventory is a venue conflict (G5).
    """

    text: str
    source: str
    asserts: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Claim:
    """One claim about the booking. ``source`` may be None (unsourced)."""

    text: str
    source: str | None


@dataclass(frozen=True)
class Case:
    """A booking case. All fields are required; see tools.read_case."""

    id: str
    category: str
    customer: str
    request_text: str
    party_size: int
    date: str
    occasion: str
    city: str
    kind: str
    private_required: bool
    budget_usd: int
    venues: list[Venue] = field(default_factory=list)
    messages: list[VenueMessage] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    required_evidence: list[str] = field(default_factory=list)
    remediation_needed: list[str] = field(default_factory=list)


def venue_from_dict(data: dict) -> Venue:
    return Venue(
        id=data["id"],
        name=data["name"],
        kind=data["kind"],
        city=data["city"],
        capacity=data.get("capacity"),
        minimum_spend_usd=data.get("minimum_spend_usd"),
        price_per_person_usd=data.get("price_per_person_usd"),
        available_dates=data.get("available_dates"),
        private=data["private"],
        requires=data.get("requires"),
    )


def case_from_dict(data: dict) -> Case:
    """Build a Case from a plain dict, validating required fields."""
    required = [
        "id",
        "category",
        "customer",
        "request_text",
        "party_size",
        "date",
        "occasion",
        "city",
        "kind",
        "private_required",
        "budget_usd",
    ]
    for key in required:
        if key not in data or data[key] in (None, ""):
            raise ValueError(f"case is missing required field: {key}")
    venues = [venue_from_dict(v) for v in data.get("venues", [])]
    messages = [
        VenueMessage(text=m["text"], source=m["source"], asserts=dict(m.get("asserts", {})))
        for m in data.get("messages", [])
    ]
    claims = [Claim(text=c["text"], source=c.get("source")) for c in data.get("claims", [])]
    return Case(
        id=data["id"],
        category=data["category"],
        customer=data["customer"],
        request_text=data["request_text"],
        party_size=data["party_size"],
        date=data["date"],
        occasion=data["occasion"],
        city=data["city"],
        kind=data["kind"],
        private_required=data["private_required"],
        budget_usd=data["budget_usd"],
        venues=venues,
        messages=messages,
        claims=claims,
        required_evidence=list(data.get("required_evidence", [])),
        remediation_needed=list(data.get("remediation_needed", [])),
    )


def venue_to_dict(venue: Venue) -> dict:
    return {
        "id": venue.id,
        "name": venue.name,
        "kind": venue.kind,
        "city": venue.city,
        "capacity": venue.capacity,
        "minimum_spend_usd": venue.minimum_spend_usd,
        "price_per_person_usd": venue.price_per_person_usd,
        "available_dates": venue.available_dates,
        "private": venue.private,
        "requires": venue.requires,
    }


def case_to_dict(case: Case) -> dict:
    """Serialise a Case back to a plain dict."""
    return {
        "id": case.id,
        "category": case.category,
        "customer": case.customer,
        "request_text": case.request_text,
        "party_size": case.party_size,
        "date": case.date,
        "occasion": case.occasion,
        "city": case.city,
        "kind": case.kind,
        "private_required": case.private_required,
        "budget_usd": case.budget_usd,
        "venues": [venue_to_dict(v) for v in case.venues],
        "messages": [
            {"text": m.text, "source": m.source, "asserts": dict(m.asserts)} for m in case.messages
        ],
        "claims": [{"text": c.text, "source": c.source} for c in case.claims],
        "required_evidence": list(case.required_evidence),
        "remediation_needed": list(case.remediation_needed),
    }
