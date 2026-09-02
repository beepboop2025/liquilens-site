"""The central fleet index exposes agent surfaces without widening authority."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads(
    (ROOT / ".well-known/ai-catalog.json").read_text(encoding="utf-8")
)
ENTRIES = {entry["identifier"]: entry for entry in CATALOG["entries"]}


def test_adjacent_products_are_individually_discoverable():
    assert {
        "urn:air:liquilens.in:catalog:riptide",
        "urn:air:liquilens.in:catalog:myquant-editorial",
        "urn:air:liquilens.in:catalog:myquant-app",
        "urn:air:liquilens.in:catalog:narcoscope",
        "urn:air:liquilens.in:local:scamshield",
    } <= ENTRIES.keys()
    assert ENTRIES["urn:air:liquilens.in:catalog:riptide"]["version"] == "1.3.0"
    assert ENTRIES[
        "urn:air:liquilens.in:catalog:myquant-editorial"
    ]["version"] == "2.1.0"
    assert ENTRIES["urn:air:liquilens.in:catalog:myquant-app"]["version"] == "2.0.0"
    assert ENTRIES["urn:air:liquilens.in:catalog:narcoscope"]["version"] == "1.4.0"

    riptide = ENTRIES["urn:air:liquilens.in:catalog:riptide"]
    assert riptide["metadata"]["sourceUpgradeVersion"] == "1.3.0"
    assert (
        riptide["metadata"]["sourceUpgradeState"]
        == "live-registry-publication-gated"
    )
    assert riptide["metadata"]["sourceUpgradeCommit"] == (
        "00b50adaea41bebe1ceb54867f47e0070ed5eec6"
    )
    assert riptide["metadata"]["apiCatalogSha256"] == (
        "sha256:b7075bdbe11883f875ebb0102b6d82e84578b62ce66d4a05e4b8b800074ee1b8"
    )


def test_undertow_rfc9727_catalog_is_bound_to_live_deployment_proof():
    metadata = ENTRIES["urn:air:liquilens.in:catalog:undertow"]["metadata"]
    assert metadata["apiCatalogUpgradeState"] == "live-externally-verified"
    assert metadata["apiCatalogSiteCommit"] == (
        "f32799cf672ca694924ac4261344b303e9afe34d")
    assert metadata["apiCatalogWorkerVersion"] == (
        "403eef54-1c52-40ba-a503-a8ddc6a4769f")
    assert metadata["apiCatalogSha256"] == (
        "sha256:11819229f11a80bb1dd280a76feeaef4929e9caf28bde2a0bc78eb48e0cb6b7e")


def test_narcoscope_exposes_the_live_host_and_active_registry_release():
    entry = ENTRIES["urn:air:liquilens.in:catalog:narcoscope"]
    assert entry["data"]["websiteUrl"] == "https://narcoscope.com"
    assert entry["data"]["remotes"] == [
        {
            "type": "streamable-http",
            "url": "https://narcoscope.com/mcp",
        }
    ]
    assert entry["metadata"]["customDomainStatus"] == "configured-live"
    assert entry["metadata"]["registryStatus"] == "active-latest"
    assert entry["metadata"]["apiCatalogSha256"] == (
        "sha256:62e006de96351351fbd8ffd8911d8adf25cb7189aa000ac7e4765bd495fc062c"
    )
    assert entry["metadata"]["sourceUpgradeCommit"] == (
        "7ae91b08fea1430b44eea8205fc1898d8c3dbc2c"
    )
    assert entry["metadata"]["sourceUpgradeImplementationCommit"] == (
        "f52f63ebc1bcbbb8b4e5e41863b778774b2bcd17"
    )
    assert entry["metadata"]["sourceUpgradeDiscoveryCommit"] == (
        "ddacf2c56ed403aebeb62ef07d09004432072b1e"
    )
    assert entry["metadata"]["registryPublicationWorkflow"].endswith(
        "/actions/runs/33578233679"
    )


def test_scamshield_remains_local_even_with_a_modern_mcp_contract():
    entry = ENTRIES["urn:air:liquilens.in:local:scamshield"]
    assert entry["version"] == "1.1.0"
    assert entry["protocolVersions"][:2] == ["2026-07-28", "2025-11-25"]
    assert entry["metadata"]["access"] == "local-only"
    assert entry["metadata"]["releaseState"] == "merged-local-only-contract"
    assert entry["metadata"]["sourceCommit"] == (
        "e05138c92bc485658c1c3f95f883f2f334dc4b08")
    assert entry["metadata"]["publicRemoteEndpoint"] == "none"
    assert entry["metadata"]["registryStatus"] == "not-published-by-design"
    assert entry["metadata"]["assessmentStorage"] == "none"
    assert entry["metadata"]["rawTextReturned"] is False


def test_carrier_and_palimpsest_versions_match_verified_release_receipts():
    carrier = ENTRIES["urn:air:liquilens.in:protocol:evidence-carrier"]
    palimpsest = ENTRIES["urn:air:liquilens.in:catalog:palimpsest-china"]
    assert carrier["version"] == "0.18.0"
    assert carrier["metadata"]["mcpBundleSha256"] == (
        "f57ce3fb488b693e633d8bc66f980b616af09a8080722a11c50507496f39a2bb"
    )
    assert carrier["metadata"]["consumerChannelSnapshotVersion"] == "0.18.0"
    assert carrier["metadata"]["releaseCommit"] == (
        "906ca033a96ea862ab813c64db2a6b01c5ce8c4f"
    )
    assert carrier["metadata"]["registryStatus"] == "active-latest"
    assert palimpsest["version"] == "1.9.3"
    assert palimpsest["metadata"]["deploymentCommit"] == (
        "1b71dd2bb2dcdec0b99691f7d4caaa13c4857574")
