"""The concierge agent: two human gates around three allowlisted tools."""

from __future__ import annotations

from dataclasses import dataclass, field

from entertainment_concierge import guardrail
from entertainment_concierge.reasoner import LiveReasoner, StubReasoner
from entertainment_concierge.tools import (
    ALLOWED_TOOLS,
    Draft,
    Proposal,
    booking_proposal,
    read_case,
    venue_message,
    venue_search,
)


@dataclass(frozen=True)
class AgentResult:
    """Everything one agent run produces (or refuses to produce)."""

    case_id: str
    decision: str  # PROPOSE | HOLD | PAUSE | BLOCK | REFUSED
    proposal: Proposal | None = None
    draft: Draft | None = None
    flags: dict = field(default_factory=dict)
    published: bool = False
    booked: bool = False
    paid: bool = False
    provenance: list[str] = field(default_factory=list)
    spend_usd: float = 0.0
    gates_checked: list[str] = field(default_factory=list)
    refusal: str = ""


class ConciergeAgent:
    """Bounded corporate-entertainment concierge agent."""

    def __init__(self, mode: str = "stub", live_model: str | None = None) -> None:
        if mode not in ("stub", "live"):
            raise ValueError(f"unknown mode: {mode!r}")
        self.mode = mode
        self._live = LiveReasoner(model=live_model) if mode == "live" else None

    def plan(self) -> list[str]:
        """The tool plan, fixed and allowlisted. Gate 1 approves this plan."""
        return list(ALLOWED_TOOLS)

    def run(
        self,
        case_data: dict,
        *,
        approve_proposal: bool,
        approve_payment: bool,
    ) -> AgentResult:
        case = read_case(case_data)
        if not approve_proposal:
            return AgentResult(
                case_id=case.id,
                decision="REFUSED",
                refusal="proposal gate not approved: no tool ran",
                gates_checked=["proposal"],
            )
        matches = venue_search(case)
        injected = guardrail.scan_injection(case.messages)
        fabricated = guardrail.scan_fabrication(case.claims)
        missing = guardrail.missing_evidence(case)
        conflicts = guardrail.scan_venue_conflicts(case)
        violations = guardrail.policy_violations(case)
        flags = {
            "injection": [message.text for message in injected],
            "fabrication": [claim.text for claim in fabricated],
            "missing_evidence": missing,
            "venue_conflicts": conflicts,
            "policy_violations": violations,
        }
        if self.mode == "live":
            assert self._live is not None
            decision, cost = self._live.decide(case, matches)
            spend = cost
        else:
            decision = StubReasoner().decide(
                case,
                matches,
                injection=bool(injected),
                fabrication=bool(fabricated),
                missing=bool(missing),
                conflicts=bool(conflicts),
                violations=bool(violations),
                remediation=bool(case.remediation_needed),
            )
            spend = 0.0
        proposal = None
        draft = None
        published = False
        booked = False
        paid = False
        if decision == "PROPOSE" and matches:
            # Gate 1 (G1): the proposal is issued and the hold placed only
            # because the booker confirmed it. Gate 2 (G2): payment only
            # with the second explicit confirmation.
            best = matches[0].venue
            proposal = booking_proposal(case, best.id)
            draft = venue_message(case, best.id, "confirm_availability")
            published = True
            booked = True
            paid = bool(approve_payment)
        return AgentResult(
            case_id=case.id,
            decision=decision,
            proposal=proposal,
            draft=draft,
            flags=flags,
            published=published,
            booked=booked,
            paid=paid,
            provenance=guardrail.cited_sources(case),
            spend_usd=spend,
            gates_checked=["proposal", "payment"],
        )
