import io
import urllib.request

import pytest

from scripts import verify_catalog_edge as verifier


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
