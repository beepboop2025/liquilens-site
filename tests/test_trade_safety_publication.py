"""Trade Safety v1 and its read-only gateway stay exact and honest."""

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
        if row["identifier"] == "urn:air:liquilens.in:protocol:trade-safety-receipt"
    )

    assert entry["url"] == "https://liquilens.in/protocol/trade-safety/"
    assert entry["version"] == "1.0.0"
    assert entry["metadata"]["implementationRelease"] == "0.18.0"
    assert entry["metadata"]["sourceTag"] == "v0.18.0"
    assert entry["metadata"]["releaseCommit"] == (
        "906ca033a96ea862ab813c64db2a6b01c5ce8c4f"
    )
    assert entry["metadata"]["releaseTagObject"] == (
        "42dd412ef27b470841b71b8bc73c0ed63a5e4a6b"
    )
    assert entry["metadata"]["offlineVerifierRegistry"].endswith("/versions/0.18.0")
    assert entry["metadata"]["requiredProducts"] == "Seiche, Undertow"
    assert entry["metadata"]["conditionalProduct"] == "LiquiLens"
    assert entry["metadata"]["hostedApi"] == (
        "https://trade-safety.liquilens.in/v1/check"
    )
    assert entry["metadata"]["hostedMcp"] == ("https://trade-safety.liquilens.in/mcp")
    assert entry["metadata"]["gatewayVersion"] == "0.2.0"
    assert entry["metadata"]["gatewaySourceRevision"] == (
        "5f46ff09288a8ee1024715db75615ab5882465fa"
    )
    assert entry["metadata"]["gatewayOciImage"].endswith(
        "@sha256:2d741addefa972e25d65f2617ce75f639321345ffe74dd02d5f3b4f668154762"
    )
    assert entry["metadata"]["x402Access"] == "disabled"
    assert "public read-only sandbox" in entry["metadata"]["gatewayStatus"]
    assert "paper-only" in entry["metadata"]["orderGuardStatus"]
    assert "live mode fails closed" in entry["metadata"]["orderGuardStatus"]
    assert "not deployed" in entry["metadata"]["alpacaPaperAdapter"]
    authority = entry["metadata"]["financialAuthority"]
    for forbidden_authority in ("cannot execute", "recommend", "allocate capital"):
        assert forbidden_authority in authority


def test_agent_catalog_exposes_only_the_read_only_trade_safety_mcp_boundary():
    catalog = json.loads(_read(".well-known/ai-catalog.json"))
    entry = next(
        row
        for row in catalog["entries"]
        if row["identifier"] == "urn:air:liquilens.in:mcp:trade-safety"
    )

    assert entry["version"] == "0.2.0"
    assert entry["data"]["name"] == "liquilens-trade-safety-gateway"
    assert entry["data"]["remotes"] == [
        {
            "type": "streamable-http",
            "url": "https://trade-safety.liquilens.in/mcp",
        }
    ]
    assert entry["capabilities"] == [
        "assess_trade_safety",
        "trade_safety_capabilities",
    ]
    assert entry["protocolVersions"] == ["2026-07-28", "2025-11-25"]
    assert entry["prompts"] == []
    assert entry["resourceTemplates"] == []
    metadata = entry["metadata"]
    assert metadata["publicToolCount"] == 2
    assert metadata["executionToolCount"] == 0
    assert metadata["x402Access"] == "disabled"
    assert metadata["sourceRevision"] == ("5f46ff09288a8ee1024715db75615ab5882465fa")
    assert metadata["ociImage"].endswith(
        "@sha256:2d741addefa972e25d65f2617ce75f639321345ffe74dd02d5f3b4f668154762"
    )
    for key in (
        "canExecute",
        "canRecommend",
        "canAllocateCapital",
        "canRouteOrder",
        "canCustody",
        "canSettle",
        "hasBrokerCredentials",
        "hasOrderSubmission",
    ):
        assert metadata[key] is False
    assert "not deployed" in metadata["alpacaPaperAdapter"]


def test_human_and_machine_surfaces_link_every_trade_safety_contract():
    page = _read("protocol/trade-safety/index.html")
    assert (
        '<link rel="canonical" href="https://liquilens.in/protocol/trade-safety/">'
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
        "public gateway is a read-only sandbox",
        "x402 is disabled",
        "5f46ff09288a8ee1024715db75615ab5882465fa",
        "2d741addefa972e25d65f2617ce75f639321345ffe74dd02d5f3b4f668154762",
        "paper-only reference adapter",
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
    assert "https://trade-safety.liquilens.in/v1/check" in llms
    assert "x402 is disabled" in llms
    assert (
        "offline read-only MCP server exposes receipt verification, not issuance"
        in llms
    )

    developers = _read("developers/index.html")
    assert "https://trade-safety.liquilens.in/mcp" in developers
    assert "The Alpaca paper adapter is source-only" in developers
    assert 'data-event="mcp_endpoint_copied"' in developers
    assert 'data-event="openapi_opened"' in developers
    trade_safety_cards = developers[
        developers.index("Trade Safety 0.2.0") : developers.index("Private book")
    ]
    assert trade_safety_cards.count('data-event="') == 3
    assert trade_safety_cards.count('data-event="mcp_endpoint_copied"') == 1
    assert trade_safety_cards.count('data-event="openapi_opened"') == 1
    assert trade_safety_cards.count('data-event="pilot_cta_clicked"') == 1
    assert 'href="/protocol/trade-safety/#protected-route-pilot"' in (
        trade_safety_cards
    )
    capabilities_link = trade_safety_cards[
        trade_safety_cards.index(
            'href="https://trade-safety.liquilens.in/v1/capabilities"'
        ) :
    ]
    assert capabilities_link.split(">", 1)[0].count("data-event") == 0


def test_protected_route_pilot_is_bounded_commercial_and_measurable():
    page = _read("protocol/trade-safety/index.html")
    for required in (
        'id="protected-route-pilot"',
        "Paid protected-route pilot",
        "30 days",
        "one broker paper-sandbox or OMS shadow route",
        "one account",
        "one strategy family",
        "one written operator policy",
        "25,000 max",
        "hard cap and no automatic overage",
        "four weekly calibration",
        "Order-path and bypass map",
        "Verifiable receipt, replay and local audit export",
        "Final evidence report with go, revise or stop decision",
        "there is no public list price",
        "No broker secret, order history or customer row",
        "A click is not counted as a qualified lead, customer, pilot, revenue",
        "no live broker credentials, routing or real-money execution",
    ):
        assert required.lower() in page.lower()

    assert page.count('data-pilot-event="email_clicked"') == 2
    assert "LiquiLens%20Protected%20Route%20Pilot" in page
    for qualification_field in (
        "Role%20and%20route%20owner",
        "Agent%20or%20runtime",
        "Paper%20broker%20or%20OMS%20shadow%20route",
        "Current%20order-control%20path",
        "Success%20threshold",
        "Preferred%20customer-owned%20environment",
    ):
        assert qualification_field in page

    for unsupported_claim in (
        "$2,500",
        "$7,500",
        "live trading protection",
        "customers use",
        "revenue generated",
    ):
        assert unsupported_claim.lower() not in page.lower()

    app = _read("protocol/trade-safety/app.js")
    assert "ALLOWED_EVENTS = {offer_viewed: true, email_clicked: true}" in app
    assert 'JSON.stringify({surface: "pilot", event: eventName})' in app
    assert 'track("offer_viewed")' in app
    assert "keepalive: true" in app
    for forbidden_payload in ("location.href", "document.referrer", "FormData"):
        assert forbidden_payload not in app

    llms = _read("llms.txt")
    assert "Paid Trade Safety protected-route pilot:" in llms
    assert "up to 25,000 assessment attempts" in llms
    assert "there is no public list price" in llms
    assert "does not provide investment advice" in llms

    access = json.loads(_read("product-card.json"))["access"]
    assert access["trade_safety_protected_route_pilot"].endswith(
        "#protected-route-pilot"
    )
    assert "30-day proof" in access["trade_safety_protected_route_pilot_scope"]
    assert (
        "no live-money execution"
        in (access["trade_safety_protected_route_pilot_scope"])
    )
    assert access["trade_safety_protected_route_pilot_contact"].startswith(
        "mailto:mrinal@liquilens.in"
    )

    catalog = json.loads(_read(".well-known/ai-catalog.json"))
    entry = next(
        row
        for row in catalog["entries"]
        if row["identifier"] == "urn:air:liquilens.in:protocol:trade-safety-receipt"
    )
    assert entry["metadata"]["protectedRoutePilot"].endswith("#protected-route-pilot")
    assert "no live-money execution" in (entry["metadata"]["protectedRoutePilotScope"])
    assert (
        "no public list price" in (entry["metadata"]["protectedRoutePilotCommercials"])
    )


def test_product_card_exposes_the_read_only_gateway_without_execution_authority():
    access = json.loads(_read("product-card.json"))["access"]
    assert access["trade_safety_receipt"] == (
        "https://liquilens.in/protocol/trade-safety/"
    )
    assert access["trade_safety_receipt_schema"].endswith(
        "/protocol/liquilens-trade-safety-receipt-v1.schema.json"
    )
    assert access["trade_safety_api"] == ("https://trade-safety.liquilens.in/v1/check")
    assert access["trade_safety_openapi"] == (
        "https://trade-safety.liquilens.in/openapi.json"
    )
    assert access["trade_safety_mcp"] == ("https://trade-safety.liquilens.in/mcp")
    assert access["trade_safety_gateway_version"] == "0.2.0"
    assert access["trade_safety_gateway_source_revision"] == (
        "5f46ff09288a8ee1024715db75615ab5882465fa"
    )
    assert access["trade_safety_x402_status"] == "disabled"
    assert "read-only sandbox" in access["trade_safety_gateway_status"].lower()
    assert all(
        value is False for value in access["trade_safety_financial_authority"].values()
    )
    assert "not deployed" in access["trade_safety_alpaca_adapter_status"]


def test_rfc9727_catalog_exposes_only_the_real_gateway_surfaces():
    catalog = json.loads(_read(".well-known/api-catalog.json"))
    by_anchor = {row["anchor"]: row for row in catalog["linkset"]}
    assert by_anchor["https://trade-safety.liquilens.in/v1/check"]["service-desc"] == [
        {
            "href": "https://trade-safety.liquilens.in/openapi.json",
            "type": "application/json",
        }
    ]
    assert by_anchor["https://trade-safety.liquilens.in/mcp"]["status"] == [
        {
            "href": "https://trade-safety.liquilens.in/healthz",
            "type": "application/json",
        }
    ]
    serialized = json.dumps(
        [
            by_anchor["https://trade-safety.liquilens.in/v1/check"],
            by_anchor["https://trade-safety.liquilens.in/mcp"],
        ]
    ).lower()
    assert "x402" not in serialized
    assert "order" not in serialized


def test_protocol_catalog_binds_v0180_release_and_stable_trade_safety_hashes():
    catalog = json.loads(_read("protocol/catalog.json"))
    assert catalog["version"] == "0.18.0"
    assert catalog["releaseCommit"] == ("906ca033a96ea862ab813c64db2a6b01c5ce8c4f")
    assert catalog["releaseTagObject"] == ("42dd412ef27b470841b71b8bc73c0ed63a5e4a6b")
    artifacts = {row["url"]: row["sha256"] for row in catalog["artifacts"]}
    for relative, expected_sha256 in TAGGED_BYTES.items():
        if relative == "protocol/fdc3/com.liquilens.evidence.schema.json":
            public_url = f"https://liquilens.in/{relative}"
        else:
            public_url = f"https://liquilens.in/{relative}"
        assert artifacts[public_url] == expected_sha256
