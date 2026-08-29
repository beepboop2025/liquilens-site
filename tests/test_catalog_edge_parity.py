import hashlib
import json
from pathlib import Path

import pytest

from scripts.verify_catalog_edge import (
    EXPECTED_MCP_CONTRACT,
    EXPECTED_MCP_TOOLS,
    EXPECTED_MCP_VERSION,
    decode_mcp_response,
    require_fetch_semantics,
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
    assert EXPECTED_MCP_VERSION == "0.1.5"
    assert EXPECTED_MCP_CONTRACT["serverInfo"] == {
        "name": "financial-evidence",
        "version": "0.1.5",
    }
    assert [tool["name"] for tool in EXPECTED_MCP_CONTRACT["tools"]] == list(
        EXPECTED_MCP_TOOLS
    )
    tools_bytes = json.dumps(
        EXPECTED_MCP_CONTRACT["tools"], sort_keys=True, separators=(",", ":")
    ).encode()
    assert hashlib.sha256(tools_bytes).hexdigest() == (
        EXPECTED_MCP_CONTRACT["toolsSha256"]
    )


def test_mcp_receipt_decoder_rejects_batches_and_multiple_sse_events():
    with pytest.raises(ValueError, match="one JSON-RPC object"):
        decode_mcp_response(b"[]", "application/json")
    with pytest.raises(ValueError, match="expected one MCP SSE data event"):
        decode_mcp_response(
            b"data: {\"id\":1}\n\ndata: {\"id\":2}\n\n",
            "text/event-stream",
        )


def test_live_fetch_receipt_requires_output_semantics_and_bound_provenance():
    digest = "sha256:" + "a" * 64
    source_url = "https://api.seiche.info/api/v2/money-markets"
    result = {
        "isError": False,
        "structuredContent": {
            "status": "complete",
            "transport_status": "complete",
            "status_semantics": "transport_only",
            "evidence_status": "not_evaluated",
            "carrier_verification": "not_performed",
            "output_status": "complete",
            "output_error": None,
            "sources": [{
                "product": "Seiche",
                "ok": True,
                "bytes": 123,
                "source_url": source_url,
                "content_sha256": digest,
                "source_reported": {
                    "adapter": "seiche_money_markets_v1",
                    "state": [{
                        "name": "response_status",
                        "value": "PARTIAL",
                        "path": "/status",
                        "provenance": {
                            "kind": "source_reported_allowlisted_field",
                            "source_url": source_url,
                            "content_sha256": digest,
                        },
                    }],
                    "clocks": "not_reported",
                },
            }],
        },
    }
    assert require_fetch_semantics(result)["product"] == "Seiche"

    drifted = json.loads(json.dumps(result))
    drifted["structuredContent"]["output_status"] = "unavailable"
    with pytest.raises(RuntimeError, match="semantic boundary differs"):
        require_fetch_semantics(drifted)

    spoofed = json.loads(json.dumps(result))
    spoofed["structuredContent"]["sources"][0]["source_reported"]["state"][0][
        "provenance"
    ]["content_sha256"] = "sha256:" + "b" * 64
    with pytest.raises(RuntimeError, match="provenance is incomplete"):
        require_fetch_semantics(spoofed)
