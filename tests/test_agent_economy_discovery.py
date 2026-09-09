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
    assert ENTRIES["urn:air:liquilens.in:catalog:narcoscope"]["version"] == "1.6.0"

    riptide = ENTRIES["urn:air:liquilens.in:catalog:riptide"]
    assert riptide["metadata"]["sourceUpgradeVersion"] == "1.3.0"
    assert (
        riptide["metadata"]["sourceUpgradeState"]
        == "live-registry-published"
    )
    assert riptide["metadata"]["sourceUpgradeCommit"] == (
        "00b50adaea41bebe1ceb54867f47e0070ed5eec6"
    )
    assert riptide["metadata"]["registryVersion"].endswith("/versions/1.3.0")
    assert riptide["metadata"]["registryUpgradeState"] == "published-active-latest"
    assert riptide["metadata"]["registryPublicationProofCommit"] == (
        "afa543ee77c396fcc2d77b4f6f84ca0de3aac362"
    )
    assert riptide["metadata"]["apiCatalogSha256"] == (
        "sha256:b7075bdbe11883f875ebb0102b6d82e84578b62ce66d4a05e4b8b800074ee1b8"
    )


def test_undertow_rfc9727_catalog_is_bound_to_live_deployment_proof():
    entry = ENTRIES["urn:air:liquilens.in:catalog:undertow"]
    metadata = entry["metadata"]
    assert entry["version"] == "1.10.0"
    assert "trade_safety_exit_context" in entry["capabilities"]
    assert metadata["publicToolCount"] == 11
    assert metadata["deploymentPublicToolCount"] == 10
    assert metadata["apiCatalogUpgradeState"] == "live-externally-verified"
    assert metadata["apiCatalogSourceCommit"] == (
        "0efb594c7f824478deec74da9e6ebda622434d21"
    )
    assert metadata["apiCatalogCoreProofCommit"] == (
        "724b445ca57b8f48793d29cda45d95f62088082a"
    )
    assert metadata["apiCatalogSiteCommit"] == (
        "9d32a5d7b1eac390b5da643b5151c15ce54ad9a5"
    )
    assert "apiCatalogWorkerVersion" not in metadata
    assert metadata["apiCatalogSha256"] == (
        "sha256:bffb6a7626d066cdb5293cc28eca465baaae99974ef951eb3280c67501cc5e84"
    )
    assert metadata["aiCatalogSha256"] == (
        "sha256:9b9184730f19e16f128477fcaa09cf99d1df46475051821ebd42af78d9014fba"
    )
    assert metadata["apiCatalogVerifiedAt"] == "2026-09-04T19:37:30Z"


def test_narcoscope_exposes_the_live_host_and_active_registry_release():
    entry = ENTRIES["urn:air:liquilens.in:catalog:narcoscope"]
    assert entry["data"]["websiteUrl"] == "https://narcoscope.com"
    assert entry["data"]["remotes"] == [
        {
            "type": "streamable-http",
            "url": "https://www.narcoscope.com/mcp",
        }
    ]
    assert entry["metadata"]["customDomainStatus"] == "configured-live"
    assert entry["metadata"]["registryStatus"] == "active-latest"
    assert entry["metadata"]["apiCatalogSha256"] == (
        "sha256:08da9a3bd68c6bc99d235d76c3439327f106421bc49cd88e6e128560c64a6291"
    )
    assert entry["metadata"]["sourceUpgradeCommit"] == (
        "e818c33feaf5f8081cbfc5807aced0cd50d8952f"
    )
    assert entry["metadata"]["productionDeploymentProvider"] == "railway-fleet"
    assert entry["metadata"]["productionReleaseReceipt"].endswith("/" + entry["metadata"]["sourceUpgradeCommit"] + "/receipt.json")
    assert entry["metadata"]["registryPublicationMethod"] == "official-maintainer-client"
    assert entry["metadata"]["sourceValidationProvider"] == "railway-native"


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
    assert carrier["version"] == "0.20.1"
    assert carrier["metadata"]["mcpBundleSha256"] == (
        "09b25571f61f4ba2bd5e1c367a580355a6e08eccf0d1c34bdde0bbd460be0ed6"
    )
    assert carrier["metadata"]["consumerChannelSnapshotVersion"] == "0.20.1"
    assert carrier["metadata"]["releaseCommit"] == (
        "6f9077bf0879a76db7b9bf98fb37839f7755dd9f"
    )
    assert carrier["metadata"]["registryStatus"] == "active-latest"
    assert palimpsest["version"] == "1.9.3"
    assert palimpsest["metadata"]["deploymentCommit"] == (
        "1b71dd2bb2dcdec0b99691f7d4caaa13c4857574")
