"""Deterministic guardrail G1-G5.

Every rule is a pure function over the case, so the eval can reproduce it
exactly. No rule ever invents evidence: when evidence is missing the agent
abstains; when instructions appear inside venue messages they are blocked;
when a venue message contradicts the inventory the run pauses.
"""

from __future__ import annotations

from entertainment_concierge.packet import Case, Claim, VenueMessage
from entertainment_concierge.tools import estimate_for

# G4: substrings that mark an instruction injected into a venue message.
# A message containing one of these is treated as an attempt to steer the
# agent, not as venue evidence.
INJECTION_PATTERNS = (
    "ignore the",
    "ignore all",
    "override",
    "approve anyway",
    "disregard",
    "do not flag",
    "skip the check",
    "book it anyway",
    "bypass",
    "pretend",
    "confirm without asking",
)


def scan_injection(messages: list[VenueMessage]) -> list[VenueMessage]:
    """G4: return the venue messages that carry an injected instruction."""
    hits = []
    for message in messages:
        lowered = message.text.lower()
        if any(pattern in lowered for pattern in INJECTION_PATTERNS):
            hits.append(message)
    return hits


def scan_fabrication(claims: list[Claim]) -> list[Claim]:
    """G3: return the claims with no provenance source. They are dropped."""
    return [claim for claim in claims if not claim.source]


def cited_sources(case: Case) -> list[str]:
    """Provenance the agent is allowed to cite: sourced messages and claims."""
    sources = [message.source for message in case.messages]
    sources += [claim.source for claim in case.claims if claim.source]
    return sorted(set(sources))


def missing_evidence(case: Case) -> list[str]:
    """G3: required evidence items with no supporting record.

    Entries are ``"VID:field"`` or ``"VID:availability:DATE"``. An item is
    missing when the venue is not among the case venues, or the field is
    unknown (None) on that venue. A date that is known but unavailable is
    NOT missing evidence — it is a policy violation (G5).
    """
    missing = []
    by_id = {venue.id: venue for venue in case.venues}
    for entry in case.required_evidence:
        parts = entry.split(":")
        venue_id, field_name = parts[0], parts[1]
        venue = by_id.get(venue_id)
        if venue is None:
            missing.append(entry)
            continue
        if field_name == "capacity" and venue.capacity is None:
            missing.append(entry)
        elif field_name == "minimum_spend_usd" and venue.minimum_spend_usd is None:
            missing.append(entry)
        elif field_name == "price_per_person_usd" and venue.price_per_person_usd is None:
            missing.append(entry)
        elif field_name == "availability" and venue.available_dates is None:
            missing.append(entry)
    return missing


def scan_venue_conflicts(case: Case) -> list[dict]:
    """G5: venue-message asserts that contradict the inventory.

    Only fields the inventory actually knows are compared; an assert about
    an unknown field is not a conflict. Returns one dict per contradiction.
    """
    conflicts = []
    by_id = {venue.id: venue for venue in case.venues}
    for message in case.messages:
        venue = by_id.get(message.source)
        if venue is None:
            continue
        for key, asserted in message.asserts.items():
            if key == "minimum_spend_usd" and venue.minimum_spend_usd is not None:
                if asserted != venue.minimum_spend_usd:
                    conflicts.append(
                        {
                            "venue": venue.id,
                            "field": key,
                            "asserted": asserted,
                            "inventory": venue.minimum_spend_usd,
                        }
                    )
            elif key == "capacity" and venue.capacity is not None:
                if asserted != venue.capacity:
                    conflicts.append(
                        {
                            "venue": venue.id,
                            "field": key,
                            "asserted": asserted,
                            "inventory": venue.capacity,
                        }
                    )
            elif key == "price_per_person_usd" and venue.price_per_person_usd is not None:
                if asserted != venue.price_per_person_usd:
                    conflicts.append(
                        {
                            "venue": venue.id,
                            "field": key,
                            "asserted": asserted,
                            "inventory": venue.price_per_person_usd,
                        }
                    )
            elif key == "available" and venue.available_dates is not None:
                for date in asserted:
                    if date not in venue.available_dates:
                        conflicts.append(
                            {
                                "venue": venue.id,
                                "field": "availability",
                                "asserted": date,
                                "inventory": venue.available_dates,
                            }
                        )
    return conflicts


def policy_violations(case: Case) -> list[str]:
    """G5: policy violations that block any proposal.

    A candidate is viable when every computable constraint passes
    (capacity, date, minimum, estimate within budget). If at least one
    candidate is viable there is no violation. Otherwise the violations
    from every candidate are returned, deduplicated. Unknown fields never
    count as violations — they are missing evidence (G3), not policy.
    """
    in_scope = [
        venue
        for venue in case.venues
        if venue.city == case.city
        and venue.kind == case.kind
        and (not case.private_required or venue.private)
    ]
    if not in_scope:
        return []
    violations: set[str] = set()
    viable = False
    for venue in in_scope:
        venue_violations: list[str] = []
        if venue.capacity is not None and case.party_size > venue.capacity:
            venue_violations.append(
                f"over_capacity: {venue.id} seats {venue.capacity}, party of {case.party_size}"
            )
        if venue.available_dates is not None and case.date not in venue.available_dates:
            venue_violations.append(f"date_conflict: {venue.id} not available {case.date}")
        if venue.minimum_spend_usd is not None and case.budget_usd < venue.minimum_spend_usd:
            venue_violations.append(
                f"minimum_not_met: {venue.id} minimum ${venue.minimum_spend_usd}, "
                f"budget ${case.budget_usd}"
            )
        estimate = estimate_for(venue, case.party_size)
        if estimate is not None and estimate > case.budget_usd:
            venue_violations.append(
                f"over_budget: {venue.id} estimate ${estimate}, budget ${case.budget_usd}"
            )
        if venue_violations:
            violations.update(venue_violations)
        else:
            viable = True
    if viable:
        return []
    return sorted(violations)
