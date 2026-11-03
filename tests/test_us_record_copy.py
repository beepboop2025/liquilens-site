"""US record figures are rendered from captured API artifacts, never typed.

The count, recall, lead, AUC, recall interval, the 2026 replay, the SVB lead
and the named misses on every published page come from two verbatim
production captures. A typed figure, a stale vintage or Seiche's withheld
reading shown as an outage all fail here.
"""
import importlib.util
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import us_record_copy as copy_gen  # noqa: E402


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
    return copy_gen.figures(copy_gen.load("us-radar-validation.json"),
                            copy_gen.load("us-evidence.json"))


def test_every_us_figure_matches_the_captured_artifacts():
    assert copy_gen.run(check=True) == []


def test_the_two_captures_and_the_site_gate_agree():
    values = figures()
    vpc = _verifier()
    assert values["count"] == vpc.US_FAILURE_COUNT
    assert values["recall"] == vpc.US_RECALL_PCT
    assert values["auc"] == vpc.US_AUC
    evidence = copy_gen.load("us-evidence.json")
    assert evidence["historical_evidence"]["status"] == "CURRENT_AMENDED_CONSTRUCTION_PIT"
    assert evidence["historical_evidence"]["validated_backtest_eligible"] is False


def test_a_typed_figure_in_a_managed_phrase_is_caught():
    values = figures()
    source = read("llms.txt")
    typed = source.replace(f"over all {values['count']} FDIC failures",
                           f"over all {int(values['count']) - 2} FDIC failures")
    assert typed != source
    problems = []
    assert copy_gen.rewrite(typed, "llms.txt", values, problems) == source
    assert problems == []
    moved = source.replace("The current diagnostic reports", "The diagnostic now reports")
    problems = []
    copy_gen.rewrite(moved, "llms.txt", values, problems)
    assert any("template matches 0 times, expected 1" in p for p in problems)


def test_no_retired_us_vintage_survives_on_a_published_page():
    vpc = _verifier()
    retired = re.compile(
        r"\b552\b|72\.8 ?(?:%|percent)|21\.7[- ]?(?:mo|month)|\b0\.854\b|four 2026 failures"
        r"|13 and 19 months|17\.3[- ]?(?:mo|month)|2 OF 4 FLAGGED|two of four flagged"
        r"|69\.0 to 76\.6|seven we missed|Five of the seven")
    hits = []
    for rel in vpc.published_files(ROOT):
        if not rel.endswith((".html", ".txt", ".js", ".mjs")) or rel.startswith(("updates/archive/", "articles/")):
            continue
        text = read(rel)
        hits += [f"{rel}: {m.group(0)}" for m in retired.finditer(text)]
    assert hits == []


def test_study_cut_figures_stay_dated_instead_of_posing_as_the_current_record():
    us = read("us/index.html")
    research = read("research/index.html")
    assert "false positive rate on the 2026-03-31 cut" in us
    assert "confusion matrix · 24 month horizon · 2026-03-31 cut" in us
    assert "not re-run on the current record" in us
    assert "July 2026 study cut" in research
    assert "precision is 4.1 percent against a 0.83 percent base rate" in research


def test_the_2026_replay_and_named_misses_follow_the_served_record():
    values = figures()
    us = read("us/index.html")
    for miss in values["_misses"]:
        if miss["cert"] not in copy_gen.MISS_NOTE:
            assert f"{miss['name']}, {miss['fail_date'][:4]}" in us
    leads = re.findall(r'<span class="months">([0-9.]+|miss)</span>', us)
    assert leads[:len(values["_flagged"])] == sorted(
        (f"{i['earliest_flag_lead_months']:.1f}" for i in values["_flagged"]),
        key=float, reverse=True)
    assert f"<h3>The {values['misses']} we missed" in us


def test_seiche_context_is_never_claimed_to_condition_the_us_scores():
    us = read("us/index.html")
    assert "conditioned on" not in us
    assert "used_in_score" in us


def test_seiche_refusals_are_named_with_their_policy_not_shown_as_outages():
    us = read("us/index.html")
    library = read("evidence-library.js")
    sample = read("access/sample/app.js")
    for source in (us, library, sample):
        assert "source_rights_restricted" in source
    assert "withheld by Seiche" in us and "No number is shown, estimated or replaced" in us
    assert "liveJSON('https://api.seiche.info" not in library
    assert "Seiche withholds this reading under its source-rights policy" in library
    assert "Seiche withholds its funding gauge under its source-rights policy" in sample


def test_status_probes_seiche_health_and_reads_the_mcp_inventory_live():
    status = read("status/index.html")
    assert "probe('https://api.seiche.info/api/health'" in status
    assert "api.seiche.info/api/public" not in status
    assert "23 public read-only tools" not in status
    assert "rpc('tools/list')" in status and "rpc('prompts/list')" in status
    assert "a dated observation, not the current release" in status


def test_radar_movement_never_reads_first_vintage():
    library = read("evidence-library.js")
    assert "first vintage" not in library
    assert "no comparable quarter" in library


def test_capability_copy_carries_no_hand_typed_package_versions():
    data = json.loads(read("updates/capabilities.json"))
    version = re.compile(r"\b\d+\.\d+(?:\.\d+|\.x)\b")
    for capability in data["capabilities"]:
        for key in ("title", "description", "state", "boundary", "action"):
            assert not version.search(capability[key]), (capability["id"], key)
    assert data["previous_review"]["url"].endswith("/updates/archive/2026-10-18.json")
    archived = json.loads(read("updates/archive/2026-10-18.json"))
    assert archived["reviewed_on"] == data["previous_review"]["reviewed_on"]


def test_india_figures_beside_a_us_lookalike_phrase_are_left_alone():
    # The India record shares phrasing with the US stats ("median lead").
    # Its stat must keep agreeing with the India sentence on the same page,
    # and a template that matches a second phrase is reported, not applied.
    research = read("research/index.html")
    sentence = re.search(r"The served headline is ([0-9.]+) percent recall excluding fraud-masked "
                         r"failures \(\d+ of \d+\) and a ([0-9.]+)-month median lead", research)
    stat = re.search(r'<b>([0-9.]+)%</b><span>served recall</span></div>\s*'
                     r'<div class="stat"><b>([0-9.]+) mo</b>', research)
    assert sentence and stat and sentence.groups() == stat.groups()
    values = figures()
    template = next(t for rel, t in copy_gen.TEMPLATES if rel == "research/index.html"
                    and t.startswith("<h3>The United States"))
    doubled = research + copy_gen.render(template, values)
    problems = []
    copy_gen.rewrite(doubled, "research/index.html", values, problems)
    assert any("matches 2 times, expected 1" in p for p in problems)
