"""A seven-tool claim requires native evidence, not the six-tool Actions receipt."""

import copy
import json
from pathlib import Path

import pytest

from scripts import verify_palimpsest_release as release
from scripts import verify_catalog_edge as edge


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "8288940062498d5e3fd60cb232cb589b3cb3b97e"
RUNTIME = "275fc2b8f6a411a7be486467bfb8fd40ff7a455740343569271a8723a3a2c8a1"


def receipt_fixture():
    return {
        "schema_version": 2, "service": "palimpsest-mcp.service", "target_sha": SOURCE,
        "server_version": "1.9.3", "server_file_sha256": RUNTIME,
        "previous_sha": "1" * 40, "previous_runtime_sha256": "2" * 64,
        "previous_runtime_source_sha": "1" * 40,
        "previous_runtime_backup": "20260909T000000Z-" + "2" * 64 + ".abcdef.py",
        "deployed_at_utc": "20260909T000000Z",
        "verification": {"github_signature": "valid", "local_initialize_list_call": "passed",
                         "target_on_origin_main": True},
    }


def metadata_fixture():
    return {"nativeDeploymentCommit": SOURCE, "nativeRuntimeSha256": "sha256:" + RUNTIME}


def native_card():
    return edge._palimpsest_card(json.loads((ROOT / ".well-known/ai-catalog.json").read_text()))


def test_actual_host_receipt_verifies_with_the_reviewed_owner_signature():
    card = native_card()
    directory = ROOT / "protocol/release-evidence/palimpsest" / card["metadata"]["nativeDeploymentCommit"]
    receipt = (directory / "host-receipt.json").read_bytes()
    signature = (directory / "host-receipt.json.sig").read_bytes()
    release.verify_signature(receipt, signature)
    release.validate_receipt(receipt, card["metadata"], card["version"])
    with pytest.raises(RuntimeError, match="signature"):
        release.verify_signature(receipt.replace(SOURCE.encode(), b"a" * 40), signature)


@pytest.mark.parametrize("field", ["nativeDeploymentReceipt", "nativeDeploymentReceiptSha256",
                                   "nativeDeploymentSignature", "nativeDeploymentSignatureSha256"])
def test_catalog_cannot_substitute_native_evidence(field):
    card = copy.deepcopy(native_card())
    card["metadata"][field] += "-substituted"
    with pytest.raises(RuntimeError):
        release.verify_release(card, {}, ROOT, None)


def test_native_receipt_schema_binds_runtime_and_rollback():
    receipt = receipt_fixture()
    assert release.validate_receipt(release.canonical(receipt), metadata_fixture(), "1.9.3") == receipt


@pytest.mark.parametrize("mutation", ["source", "runtime", "version", "service", "schema",
                                     "verification", "boolean_acceptance", "clock", "future", "rollback", "backup",
                                     "rollback_presence", "invented_actions"])
def test_native_receipt_rejects_a_different_release_boundary(mutation):
    receipt = receipt_fixture()
    if mutation == "source":
        receipt["target_sha"] = "a" * 40
    elif mutation == "runtime":
        receipt["server_file_sha256"] = "b" * 64
    elif mutation == "version":
        receipt["server_version"] = "1.9.2"
    elif mutation == "service":
        receipt["service"] = "unrelated.service"
    elif mutation == "schema":
        receipt["schema_version"] = True
    elif mutation == "verification":
        receipt["verification"]["target_on_origin_main"] = False
    elif mutation == "boolean_acceptance":
        receipt["verification"]["target_on_origin_main"] = 1
    elif mutation == "clock":
        receipt["deployed_at_utc"] = "20261309T000000Z"
    elif mutation == "future":
        receipt["deployed_at_utc"] = "20990909T000000Z"
    elif mutation == "rollback":
        receipt["previous_runtime_sha256"] = "3" * 64
    elif mutation == "backup":
        receipt["previous_runtime_backup"] = "../../outside.py"
    elif mutation == "rollback_presence":
        receipt["previous_runtime_source_sha"] = None
    else:
        receipt["workflow_run_id"] = 33258332928
    with pytest.raises(RuntimeError):
        release.validate_receipt(release.canonical(receipt), metadata_fixture(), "1.9.3")


def test_receipt_requires_exact_original_canonical_bytes():
    with pytest.raises(RuntimeError, match="canonical"):
        release.validate_receipt(release.canonical(receipt_fixture()) + b" ", metadata_fixture(), "1.9.3")


def test_seven_tools_cannot_use_only_the_historical_actions_receipt(tmp_path):
    with pytest.raises(RuntimeError, match="requires an exact native"):
        release.verify_release({"metadata": {}}, {}, tmp_path, None)


def test_signature_from_another_release_namespace_cannot_authorize_palimpsest():
    directory = ROOT / "protocol/release-evidence/narcoscope/0f3887d456fbb985a1dd3532ec689cda259e1aa4"
    with pytest.raises(RuntimeError, match="signature"):
        release.verify_signature((directory / "receipt.json").read_bytes(),
                                 (directory / "receipt.json.sig").read_bytes())


def research_body():
    row = {"id": "one", "name": "One", "description": "Evidence metadata", "layer": "research",
           "cadence": "source-dependent", "geography": [], "sources": [],
           "artifacts": {"evidence_state": "unknown", "observed_at": None},
           "license": {"name": None, "url": None},
           "urls": {"latest": None, "landing_page": None, "method": None},
           "values_included": False}
    return {"schema": "palimpsest.research-catalog.v1", "metadata_only": True,
            "generated_at": "2026-09-09T05:06:33Z", "truncated": {},
            "source_url": "https://www.palimpsest.info/readings/research-catalog-latest.json",
            "offset": 0, "returned": 1, "total": 1, "next_offset": None, "datasets": [row],
            "seiche": {"site": "https://seiche.info/#RESEARCH",
                       "api": "https://api.seiche.info/api/v2/research-network",
                       "mcp": "https://api.seiche.info/mcp", "tool": "research_network",
                       "arguments": {"topic": "all"}}, "boundary": "Separate research context."}


def research_result(body):
    return {"isError": False, "structuredContent": body,
            "content": [{"type": "text", "text": json.dumps(body)}]}


def test_research_probe_retains_unknown_state_without_inventing_freshness():
    edge._validate_palimpsest_research_catalog(research_result(research_body()))


@pytest.mark.parametrize("mutation", ["top_level_values", "source_values", "description_values",
                                     "license_values", "fresh_state", "observation_clock", "gated_url"])
def test_research_projection_rejects_observations_and_invented_freshness(mutation):
    body = research_body()
    row = body["datasets"][0]
    if mutation == "top_level_values":
        body["observations"] = [{"source_id": "chinamoney", "value": 4.2}]
    elif mutation == "source_values":
        row["sources"] = [{"source_id": "chinamoney", "value": 4.2}]
    elif mutation == "description_values":
        row["description"] = {"value": 4.2}
    elif mutation == "license_values":
        row["license"]["name"] = {"value": 4.2}
    elif mutation == "fresh_state":
        row["artifacts"]["evidence_state"] = "fresh"
    elif mutation == "observation_clock":
        row["artifacts"]["observed_at"] = body["generated_at"]
    else:
        row["artifacts"]["evidence_state"] = "gated"
        row["urls"]["latest"] = "https://www.palimpsest.info/restricted-values.json"
    with pytest.raises(RuntimeError):
        edge._validate_palimpsest_research_catalog(research_result(body))


@pytest.mark.parametrize("mutation", ["values", "extra_value", "nested_value", "error", "text",
                                     "handoff", "count", "bool_count", "pagination", "source", "metadata_flag"])
def test_research_probe_rejects_value_leaks_or_broken_pagination_and_handoff(mutation):
    body = research_body()
    if mutation == "values":
        body["datasets"][0]["values_included"] = True
    elif mutation == "extra_value":
        body["datasets"][0]["value"] = 42
    elif mutation == "nested_value":
        body["datasets"][0]["artifacts"]["value"] = 42
    elif mutation == "handoff":
        body["seiche"]["mcp"] = "https://attacker.example/mcp"
    elif mutation == "count":
        body["returned"] = 0
    elif mutation == "bool_count":
        body["returned"] = True
    elif mutation == "pagination":
        body["next_offset"] = 3
    elif mutation == "source":
        body["source_url"] = "https://attacker.example/catalog.json"
    elif mutation == "metadata_flag":
        body["metadata_only"] = 1
    result = research_result(body)
    if mutation == "error":
        result["isError"] = True
    elif mutation == "text":
        result["content"][0]["text"] = "{}"
    with pytest.raises(RuntimeError):
        edge._validate_palimpsest_research_catalog(result)


def test_native_catalog_cannot_omit_the_host_receipt_identity():
    catalog = json.loads((ROOT / ".well-known/ai-catalog.json").read_text())
    card = copy.deepcopy(next(row for row in catalog["entries"] if row["identifier"] == edge.PALIMPSEST_CARD_ID))
    if "research_catalog" not in card["capabilities"]:
        card["capabilities"].insert(0, "research_catalog")
    card["metadata"]["publicToolCount"] = 7
    card["metadata"].pop("nativeDeploymentCommit", None)
    metadata = copy.deepcopy(card["metadata"])
    live = {"version": card["version"], "data": {"name": metadata["mcpServerName"],
            "version": card["version"], "remotes": [{"url": metadata["mcpEndpoint"]}]},
            "metadata": metadata, "capabilities": card["capabilities"],
            "prompts": card["prompts"], "resources": card["resources"]}
    with pytest.raises(RuntimeError, match="nativeDeploymentCommit"):
        edge._validate_palimpsest_live_agreement(card, {"entries": [live]}, {}, {})


def source_reported_research():
    body = research_body()
    row = body["datasets"][0]
    row["artifacts"] = {"evidence_state": "fresh", "observed_at": "2026-09-09T05:00:00Z"}
    row["urls"]["latest"] = "https://palimpsest.info/readings/one-latest.json"
    research = {"schema": "palimpsest-research-catalog/v1", "metadata_only": True,
                "generated_at": body["generated_at"], "datasets": copy.deepcopy(body["datasets"])}
    public = {"schema": "palimpsest-data-catalog/v1", "generated_at": body["generated_at"],
              "datasets": copy.deepcopy(body["datasets"])}
    public["datasets"][0]["artifacts"]["latest_available"] = True
    return body, research, public


def test_research_accepts_edition_bound_source_clock_without_treating_generation_as_observation():
    body, research, public = source_reported_research()
    edge._validate_palimpsest_research_catalog(research_result(body), (research, public))
    assert body["datasets"][0]["artifacts"]["observed_at"] != body["generated_at"]


@pytest.mark.parametrize("mutation", [
    "source_clock", "public_clock", "source_state", "public_state", "source_generation",
    "public_generation", "future_observation", "future_generation", "naive_clock", "missing_clock",
    "public_denied", "download_missing", "download_changed", "source_value", "public_duplicate",
    "source_duplicate", "source_count", "source_id", "unknown_state", "gated_clock",
])
def test_research_source_clock_proof_rejects_fabrication_rights_and_identity_drift(mutation):
    body, research, public = source_reported_research()
    row = body["datasets"][0]
    source = research["datasets"][0]
    original = public["datasets"][0]
    if mutation == "source_clock": source["artifacts"]["observed_at"] = "2026-09-09T04:00:00Z"
    elif mutation == "public_clock": original["artifacts"]["observed_at"] = "2026-09-09T04:00:00Z"
    elif mutation == "source_state": source["artifacts"]["evidence_state"] = "stale"
    elif mutation == "public_state": original["artifacts"]["evidence_state"] = "stale"
    elif mutation == "source_generation": research["generated_at"] = "2026-09-09T05:06:34Z"
    elif mutation == "public_generation": public["generated_at"] = "2026-09-09T05:06:34Z"
    elif mutation == "future_generation":
        for document in (body, research, public): document["generated_at"] = "2999-01-01T00:00:00Z"
    elif mutation in {"future_observation", "naive_clock", "missing_clock", "unknown_state", "gated_clock"}:
        for dataset in (row, source, original):
            if mutation == "future_observation": dataset["artifacts"]["observed_at"] = "2026-09-09T05:07:00Z"
            elif mutation == "naive_clock": dataset["artifacts"]["observed_at"] = "2026-09-09T05:00:00"
            elif mutation == "missing_clock": dataset["artifacts"]["observed_at"] = None
            else: dataset["artifacts"]["evidence_state"] = "gated" if mutation == "gated_clock" else "safe"
    elif mutation == "public_denied": original["publication_allowed"] = False
    elif mutation == "download_missing": original["artifacts"]["latest_available"] = False
    elif mutation == "download_changed": original["urls"]["latest"] = "https://palimpsest.info/other.json"
    elif mutation == "source_value": source["values_included"] = True
    elif mutation == "public_duplicate": public["datasets"].append(copy.deepcopy(original))
    elif mutation == "source_duplicate": research["datasets"].append(copy.deepcopy(source))
    elif mutation == "source_count": research["datasets"] = []
    elif mutation == "source_id": source["id"] = "another"
    with pytest.raises(RuntimeError):
        edge._validate_palimpsest_research_catalog(research_result(body), (research, public))


@pytest.mark.parametrize("mutation", [None, "hash", "bytes", "missing_anchor", "edition_changed", "invalid_edition"])
def test_research_source_fetch_binds_exact_bytes_to_one_static_edition(monkeypatch, mutation):
    import hashlib
    _, research, public = source_reported_research()
    documents = {
        "readings/research-catalog-latest.json": json.dumps(research).encode(),
        "readings/public-data-catalog-latest.json": json.dumps(public).encode(),
    }
    manifest = {"schema_version": "palimpsest.railway-static-release.v1", "state": "artifact_ready",
                "deployment_source": "local-git-archive", "github_required": False,
                "source_commit": "a" * 40,
                "critical_files": {path: {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
                                   for path, raw in documents.items()}}
    anchor = manifest["critical_files"]["readings/research-catalog-latest.json"]
    if mutation == "hash": anchor["sha256"] = "b" * 64
    elif mutation == "bytes": anchor["bytes"] += 1
    elif mutation == "missing_anchor": manifest["critical_files"] = {}
    elif mutation == "invalid_edition": manifest["source_commit"] = "main"
    calls = []
    def fetch(url, **kwargs):
        assert url.startswith("https://www.palimpsest.info/")
        path = url.removeprefix("https://www.palimpsest.info/")
        calls.append(path)
        raw = json.dumps(manifest).encode() if path == "railway-release.json" else documents[path]
        if mutation == "edition_changed" and calls.count("railway-release.json") == 2: raw += b"\n"
        return raw, {"content-type": "application/json"}, url
    monkeypatch.setattr(edge, "_fetch_bytes", fetch)
    if mutation is None:
        assert edge._palimpsest_research_source_catalogs() == (research, public)
        assert calls.count("railway-release.json") == 2
    else:
        with pytest.raises(RuntimeError): edge._palimpsest_research_source_catalogs()
