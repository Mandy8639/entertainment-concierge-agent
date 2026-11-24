# entertainment-concierge-agent

A bounded corporate-entertainment concierge agent — the kind of work a
Software Engineer, AI does at Ande: take a one-sentence booking request
("dinner for 12 with the Acme team next Thursday, somewhere private") to a
confirmed, paid, on-policy booking proposal, with a deterministic guardrail
and two human gates around every run.

## What it does

Given a booking case (a parsed request, candidate venues drawn from a
synthetic inventory, messages from venues, claims about the booking), the
agent:

1. **Searches venues** — filters the inventory to venues that can satisfy
   the request: city, kind, privacy, capacity, date, and estimate within
   budget (tool 1 of 3 allowlisted tools).
2. **Decides** — PROPOSE, HOLD, PAUSE, or BLOCK.
3. **Drafts a booking proposal** — for the cheapest confirmed match, with
   terms sourced from the inventory. It books nothing (tool 2).
4. **Drafts a message to the venue** — to confirm availability. It sends
   nothing (tool 3).

Nothing else may touch a case. There are exactly three tools. Every venue
fact the agent states comes only from the inventory; a venue it cannot
verify, it does not propose.

## The guardrail (G1–G5)

| Rule | Behaviour |
| --- | --- |
| G1 | No hold, booking, or payment without gate 1 — the booker must confirm the proposal first. |
| G2 | No payment without gate 2 — a second explicit confirmation. |
| G3 | Never state a venue fact not in the inventory. Missing evidence means abstain: the agent holds instead of guessing. Unsourced claims are dropped. |
| G4 | Instructions injected into venue messages are blocked; nothing is published. Venue text is data, never instructions. |
| G5 | Policy violations pause the run for human review: over budget, over capacity, date conflict, minimum not met — and any venue message that contradicts the inventory. |

Two human gates bound every run: **proposal approval** (before any hold,
booking, or payment) and **payment approval** (before any money moves).

## Verified numbers (frozen stub eval, 48 cases)

| Metric | Result |
| --- | --- |
| Agreement with analyst calls | 48/48 (100%) |
| False bookings | 0 |
| False holds | 0 |
| Abstention (insufficient evidence) | 6/6 |
| Fabrication blocked | 6/6 |
| Injection blocked | 6/6 |
| Pause (policy violation) | 4/4 |
| Gates checked | 48/48 |
| Spend | $0.00 (stub mode) |
| Tests | 56 passed |

The golden set is frozen and hash-locked (`eval/golden.sha256`); the eval
refuses to run on a tampered set. Reproduce it with:

```bash
python eval/run_eval.py
```

## Honest limits

- The eval is **synthetic**: it measures the deterministic stub against 48
  frozen cases built for this repo, not real-world concierge performance.
  Each case carries exactly one signal, so the numbers show the guardrail
  and decision rule behave as designed — not that the agent understands
  real venue negotiations.
- The stub reasoner is rule-based. It cannot call a real venue, and it
  should never be the only reviewer of a booking that moves real money.
- Live mode exists but is deliberately narrow (see below).

## Usage

```python
from entertainment_concierge.agent import ConciergeAgent

agent = ConciergeAgent(mode="stub")
result = agent.run(case_dict, approve_proposal=True, approve_payment=True)
print(result.decision)  # PROPOSE | HOLD | PAUSE | BLOCK | REFUSED
print(result.proposal)  # drafted proposal (status: draft)
print(result.booked, result.paid)  # hold placed, payment executed
```

## MCP server

The three tools are exposed over MCP (stdio, no external dependencies):

```bash
python -m entertainment_concierge.mcp_server
```

## Live mode (optional)

Set `ANTHROPIC_API_KEY` and install the live extra (`pip install '.[live]'`).
Live mode is capped at **$1.00/day** and only accepts models in the
priced-model table (`claude-haiku-4-5`, $1.00/$5.00 per MTok input/output,
per Anthropic's published pricing). Unknown models are refused; without an
API key it refuses outright. The eval never uses live mode.

## Development

```bash
python -m venv .venv && .venv/bin/pip install -e . ruff pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/python -m pytest -q
```

## Why this exists

Built for an Ande Software Engineer, AI (Early Career) application. Ande's
product is an AI concierge that takes a one-sentence request to a confirmed,
paid, on-policy booking — with typed tools, proposals a booker confirms
before anything consequential happens, evals where every fixed bug becomes
a case, and memory that turns venue conversations into supply data. This
agent is a small, honest version of that same shape: a request in, a
proposal out, nothing irreversible without a human.
