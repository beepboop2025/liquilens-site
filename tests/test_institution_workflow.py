"""Identity, partial-evidence and authority invariants for the public recipe."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

RECIPES = Path(__file__).resolve().parents[1] / "developers" / "recipes"
sys.path.insert(0, str(RECIPES))
spec = importlib.util.spec_from_file_location("institution_workflow", RECIPES / "institution_review.py")
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


def packet():
    body = {"schema": "liquilens.review-packet.v1", "status": "covered",
            "entity": {"slug": "example-lender", "name": "Example Lender"},
            "human_review_required": True, "board": {"as_of": "2025-03-31", "score": 0},
            "coverage": {"dark_lenses": [{"lens": "market", "reason": "not computed"}]}}
    body["content_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False,
                                                       allow_nan=False, separators=(",", ":")).encode()).hexdigest()
    return body


def transport(fixtures, fail_product=None):
    calls = []
    def send(url, body, headers):
        calls.append((url, body, headers))
        if fail_product and fail_product in url:
            raise workflow.ResearchError("service unavailable")
        method = body["method"]
        if method == "notifications/initialized":
            return 202, {}, b""
        result = {"protocolVersion": "2025-11-25"} if method == "initialize" else {
            "structuredContent": copy.deepcopy(fixtures[body["params"]["name"]])}
        return 200, {}, json.dumps({"jsonrpc": "2.0", "id": body["id"], "result": result}).encode()
    return send, calls


def sources(**extra):
    return {"institution_review_packet": packet(), "data_health": {"fresh": 1, "stale": 1},
            "funding_stress_now": {"schema": "seiche.public.v2", "generated_at": "2026-09-01T00:00:00Z"},
            "money_market_context": {"schema": "seiche.money-market-desk.v1", "ok": True}, **extra}


def test_independent_dates_zero_missingness_and_unassessed_compliance_survive():
    send, calls = transport(sources())
    result = workflow.review(institution="Example Lender", jurisdiction="IN", verification=True, transport=send)
    assert result["retrieval_outcome"] == "responses_returned"
    assert result["regulatory_assessment"]["status"] == "not_assessed"
    assert result["execution_authority"] is False
    assert result["sections"][0]["evidence"] == packet()
    assert result["sections"][2]["evidence"]["generated_at"] == "2026-09-01T00:00:00Z"
    assert all(entry["retrieved_at"] for entry in result["sections"])
    assert all(headers["X-Liquilens-Traffic-Class"] == "synthetic" for _, _, headers in calls)
    assert len([b for _, b, _ in calls if b["method"] == "tools/call"]) == 4


@pytest.mark.parametrize("change", [lambda p: p["board"].update(score=100),
                                   lambda p: p.update(entity={"slug": "other", "name": "Other"}),
                                   lambda p: p.update(entity=[]),
                                   lambda p: p.update(human_review_required=False)])
def test_mismatched_or_tampered_packets_never_enter_the_review(change):
    data = packet()
    change(data)
    send, _ = transport(sources(institution_review_packet=data))
    result = workflow.review(institution="example-lender", transport=send)
    assert result["retrieval_outcome"] == "partial_or_unavailable"
    assert result["sections"][0]["status"] == "error"
    assert "evidence" not in result["sections"][0]
    assert result["sections"][2]["status"] == "returned"


def test_uncovered_bank_does_not_trigger_a_guessed_dossier():
    send, calls = transport(sources(banking_specialisation_coverage={"rows": []}))
    result = workflow.review(bank_slug="missing-bank", transport=send)
    assert result["retrieval_outcome"] == "partial_or_unavailable"
    assert not any(b.get("params", {}).get("name") == "bank_asset_quality_review" for _, b, _ in calls)
    assert result["sections"][1]["status"] == "not_requested"


@pytest.mark.parametrize("product", ["api.liquilens.in", "api.seiche.info"])
def test_one_failed_service_preserves_the_other_without_retry(product):
    send, calls = transport(sources(), fail_product=product)
    result = workflow.review(institution="example-lender", transport=send)
    assert result["retrieval_outcome"] == "partial_or_unavailable"
    assert sum(product in url for url, _, _ in calls) == 1
    assert any(s["status"] == "returned" for s in result["sections"])


def test_not_covered_and_source_unavailability_cannot_become_success():
    missing = {"schema": "liquilens.review-packet.v1", "status": "not_covered",
               "query": "example-lender", "human_review_required": True}
    send, _ = transport(sources(institution_review_packet=missing,
                               money_market_context={"schema": "seiche.money-market-desk.v1", "ok": False}))
    result = workflow.review(institution="example-lender", transport=send)
    assert result["retrieval_outcome"] == "partial_or_unavailable"
    assert result["sections"][0]["evidence"]["status"] == "not_covered"


def test_invalid_identifiers_do_not_make_network_calls():
    def forbidden(*_):
        pytest.fail("unexpected network request")
    for query in ["\nname", "###", "x" * 161]:
        with pytest.raises(ValueError):
            workflow.review(institution=query, transport=forbidden)
