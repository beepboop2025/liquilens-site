"""Offline, caller-triggered watchlist acceptance and partial-failure contracts."""
import copy
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECIPE_DIR = ROOT / "developers/recipes"
SPEC = importlib.util.spec_from_file_location("bank_watchlist", RECIPE_DIR / "bank_watchlist.py")
watch = importlib.util.module_from_spec(SPEC)
sys.path.insert(0, str(RECIPE_DIR))
try:
    SPEC.loader.exec_module(watch)
finally:
    sys.path.pop(0)

UUID4 = "7d01321d-7cec-4af5-b662-974bb9a6af02"
SLUGS = ["first-bank", "second-bank", "third-bank"]
COVERAGE = {"schema": "liquilens.bank-specialisation.v1", "asof": "2026-08-01",
            "rows": [{"slug": slug, "status": "observed"} for slug in SLUGS]}
REVIEW = {
    "slug": "first-bank", "status": "observed", "period_end": "2026-03-31",
    "available_at": "2026-07-14", "retrieved_at": "2026-08-01T10:00:00Z",
    "sources": [{"url": "https://example.org/filing", "sha256": "a" * 64}],
    "metrics": {"recoveries": 0, "write_offs": None},
    "history": [{"period_end": "2025-03-31", "value": 0}],
    "freshness": {"status": "stale"}, "real_money_eligible": False,
    "validated_backtest_eligible": False, "score_authority": False,
    "interpretation_limits": ["A write-off is not a cash recovery"],
}


class Transport:
    def __init__(self, *, coverage=None, reviews=None, fail_slug=None, failure="transport", fail_stage=None):
        self.coverage = copy.deepcopy(COVERAGE if coverage is None else coverage)
        self.reviews = copy.deepcopy(reviews or {slug: {**REVIEW, "slug": slug} for slug in SLUGS})
        self.calls = []
        self.fail_slug = fail_slug
        self.failure = failure
        self.fail_stage = fail_stage

    def __call__(self, url, payload, headers):
        self.calls.append((url, copy.deepcopy(payload), dict(headers)))
        method = payload["method"]
        if method == "initialize":
            if self.fail_stage == "initialize":
                raise watch.ResearchError("fixture initialization failure")
            result = {"protocolVersion": "2025-11-25"}
        elif method == "notifications/initialized":
            return 202, {}, b""
        elif payload["params"]["name"] == "banking_specialisation_coverage":
            if self.fail_stage == "coverage":
                raise watch.ResearchError("fixture coverage failure")
            result = {"structuredContent": self.coverage}
        else:
            slug = payload["params"]["arguments"]["slug"]
            if slug == self.fail_slug:
                if self.failure == "transport":
                    raise watch.ResearchError("HTTP 429; no automatic retry")
                if self.failure == "malformed-content":
                    result = {"content": None}
                elif self.failure == "numeric-content":
                    result = {"content": 7}
                else:
                    result = {"isError": True, "structuredContent": self.reviews[slug]}
            else:
                result = {"structuredContent": self.reviews[slug]}
        return 200, {"Mcp-Session-Id": "fixture-session"}, json.dumps(
            {"jsonrpc": "2.0", "id": payload["id"], "result": result}).encode()

    def review_slugs(self):
        return [payload["params"]["arguments"]["slug"] for _, payload, _ in self.calls
                if payload["params"].get("name") == "bank_asset_quality_review"]


def test_one_session_one_coverage_and_sequential_explicit_reviews():
    transport = Transport()
    result = watch.watchlist(SLUGS, transport=transport)
    assert result["outcome"] == "evidence_returned" and result["complete"] is True
    assert result["requested_slugs"] == SLUGS
    assert result["execution_authority"] is False
    methods = [payload["method"] for _, payload, _ in transport.calls]
    assert methods == ["initialize", "notifications/initialized"] + ["tools/call"] * 4
    assert sum(payload["params"].get("name") == "banking_specialisation_coverage"
               for _, payload, _ in transport.calls) == 1
    assert transport.review_slugs() == SLUGS
    for url, payload, headers in transport.calls[2:]:
        assert url == "https://api.liquilens.in/mcp"
        assert headers["Mcp-Session-Id"] == "fixture-session"
        assert headers["MCP-Protocol-Version"] == "2025-11-25"
        if "slug" in payload["params"]["arguments"]:
            assert payload["params"]["arguments"]["include_history"] is True


def test_evidence_clocks_sources_zeros_nulls_and_gates_are_unchanged():
    transport = Transport()
    result = watch.watchlist([SLUGS[0]], transport=transport)
    assert result["evidence"]["coverage"] == COVERAGE
    row = result["results"][0]
    assert row["evidence"]["review"] == REVIEW
    assert row["retrieved_at"] != REVIEW["retrieved_at"]
    assert row["evidence"]["review"]["freshness"]["status"] == "stale"
    assert transport.reviews[SLUGS[0]] == REVIEW


def test_unknown_slug_is_reported_and_never_fuzzily_requested():
    transport = Transport()
    result = watch.watchlist(["first", "first-bank", "unknown"], transport=transport)
    assert transport.review_slugs() == ["first-bank"]
    assert [row["outcome"] for row in result["results"]] == ["not_covered", "evidence_returned", "not_covered"]
    assert result["complete"] is True and result["outcome"] == "unavailable"
    assert "evidence" not in result["results"][0]


@pytest.mark.parametrize("status", ["unavailable", "not_covered"])
def test_unavailable_review_preserved_without_retry_and_later_bank_reviewed(status):
    missing = {"slug": "first-bank", "status": status, "metrics": None,
               "sources": [], "reason": "No accepted filing", "available_at": None}
    transport = Transport(reviews={"first-bank": missing, "second-bank": {**REVIEW, "slug": "second-bank"}})
    result = watch.watchlist(SLUGS[:2], transport=transport)
    assert result["results"][0]["evidence"]["review"] == missing
    assert result["results"][0]["outcome"] == status
    assert result["results"][1]["outcome"] == "evidence_returned"
    assert result["complete"] is True and result["outcome"] == "unavailable"


@pytest.mark.parametrize("slugs", [[], SLUGS * 7, ["first-bank", "first-bank"],
                                   ["First Bank"], [" first-bank"], ["first_bank"],
                                   ["https://other.test"], [None], ["a" * 129], "first-bank"])
def test_invalid_selection_fails_before_any_network(slugs):
    transport = Transport()
    with pytest.raises(watch.ResearchError):
        watch.watchlist(slugs, transport=transport)
    assert transport.calls == []


def test_twenty_distinct_banks_is_the_inclusive_bound():
    slugs = ["bank-" + str(number) for number in range(20)]
    transport = Transport(coverage={"rows": [{"slug": slug} for slug in slugs]},
                          reviews={slug: {**REVIEW, "slug": slug} for slug in slugs})
    result = watch.watchlist(slugs, transport=transport)
    assert len(result["results"]) == 20 and result["complete"] is True
    assert transport.review_slugs() == slugs


@pytest.mark.parametrize("failure", ["transport", "tool", "malformed-content", "numeric-content"])
def test_midrun_failure_keeps_partial_evidence_and_stops(failure):
    transport = Transport(fail_slug="second-bank", failure=failure)
    result = watch.watchlist(SLUGS, transport=transport)
    assert result["complete"] is False and result["outcome"] == "error"
    assert result["error"]["stage"] == "review"
    assert [row["outcome"] for row in result["results"]] == ["evidence_returned", "error", "not_attempted"]
    assert result["results"][0]["evidence"]["review"] == REVIEW
    assert transport.review_slugs() == SLUGS[:2]


def test_mismatched_review_identity_is_rejected_and_stops():
    transport = Transport(reviews={"first-bank": {**REVIEW, "slug": "wrong-bank"}})
    result = watch.watchlist(SLUGS, transport=transport)
    assert "identity" in result["error"]["reason"]
    assert result["results"][0]["outcome"] == "error"
    assert "evidence" not in result["results"][0]
    assert transport.review_slugs() == ["first-bank"]


@pytest.mark.parametrize("stage", ["initialize", "coverage"])
def test_setup_failure_reports_every_bank_not_attempted(stage):
    transport = Transport(fail_stage=stage)
    result = watch.watchlist(SLUGS, transport=transport)
    assert result["error"]["stage"] == stage
    assert result["complete"] is False and result["outcome"] == "error"
    assert [row["outcome"] for row in result["results"]] == ["not_attempted"] * 3
    assert transport.review_slugs() == []


@pytest.mark.parametrize("coverage", [{}, {"rows": None}, {"rows": {"first-bank": True}}])
def test_missing_coverage_rows_cannot_authorize_reviews(coverage):
    transport = Transport(coverage=coverage)
    result = watch.watchlist(SLUGS, transport=transport)
    assert result["outcome"] == "error" and result["error"]["stage"] == "coverage"
    assert result["evidence"]["coverage"] == coverage
    assert transport.review_slugs() == []


@pytest.mark.parametrize("client_id", [None, UUID4, UUID4.upper()])
@pytest.mark.parametrize("verification", [False, True])
def test_optional_id_and_synthetic_classification(client_id, verification):
    transport = Transport()
    result = watch.watchlist(["first-bank"], client_id=client_id,
                             verification=verification, transport=transport)
    assert result["verification"] is verification
    assert UUID4 not in json.dumps(result)
    for url, _, headers in transport.calls:
        assert url == "https://api.liquilens.in/mcp"
        if client_id is None:
            assert "X-Liquilens-Client-Id" not in headers
        else:
            assert headers["X-Liquilens-Client-Id"] == UUID4
        if verification:
            assert headers["X-Liquilens-Traffic-Class"] == "synthetic"
            assert headers["User-Agent"] == "LiquiLens-Operator-Growth-Audit/1.0"
        else:
            assert "X-Liquilens-Traffic-Class" not in headers
            assert "Operator" not in headers["User-Agent"]


@pytest.mark.parametrize("client_id", ["", "me@example.org", "not-a-uuid", 123,
                                       "7d01321d-7cec-1af5-b662-974bb9a6af02",
                                       "7d01321d-7cec-4af5-7662-974bb9a6af02",
                                       UUID4.replace("-", ""), "{" + UUID4 + "}"])
def test_invalid_client_identity_fails_before_any_network(client_id):
    transport = Transport()
    with pytest.raises(watch.ResearchError, match="UUID4"):
        watch.watchlist(["first-bank"], client_id=client_id, transport=transport)
    assert transport.calls == []


@pytest.mark.parametrize("scenario,expected", [("success", 0), ("unavailable", 2),
                                              ("partial", 1), ("malformed-partial", 1)])
def test_cli_exit_matches_full_partial_or_unavailable_report(monkeypatch, capsys, scenario, expected):
    partial = scenario in ("partial", "malformed-partial")
    transport = Transport(fail_slug="second-bank" if partial else None,
                          failure="malformed-content" if scenario == "malformed-partial" else "transport")
    real_watchlist = watch.watchlist
    monkeypatch.setattr(watch, "watchlist", lambda slugs, **kwargs: real_watchlist(slugs, transport=transport, **kwargs))
    slugs = ["unknown"] if scenario == "unavailable" else SLUGS
    assert watch.main([*slugs, "--verification", "--client-id", UUID4]) == expected
    captured = capsys.readouterr()
    assert captured.err == ""
    report = json.loads(captured.out)
    assert len(report["results"]) == len(slugs)
    assert report["complete"] is not partial
    if partial:
        assert report["results"][0]["evidence"]["review"] == REVIEW


def test_cli_invalid_selection_returns_failure_before_network(monkeypatch, capsys):
    transport = Transport()
    real_watchlist = watch.watchlist
    monkeypatch.setattr(watch, "watchlist", lambda slugs, **kwargs: real_watchlist(slugs, transport=transport, **kwargs))
    assert watch.main(["first-bank", "first-bank"]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and json.loads(captured.err)["outcome"] == "error"
    assert transport.calls == []


def test_published_guide_and_entry_link_exist():
    page = (ROOT / "developers/index.html").read_text()
    guide = (RECIPE_DIR / "bank-watchlist.md").read_text()
    assert '/developers/recipes/bank-watchlist.md' in page
    assert '/developers/recipes/bank_watchlist.py' in guide
    assert '/developers/recipes/financial_research.py' in guide
    assert '--verification' in guide and '--client-id' in guide
