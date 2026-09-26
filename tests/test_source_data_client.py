import importlib.util
import io
import json
from pathlib import Path
import sys

import pytest

RECIPES = Path(__file__).resolve().parents[1] / "developers/recipes"
sys.path.insert(0, str(RECIPES))
import financial_research as client
import source_data


def test_negotiated_version_is_used_for_later_requests():
    calls = []
    def transport(url, payload, headers):
        calls.append(dict(headers))
        if payload["method"] == "notifications/initialized":
            return 202, {}, b""
        result = {"protocolVersion": "2025-06-18", "serverInfo": {"name": "archive", "version": "1"}}
        return 200, {}, json.dumps({"jsonrpc": "2.0", "id": payload["id"], "result": result}).encode()
    reader = client.Client(client.RESEARCH_DATA_ENDPOINT, transport=transport)
    reader.initialize()
    assert calls[-1]["MCP-Protocol-Version"] == "2025-06-18"


def test_sse_stops_at_matching_reply_without_waiting_for_stream_close():
    class Stream(io.BytesIO):
        headers = {"Content-Type": "text/event-stream; charset=utf-8"}
        def readline(self, count):
            line = super().readline(count)
            assert line, "client waited for stream close after receiving its reply"
            return line
    stream = Stream(b': heartbeat\r\n\r\ndata: {"jsonrpc":"2.0","method":"notifications/progress"}\n\n'
                    b'event: message\ndata: {"jsonrpc":"2.0",\ndata: "id":1,"result":{"ok":true}}\n\n')
    assert json.loads(client.read_response(stream, {"id": 1}))["result"] == {"ok": True}


def test_sse_incomplete_or_oversized_reply_is_a_transport_failure(monkeypatch):
    class Stream(io.BytesIO):
        headers = {"Content-Type": "text/event-stream"}
    with pytest.raises(client.ResearchError, match="matching"):
        client.read_response(Stream(b'data: {"id":2}\n\n'), {"id": 1})
    monkeypatch.setattr(client, "MAX_BYTES", 10)
    with pytest.raises(client.ResearchError, match="limit"):
        client.read_response(Stream(b":" + b"x" * 100), {"id": 1})


def test_source_data_preserves_missing_values_receipts_and_next_page():
    evidence = {"schema": "liquilens.research-data.v1", "series": {"dataset": "ofr-repo", "id": "rate"}, "next_offset": 2,
                "rows": [{"dataset": "ofr-repo", "series": "rate", "value": None, "state": "unavailable"},
                         {"dataset": "ofr-repo", "series": "rate", "value": 0, "unit": "percent", "receipt": "abc"}],
                "receipts": {"abc": {"retrieved_at": "2026-09-25T10:00:00Z"}}}
    calls = []
    def transport(url, payload, headers):
        calls.append(payload)
        assert url == client.RESEARCH_DATA_ENDPOINT
        assert headers["X-Liquilens-Traffic-Class"] == "synthetic"
        if payload["method"] == "initialize":
            result = {"protocolVersion": "2025-06-18", "serverInfo": {"name": "archive"}}
        elif payload["method"] == "notifications/initialized":
            return 202, {}, b""
        else:
            result = {"structuredContent": evidence}
        return 200, {}, json.dumps({"jsonrpc": "2.0", "id": payload["id"], "result": result}).encode()
    result = source_data.query("observations", {"dataset": "ofr-repo", "series": "rate", "limit": 2}, verification=True, transport=transport)
    assert result == evidence
    assert len(calls) == 3  # no hidden next-page request


@pytest.mark.parametrize("command,args", [("observations", {}), ("catalog", {"dataset": "x"}),
    ("series", {"dataset": "x", "limit": True}), ("series", {"dataset": "x", "limit": 1.5}),
    ("catalog", {"product": "unknown"}), ("tracked-institutions", {"limit": 501})])
def test_invalid_source_queries_never_call_network(command, args):
    def transport(*unused):
        pytest.fail("invalid input reached the network")
    with pytest.raises(client.ResearchError):
        source_data.query(command, args, transport=transport)
