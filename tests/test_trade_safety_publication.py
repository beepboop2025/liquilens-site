"""Trade Safety v1 stays byte-exact, discoverable, and honest about hosting."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TAGGED_BYTES = {
    "protocol/liquilens-trade-safety-request-v1.schema.json": (
        "73af15f84b09b0772368095a01d0f076b9334dd8bbdf9637015aed86e35a47f5"
    ),
    "protocol/liquilens-trade-safety-policy-v1.schema.json": (
        "d9171e61c2d378eec545a14bbab0d1ca54302397c809eeeeaae55fb9154ae8d1"
    ),
    "protocol/liquilens-broker-preview-reference-v1.schema.json": (
        "89069649379ca759382dcf3f9237e58b069e7fddeeecae6cffa686bbe7351422"
    ),
    "protocol/liquilens-trade-safety-receipt-v1.schema.json": (
        "c2232ae5f80eb42edf7562ae5f5e44ccb9866a13717b697b4d41c28e74b25abe"
    ),
    "protocol/fdc3/com.liquilens.evidence.schema.json": (
        "9519474a4d0bf3a77834320d9aa43a88d5df96d49f691110154050212c7511b7"
    ),
    "protocol/fdc3/com.liquilens.trade-safety-receipt.schema.json": (
        "6c013eef85134e17b649e67c75227a698b76b7d97c7048edb3e8cd703563620b"
    ),
    "protocol/fdc3/trade-safety-intents.json": (
        "e35efa5568c0328e96871010ff2d52afe767d65deaa1cadd13f759391047a0a2"
    ),
    "protocol/trade-safety/specification.md": (
        "1b630294f2da9d12de73728712d09b96584aaf80f67c2ff7049811de608533ae"
    ),
    "protocol/trade-safety/adoption-plan.md": (
        "9e3afaa9811d8bd691a4a6013f2fc424f5d989baaddd4400600789694593299c"
    ),
}
SPEC_SCHEMA_COMPATIBILITY_ALIASES = {
    "protocol/protocol/liquilens-trade-safety-request-v1.schema.json": (
        "https://liquilens.in/protocol/liquilens-trade-safety-request-v1.schema.json"
    ),
    "protocol/protocol/liquilens-trade-safety-policy-v1.schema.json": (
        "https://liquilens.in/protocol/liquilens-trade-safety-policy-v1.schema.json"
    ),
    "protocol/protocol/liquilens-broker-preview-reference-v1.schema.json": (
        "https://liquilens.in/protocol/liquilens-broker-preview-reference-v1.schema.json"
    ),
    "protocol/protocol/liquilens-trade-safety-receipt-v1.schema.json": (
        "https://liquilens.in/protocol/liquilens-trade-safety-receipt-v1.schema.json"
    ),
    "protocol/integrations/fdc3/com.liquilens.trade-safety-receipt.schema.json": (
        "https://liquilens.in/protocol/fdc3/"
        "com.liquilens.trade-safety-receipt.schema.json"
    ),
}


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_published_contracts_are_exact_v0171_tag_bytes():
    for relative, expected_sha256 in TAGGED_BYTES.items():
        path = ROOT / relative
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_sha256


def test_trade_safety_schemas_use_stable_canonical_ids():
    for relative in (
        "protocol/liquilens-trade-safety-request-v1.schema.json",
        "protocol/liquilens-trade-safety-policy-v1.schema.json",
        "protocol/liquilens-broker-preview-reference-v1.schema.json",
        "protocol/liquilens-trade-safety-receipt-v1.schema.json",
        "protocol/fdc3/com.liquilens.trade-safety-receipt.schema.json",
    ):
        schema = json.loads(_read(relative))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"] == f"https://liquilens.in/{relative}"


def test_byte_exact_specification_relative_links_resolve_compatibly():
    specification = _read("protocol/trade-safety/specification.md")
    for alias, canonical in SPEC_SCHEMA_COMPATIBILITY_ALIASES.items():
        linked_relative = "../" + alias.removeprefix("protocol/")
        assert f"]({linked_relative})" in specification
        alias_schema = json.loads(_read(alias))
        assert alias_schema == {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$ref": canonical,
        }

    intents_alias = "protocol/integrations/fdc3/trade-safety-intents.json"
    assert "](../integrations/fdc3/trade-safety-intents.json)" in specification
    assert json.loads(_read(intents_alias)) == json.loads(
        _read("protocol/fdc3/trade-safety-intents.json")
    )


def test_agent_catalog_has_a_dedicated_non_executing_trade_safety_entry():
    catalog = json.loads(_read(".well-known/ai-catalog.json"))
    entry = next(
        row
        for row in catalog["entries"]
        if row["identifier"]
        == "urn:air:liquilens.in:protocol:trade-safety-receipt"
    )

    assert entry["url"] == "https://liquilens.in/protocol/trade-safety/"
    assert entry["version"] == "1.0.0"
    assert entry["metadata"]["requiredProducts"] == "Seiche, Undertow"
    assert entry["metadata"]["conditionalProduct"] == "LiquiLens"
    assert entry["metadata"]["hostedApi"] == "none"
    assert "no public hosted gateway" in entry["metadata"]["gatewayStatus"]
    authority = entry["metadata"]["financialAuthority"]
    for forbidden_authority in ("cannot execute", "recommend", "allocate capital"):
        assert forbidden_authority in authority


def test_human_and_machine_surfaces_link_every_trade_safety_contract():
    page = _read("protocol/trade-safety/index.html")
    assert (
        '<link rel="canonical" '
        'href="https://liquilens.in/protocol/trade-safety/">'
    ) in page
    assert page.count("<h1") == 1
    for phrase in (
        "Seiche",
        "Undertow",
        "LiquiLens",
        "pass",
        "limit",
        "hold",
        "unavailable",
        "No execution authority",
        "No public hosted Trade Safety API",
        "required <code>not_applicable</code> section",
    ):
        assert phrase in page

    for relative in TAGGED_BYTES:
        public_url = f"https://liquilens.in/{relative}"
        if relative.startswith("protocol/"):
            assert public_url in _read("protocol/catalog.json")

    llms = _read("llms.txt")
    sitemap = _read("sitemap.xml")
    assert "https://liquilens.in/protocol/trade-safety/" in llms
    assert "https://liquilens.in/protocol/trade-safety/" in sitemap
    assert "No public hosted Trade Safety API" in llms
    assert "offline read-only MCP server exposes receipt verification, not issuance" in llms


def test_product_card_exposes_contracts_without_inventing_a_hosted_api():
    access = json.loads(_read("product-card.json"))["access"]
    assert access["trade_safety_receipt"] == (
        "https://liquilens.in/protocol/trade-safety/"
    )
    assert access["trade_safety_receipt_schema"].endswith(
        "/protocol/liquilens-trade-safety-receipt-v1.schema.json"
    )
    assert "No public hosted gateway" in access["trade_safety_gateway_status"]
    assert not any(
        key in access
        for key in ("trade_safety_api", "trade_safety_openapi", "trade_safety_mcp")
    )


def test_rfc9727_catalog_does_not_claim_the_unhosted_gateway():
    api_catalog = _read(".well-known/api-catalog.json").lower()
    assert "trade-safety" not in api_catalog
    assert "trade_safety" not in api_catalog


def test_protocol_catalog_binds_v0171_release_and_trade_safety_hashes():
    catalog = json.loads(_read("protocol/catalog.json"))
    assert catalog["version"] == "0.17.1"
    assert catalog["releaseCommit"] == (
        "a74274236e177404c2d254541e6a4110a4ce8a0d"
    )
    assert catalog["releaseTagObject"] == (
        "8844ee4556d59472a587cb9ceb412112c23543db"
    )
    artifacts = {row["url"]: row["sha256"] for row in catalog["artifacts"]}
    for relative, expected_sha256 in TAGGED_BYTES.items():
        if relative == "protocol/fdc3/com.liquilens.evidence.schema.json":
            public_url = f"https://liquilens.in/{relative}"
        else:
            public_url = f"https://liquilens.in/{relative}"
        assert artifacts[public_url] == expected_sha256
