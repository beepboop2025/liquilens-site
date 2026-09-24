"""Release verification must remain distinguishable from ordinary clients."""
import io
import json

import pytest

from scripts import verify_catalog_edge as verifier


@pytest.mark.parametrize("extra_headers", [
    None,
    {"X-Liquilens-Traffic-Class": "external", "Mcp-Session-Id": "test-session"},
    {"x-LIQUILENS-tRaFFIC-CLASS": "unknown"},
])
def test_mcp_verification_always_sends_one_synthetic_marker(monkeypatch, extra_headers):
    endpoint = "https://api.liquilens.in/mcp"
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    seen = []

    class Response(io.BytesIO):
        headers = {"Content-Type": "application/json"}

        def geturl(self):
            return endpoint

    def open_request(request, **kwargs):
        seen.append(request)
        return Response(b'{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}')

    monkeypatch.setattr(verifier, "_validate_public_https_url", lambda url: None)
    monkeypatch.setattr(verifier._SAFE_OPENER, "open", open_request)
    result, _ = verifier._mcp_request(endpoint, payload, extra_headers=extra_headers)

    assert result["result"] == {"tools": []}
    assert len(seen) == 1
    assert [(name.lower(), value) for name, value in seen[0].header_items()
            if name.lower() == "x-liquilens-traffic-class"] == [
                ("x-liquilens-traffic-class", "synthetic")]
    headers = {name.lower(): value for name, value in seen[0].header_items()}
    assert headers["x-liquilens-traffic-class"] == "synthetic"
    assert headers["user-agent"] == "LiquiLens-edge-check/1"
    assert json.loads(seen[0].data) == payload
    if extra_headers and "Mcp-Session-Id" in extra_headers:
        assert headers["mcp-session-id"] == "test-session"
