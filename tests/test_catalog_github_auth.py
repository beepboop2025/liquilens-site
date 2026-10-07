import io
import json
import urllib.request

import pytest

from scripts import verify_catalog_edge as verifier


@pytest.mark.parametrize("payload_bytes,accepted", [(2_200_000, True), (4_200_000, False)])
def test_mcp_reader_enforces_the_worker_http_envelope(monkeypatch, payload_bytes, accepted):
    url = verifier.DEFAULT_MCP_URL
    payload = {"jsonrpc": "2.0", "id": "expanded-atlas", "result": {"context": "x" * payload_bytes}}
    raw = json.dumps(payload).encode()
    monkeypatch.setattr(verifier, "_validate_public_https_url", lambda value: value)

    def open_request(request, **kwargs):
        response = io.BytesIO(raw)
        response.headers = {"Content-Type": "application/json"}
        response.geturl = lambda: url
        return response

    monkeypatch.setattr(verifier._SAFE_OPENER, "open", open_request)
    request = {"jsonrpc": "2.0", "id": "expanded-atlas", "method": "tools/call"}
    if accepted:
        actual, _ = verifier._mcp_request(url, request)
        assert actual == payload
    else:
        with pytest.raises(RuntimeError, match="MCP response exceeds the 4194304-byte response limit"):
            verifier._mcp_request(url, request)
    assert verifier.MAX_JSON_BODY_BYTES == 2 * 1024 * 1024


@pytest.mark.parametrize("url,authenticated", [
    ("https://api.github.com/repos/beepboop2025/seiche/actions/runs/1", True),
    ("https://api.github.com:443/repos/beepboop2025/seiche/commits/main/status", True),
    ("https://liquilens.in/.well-known/ai-catalog.json", False),
    ("https://api.github.com.evil.example/repo", False),
    ("https://api.github.com./repo", False),
    ("https://api.github.com:444/repo", False),
    ("http://api.github.com/repo", False),
    ("https://user@api.github.com/repo", False),
])
def test_ephemeral_github_credential_is_strictly_origin_scoped(monkeypatch, url, authenticated):
    # Isolate header scope even for URLs the separate network validator rejects.
    monkeypatch.setattr(verifier, "_validate_public_https_url", lambda value: value)
    monkeypatch.setenv("GITHUB_TOKEN", "ephemeral-test-token")
    requests = []

    def open_request(request, **kwargs):
        requests.append(request)
        response = io.BytesIO(b"{}")
        response.headers = {"Content-Type": "application/json"}
        response.geturl = lambda: url
        return response

    monkeypatch.setattr(verifier._SAFE_OPENER, "open", open_request)
    verifier._fetch_bytes(url, accept="application/json")
    request = requests[0]
    assert request.get_header("Authorization") == (
        "Bearer ephemeral-test-token" if authenticated else None
    )
    assert "Authorization" not in request.headers
    # urllib's default redirect implementation only copies ordinary headers.
    redirected = urllib.request.HTTPRedirectHandler().redirect_request(
        request, None, 302, "Found", {}, "https://liquilens.in/"
    )
    assert redirected.get_header("Authorization") is None


def test_malformed_token_never_reaches_network_or_error_text(monkeypatch):
    monkeypatch.setattr(verifier, "_validate_public_https_url", lambda value: value)
    monkeypatch.setenv("GITHUB_TOKEN", "secret\r\nX-Other: injected")
    monkeypatch.setattr(verifier._SAFE_OPENER, "open", lambda *a, **k: pytest.fail("network called"))
    with pytest.raises(RuntimeError, match="invalid whitespace") as error:
        verifier._fetch_bytes("https://api.github.com/repos/a/b", accept="application/json")
    assert "secret" not in str(error.value)


def test_verifier_still_rejects_redirects_before_following_them(monkeypatch):
    monkeypatch.setattr(verifier, "_validate_public_https_url", lambda value: value)
    request = urllib.request.Request("https://api.github.com/repos/a/b")
    request.add_unredirected_header("Authorization", "Bearer ephemeral-test-token")
    with pytest.raises(RuntimeError, match="redirects are not accepted"):
        verifier._RejectRedirects().redirect_request(
            request, None, 302, "Found", {}, "https://liquilens.in/"
        )


def test_registry_timeout_still_consumes_the_shared_deadline(monkeypatch):
    monkeypatch.setattr(verifier.time, "monotonic", lambda: 100.0)
    with verifier._network_budget(7.0):
        assert verifier._bounded_timeout(verifier.REGISTRY_REQUEST_TIMEOUT, "Registry") == 7.0
        monkeypatch.setattr(verifier.time, "monotonic", lambda: 107.0)
        with pytest.raises(RuntimeError, match="network deadline exhausted"):
            verifier._bounded_timeout(verifier.REGISTRY_REQUEST_TIMEOUT, "Registry")


def test_mcp_retry_deadline_retains_the_original_failure(monkeypatch, capsys):
    calls = []

    def reject(*args):
        calls.append(args)
        raise RuntimeError("source response exceeds the selected byte ceiling")

    def expired(delay):
        raise RuntimeError("network deadline exhausted before retry")

    monkeypatch.setattr(verifier, "_verify_mcp", reject)
    monkeypatch.setattr(verifier, "_bounded_sleep", expired)
    with pytest.raises(RuntimeError, match="selected byte ceiling.*deadline exhausted"):
        verifier._verify_mcp_with_retries(
            url=verifier.DEFAULT_MCP_URL, expected_version_tag="source",
            attempts=24, delay=5,
        )
    assert len(calls) == 1
    assert "MCP attempt 1/24: source response exceeds" in capsys.readouterr().out


def test_read_timeout_names_the_failing_public_endpoint(monkeypatch):
    url = "https://registry.modelcontextprotocol.io/v0.1/servers/example/versions/latest"
    monkeypatch.setattr(verifier, "_validate_public_https_url", lambda value: value)

    def time_out(*args, **kwargs):
        raise TimeoutError("The read operation timed out")

    monkeypatch.setattr(verifier._SAFE_OPENER, "open", time_out)
    with pytest.raises(RuntimeError, match="GET timed out") as error:
        verifier._fetch_bytes(url, accept="application/json")
    assert url in str(error.value)


def test_four_product_proofs_start_together_and_share_the_original_deadline(monkeypatch):
    import json
    import threading

    ready = threading.Barrier(4, timeout=5)
    monkeypatch.setattr(verifier.time, "monotonic", lambda: 100.0)

    def proof(label):
        ready.wait()
        assert verifier._bounded_timeout(20, label) == 7.0
        return label + " passed"

    monkeypatch.setattr(verifier, "_verify_palimpsest_release_with_retries",
                        lambda **kwargs: proof("Palimpsest"))
    monkeypatch.setattr(verifier, "_verify_sibling_product",
                        lambda label, card: proof(label))
    with verifier._network_budget(7):
        result = verifier._verify_external_release_proofs(
            ai_catalog=json.loads(verifier.CATALOG_PATH.read_text()), api_catalog={},
            palimpsest_proof=True, sibling_proof=True, attempts=1, delay=0)
    assert result == ("Palimpsest passed", "Undertow passed; Riptide passed; NarcoScope passed")


def test_concurrent_siblings_keep_retry_caps_and_fail_on_one_missing_proof(monkeypatch):
    import json
    from collections import Counter

    calls = Counter()

    def proof(label, card):
        calls[label] += 1
        if label == "NarcoScope":
            raise RuntimeError("Registry unavailable")
        return label + " passed"

    monkeypatch.setattr(verifier, "_verify_sibling_product", proof)
    monkeypatch.setattr(verifier, "_bounded_sleep", lambda delay: None)
    with pytest.raises(RuntimeError, match="NarcoScope: Registry unavailable") as error:
        verifier._verify_sibling_products_with_retries(
            ai_catalog=json.loads(verifier.CATALOG_PATH.read_text()), attempts=99, delay=99)
    assert calls == {"Undertow": 1, "Riptide": 1, "NarcoScope": 2}
    assert "passed=Undertow passed; Riptide passed" in str(error.value)
