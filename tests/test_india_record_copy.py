"""India crisis-record figures are rendered from captured API artifacts, never typed.

Recall excluding fraud-masked failures, the flagged count, the median lead,
the Fisher test and the two alert dials on every live page come from two
verbatim captures of the endpoints the evidence_india MCP tool reads. A typed
figure, the pre-correction vintage, or a pair of captures that disagree all
fail here. Dated articles keep what they published, under a correction note
(tests/test_article_corrections.py).
"""
import importlib.util
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import india_record_copy as copy_gen  # noqa: E402

CORRECTED_ONSETS = {
    "madhavpura-mercantile-co-operative-bank": ("2012-06-04", "2001-03-13"),
    "ckp-co-operative-bank": ("2020-04-30", "2014-05-02"),
    "rupee-co-operative-bank": ("2022-09-22", "2013-02-22"),
}


def _verifier():
    spec = importlib.util.spec_from_file_location(
        "verify_public_claims", os.path.join(ROOT, "scripts", "verify_public_claims.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def figures():
    return copy_gen.figures(copy_gen.load("india-evidence.json"),
                            copy_gen.load("india-alert-modes.json"))


def test_every_india_figure_matches_the_captured_artifacts():
    assert copy_gen.run(check=True) == []


def test_the_captures_are_the_endpoints_evidence_india_reads():
    assert copy_gen.CAPTURES == {
        "india-evidence.json": "https://api.liquilens.in/api/evidence/summary",
        "india-alert-modes.json": "https://api.liquilens.in/api/evidence/alert-modes",
    }
    for name in copy_gen.CAPTURES:
        status = copy_gen.load(name)["historical_evidence"]
        assert status["status"] == "PERIOD_END_PROXY_CONSTRUCTION_PIT"
        assert status["validated_backtest_eligible"] is False
        assert status["real_money_eligible"] is False


def test_the_capture_is_the_corrected_record():
    evidence = copy_gen.load("india-evidence.json")
    rows = {row["slug"]: row for row in evidence["institutions"]}
    for slug, (licence_cancellation, onset) in CORRECTED_ONSETS.items():
        assert rows[slug]["default_date"] == onset != licence_cancellation
        assert rows[slug]["verdict"] == "insufficient_data"
        assert rows[slug]["earliest_lead_months"] is None
    assert evidence["summary"]["insufficient_data"] >= len(CORRECTED_ONSETS)


def test_the_rendered_values_follow_the_capture():
    values = figures()
    evidence = copy_gen.load("india-evidence.json")
    ex = evidence["uncertainty"]["recall_ex_fraud"]
    assert values["recall_ex"] == f"{evidence['summary']['recall_ex_fraud_pct']:.1f}"
    assert (values["k_ex"], values["n_ex"]) == (str(ex["k"]), str(ex["n"]))
    assert float(values["lead"]) == float(evidence["summary"]["median_lead_months"])
    assert float(values["fisher_p"]) == evidence["ensemble_fisher"]["p_value_one_sided"]
    home = read("index.html")
    assert f'<div class="num">{values["k_ex"]} of {values["n_ex"]}</div>' in home
    assert f"one-sided Fisher exact p = {values['fisher_p']}" in home


def test_a_typed_figure_in_a_managed_phrase_is_caught():
    values = figures()
    source = read("llms.txt")
    typed = source.replace(f"reports {values['recall_ex']} percent recall", "reports 88.9 percent recall")
    assert typed != source
    problems = []
    assert copy_gen.rewrite(typed, "llms.txt", values, problems) == source
    assert problems == []
    moved = source.replace("The served headline reports", "The headline now reports")
    problems = []
    copy_gen.rewrite(moved, "llms.txt", values, problems)
    assert any("template matches 0 times, expected 1" in p for p in problems)


def test_disagreeing_captures_are_refused():
    evidence = copy_gen.load("india-evidence.json")
    modes = copy_gen.load("india-alert-modes.json")
    stale = json.loads(json.dumps(modes))
    for row in stale["modes"]:
        if row["mode"] == "sensitive":
            row["recall_ex_fraud"]["k"] += 3
    try:
        copy_gen.figures(evidence, stale)
    except ValueError as exc:
        assert "recapture" in str(exc)
    else:
        raise AssertionError("a stale alert-mode capture was accepted")


def test_no_pre_correction_india_figure_survives_on_a_live_page():
    vpc = _verifier()
    retired = re.compile(
        r"(?<![\d.])88\.9 ?(?:%|percent)|(?<![\d.])21\.5[- ]?(?:mo\b|month)|\b16 of 18\b|\b11 of 16\b"
        r"|\b0\.713\b|p &lt; 0\.001|\b0\.00032\b|Math\.round\(21\*p\)|data-month=\"21\.5\""
        r"|\b2012-06-04\b|\b2020-04-30\b|\b2022-09-22\b")
    hits = []
    for rel in vpc.published_files(ROOT):
        if not rel.endswith((".html", ".txt", ".js", ".mjs", ".json", ".xml")):
            continue
        if rel.startswith(("articles/", "updates/archive/")):
            continue  # dated publications carry correction notes instead
        text = read(rel)
        hits += [f"{rel}: {m.group(0)}" for m in retired.finditer(text)]
    assert hits == []
