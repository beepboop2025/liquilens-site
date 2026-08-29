import hashlib
import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest
import scripts.verify_catalog_edge as verifier

from scripts.verify_catalog_edge import (
    API_CATALOG_LINK,
    DEFAULT_API_CATALOG_URL,
    EXPECTED_MCP_CONTRACT,
    EXPECTED_MCP_TOOLS,
    EXPECTED_MCP_VERSION,
    PALIMPSEST_CARD_ID,
    PALIMPSEST_RIGHTS_URI,
    RFC_9727_PROFILE,
    _mime_matches_declared,
    _read_bounded,
    _require_modern_result,
    _palimpsest_rights_resource,
    _parser,
    _palimpsest_surface_lists,
    _sibling_registry_version,
    _validate_palimpsest_live_agreement,
    _validate_palimpsest_receipts,
    _validate_palimpsest_rights_resource,
    _validate_palimpsest_surface_lists,
    _validate_sibling_api_catalog_response,
    _validate_sibling_mcp,
    _validate_github_deployment,
    _validate_modern_sibling_discovery,
    _validate_sibling_registry,
    _validate_sibling_source_workflow,
    _validate_public_https_url,
    compact_json_bytes,
    decode_mcp_response,
    response_problem,
    response_headers_problem,
)


ROOT = Path(__file__).resolve().parents[1]


def _workflow(path):
    script = """
const { readFileSync } = require('node:fs');
const YAML = require('yaml');
process.stdout.write(JSON.stringify(YAML.parse(readFileSync(process.argv[1], 'utf8'))));
"""
    result = subprocess.run(
        ["node", "-e", script, str(ROOT / path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_edge_parity_accepts_only_the_exact_committed_catalog():
    expected = json.loads(
        (ROOT / ".well-known/ai-catalog.json").read_text(encoding="utf-8")
    )
    body = json.dumps(expected, separators=(",", ":")).encode()
    assert response_problem(expected, body, "application/ai-catalog+json") is None


def test_edge_parity_accepts_the_exact_protocol_catalog():
    expected = json.loads((ROOT / "protocol/catalog.json").read_text(encoding="utf-8"))
    body = json.dumps(expected, separators=(",", ":")).encode()
    assert (
        response_problem(
            expected,
            body,
            "application/json; charset=utf-8",
            "application/json",
        )
        is None
    )


def test_edge_parity_accepts_the_exact_rfc_9727_api_catalog():
    expected = json.loads(
        (ROOT / ".well-known/api-catalog.json").read_text(encoding="utf-8")
    )
    assert (
        response_problem(
            expected,
            compact_json_bytes(expected),
            'application/linkset+json; profile="https://www.rfc-editor.org/info/rfc9727"; charset=utf-8',
            "application/linkset+json",
            expected_body=compact_json_bytes(expected),
            expected_profile=RFC_9727_PROFILE,
        )
        is None
    )


def test_api_catalog_self_anchor_registers_the_three_product_catalogs():
    api_catalog = json.loads(
        (ROOT / ".well-known/api-catalog.json").read_text(encoding="utf-8")
    )
    ai_catalog = json.loads(
        (ROOT / ".well-known/ai-catalog.json").read_text(encoding="utf-8")
    )
    by_identifier = {entry["identifier"]: entry for entry in ai_catalog["entries"]}
    self_links = [
        linkset
        for linkset in api_catalog["linkset"]
        if linkset.get("anchor") == DEFAULT_API_CATALOG_URL
    ]
    assert len(api_catalog["linkset"]) == 17
    assert len(self_links) == 1
    assert self_links[0]["api-catalog"] == [
        {
            "href": by_identifier[identifier]["metadata"]["apiCatalog"],
            "type": "application/linkset+json",
        }
        for identifier in (
            "urn:air:liquilens.in:catalog:undertow",
            "urn:air:liquilens.in:catalog:riptide",
            "urn:air:liquilens.in:catalog:narcoscope",
        )
    ]


def test_edge_parity_rejects_semantically_equal_but_nonidentical_api_catalog():
    expected = json.loads(
        (ROOT / ".well-known/api-catalog.json").read_text(encoding="utf-8")
    )
    problem = response_problem(
        expected,
        json.dumps(expected, indent=2).encode(),
        f'application/linkset+json; profile="{RFC_9727_PROFILE}"',
        "application/linkset+json",
        expected_body=compact_json_bytes(expected),
        expected_profile=RFC_9727_PROFILE,
    )
    assert problem is not None
    assert "byte-for-byte" in problem


def test_edge_parity_requires_the_rfc_9727_profile_link_and_cors():
    expected = json.loads(
        (ROOT / ".well-known/api-catalog.json").read_text(encoding="utf-8")
    )
    assert (
        response_problem(
            expected,
            compact_json_bytes(expected),
            "application/linkset+json",
            "application/linkset+json",
            expected_body=compact_json_bytes(expected),
            expected_profile=RFC_9727_PROFILE,
        )
        == "unexpected content type profile: <missing>"
    )
    headers = {
        "Link": API_CATALOG_LINK,
        "Access-Control-Allow-Origin": "*",
    }
    assert (
        response_headers_problem(
            headers,
            expected_link=API_CATALOG_LINK,
            expected_cors_origin="*",
        )
        is None
    )
    assert "Access-Control-Allow-Origin" in response_headers_problem(
        {"Link": API_CATALOG_LINK},
        expected_link=API_CATALOG_LINK,
        expected_cors_origin="*",
    )


def test_edge_parity_names_a_missing_api_catalog_anchor():
    expected = json.loads(
        (ROOT / ".well-known/api-catalog.json").read_text(encoding="utf-8")
    )
    missing_anchor = expected["linkset"][0]["anchor"]
    actual = {
        "linkset": [
            item for item in expected["linkset"] if item["anchor"] != missing_anchor
        ]
    }
    problem = response_problem(
        expected,
        compact_json_bytes(actual),
        f'application/linkset+json; profile="{RFC_9727_PROFILE}"',
        "application/linkset+json",
        expected_body=compact_json_bytes(expected),
        expected_profile=RFC_9727_PROFILE,
    )
    assert problem is not None
    assert missing_anchor in problem


def test_edge_verifier_has_a_default_live_api_catalog_argument():
    args = _parser().parse_args([])
    assert args.api_catalog_url == DEFAULT_API_CATALOG_URL
    assert args.palimpsest_proof is True
    assert args.sibling_proof is True
    assert args.external_proof_only is False


def test_external_proof_mode_never_requires_the_live_central_catalogs(
    monkeypatch,
    capsys,
):
    observed_palimpsest = {}
    observed_siblings = {}

    def fake_palimpsest_proof(**arguments):
        observed_palimpsest.update(arguments)
        return "Palimpsest proof passed"

    def fake_sibling_proof(**arguments):
        observed_siblings.update(arguments)
        return "sibling proof passed"

    def forbidden_live_central_check(**_arguments):
        raise AssertionError("external proof mode reached a central live check")

    monkeypatch.setattr(
        verifier,
        "_verify_palimpsest_release_with_retries",
        fake_palimpsest_proof,
    )
    monkeypatch.setattr(
        verifier,
        "_verify_sibling_products_with_retries",
        fake_sibling_proof,
    )
    monkeypatch.setattr(verifier, "_verify_url", forbidden_live_central_check)
    monkeypatch.setattr(
        verifier,
        "_verify_mcp_with_retries",
        forbidden_live_central_check,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "verify_catalog_edge.py",
            "--external-proof-only",
            "--attempts",
            "1",
            "--delay",
            "0",
        ],
    )

    assert verifier.main() == 0
    assert observed_palimpsest["attempts"] == 1
    assert observed_palimpsest["delay"] == 0
    assert observed_palimpsest["ai_catalog"]["entries"]
    assert observed_palimpsest["api_catalog"]["linkset"]
    assert observed_siblings["attempts"] == 1
    assert observed_siblings["delay"] == 0
    assert observed_siblings["ai_catalog"]["entries"]
    output = capsys.readouterr().out
    assert "Palimpsest proof passed" in output
    assert "sibling proof passed" in output


def test_publish_preflight_rejects_external_proof_opt_outs(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["verify_catalog_edge.py", "--external-proof-only", "--no-sibling-proof"],
    )
    with pytest.raises(SystemExit, match="cannot be combined"):
        verifier.main()


def test_external_proofs_attempt_siblings_even_when_palimpsest_fails(monkeypatch):
    sibling_called = False

    def failed_palimpsest(**_arguments):
        raise RuntimeError("Palimpsest unavailable")

    def passed_siblings(**_arguments):
        nonlocal sibling_called
        sibling_called = True
        return "all siblings passed"

    monkeypatch.setattr(
        verifier,
        "_verify_palimpsest_release_with_retries",
        failed_palimpsest,
    )
    monkeypatch.setattr(
        verifier,
        "_verify_sibling_products_with_retries",
        passed_siblings,
    )
    with pytest.raises(RuntimeError, match="passed=all siblings passed"):
        verifier._verify_external_release_proofs(
            ai_catalog={},
            api_catalog={},
            palimpsest_proof=True,
            sibling_proof=True,
            attempts=1,
            delay=0,
        )
    assert sibling_called is True


def test_publish_workflows_block_on_external_proof_before_mutation():
    edge = _workflow(".github/workflows/deploy-catalog-edge.yml")["jobs"]["deploy"]
    pages = _workflow(".github/workflows/pages.yml")["jobs"]["deploy"]
    edge_steps = edge["steps"]
    pages_steps = pages["steps"]

    edge_names = [step.get("name") for step in edge_steps]
    pages_names = [step.get("name") for step in pages_steps]
    proof_name = "Require external proof before publishing catalog claims"
    upload_name = "Upload the exact committed candidate without production traffic"
    main_name = "Require current protected main immediately before candidate upload"
    assert edge_names.index(proof_name) < edge_names.index(upload_name)
    assert edge_names.index(main_name) + 1 == edge_names.index(upload_name)
    edge_proof = edge_steps[edge_names.index(proof_name)]
    assert edge_proof["timeout-minutes"] * 60 >= 150
    assert "--budget-seconds 150" in edge_proof["run"]
    assert "continue-on-error" not in edge_proof
    upload = edge_steps[edge_names.index(upload_name)]
    assert "versions upload" in upload["with"]["command"]
    assert "--strict" in upload["with"]["command"]
    rollout = next(
        step for step in edge_steps if step.get("name", "").startswith("Stage at zero")
    )
    script = rollout["run"]
    assert '"$PREVIOUS_VERSION_ID@100%" "$CANDIDATE_VERSION_ID@0%"' in script
    assert "--worker-version-id" in script
    assert '"$CANDIDATE_VERSION_ID@100%"' in script
    assert 'wrangler rollback "$PREVIOUS_VERSION_ID"' in script
    assert script.count("require_current_main") >= 3
    assert edge["timeout-minutes"] >= sum(
        step.get("timeout-minutes", 0) for step in edge_steps
    )

    pages_proof_index = pages_names.index(proof_name)
    artifact_index = next(
        index
        for index, step in enumerate(pages_steps)
        if str(step.get("uses", "")).startswith("actions/upload-pages-artifact@")
    )
    deploy_index = next(
        index
        for index, step in enumerate(pages_steps)
        if str(step.get("uses", "")).startswith("actions/deploy-pages@")
    )
    main_index = pages_names.index(
        "Require current protected main immediately before Pages publication"
    )
    post_index = pages_names.index(
        "Require deployed Pages bytes to match the protected-main artifact"
    )
    assert pages_proof_index < main_index
    assert main_index + 1 == artifact_index
    assert deploy_index < post_index
    post = pages_steps[post_index]
    assert "--pages-proof-only" in post["run"]
    assert '${PAGE_BASE_URL/#http:\\/\\//https:\\/\\/}' in post["run"]
    assert "--budget-seconds 150" in post["run"]
    assert "continue-on-error" not in post
    assert post["timeout-minutes"] * 60 >= 150
    preserve = pages_steps[
        pages_names.index("Preserve postdeployment verifiers outside the site artifact")
    ]["run"]
    assert 'cp llms.txt "$RUNNER_TEMP/pages-proof/llms.txt"' in preserve
    assert 'cp sitemap.xml "$RUNNER_TEMP/pages-proof/sitemap.xml"' in preserve


def test_pages_proof_checks_compact_edge_catalogs_and_raw_static_files(monkeypatch):
    expected_by_path = {
        "/.well-known/ai-catalog.json": compact_json_bytes(
            json.loads((ROOT / ".well-known/ai-catalog.json").read_text())
        ),
        "/.well-known/api-catalog.json": compact_json_bytes(
            json.loads((ROOT / ".well-known/api-catalog.json").read_text())
        ),
        "/protocol/catalog.json": compact_json_bytes(
            json.loads((ROOT / "protocol/catalog.json").read_text())
        ),
        "/llms.txt": (ROOT / "llms.txt").read_bytes(),
        "/sitemap.xml": (ROOT / "sitemap.xml").read_bytes(),
    }
    seen = []

    monkeypatch.setattr(verifier, "_validate_public_https_url", lambda url: url)

    def fetch(url, **_kwargs):
        path = verifier.urllib.parse.urlsplit(url).path
        seen.append(path)
        return expected_by_path[path], {}, url

    monkeypatch.setattr(verifier, "_fetch_bytes", fetch)
    results = verifier._verify_pages_bytes(
        base_url="https://liquilens.in/",
        attempts=1,
        delay=0,
    )
    assert seen == list(expected_by_path)
    assert len(results) == 5


def test_edge_parity_explains_a_missing_carrier_entry():
    expected = json.loads(
        (ROOT / ".well-known/ai-catalog.json").read_text(encoding="utf-8")
    )
    actual = dict(expected)
    actual["entries"] = [
        row
        for row in expected["entries"]
        if row["identifier"] != "urn:air:liquilens.in:protocol:evidence-carrier"
    ]
    problem = response_problem(
        expected,
        json.dumps(actual).encode(),
        "application/ai-catalog+json; charset=utf-8",
    )
    assert problem is not None
    assert "urn:air:liquilens.in:protocol:evidence-carrier" in problem


def test_mcp_receipt_decoder_accepts_one_json_or_sse_message():
    payload = {
        "jsonrpc": "2.0",
        "id": "tools",
        "result": {"tools": [{"name": name} for name in EXPECTED_MCP_TOOLS]},
    }
    encoded = json.dumps(payload).encode()
    assert decode_mcp_response(encoded, "application/json; charset=utf-8") == payload
    assert (
        decode_mcp_response(
            b"event: message\ndata: " + encoded + b"\n\n",
            "text/event-stream; charset=utf-8",
        )
        == payload
    )
    assert EXPECTED_MCP_VERSION == "0.1.4"
    assert EXPECTED_MCP_CONTRACT["serverInfo"] == {
        "name": "financial-evidence",
        "version": "0.1.4",
    }
    assert [tool["name"] for tool in EXPECTED_MCP_CONTRACT["tools"]] == list(
        EXPECTED_MCP_TOOLS
    )


def test_mcp_receipt_decoder_rejects_batches_and_multiple_sse_events():
    with pytest.raises(ValueError, match="one JSON-RPC object"):
        decode_mcp_response(b"[]", "application/json")
    with pytest.raises(ValueError, match="expected one MCP SSE data event"):
        decode_mcp_response(
            b'data: {"id":1}\n\ndata: {"id":2}\n\n',
            "text/event-stream",
        )


def _palimpsest_card():
    catalog = json.loads(
        (ROOT / ".well-known/ai-catalog.json").read_text(encoding="utf-8")
    )
    return next(
        entry
        for entry in catalog["entries"]
        if entry["identifier"] == PALIMPSEST_CARD_ID
    )


def _sibling_card(identifier):
    catalog = json.loads(
        (ROOT / ".well-known/ai-catalog.json").read_text(encoding="utf-8")
    )
    return next(
        entry for entry in catalog["entries"] if entry["identifier"] == identifier
    )


def _palimpsest_receipts(card):
    metadata = card["metadata"]
    snapshot_digest = metadata["registrySnapshotSha256"].removeprefix("sha256:")
    deployment_run_id = int(metadata["deploymentRun"].rsplit("/", 1)[-1])
    registry_run_id = int(metadata["registryRun"].rsplit("/", 1)[-1])
    return {
        "deployment": {
            "repository": "beepboop2025/palimpsest",
            "target_sha": metadata["deploymentCommit"],
            "server_version": card["version"],
            "workflow_run_id": deployment_run_id,
            "public_mcp_url": metadata["mcpEndpoint"],
            "public_smoke": "passed",
        },
        "registry publication": {
            "repository": "beepboop2025/palimpsest",
            "target_sha": metadata["deploymentCommit"],
            "server_version": card["version"],
            "server_name": metadata["mcpServerName"],
            "workflow_run_id": registry_run_id,
            "deploy_run_id": deployment_run_id,
            "official_status": "active",
            "official_is_latest": True,
            "registry_response_sha256": snapshot_digest,
        },
        "Registry latest snapshot": {
            "server": {
                "name": metadata["mcpServerName"],
                "version": card["version"],
                "remotes": [
                    {"type": "streamable-http", "url": metadata["mcpEndpoint"]}
                ],
            },
            "_meta": {
                "io.modelcontextprotocol.registry/official": {
                    "status": "active",
                    "isLatest": True,
                }
            },
        },
    }


def test_palimpsest_receipts_are_bound_to_source_version_and_workflow_runs():
    card = _palimpsest_card()
    receipts = _palimpsest_receipts(card)
    _validate_palimpsest_receipts(card, receipts)

    receipts["deployment"]["workflow_run_id"] += 1
    with pytest.raises(RuntimeError, match="deployment workflow run differs"):
        _validate_palimpsest_receipts(card, receipts)


def test_palimpsest_catalog_registry_and_initialize_must_agree():
    card = _palimpsest_card()
    metadata = card["metadata"]
    live_card = {
        "version": card["version"],
        "capabilities": card["capabilities"],
        "prompts": card["prompts"],
        "resources": card["resources"],
        "data": {
            "name": metadata["mcpServerName"],
            "version": card["version"],
            "remotes": [{"url": metadata["mcpEndpoint"]}],
        },
        "metadata": {
            field: metadata[field]
            for field in (
                "publicToolCount",
                "publicPromptCount",
                "publicResourceCount",
                "deploymentCommit",
                "deploymentReceipt",
                "deploymentReceiptSha256",
                "deploymentRun",
                "registryReceipt",
                "registryReceiptSha256",
                "registryRun",
                "registrySnapshot",
                "registrySnapshotSha256",
            )
        },
    }
    live_catalog = {"entries": [live_card]}
    live_registry = {
        "server": {
            "name": metadata["mcpServerName"],
            "version": card["version"],
        }
    }
    initialize = {
        "protocolVersion": "2025-06-18",
        "serverInfo": {"name": "palimpsest", "version": card["version"]},
    }
    _validate_palimpsest_live_agreement(
        card,
        live_catalog,
        live_registry,
        initialize,
    )

    live_card["resources"] = []
    with pytest.raises(RuntimeError, match="live catalog resources differs"):
        _validate_palimpsest_live_agreement(
            card,
            live_catalog,
            live_registry,
            initialize,
        )
    live_card["resources"] = card["resources"]

    live_card["metadata"]["publicResourceCount"] = 0
    with pytest.raises(RuntimeError, match="live catalog publicResourceCount differs"):
        _validate_palimpsest_live_agreement(
            card,
            live_catalog,
            live_registry,
            initialize,
        )
    live_card["metadata"]["publicResourceCount"] = metadata["publicResourceCount"]

    initialize["serverInfo"]["version"] = "1.9.2"
    with pytest.raises(RuntimeError, match="Palimpsest MCP version differs"):
        _validate_palimpsest_live_agreement(
            card,
            live_catalog,
            live_registry,
            initialize,
        )


def test_palimpsest_live_inventory_calls_and_matches_exact_declarations(monkeypatch):
    card = _palimpsest_card()
    endpoint = card["metadata"]["mcpEndpoint"]
    method_results = {
        "tools/list": {"tools": [{"name": name} for name in card["capabilities"]]},
        "prompts/list": {"prompts": [{"name": name} for name in card["prompts"]]},
        "resources/list": {
            "resources": [
                {
                    "name": "china-economic-publication-rights",
                    "uri": uri,
                }
                for uri in card["resources"]
            ]
        },
    }
    calls = []

    def fake_mcp_request(url, payload, **headers):
        assert url == endpoint
        assert headers == {"protocol_version": "2025-06-18"}
        calls.append(payload["method"])
        return {
            "jsonrpc": "2.0",
            "id": payload["id"],
            "result": method_results[payload["method"]],
        }, {}

    monkeypatch.setattr(verifier, "_mcp_request", fake_mcp_request)
    surfaces = _palimpsest_surface_lists(endpoint)
    _validate_palimpsest_surface_lists(card, surfaces)
    assert calls == ["tools/list", "prompts/list", "resources/list"]


def test_palimpsest_live_inventory_rejects_extra_or_paginated_surfaces():
    card = _palimpsest_card()
    surfaces = {
        "tools": {"tools": [{"name": name} for name in card["capabilities"]]},
        "prompts": {"prompts": [{"name": name} for name in card["prompts"]]},
        "resources": {
            "resources": [
                {"uri": "palimpsest://china-economic/publication-rights"},
                {"uri": "palimpsest://undeclared"},
            ]
        },
    }
    with pytest.raises(RuntimeError, match="live resources count differs"):
        _validate_palimpsest_surface_lists(card, surfaces)

    surfaces["resources"]["resources"] = [
        {"uri": "palimpsest://china-economic/publication-rights"}
    ]
    surfaces["tools"]["nextCursor"] = "another-page"
    with pytest.raises(RuntimeError, match="tools/list is paginated"):
        _validate_palimpsest_surface_lists(card, surfaces)


def _rights_resource_result():
    rights = {
        "status": "restricted",
        "availability": "unavailable",
        "evidence_class": "restricted",
        "publication_allowed": False,
        "counts": {
            "allowed_records": 0,
            "published_records": 0,
            "restricted_records": 2259,
        },
        "no_partial_rows": True,
    }
    return {
        "contents": [
            {
                "uri": PALIMPSEST_RIGHTS_URI,
                "mimeType": "application/json",
                "text": json.dumps(rights),
            }
        ]
    }


def test_palimpsest_reads_and_validates_fail_closed_publication_rights(monkeypatch):
    endpoint = _palimpsest_card()["metadata"]["mcpEndpoint"]
    expected_result = _rights_resource_result()

    def fake_mcp_request(url, payload, **headers):
        assert url == endpoint
        assert payload["method"] == "resources/read"
        assert payload["params"] == {"uri": PALIMPSEST_RIGHTS_URI}
        assert headers == {"protocol_version": "2025-06-18"}
        return {
            "jsonrpc": "2.0",
            "id": payload["id"],
            "result": expected_result,
        }, {}

    monkeypatch.setattr(verifier, "_mcp_request", fake_mcp_request)
    result = _palimpsest_rights_resource(endpoint, PALIMPSEST_RIGHTS_URI)
    _validate_palimpsest_rights_resource(result, PALIMPSEST_RIGHTS_URI)


def test_palimpsest_rights_resource_rejects_publication_or_value_like_state():
    result = _rights_resource_result()
    rights = json.loads(result["contents"][0]["text"])
    rights["publication_allowed"] = True
    result["contents"][0]["text"] = json.dumps(rights)
    with pytest.raises(RuntimeError, match="publication_allowed must be boolean false"):
        _validate_palimpsest_rights_resource(result, PALIMPSEST_RIGHTS_URI)

    result = _rights_resource_result()
    rights = json.loads(result["contents"][0]["text"])
    rights["counts"]["published_records"] = 1
    result["contents"][0]["text"] = json.dumps(rights)
    with pytest.raises(RuntimeError, match="published records must be integer zero"):
        _validate_palimpsest_rights_resource(result, PALIMPSEST_RIGHTS_URI)

    result = _rights_resource_result()
    result["contents"].append(dict(result["contents"][0]))
    with pytest.raises(RuntimeError, match="exactly one content"):
        _validate_palimpsest_rights_resource(result, PALIMPSEST_RIGHTS_URI)


def test_sibling_api_catalog_requires_profile_declared_digest_and_mcp_anchor():
    card = json.loads(
        json.dumps(_sibling_card("urn:air:liquilens.in:catalog:undertow"))
    )
    metadata = card["metadata"]
    registry_url = (
        "https://registry.modelcontextprotocol.io/v0.1/servers/"
        "io.github.beepboop2025%2Fundertow/versions/latest"
    )
    payload = {
        "linkset": [
            {
                "anchor": metadata["mcpEndpoint"],
                "service-meta": [{"href": registry_url, "type": "application/json"}],
            }
        ]
    }
    body = compact_json_bytes(payload)
    metadata["apiCatalogSha256"] = f"sha256:{hashlib.sha256(body).hexdigest()}"
    headers = {
        "content-type": (f'application/linkset+json; profile="{RFC_9727_PROFILE}"'),
        "link": f'<{metadata["apiCatalog"]}>; rel="api-catalog"',
        "access-control-allow-origin": "*",
    }
    assert (
        _validate_sibling_api_catalog_response(
            "Undertow",
            card,
            body,
            headers,
        )
        == payload
    )

    bad_headers = dict(headers)
    bad_headers["content-type"] = "application/linkset+json"
    with pytest.raises(RuntimeError, match="catalog profile differs"):
        _validate_sibling_api_catalog_response(
            "Undertow",
            card,
            body,
            bad_headers,
        )
    with pytest.raises(RuntimeError, match="catalog SHA-256 differs"):
        _validate_sibling_api_catalog_response(
            "Undertow",
            card,
            body + b"\n",
            headers,
        )


def test_sibling_mcp_inventory_must_match_the_central_card_exactly():
    card = _sibling_card("urn:air:liquilens.in:catalog:riptide")
    initialize = {
        "protocolVersion": "2025-06-18",
        "serverInfo": {"name": "riptide", "version": card["version"]},
    }
    tools = {"tools": [{"name": name} for name in card["capabilities"]]}
    _validate_sibling_mcp("Riptide", card, initialize, tools)

    tools["tools"].append({"name": "undeclared_tool"})
    with pytest.raises(RuntimeError, match="live public tool count differs"):
        _validate_sibling_mcp("Riptide", card, initialize, tools)


def test_riptide_registry_split_requires_every_explicit_gate():
    card = _sibling_card("urn:air:liquilens.in:catalog:riptide")
    assert _sibling_registry_version("Riptide", card) == "1.2.0"
    assert {
        key: card["metadata"][key]
        for key in (
            "sourceUpgradeProofVisibility",
            "sourceUpgradeProofState",
            "sourceUpgradeProofPubliclyFetchable",
        )
    } == {
        "sourceUpgradeProofVisibility": "owner-private",
        "sourceUpgradeProofState": "owner-verified-success",
        "sourceUpgradeProofPubliclyFetchable": False,
    }
    payload = {
        "server": {
            "name": card["data"]["name"],
            "version": "1.2.0",
            "repository": {
                "url": "https://github.com/beepboop2025/riptide",
                "source": "github",
            },
            "remotes": [{"url": card["metadata"]["mcpEndpoint"]}],
        },
        "_meta": {
            "io.modelcontextprotocol.registry/official": {
                "status": "active",
                "isLatest": True,
            }
        },
    }
    _validate_sibling_registry(
        "Riptide",
        card,
        payload,
        expected_version="1.2.0",
        require_latest=True,
    )

    undeclared = json.loads(json.dumps(card))
    undeclared["metadata"]["registryUpgradeState"] = "not-declared"
    with pytest.raises(RuntimeError, match="registryUpgradeState differs"):
        _sibling_registry_version("Riptide", undeclared)


def test_narcoscope_registry_workflow_binds_the_declared_source_sha():
    card = _sibling_card("urn:air:liquilens.in:catalog:narcoscope")
    payload = {
        "id": 33260765822,
        "repository": {"full_name": "beepboop2025/narcoscope"},
        "status": "completed",
        "conclusion": "success",
        "head_sha": card["metadata"]["sourceUpgradeCommit"],
        "head_branch": "main",
        "path": ".github/workflows/registry-publish.yml",
        "event": "workflow_dispatch",
    }
    _validate_sibling_source_workflow(
        "NarcoScope",
        card,
        payload,
        33260765822,
        "beepboop2025/narcoscope",
        expected_workflow=".github/workflows/registry-publish.yml",
        expected_event="workflow_dispatch",
    )
    payload["head_sha"] = "0" * 40
    with pytest.raises(RuntimeError, match="workflow source SHA differs"):
        _validate_sibling_source_workflow(
            "NarcoScope",
            card,
            payload,
            33260765822,
            "beepboop2025/narcoscope",
            expected_workflow=".github/workflows/registry-publish.yml",
            expected_event="workflow_dispatch",
        )

    payload["head_sha"] = card["metadata"]["sourceUpgradeCommit"]
    payload["event"] = "pull_request"
    with pytest.raises(RuntimeError, match="workflow event differs"):
        _validate_sibling_source_workflow(
            "NarcoScope",
            card,
            payload,
            33260765822,
            "beepboop2025/narcoscope",
            expected_workflow=".github/workflows/registry-publish.yml",
            expected_event="workflow_dispatch",
        )


def test_modern_mcp_result_requires_complete_metadata_and_no_session():
    payload = {
        "jsonrpc": "2.0",
        "id": "probe",
        "result": {
            "resultType": "complete",
            "_meta": {
                "io.modelcontextprotocol/serverInfo": {
                    "name": "riptide",
                    "version": "1.3.0",
                }
            },
        },
    }
    assert (
        _require_modern_result(
            payload,
            {},
            "probe",
            expected_name="riptide",
            expected_version="1.3.0",
        )
        == payload["result"]
    )
    with pytest.raises(RuntimeError, match="Mcp-Session-Id"):
        _require_modern_result(
            payload,
            {"mcp-session-id": "forbidden"},
            "probe",
            expected_name="riptide",
            expected_version="1.3.0",
        )
    del payload["result"]["_meta"]
    with pytest.raises(RuntimeError, match="serverInfo"):
        _require_modern_result(
            payload,
            {},
            "probe",
            expected_name="riptide",
            expected_version="1.3.0",
        )


def test_modern_discovery_may_report_a_verified_subset_of_advertised_versions():
    card = _sibling_card("urn:air:liquilens.in:catalog:narcoscope")
    result = {
        "supportedVersions": ["2026-07-28"],
        "capabilities": {"tools": {}},
        "ttlMs": 0,
        "cacheScope": "private",
    }
    _validate_modern_sibling_discovery("NarcoScope", card, result)

    result["supportedVersions"] = ["2026-07-28", "2099-01-01"]
    with pytest.raises(RuntimeError, match="supported versions are invalid"):
        _validate_modern_sibling_discovery("NarcoScope", card, result)

    result["supportedVersions"] = ["2026-07-28"]
    result["ttlMs"] = -1
    with pytest.raises(RuntimeError, match="invalid ttlMs"):
        _validate_modern_sibling_discovery("NarcoScope", card, result)

    result["ttlMs"] = 0
    result["cacheScope"] = "shared"
    with pytest.raises(RuntimeError, match="invalid cacheScope"):
        _validate_modern_sibling_discovery("NarcoScope", card, result)


def test_network_boundary_rejects_private_resolution_and_oversized_bodies(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))
        ],
    )
    with pytest.raises(RuntimeError, match="non-public"):
        _validate_public_https_url("https://api.github.com/example")
    with pytest.raises(RuntimeError, match="allowlisted"):
        _validate_public_https_url("https://attacker.example/catalog")

    class Response:
        def read(self, _limit):
            return b"12345"

    with pytest.raises(RuntimeError, match="response limit"):
        _read_bounded(Response(), 4, "receipt")


def test_github_deployment_proof_requires_exact_sha_and_success(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))
        ],
    )
    deployment = {
        "id": 7,
        "sha": "a" * 40,
        "ref": "a" * 40,
        "task": "deploy",
        "environment": "Production",
    }
    statuses = [
        {
            "state": "success",
            "environment_url": "https://narcoscope.com",
        }
    ]
    _validate_github_deployment(
        "NarcoScope",
        deployment,
        statuses,
        expected_id=7,
        expected_sha="a" * 40,
    )
    statuses[0]["state"] = "failure"
    with pytest.raises(RuntimeError, match="deployment status differs"):
        _validate_github_deployment(
            "NarcoScope",
            deployment,
            statuses,
            expected_id=7,
            expected_sha="a" * 40,
        )


def test_linkset_json_mime_accepts_static_json_compatibility_only():
    assert _mime_matches_declared(
        "application/json; charset=utf-8",
        "application/ai-catalog+json",
    )
    assert _mime_matches_declared(
        "application/ai-catalog+json",
        "application/ai-catalog+json",
    )
    assert not _mime_matches_declared("text/html", "application/ai-catalog+json")
