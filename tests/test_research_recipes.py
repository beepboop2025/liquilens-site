"""Exercise the downloadable client against offline MCP and HTTP transports."""
import copy
import importlib.util
import json
from pathlib import Path
import time
import tomllib
from urllib.error import HTTPError

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("financial_research", ROOT / "developers/recipes/financial_research.py")
recipe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recipe)

COVERAGE = {"schema": "liquilens.bank-specialisation.v1", "rows": [{"slug": "cosmos-ucb", "status": "observed"}]}
REVIEW = {"slug": "cosmos-ucb", "status": "observed", "period_end": "2026-03-31",
          "available_at": "2026-08-01", "sources": ["https://example.org/filing"],
          "interpretation_limits": ["A write-off is not a cash recovery"],
          "metrics": {"missing": None}, "score_authority": False}
DESK = {"schema": "seiche.money-market-desk.v1", "ok": True, "asof": "2026-08-01",
        "freshness": {"status": "stale"}, "caveats": ["Historical context only"],
        "source_metadata": [{"id": "fred_sofr", "asof": "2026-08-01"}], "context_only": True}


class Transport:
    def __init__(self, evidence=None, *, text=False):
        self.evidence = evidence or {"banking_specialisation_coverage": COVERAGE,
                                     "bank_asset_quality_review": REVIEW,
                                     "money_market_context": DESK}
        self.calls = []
        self.text = text

    def __call__(self, url, payload, headers):
        self.calls.append((url, copy.deepcopy(payload), dict(headers)))
        method = payload["method"]
        if method == "notifications/initialized":
            return 202, {}, b""
        if method == "initialize":
            result = {"protocolVersion": recipe.PROTOCOL, "capabilities": {},
                      "serverInfo": {"name": "fixture", "version": "1"}}
        else:
            value = self.evidence[payload["params"]["name"]]
            result = {"content": [{"type": "text", "text": json.dumps(value)}]} if self.text else {"structuredContent": value}
        return 200, {"Mcp-Session-Id": "fixture-session"}, json.dumps({"jsonrpc": "2.0", "id": payload["id"], "result": result}).encode()


def test_bank_review_discovers_exact_slug_and_preserves_evidence():
    transport = Transport()
    result = recipe.research("bank-review", "cosmos-ucb", transport=transport)
    assert result["outcome"] == "evidence_returned"
    assert result["evidence"] == {"coverage": COVERAGE, "review": REVIEW}
    assert result["execution_authority"] is False
    calls = transport.calls
    assert [call[1]["method"] for call in calls] == ["initialize", "notifications/initialized", "tools/call", "tools/call"]
    assert calls[0][1]["params"]["clientInfo"] == recipe.CLIENT_INFO
    assert calls[-1][1]["params"] == {"name": "bank_asset_quality_review", "arguments": {"slug": "cosmos-ucb", "include_history": True}}
    assert calls[-1][2]["Mcp-Session-Id"] == "fixture-session"
    assert calls[-1][2]["MCP-Protocol-Version"] == "2025-11-25"
    assert "X-Liquilens-Traffic-Class" not in calls[-1][2]
    assert "Operator" not in calls[-1][2]["User-Agent"]


def test_unknown_slug_is_not_fuzzily_matched_or_requested():
    transport = Transport()
    result = recipe.research("bank-review", "cosmos", transport=transport)
    assert result["outcome"] == "not_covered"
    assert len(transport.calls) == 3
    assert "review" not in result["evidence"]


def test_coverage_only_has_no_review_call():
    transport = Transport()
    result = recipe.research("bank-review", transport=transport)
    assert result["evidence"] == {"coverage": COVERAGE}
    assert len(transport.calls) == 3


@pytest.mark.parametrize("available", [True, False])
def test_funding_preserves_stale_or_unavailable_facts(available):
    desk = {**DESK, "ok": available}
    transport = Transport({"money_market_context": desk}, text=True)
    result = recipe.research("funding-brief", transport=transport)
    assert result["evidence"]["money_market"] == desk
    assert result["outcome"] == ("evidence_returned" if available else "unavailable")
    assert transport.calls[-1][1]["params"]["arguments"] == {"section": "all"}


def test_operator_verification_is_explicit_and_distinct_from_normal_readers():
    transport = Transport()
    result = recipe.research("funding-brief", verification=True, transport=transport)
    assert result["verification"] is True
    for _, _, headers in transport.calls:
        assert headers["X-Liquilens-Traffic-Class"] == "synthetic"
        assert headers["User-Agent"] == "LiquiLens-Operator-Growth-Audit/1.0"


@pytest.mark.parametrize("message", [
    {"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "quota"}},
    {"jsonrpc": "2.0", "id": 1, "result": {"isError": True, "structuredContent": {"looks": "useful"}}},
    {"jsonrpc": "2.0", "id": 2, "result": {"structuredContent": REVIEW}},
    {"jsonrpc": "2.0", "id": 1, "result": {"content": []}},
    {"jsonrpc": "2.0", "id": 1, "result": {"structuredContent": {"status": "FAILED", "reason": "upstream failed"}}},
    {"jsonrpc": "2.0", "id": 1, "result": {"structuredContent": [REVIEW]}},
])
def test_rpc_and_tool_failures_cannot_become_research(message):
    client = recipe.Client(recipe.ENDPOINTS["bank-review"], transport=lambda *_: (200, {}, json.dumps(message).encode()))
    with pytest.raises(recipe.ResearchError):
        client.call("bank_asset_quality_review", {})


def test_malformed_json_and_nonfinite_numbers_fail():
    for raw in (b"not JSON", b'{"value":NaN}', b'\xff'):
        with pytest.raises(recipe.ResearchError):
            recipe.parse_json(raw)


def test_unexpected_negotiation_stops_before_calling_tools():
    transport = lambda *_: (200, {}, b'{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"unexpected"}}')
    with pytest.raises(recipe.ResearchError, match="negotiate"):
        recipe.Client(recipe.ENDPOINTS["bank-review"], transport=transport).initialize()


def test_http_failure_and_redirects_are_not_followed(monkeypatch):
    class Opener:
        def open(self, *_args, **_kwargs):
            raise HTTPError(recipe.ENDPOINTS["bank-review"], 429, "limited", {}, None)
    monkeypatch.setattr(recipe, "build_opener", lambda *_: Opener())
    with pytest.raises(recipe.ResearchError, match="HTTP 429"):
        recipe._exchange(recipe.ENDPOINTS["bank-review"], {}, {})
    with pytest.raises(recipe.ResearchError, match="redirect refused"):
        recipe.NoRedirects().redirect_request(None, None, 302, None, None, "https://other.test")
    with pytest.raises(recipe.ResearchError, match="not allowed"):
        recipe.Client("https://other.test/mcp")


def test_response_cap_and_wall_clock_deadline(monkeypatch):
    class Response:
        status = 200
        headers = {}
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def read(self, count):
            assert count == recipe.MAX_BYTES + 1
            return b" " * count
    class Opener:
        def open(self, *_args, **kwargs):
            assert kwargs["timeout"] == 20
            return Response()
    monkeypatch.setattr(recipe, "build_opener", lambda *_: Opener())
    with pytest.raises(recipe.ResearchError, match="2 MiB"):
        recipe._exchange(recipe.ENDPOINTS["bank-review"], {}, {})
    monkeypatch.setattr(recipe, "TIMEOUT", 0.01)
    monkeypatch.setattr(recipe, "_exchange", lambda *_: time.sleep(0.1))
    with pytest.raises(recipe.ResearchError, match="deadline"):
        recipe.exchange(recipe.ENDPOINTS["bank-review"], {}, {})


def test_cli_error_exit_and_unavailable_exit(monkeypatch, capsys):
    def failure(*_args, **_kwargs):
        raise recipe.ResearchError("fixture failure")
    monkeypatch.setattr(recipe, "research", failure)
    assert recipe.main(["funding-brief"]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and json.loads(captured.err)["outcome"] == "error"
    monkeypatch.setattr(recipe, "research", lambda *_args, **_kwargs: {"outcome": "unavailable"})
    assert recipe.main(["funding-brief"]) == 2


def test_client_downloads_and_page_entry_are_consistent():
    base = ROOT / "developers/recipes"
    cursor = json.loads((base / "cursor-mcp.json").read_text())
    codex = tomllib.loads((base / "codex-mcp.toml").read_text())
    assert cursor["mcpServers"] == codex["mcp_servers"]
    assert {row["url"] for row in cursor["mcpServers"].values()} == set(recipe.ENDPOINTS.values())
    manifest = json.loads((base / "manifest.json").read_text())
    assert manifest["clientInfo"] == recipe.CLIENT_INFO
    assert {row["id"] for row in manifest["recipes"]} == set(recipe.ENDPOINTS)
    page = (ROOT / "developers/index.html").read_text()
    for filename in ("financial_research.py", "cursor-mcp.json", "codex-mcp.toml", "manifest.json"):
        assert "/developers/recipes/" + filename in page
    assert "--verification" in page and "no API key or LLM" in page
