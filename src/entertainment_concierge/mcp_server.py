"""Minimal MCP server (stdio JSON-RPC 2.0), no external dependencies.

Exposes the three allowlisted tools over the Model Context Protocol:
tools/list and tools/call. Run: python -m entertainment_concierge.mcp_server
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict

from entertainment_concierge.tools import (
    ALLOWED_TOOLS,
    booking_proposal,
    read_case,
    venue_message,
    venue_search,
)

TOOLS = {
    "venue_search": {
        "description": "Filter the inventory to venues that can satisfy a booking case.",
        "inputSchema": {
            "type": "object",
            "properties": {"case": {"type": "object"}},
            "required": ["case"],
        },
    },
    "booking_proposal": {
        "description": "Draft a booking proposal for one matching venue. Never books.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "case": {"type": "object"},
                "venue_id": {"type": "string"},
            },
            "required": ["case", "venue_id"],
        },
    },
    "venue_message": {
        "description": "Draft a message to one candidate venue. Never sends.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "case": {"type": "object"},
                "venue_id": {"type": "string"},
                "purpose": {"type": "string"},
            },
            "required": ["case", "venue_id", "purpose"],
        },
    },
}


def _tool_result(payload: object) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(payload, indent=2)}]}


def handle(request: dict) -> dict | None:
    """Handle one JSON-RPC request. Returns None for notifications."""
    method = request.get("method", "")
    request_id = request.get("id")
    params = request.get("params", {}) or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "entertainment-concierge-agent", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method.startswith("notifications/"):
        return None
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {"name": name, **spec} for name, spec in TOOLS.items() if name in ALLOWED_TOOLS
                ]
            },
        }
    if method == "tools/call":
        name = params.get("name", "")
        arguments = params.get("arguments", {}) or {}
        try:
            if name == "venue_search":
                case = read_case(arguments["case"])
                matches = venue_search(case)
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": _tool_result([asdict(match) for match in matches]),
                }
            if name == "booking_proposal":
                case = read_case(arguments["case"])
                proposal = booking_proposal(case, arguments["venue_id"])
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": _tool_result(asdict(proposal)),
                }
            if name == "venue_message":
                case = read_case(arguments["case"])
                draft = venue_message(case, arguments["venue_id"], arguments["purpose"])
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": _tool_result(asdict(draft)),
                }
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": f"unknown tool: {name}"},
            }
        except (KeyError, ValueError) as exc:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": str(exc)},
            }
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"unknown method: {method}"},
    }


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
