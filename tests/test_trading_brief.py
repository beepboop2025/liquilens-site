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
