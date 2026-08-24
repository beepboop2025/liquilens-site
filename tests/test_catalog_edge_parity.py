import json
from pathlib import Path

import pytest

from scripts.verify_catalog_edge import (
    EXPECTED_MCP_TOOLS,
    EXPECTED_MCP_VERSION,
    decode_mcp_response,
    response_problem,
)


ROOT = Path(__file__).resolve().parents[1]


def test_edge_parity_accepts_only_the_exact_committed_catalog():
    expected = json.loads(
        (ROOT / ".well-known/ai-catalog.json").read_text(encoding="utf-8")
    )
    body = json.dumps(expected, separators=(",", ":")).encode()
    assert response_problem(expected, body, "application/ai-catalog+json") is None


def test_edge_parity_accepts_the_exact_protocol_catalog():
    expected = json.loads(
        (ROOT / "protocol/catalog.json").read_text(encoding="utf-8")
    )
    body = json.dumps(expected, separators=(",", ":")).encode()
    assert response_problem(
        expected,
        body,
        "application/json; charset=utf-8",
        "application/json",
    ) is None


def test_edge_parity_explains_a_missing_carrier_entry():
    expected = json.loads(
        (ROOT / ".well-known/ai-catalog.json").read_text(encoding="utf-8")
    )
    actual = dict(expected)
    actual["entries"] = [
        row for row in expected["entries"]
        if row["identifier"] != "urn:air:liquilens.in:protocol:evidence-carrier"
    ]
    problem = response_problem(
        expected,
        json.dumps(actual).encode(),
        "application/ai-catalog+json; charset=utf-8",
    )
    assert problem is not None
    assert "urn:air:liquilens.in:protocol:evidence-carrier" in problem


def test_mcp_receipt_decoder_accepts_one_json_or_sse_message():
    payload = {
        "jsonrpc": "2.0",
        "id": "tools",
        "result": {"tools": [{"name": name} for name in EXPECTED_MCP_TOOLS]},
    }
    encoded = json.dumps(payload).encode()
    assert decode_mcp_response(encoded, "application/json; charset=utf-8") == payload
    assert decode_mcp_response(
        b"event: message\ndata: " + encoded + b"\n\n",
        "text/event-stream; charset=utf-8",
    ) == payload
    assert EXPECTED_MCP_VERSION == "0.1.3"


def test_mcp_receipt_decoder_rejects_batches_and_multiple_sse_events():
    with pytest.raises(ValueError, match="one JSON-RPC object"):
        decode_mcp_response(b"[]", "application/json")
    with pytest.raises(ValueError, match="expected one MCP SSE data event"):
        decode_mcp_response(
            b"data: {\"id\":1}\n\ndata: {\"id\":2}\n\n",
            "text/event-stream",
        )
