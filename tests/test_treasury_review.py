"""Review bindings, failure visibility and honest local-use measurement."""
import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "developers/recipes"))
import treasury_review as review


def brief(*, day=1, verification=False):
    return {
        "schema": review.BRIEF_SCHEMA,
        "request": {"bank_slug": "example-bank", "size_usd": 100000},
        "verification": verification, "execution_authority": False,
        "started_at": f"2026-10-{day:02d}T09:00:00Z",
        "retrieved_at": f"2026-10-{day:02d}T09:00:10Z",
        "complete": True, "outcome": "evidence_returned",
        "comparison": {"status": "untrusted summary is ignored", "sections": []},
        "sections": [
            {"recipe": "funding-brief", "endpoint": review.ENDPOINTS["funding-brief"],
             "outcome": "evidence_returned", "evidence": {"money_market": {
                 "schema": "seiche.money-market-desk.v1", "ok": True,
                 "observation_date": "2026-09-30", "value": 0, "missing_value": None}}},
            {"recipe": "bank-review", "endpoint": review.ENDPOINTS["bank-review"],
             "outcome": "evidence_returned", "evidence": {"review": {
                 "slug": "example-bank", "status": "observed", "period": "2026-06-30"}}},
            {"recipe": "exit-brief", "endpoint": review.ENDPOINTS["exit-brief"],
             "outcome": "evidence_returned", "evidence": {"exit_cost": {
                 "asset": "BTC", "requested_size_usd": 100000,
                 "sell_cost_bp_by_venue": {"example": 0, "missing": None}}}},
        ],
    }


def assessments(disposition="reviewed"):
    return {recipe: {"disposition": disposition, "note": "Synthetic test assessment."}
            for recipe in review.PRODUCTS}


def record(*, day=1, verification=False, reviewer="fixture-reviewer", disposition="reviewed"):
    return review.acknowledge(review.prepare(brief(day=day, verification=verification)),
                              reviewer=reviewer, assessments=assessments(disposition),
                              reviewed_at=f"2026-10-{day:02d}T10:00:00Z")


def test_preparation_preserves_exact_sources_clocks_zero_null_and_authority():
    source = brief()
    before = copy.deepcopy(source)
    packet = review.prepare(source)
    assert source == before
    assert packet["source_brief"] == source
    assert packet["brief_sha256"] == review.digest(source)
    assert packet["boundaries"] == review.BOUNDARIES
    assert {row["product"] for row in packet["review_queue"]} == {"Seiche", "LiquiLens", "Undertow"}
    assert all(row["comparison"]["status"] == "no_baseline" for row in packet["review_queue"])
    assert all(row["freshness_assessment"] == "human_review_required" for row in packet["review_queue"])
    source["sections"][0]["evidence"]["money_market"]["value"] = 5
    assert packet["source_brief"]["sections"][0]["evidence"]["money_market"]["value"] == 0


def test_gaps_and_failed_siblings_remain_visible_even_if_brief_says_complete():
    source = brief()
    source["sections"][0]["evidence"]["money_market"]["freshness"] = {"status": "stale"}
    source["sections"][2].update(outcome="error", reason="fixture timeout")
    del source["sections"][2]["evidence"]
    packet = review.prepare(source)
    rows = {row["recipe"]: row for row in packet["review_queue"]}
    assert rows["funding-brief"]["source_inspection"]["signals"] == [
        {"path": "/money_market/freshness/status", "value": "stale"}]
    assert rows["exit-brief"]["evidence_sha256"] is None
    assert rows["exit-brief"]["retrieval_outcome"] == "error"
    assert rows["funding-brief"]["priority"] == rows["exit-brief"]["priority"] == 0
    assert rows["bank-review"]["evidence_sha256"] is not None
    assert packet["source_brief"]["complete"] is True  # Retained, never used as eligibility.


def test_exact_source_changes_recomputed_and_clock_only_change_is_visible():
    old, new = brief(), brief(day=2)
    packet = review.prepare(new, old)
    assert all(row["comparison"]["status"] == "unchanged_payload" for row in packet["review_queue"])
    new["sections"][0]["evidence"]["money_market"]["observation_date"] = "2026-10-01"
    packet = review.prepare(new, old)
    row = next(row for row in packet["review_queue"] if row["recipe"] == "funding-brief")
    assert row["comparison"]["changes"] == [{"path": "/money_market/observation_date", "kind": "changed"}]
    assert "risk_score" not in row


def test_source_flags_preserve_rights_and_json_pointer_escaping():
    evidence = {"a/b": {"~": {"status": "SOURCE_REVIEW_HOLD", "available": False}},
                "other": {"rights_status": "restricted", "value": None}}
    result = review.source_signals(evidence)
    assert {row["path"] for row in result["signals"]} == {
        "/a~1b/~0/status", "/a~1b/~0/available", "/other/rights_status"}
    assert result["inspection_truncated"] is False


def test_bounded_inspection_never_presents_omissions_as_an_all_clear(monkeypatch):
    monkeypatch.setattr(review, "MAX_SIGNALS", 2)
    result = review.source_signals({str(i): {"status": "unknown"} for i in range(8)})
    assert len(result["signals"]) == 2 and result["inspection_truncated"] is True
    monkeypatch.setattr(review, "MAX_DEPTH", 1)
    assert review.source_signals({"nested": {"status": "stale"}})["inspection_truncated"] is True
    monkeypatch.setattr(review, "MAX_NODES", 1)
    assert review.source_signals({"a": 1})["inspection_truncated"] is True


@pytest.mark.parametrize("mutation", [
    lambda b: b.update(verification="false"),
    lambda b: b.update(execution_authority=True),
    lambda b: b["request"].update(bank_slug=None),
    lambda b: b["request"].update(size_usd=True),
    lambda b: b["request"].update(extra="unexpected"),
    lambda b: b.update(sections=b["sections"][:2]),
    lambda b: b["sections"].__setitem__(2, b["sections"][0]),
    lambda b: b["sections"][0].update(endpoint="https://example.invalid/mcp"),
    lambda b: b["sections"][0].update(evidence=None),
    lambda b: b["sections"][0].update(evidence={"not_funding": 0}),
    lambda b: b["sections"][0]["evidence"]["money_market"].update(ok="true"),
    lambda b: b["sections"][0].update(outcome="safe"),
    lambda b: b["sections"][1]["evidence"]["review"].update(slug="different-bank"),
    lambda b: b["sections"][2]["evidence"]["exit_cost"].update(asset="ETH"),
    lambda b: b["sections"][2]["evidence"]["exit_cost"].update(requested_size_usd=1000),
    lambda b: b.update(retrieved_at="2026-10-01T09:00:10"),
    lambda b: b.update(retrieved_at="2026-09-01T09:00:10Z"),
])
def test_invalid_scope_identity_or_boundaries_rejected(mutation):
    source = brief()
    mutation(source)
    with pytest.raises(review.ResearchError):
        review.prepare(source)


@pytest.mark.parametrize("mutation", [
    lambda b: b["request"].update(bank_slug="another-bank"),
    lambda b: b["request"].update(size_usd=1000),
    lambda b: b.update(verification=True),
    lambda b: b.update(retrieved_at="2026-10-02T09:00:00Z"),
])
def test_baselines_cannot_mix_identity_modes_or_overlapping_captures(mutation):
    previous = brief()
    mutation(previous)
    with pytest.raises(review.ResearchError):
        review.prepare(brief(day=2), previous)


def test_acknowledgement_binds_human_notes_to_all_sections_without_upgrading_them():
    source = brief()
    source["sections"][0]["evidence"]["money_market"]["status"] = "stale"
    packet = review.prepare(source)
    notes = assessments("follow_up")
    result = review.acknowledge(packet, reviewer="fixture-reviewer", assessments=notes,
                                reviewed_at="2026-10-01T15:30:00+05:30")
    assert result["reviewed_at"] == "2026-10-01T10:00:00+00:00"
    assert result["worksheet"]["source_brief"] == source
    assert result["boundaries"] == review.BOUNDARIES
    assert result["measurement_class"] == "local_self_reported_review"
    notes["funding-brief"]["note"] = "Changed outside the record"
    assert result["assessments"]["funding-brief"]["note"] != notes["funding-brief"]["note"]
    review.validate_record(result)


@pytest.mark.parametrize("mutation", [
    lambda p: p["source_brief"]["request"].update(bank_slug="another-bank"),
    lambda p: p["review_queue"][0].update(priority=9),
    lambda p: p.update(verification=not p["verification"]),
    lambda p: p["boundaries"].update(execution_authority=True),
])
def test_modified_worksheets_cannot_receive_acknowledgements(mutation):
    packet = review.prepare(brief())
    mutation(packet)
    with pytest.raises(review.ResearchError):
        review.acknowledge(packet, reviewer="fixture-reviewer", assessments=assessments(),
                           reviewed_at="2026-10-01T10:00:00Z")


@pytest.mark.parametrize("overrides", [
    {"reviewer": ""}, {"reviewer": "person@example.com"},
    {"assessments": {}}, {"assessments": assessments("approve")},
    {"reviewed_at": "2026-10-01T08:00:00Z"}, {"reviewed_at": "2026-10-01T10:00:00"},
    {"reviewed_at": "2099-10-01T10:00:00Z"},
])
def test_reviews_need_explicit_valid_human_input(overrides):
    args = {"reviewer": "fixture-reviewer", "assessments": assessments(),
            "reviewed_at": "2026-10-01T10:00:00Z", **overrides}
    with pytest.raises(review.ResearchError):
        review.acknowledge(review.prepare(brief()), **args)


def test_empty_or_oversized_notes_rejected():
    for note in ["   ", "x" * 2001, "control\x00character"]:
        notes = assessments()
        notes["bank-review"]["note"] = note
        with pytest.raises(review.ResearchError):
            review.acknowledge(review.prepare(brief()), reviewer="fixture-reviewer", assessments=notes,
                               reviewed_at="2026-10-01T10:00:00Z")


def test_measurement_excludes_operators_deduplicates_and_does_not_invent_customers():
    first, second = record(), record(day=2, disposition="follow_up")
    result = review.measure([first, copy.deepcopy(first), second, record(verification=True)])
    assert result["operator_records_excluded"] == result["duplicate_records_excluded"] == 1
    assert result["distinct_review_acknowledgements"] == 2
    assert result["reviewer_aliases"] == result["aliases_reviewing_on_multiple_utc_days"] == 1
    assert result["section_dispositions"] == {"reviewed": 3, "follow_up": 3, "deferred": 0}
    assert all(result[key] is None for key in ("verified_external_users", "customer_retention", "paid_adoption"))


def test_rewording_or_redating_same_snapshot_does_not_create_repeat_use():
    first = record()
    again = review.acknowledge(first["worksheet"], reviewer="fixture-reviewer",
                               assessments=assessments("deferred"), reviewed_at="2026-10-02T10:00:00Z")
    result = review.measure([again, first])
    assert result["distinct_review_acknowledgements"] == 1
    assert result["aliases_reviewing_on_multiple_utc_days"] == 0
    assert result["section_dispositions"]["reviewed"] == 3


def test_records_bind_to_original_notes_and_cannot_change_verification():
    for change in [lambda r: r.update(verification=False),
                   lambda r: r["assessments"]["bank-review"].update(note="Tampered")]:
        result = record(verification=True)
        change(result)
        with pytest.raises(review.ResearchError):
            review.measure([result])


@pytest.mark.parametrize("raw", ['{"key": 1, "key": 2}', '{"v": NaN}', '{"v": 1e999}', '[] trailing'])
def test_ambiguous_or_nonfinite_json_rejected(tmp_path, raw):
    path = tmp_path / "bad.json"
    path.write_text(raw)
    with pytest.raises(review.ResearchError):
        review.read_json(path)


def test_file_limits_apply_before_parsing(tmp_path, monkeypatch):
    monkeypatch.setattr(review, "MAX_FILE_BYTES", 20)
    path = tmp_path / "large.json"
    path.write_text(json.dumps({"value": "x" * 30}))
    with pytest.raises(review.ResearchError, match="limit"):
        review.read_json(path)


def test_markdown_treats_source_fields_as_data_and_keeps_review_pending():
    source = brief()
    source["sections"][0]["evidence"]["money_market"]["```\n# forged header"] = {"status": "stale"}
    output = review.markdown(review.prepare(source))
    assert "awaiting human assessment" in output
    assert "\n# forged header\n" not in output
    assert "````json" in output


def test_cli_is_offline_and_no_human_review_is_fabricated(tmp_path, capsys, monkeypatch):
    def network_forbidden(*_args, **_kwargs):
        pytest.fail("offline review must not request network access")
    import socket
    monkeypatch.setattr(socket, "create_connection", network_forbidden)
    path = tmp_path / "brief.json"
    path.write_text(json.dumps(brief(verification=True)))
    assert review.main(["prepare", str(path)]) == 0
    packet = json.loads(capsys.readouterr().out)
    assert "assessments" not in packet
    worksheet = tmp_path / "worksheet.json"
    worksheet.write_text(json.dumps(packet))
    notes = tmp_path / "notes.json"
    notes.write_text(json.dumps(assessments()))
    assert review.main(["acknowledge", str(worksheet), "--reviewer", "fixture-reviewer",
                        "--assessments", str(notes), "--reviewed-at", "2026-10-01T10:00:00Z"]) == 0
    acknowledgement = tmp_path / "record.json"
    acknowledgement.write_text(capsys.readouterr().out)
    assert review.main(["measure", str(acknowledgement)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["operator_records_excluded"] == 1
    assert result["distinct_review_acknowledgements"] == 0
    assert review.main(["prepare", str(tmp_path / "missing.json")]) == 1
    assert json.loads(capsys.readouterr().err)["status"] == "error"
