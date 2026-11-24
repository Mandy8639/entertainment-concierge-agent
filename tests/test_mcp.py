"""Tests for the MCP server (stdio JSON-RPC, no external dependencies)."""

from __future__ import annotations

import json

from entertainment_concierge.mcp_server import handle
from tests.conftest import clean_case


def test_initialize_and_ping() -> None:
    response = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert response["result"]["serverInfo"]["name"] == "entertainment-concierge-agent"
    assert handle({"jsonrpc": "2.0", "id": 2, "method": "ping"})["result"] == {}


def test_notifications_return_none() -> None:
    assert handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_tools_list_exposes_exactly_three_tools() -> None:
    response = handle({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
    names = [tool["name"] for tool in response["result"]["tools"]]
    assert names == ["venue_search", "booking_proposal", "venue_message"]


def test_tools_call_venue_search() -> None:
    response = handle(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "venue_search", "arguments": {"case": clean_case()}},
        }
    )
    matches = json.loads(response["result"]["content"][0]["text"])
    assert [m["venue"]["id"] for m in matches] == ["V001", "V002"]


def test_tools_call_booking_proposal() -> None:
    response = handle(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "booking_proposal",
                "arguments": {"case": clean_case(), "venue_id": "V001"},
            },
        }
    )
    proposal = json.loads(response["result"]["content"][0]["text"])
    assert proposal["status"] == "draft"
    assert proposal["venue_id"] == "V001"


def test_tools_call_venue_message() -> None:
    response = handle(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "venue_message",
                "arguments": {
                    "case": clean_case(),
                    "venue_id": "V001",
                    "purpose": "confirm_availability",
                },
            },
        }
    )
    draft = json.loads(response["result"]["content"][0]["text"])
    assert draft["sent"] is False


def test_tools_call_unknown_tool_and_method_return_errors() -> None:
    unknown_tool = handle(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "book_venue", "arguments": {}},
        }
    )
    assert unknown_tool["error"]["code"] == -32602
    unknown_method = handle({"jsonrpc": "2.0", "id": 8, "method": "resources/list"})
    assert unknown_method["error"]["code"] == -32601


def test_tools_call_bad_arguments_return_error() -> None:
    response = handle(
        {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "booking_proposal",
                "arguments": {"case": clean_case(), "venue_id": "V013"},
            },
        }
    )
    assert response["error"]["code"] == -32602
