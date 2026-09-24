"""Exercise partial research, comparison identity and discovery without network."""
import copy
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "developers/recipes"))
import trading_brief as brief


def transport(*, failed=(), missing=False):
    calls = []
    def run(url, payload, headers):
        calls.append((url, copy.deepcopy(payload), dict(headers)))
        method = payload["method"]
        if method == "notifications/initialized":
            return 202, {}, b""
        if method == "initialize":
            result = {"protocolVersion": "2025-11-25"}
        elif method == "tools/list":
            result = {"tools": [] if missing else [{"name": n} for names in brief.REQUIRED.values() for n in names]}
        else:
            name = payload["params"]["name"]
            if name in failed:
                raise brief.ResearchError("HTTP 429; no automatic retry")
            values = {
                "money_market_context": {"schema": "seiche.money-market-desk.v1", "ok": True,
                                         "freshness": {"status": "stale"}, "value": None},
                "exit_cost": {"asset": "BTC", "requested_size_usd": 100000,
                              "sell_cost_bp_by_venue": {"one": 0, "two": None}},
                "banking_specialisation_coverage": {"rows": [{"slug": "cosmos-ucb"}]},
                "bank_asset_quality_review": {"slug": "cosmos-ucb", "status": "observed"},
            }
            result = {"structuredContent": values[name]}
        return 200, {}, json.dumps({"jsonrpc": "2.0", "id": payload["id"], "result": result}).encode()
    return run, calls


def test_brief_preserves_stale_missing_and_zero_values_and_all_three_sources():
    wire, calls = transport()
    result = brief.brief(slug="cosmos-ucb", transport=wire, verification=True)
    assert result["complete"] is True
    assert result["execution_authority"] is False
    assert len(result["sections"]) == 3
    assert result["sections"][0]["evidence"]["money_market"]["freshness"] == {"status": "stale"}
    assert result["sections"][1]["evidence"]["exit_cost"]["sell_cost_bp_by_venue"] == {"one": 0, "two": None}
    assert len([p for _, p, _ in calls if p["method"] == "tools/call"]) == 4
    assert all(h["X-Liquilens-Traffic-Class"] == "synthetic" for _, _, h in calls)


def test_failed_service_keeps_sibling_results_without_retry():
    wire, calls = transport(failed=("exit_cost",))
    result = brief.brief(transport=wire)
    assert result["outcome"] == "partial" and result["complete"] is False
    assert result["sections"][0]["evidence"]["money_market"]["ok"] is True
    assert "evidence" not in result["sections"][1]
    assert result["sections"][1]["outcome"] == "error"
    assert sum(p.get("params", {}).get("name") == "exit_cost" for _, p, _ in calls) == 1


def test_comparison_ignores_retrieval_time_but_preserves_source_changes():
    wire, _ = transport()
    first = brief.brief(transport=wire)
    second = brief.brief(transport=wire, previous=first)
    assert all(row["status"] == "unchanged_payload" for row in second["comparison"]["sections"])
    first["sections"][0]["evidence"]["money_market"]["value"] = 0
    changes = brief.compare(second, first)
    assert changes["sections"][0]["status"] == "changed_payload"


def comparison(before, after, *, previous_outcome="evidence_returned", outcome="evidence_returned"):
    previous = {"schema": brief.SCHEMA, "request": {"bank_slug": None, "size_usd": 100000},
                "retrieved_at": "2026-09-23T00:00:00Z", "sections": [
                    {"recipe": "funding-brief", "outcome": previous_outcome, "evidence": before}]}
    current = copy.deepcopy(previous)
    current["retrieved_at"] = "2026-09-24T00:00:00Z"
    current["sections"][0].update(evidence=after, outcome=outcome)
    return brief.compare(current, previous)["sections"][0]


def test_comparison_exposes_stable_digests_and_distinct_clock_and_value_paths():
    first = {"generated_at": "2026-09-23T00:00:00Z", "value": 0}
    reordered = {"value": 0, "generated_at": first["generated_at"]}
    same = comparison(first, reordered)
    assert same["status"] == "unchanged_payload"
    assert same["previous_evidence_sha256"] == same["current_evidence_sha256"] == brief.digest(first)
    assert same["changes"] == [] and same["outcome_changed"] is False
    assert same["changes_truncated"] is False and same["truncation_reasons"] == []
    clock = comparison(first, {**first, "generated_at": "2026-09-24T00:00:00Z"})
    value = comparison(first, {**first, "value": 1})
    assert clock["status"] == value["status"] == "changed_payload"
    assert clock["changes"] == [{"path": "/generated_at", "kind": "changed"}]
    assert value["changes"] == [{"path": "/value", "kind": "changed"}]
    assert clock["current_evidence_sha256"] != value["current_evidence_sha256"]


@pytest.mark.parametrize("before,after,expected", [
    ({}, {"v": None}, [{"path": "/v", "kind": "added"}]),
    ({"v": None}, {}, [{"path": "/v", "kind": "removed"}]),
    ({"v": None}, {"v": False}, [{"path": "/v", "kind": "changed"}]),
    ({"v": False}, {"v": 0}, [{"path": "/v", "kind": "changed"}]),
    ({"v": True}, {"v": 1}, [{"path": "/v", "kind": "changed"}]),
    ({"v": 0}, {"v": 0.0}, [{"path": "/v", "kind": "changed"}]),
    ({"v": 0.0}, {"v": -0.0}, [{"path": "/v", "kind": "changed"}]),
    ({"v": {}}, {"v": []}, [{"path": "/v", "kind": "changed"}]),
    ({"v": {"nested": 1}}, {"v": None}, [{"path": "/v", "kind": "changed"}]),
    ({}, {"v": {"nested": 1}}, [{"path": "/v", "kind": "added"}]),
    ({"v": {"nested": 1}}, {}, [{"path": "/v", "kind": "removed"}]),
    ({}, None, [{"path": "", "kind": "changed"}]),
    ({"a/b": {"~": []}}, {"a/b": {"~": [None]}}, [{"path": "/a~1b/~0/0", "kind": "added"}]),
    ({"": 0}, {"": False}, [{"path": "/", "kind": "changed"}]),
    ({"v": [1, 2]}, {"v": [0, 1, 2]}, [
        {"path": "/v/0", "kind": "changed"}, {"path": "/v/1", "kind": "changed"},
        {"path": "/v/2", "kind": "added"}]),
    ({"v": [1, 2]}, {"v": [1]}, [{"path": "/v/1", "kind": "removed"}]),
])
def test_comparison_preserves_json_types_presence_and_pointer_semantics(before, after, expected):
    result = comparison(before, after)
    assert result["status"] == "changed_payload"
    assert result["changes"] == expected
    assert result["changes_truncated"] is False
    assert result["previous_evidence_sha256"] != result["current_evidence_sha256"]


def test_outcome_transition_is_distinct_from_evidence_change():
    result = comparison({"status": "unavailable"}, {"status": "unavailable"},
                        previous_outcome="unavailable")
    assert result["outcome_changed"] is True
    assert result["previous_outcome"] == "unavailable" and result["outcome"] == "evidence_returned"
    assert result["status"] == "unchanged_payload" and result["changes"] == []


def test_failure_recovery_and_missing_evidence_do_not_become_unchanged():
    wire, _ = transport()
    good = brief.brief(transport=wire)
    bad = copy.deepcopy(good)
    bad["sections"][0] = {"recipe": "funding-brief", "outcome": "error", "reason": "fixture timeout"}
    failure = brief.compare(bad, good)["sections"][0]
    recovery = brief.compare(good, bad)["sections"][0]
    for row in (failure, recovery):
        assert row["status"] == "not_comparable" and row["outcome_changed"] is True
        assert row["changes"] == [] and row["changes_truncated"] is False
    assert failure["current_evidence_sha256"] is None
    assert recovery["previous_evidence_sha256"] is None
    assert failure["previous_evidence_sha256"] == recovery["current_evidence_sha256"]
    # Present JSON null is evidence, not the missing-evidence sentinel.
    bad["sections"][0]["evidence"] = None
    row = brief.compare(bad, good)["sections"][0]
    assert row["current_evidence_sha256"] == brief.digest(None)
    assert row["status"] == "changed_payload"


def test_change_count_limit_is_deterministic_and_does_not_claim_truncation_at_exact_limit():
    keys = [f"k{i:03}" for i in range(brief.MAX_CHANGES + 1)]
    exact = {key: 0 for key in keys[:-1]}
    assert comparison({}, exact)["changes_truncated"] is False
    forward = comparison({}, {key: 0 for key in keys})
    reverse = comparison({}, {key: 0 for key in reversed(keys)})
    assert forward == reverse
    assert len(forward["changes"]) == brief.MAX_CHANGES
    assert forward["changes"][-1]["path"] == "/" + keys[-2]
    assert forward["changes_truncated"] is True and forward["truncation_reasons"] == ["max_changes"]


def test_change_depth_limit_reports_ancestor_without_hiding_that_detail_is_incomplete():
    before, after = {"leaf": 0}, {"leaf": 1}
    for _ in range(brief.MAX_CHANGE_DEPTH):
        before, after = {"child": before}, {"child": after}
    row = comparison(before, after)
    assert row["changes"] == [{"path": "/child" * brief.MAX_CHANGE_DEPTH, "kind": "changed"}]
    assert row["changes_truncated"] is True and row["truncation_reasons"] == ["max_depth"]
    # An equal deep subtree must not cause false truncation when another field changes.
    row = comparison({"same": before, "v": 0}, {"same": before, "v": 1})
    assert row["changes"] == [{"path": "/v", "kind": "changed"}]
    assert row["changes_truncated"] is False


def test_change_output_budget_never_slices_or_invents_a_pointer():
    long_key = "\N{SNOWMAN}" * brief.MAX_CHANGE_BYTES
    row = comparison({}, {"a": 0, long_key: 1})
    assert row["status"] == "changed_payload"
    assert row["changes"] == [{"path": "/a", "kind": "added"}]
    assert row["changes_truncated"] is True and row["truncation_reasons"] == ["max_bytes"]
    assert len(json.dumps(row["changes"], separators=(",", ":")).encode()) <= brief.MAX_CHANGE_BYTES


def test_no_baseline_contract_is_unchanged():
    wire, _ = transport()
    report = brief.brief(transport=wire)
    assert report["comparison"] == {"status": "no_baseline", "sections": []}


@pytest.mark.parametrize("change", ["size", "missing_section", "duplicate", "slug"])
def test_incompatible_baseline_fails_before_any_requests(change):
    wire, _ = transport()
    previous = brief.brief(transport=wire)
    if change == "size": previous["request"]["size_usd"] = 1000
    if change == "slug": previous["request"]["bank_slug"] = "cosmos-ucb"
    if change == "missing_section": previous["sections"].pop()
    if change == "duplicate": previous["sections"][1] = previous["sections"][0]
    wire, calls = transport()
    with pytest.raises(brief.ResearchError): brief.brief(transport=wire, previous=previous)
    assert calls == []


def test_uncovered_bank_stays_partial_without_requesting_another_bank():
    wire, calls = transport()
    result = brief.brief(slug="not-covered", transport=wire)
    assert result["sections"][2]["outcome"] == "not_covered"
    assert result["complete"] is False
    assert not any(p.get("params", {}).get("name") == "bank_asset_quality_review" for _, p, _ in calls)


@pytest.mark.parametrize("missing", [True, False])
def test_doctor_checks_required_tools_and_never_calls_research(missing):
    wire, calls = transport(missing=missing)
    report = brief.doctor(transport=wire)
    assert report["ready"] is not missing
    assert report["research_calls"] == 0
    assert len(calls) == 9
    assert all(p["method"] != "tools/call" for _, p, _ in calls)


def test_prior_error_is_not_claimed_as_unchanged_evidence():
    failed, _ = transport(failed=("exit_cost",))
    previous = brief.brief(transport=failed)
    wire, _ = transport()
    report = brief.brief(transport=wire, previous=previous)
    assert report["comparison"]["sections"][1]["status"] == "not_comparable"


def test_source_text_cannot_break_markdown_fence():
    wire, _ = transport()
    report = brief.brief(transport=wire)
    report["sections"][0]["evidence"]["text"] = "```\n# untrusted\n```"
    rendered = brief.markdown(report)
    assert "````json" in rendered


def test_comparison_source_keys_remain_inside_one_content_aware_json_fence():
    wire, _ = transport()
    previous = brief.brief(transport=wire)
    report = copy.deepcopy(previous)
    keys = ["![source key](https://example.invalid/image)",
            "[source link](https://example.invalid/link)",
            "````````\n![escape attempt](x)\n````````",
            '<img src="https://example.invalid/raw">']
    report["sections"][0]["evidence"].update({key: 0 for key in keys})
    report["comparison"] = brief.compare(report, previous)
    rendered = brief.markdown(report)
    comparison_block = rendered.split("## Changes since the previous brief\n\n", 1)[1].splitlines()
    assert comparison_block[0] == "`````````json"
    assert comparison_block[-1] == "`````````"
    assert json.loads("\n".join(comparison_block[1:-1])) == report["comparison"]
    assert all(not line.startswith("`````````") for line in comparison_block[1:-1])

    # Exercise a real CommonMark renderer when locally available, without a
    # new runtime/CI dependency. The fence/round-trip checks above always run.
    import shutil
    import subprocess
    from html.parser import HTMLParser
    if shutil.which("pandoc"):
        class Tags(HTMLParser):
            def __init__(self):
                super().__init__()
                self.names = []
            def handle_starttag(self, tag, attrs):
                self.names.append(tag)
        html = subprocess.run(["pandoc", "--from=commonmark", "--to=html5", "--no-highlight"],
                              input=rendered, text=True, capture_output=True, check=True).stdout
        tags = Tags()
        tags.feed(html)
        assert "img" not in tags.names and "a" not in tags.names
        assert tags.names.count("pre") == len(report["sections"]) + 1


def test_previous_input_is_bounded_and_requires_schema(tmp_path):
    path = tmp_path / "previous.json"
    path.write_text('{"schema":"unrelated"}')
    with pytest.raises(brief.ResearchError): brief.previous_report(path)
    path.write_bytes(b" " * (brief.MAX_PREVIOUS_BYTES + 1))
    with pytest.raises(brief.ResearchError, match="8 MiB"): brief.previous_report(path)


def test_download_archive_matches_sources_and_declared_hashes():
    import hashlib
    import io
    import zipfile
    spec = importlib.util.spec_from_file_location("agent_kit", ROOT / "scripts/build_agent_kit.py")
    kit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kit)
    files = kit.assets()
    raw = (ROOT / "agents/trading-research-kit.zip").read_bytes()
    assert raw == kit.archive(files) == kit.archive(files)
    manifest = json.loads((ROOT / "agents/manifest.json").read_bytes())
    assert manifest["archive"]["sha256"] == hashlib.sha256(raw).hexdigest()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert set(archive.namelist()) == set(files)
        for name, body in files.items():
            assert archive.read(name) == body
            assert (ROOT / "agents" / name).read_bytes() == body
            assert manifest["files"][name] == {"sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}


def test_n8n_research_step_preserves_quality_and_rejects_gauge_or_invalid_clock():
    import subprocess
    workflow = json.loads((ROOT / "agents/n8n-funding-research.json").read_bytes())
    request = next(n for n in workflow["nodes"] if n["type"] == "n8n-nodes-base.httpRequest")
    assert request["parameters"]["url"] == "https://api.seiche.info/api/public"
    script = next(n for n in workflow["nodes"] if n["type"] == "n8n-nodes-base.code")["parameters"]["jsCode"]
    runner = r"""
const vm = require('node:vm');
const code = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const evidence = {schema:'seiche.public.v2', generated_at:'2026-09-24T09:00:00Z',
                  conclusion:null, data_quality:{status_counts:{stale:1}, fresh_share_pct:0}};
function run(value) {
  return vm.runInNewContext('(function(){'+code+'})()', {$input:{all:()=>[{json:value}]},Date}, {timeout:1000});
}
const result = run(evidence)[0].json;
if (result.evidence !== evidence || result.execution_authority !== false) throw Error('evidence changed');
for (const bad of [{...evidence, schema:'seiche.gauge.v1'}, {...evidence, data_quality:null},
                   {...evidence, generated_at:'not-a-date'}]) {
  try { run(bad); throw Error('bad evidence accepted'); }
  catch (error) { if (!String(error).includes('Unexpected funding evidence contract')) throw error; }
}
"""
    subprocess.run(["node", "-e", runner], input=json.dumps(script), text=True, check=True)
