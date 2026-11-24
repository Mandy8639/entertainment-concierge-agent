"""The three allowlisted tools. Nothing else may touch a case.

1. venue_search — filter the inventory to venues that can satisfy the case.
2. booking_proposal — draft a booking proposal. It never books.
3. venue_message — draft a message to a venue. It never sends.
"""

from __future__ import annotations

from dataclasses import dataclass

from entertainment_concierge.packet import Case, Venue, case_from_dict

ALLOWED_TOOLS = (
    "venue_search",
    "booking_proposal",
    "venue_message",
)

MESSAGE_PURPOSES = (
    "confirm_availability",
    "negotiate_minimum",
    "request_menu",
)


@dataclass(frozen=True)
class VenueMatch:
    """One venue that can satisfy the case, with its estimate."""

    venue: Venue
    estimate_usd: int
    source: str


@dataclass(frozen=True)
class Proposal:
    """A drafted booking proposal. Status is always 'draft': it books nothing."""

    venue_id: str
    venue_name: str
    date: str
    party_size: int
    estimate_usd: int
    minimum_usd: int
    terms: list[str]
    status: str = "draft"


@dataclass(frozen=True)
class Draft:
    """A drafted message to a venue. ``sent`` is always False: it sends nothing."""

    to_venue: str
    to_venue_id: str
    purpose: str
    subject: str
    body: str
    sent: bool = False


def estimate_for(venue: Venue, party_size: int) -> int | None:
    """Total estimate: the larger of the minimum and price x party.

    Returns None when either input is unknown — the agent must not guess.
    """
    if venue.minimum_spend_usd is None or venue.price_per_person_usd is None:
        return None
    return max(venue.minimum_spend_usd, venue.price_per_person_usd * party_size)


def venue_search(case: Case) -> list[VenueMatch]:
    """Tool 1: venues that can satisfy the case, cheapest first.

    A venue matches only when every fact is known and passes: city, kind,
    private requirement, capacity, date availability, and estimate within
    budget. Unknown facts exclude the venue (G3) rather than being guessed.
    """
    matches = []
    for venue in case.venues:
        if venue.city != case.city or venue.kind != case.kind:
            continue
        if case.private_required and not venue.private:
            continue
        if venue.capacity is None or case.party_size > venue.capacity:
            continue
        if venue.available_dates is None or case.date not in venue.available_dates:
            continue
        estimate = estimate_for(venue, case.party_size)
        if estimate is None or estimate > case.budget_usd:
            continue
        matches.append(VenueMatch(venue=venue, estimate_usd=estimate, source=venue.id))
    matches.sort(key=lambda match: (match.estimate_usd, match.venue.id))
    return matches


def booking_proposal(case: Case, venue_id: str) -> Proposal:
    """Tool 2: draft a booking proposal for one matching venue.

    The proposal is a draft: it holds nothing, books nothing, and pays
    nothing. Only a venue returned by venue_search may be proposed.
    """
    matches = {match.venue.id: match for match in venue_search(case)}
    if venue_id not in matches:
        raise ValueError(f"venue {venue_id!r} is not a confirmed match for this case")
    match = matches[venue_id]
    venue = match.venue
    terms = [
        f"Private room: {'yes' if venue.private else 'no'}",
        f"Minimum spend: ${venue.minimum_spend_usd}",
        f"Price per person: ${venue.price_per_person_usd}",
    ]
    if venue.requires:
        terms.append(f"Pre-booking step (human): {venue.requires}")
    terms.append("Booker confirmation required before any hold, booking, or payment.")
    return Proposal(
        venue_id=venue.id,
        venue_name=venue.name,
        date=case.date,
        party_size=case.party_size,
        estimate_usd=match.estimate_usd,
        minimum_usd=venue.minimum_spend_usd or 0,
        terms=terms,
    )


def venue_message(case: Case, venue_id: str, purpose: str) -> Draft:
    """Tool 3: draft a message to one candidate venue. It is never sent.

    The body cites inventory facts only — never a fact the inventory does
    not know.
    """
    if purpose not in MESSAGE_PURPOSES:
        raise ValueError(f"unknown message purpose: {purpose!r}")
    by_id = {venue.id: venue for venue in case.venues}
    if venue_id not in by_id:
        raise ValueError(f"unknown venue: {venue_id!r}")
    venue = by_id[venue_id]
    capacity_text = (
        f"Your listed capacity is {venue.capacity}"
        if venue.capacity is not None
        else "Your listed capacity is not published"
    )
    minimum_text = (
        f"your minimum spend is ${venue.minimum_spend_usd}"
        if venue.minimum_spend_usd is not None
        else "your minimum spend is not published"
    )
    price_text = (
        f"Your listed price per person is ${venue.price_per_person_usd}."
        if venue.price_per_person_usd is not None
        else "Your price per person is not published."
    )
    if purpose == "confirm_availability":
        subject = f"Availability check — {case.party_size} guests on {case.date}"
        body = (
            f"Hello {venue.name}, confirming availability for a party of "
            f"{case.party_size} on {case.date} for a {case.occasion}. "
            f"{capacity_text} and {minimum_text}. Please confirm the date is still open."
        )
    elif purpose == "negotiate_minimum":
        subject = f"Minimum spend — {case.party_size} guests on {case.date}"
        body = (
            f"Hello {venue.name}, our budget for {case.party_size} guests on "
            f"{case.date} is ${case.budget_usd}. {minimum_text.capitalize()}. "
            f"Is there any flexibility on the minimum?"
        )
    else:  # request_menu
        subject = f"Menu options — {case.party_size} guests on {case.date}"
        body = (
            f"Hello {venue.name}, could you share menu options for a party of "
            f"{case.party_size} on {case.date}? {price_text}"
        )
    return Draft(
        to_venue=venue.name,
        to_venue_id=venue.id,
        purpose=purpose,
        subject=subject,
        body=body,
    )


def read_case(data: dict) -> Case:
    """Load and validate a case. Raises ValueError if malformed."""
    return case_from_dict(data)
