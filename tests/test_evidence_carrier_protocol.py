"""The public Evidence Carrier endpoints remain exact, licensed, and discoverable."""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "protocol/liquilens-evidence-carrier-v1.schema.json": (
        "https://liquilens.in/protocol/liquilens-evidence-carrier-v1.schema.json",
        "7f8494d8470853dc88665ea32c1dccb40cc58c55b07e9267aa28c81f83c1ccd3",
    ),
    "protocol/liquilens-evidence-carrier-reference-v1.schema.json": (
        "https://liquilens.in/protocol/liquilens-evidence-carrier-reference-v1.schema.json",
        "d54043bf11359749597bff7495b0fffe6ff8453a35144cee4a2bd69711fec7e8",
    ),
    "protocol/liquilens-fleet-brief-v1.schema.json": (
        "https://liquilens.in/protocol/liquilens-fleet-brief-v1.schema.json",
        "aaf95337ff973dfbdda97e8ac63975a61b199e43854927404055fbeb52fc6058",
    ),
    "protocol/fdc3/com.liquilens.evidence.schema.json": (
        "https://liquilens.in/protocol/fdc3/com.liquilens.evidence.schema.json",
        "9519474a4d0bf3a77834320d9aa43a88d5df96d49f691110154050212c7511b7",
    ),
    "protocol/openlineage/liquilens-evidence-facet.schema.json": (
        "https://liquilens.in/protocol/openlineage/liquilens-evidence-facet.schema.json",
        "e4c6035452d75be280a7b717f85da87319a078dbf5563e62ac3a3cb83486e9a5",
    ),
}
TRADE_SAFETY_ARTIFACTS = {
    "protocol/liquilens-trade-safety-request-v1.schema.json": (
        "https://liquilens.in/protocol/liquilens-trade-safety-request-v1.schema.json",
        "73af15f84b09b0772368095a01d0f076b9334dd8bbdf9637015aed86e35a47f5",
    ),
    "protocol/liquilens-trade-safety-policy-v1.schema.json": (
        "https://liquilens.in/protocol/liquilens-trade-safety-policy-v1.schema.json",
        "d9171e61c2d378eec545a14bbab0d1ca54302397c809eeeeaae55fb9154ae8d1",
    ),
    "protocol/liquilens-broker-preview-reference-v1.schema.json": (
        "https://liquilens.in/protocol/liquilens-broker-preview-reference-v1.schema.json",
        "89069649379ca759382dcf3f9237e58b069e7fddeeecae6cffa686bbe7351422",
    ),
    "protocol/liquilens-trade-safety-receipt-v1.schema.json": (
        "https://liquilens.in/protocol/liquilens-trade-safety-receipt-v1.schema.json",
        "c2232ae5f80eb42edf7562ae5f5e44ccb9866a13717b697b4d41c28e74b25abe",
    ),
    "protocol/fdc3/com.liquilens.trade-safety-receipt.schema.json": (
        "https://liquilens.in/protocol/fdc3/com.liquilens.trade-safety-receipt.schema.json",
        "6c013eef85134e17b649e67c75227a698b76b7d97c7048edb3e8cd703563620b",
    ),
    "protocol/fdc3/trade-safety-intents.json": (
        "https://liquilens.in/protocol/fdc3/trade-safety-intents.json",
        "e35efa5568c0328e96871010ff2d52afe767d65deaa1cadd13f759391047a0a2",
    ),
    "protocol/trade-safety/specification.md": (
        "https://liquilens.in/protocol/trade-safety/specification.md",
        "1b630294f2da9d12de73728712d09b96584aaf80f67c2ff7049811de608533ae",
    ),
    "protocol/trade-safety/adoption-plan.md": (
        "https://liquilens.in/protocol/trade-safety/adoption-plan.md",
        "9e3afaa9811d8bd691a4a6013f2fc424f5d989baaddd4400600789694593299c",
    ),
}
EXPECTED_CHANNELS = {
    "official-mcp-registry": (
        "live",
        "https://registry.modelcontextprotocol.io/v0.1/servers/"
        "io.github.beepboop2025%2Fliquilens-evidence-carrier/versions/0.17.1",
    ),
    "agent-skill": (
        "live",
        "https://github.com/beepboop2025/liquilens-evidence-carrier/tree/"
        "skill-v0.15.0/skills/liquilens-evidence",
    ),
    "codex-plugin": (
        "live",
        "https://github.com/beepboop2025/liquilens-evidence-carrier/tree/"
        "plugin-v0.14.1/plugins/liquilens-evidence",
    ),
    "vscode-vsix": (
        "live",
        "https://github.com/beepboop2025/liquilens-evidence-carrier/releases/"
        "download/vscode-v0.1.0/liquilens-evidence-0.1.0.vsix",
    ),
    "browser-verifier": (
        "live",
        "https://beepboop2025.github.io/liquilens-evidence-carrier/",
    ),
    "exact-sha-cdn-module": (
        "live",
        "https://cdn.jsdelivr.net/gh/beepboop2025/"
        "liquilens-evidence-carrier@68e5eead7ad7a78e3c379820a499cf3c7c34048b/"
        "browser/verifier.mjs",
    ),
    "uvx-immutable-wheel": (
        "live",
        "https://github.com/beepboop2025/liquilens-evidence-carrier/releases/"
        "download/v0.17.1/liquilens_evidence-0.17.1-py3-none-any.whl"
        "#sha256=dec2751fa2f20d09a1a77b5f25ae99f28fa49484ea1bf5ede7ca2bcdd86610ea",
    ),
    "homebrew": (
        "live",
        "https://github.com/beepboop2025/homebrew-tap/blob/"
        "ae2c2ef6f91cd58f821b9e3644f318fb15d26d56/Formula/"
        "liquilens-evidence.rb",
    ),
    "oci": (
        "live",
        "https://ghcr.io/v2/beepboop2025/liquilens-evidence-carrier/manifests/"
        "sha256:9ec0646269357e971a67e88c8076c3c52c1561b094c1f2093ee19882a33294d1",
    ),
    "mcp-oci": (
        "live",
        "https://ghcr.io/v2/beepboop2025/liquilens-evidence-carrier-mcp/"
        "manifests/sha256:d55f69e55e579603ae8b510de76b1191047427a92569424a"
        "17729ea7f7e3e2f7",
    ),
    "devcontainer-feature": (
        "live",
        "https://ghcr.io/v2/beepboop2025/liquilens-devcontainer-features/"
        "liquilens-evidence/manifests/sha256:79ac17d7c3f91dc9360c6aa63cb9e4fa"
        "0081d5c81e1a1492b2198a8280f5b22d",
    ),
    "research-notebook": (
        "live",
        "https://github.com/beepboop2025/liquilens-evidence-carrier/blob/"
        "3d079421c830fcc97ea08da3c54b8429eb5ed542/notebooks/"
        "evidence_carrier_research.ipynb",
    ),
    "mybinder": (
        "live",
        "https://mybinder.org/v2/gh/beepboop2025/liquilens-evidence-carrier/"
        "3d079421c830fcc97ea08da3c54b8429eb5ed542?urlpath=lab/tree/"
        "notebooks/evidence_carrier_research.ipynb",
    ),
    "colab": (
        "fetched_rendered_only",
        "https://colab.research.google.com/github/beepboop2025/"
        "liquilens-evidence-carrier/blob/"
        "3d079421c830fcc97ea08da3c54b8429eb5ed542/notebooks/"
        "evidence_carrier_research.ipynb",
    ),
    "nix-flake": (
        "live",
        "https://github.com/beepboop2025/liquilens-evidence-carrier/blob/"
        "3c97b71093f8bca201e74bb5cc7ddbe50d9fa052/NIX.md",
    ),
    "openbb-extension": (
        "live",
        "https://github.com/beepboop2025/liquilens-evidence-carrier/tree/"
        "05a77927496bf22c8bfdb7cbce2d6f43054911d0/integrations/openbb",
    ),
    "airflow-provider": (
        "live",
        "https://github.com/beepboop2025/liquilens-airflow-provider/releases/"
        "download/v0.1.0/liquilens_airflow_provider-0.1.0-py3-none-any.whl"
        "#sha256=aa91a2528ebf2e1583c379a08ce60f9aa52fc33d9d89da0bab9876d5720956bf",
    ),
    "fdc3-evidence-inspector": (
        "live_reference_consumer",
        "https://beepboop2025.github.io/financial-evidence-skills/"
        "integrations/fdc3/evidence-inspector/",
    ),
}


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_schema_bytes_and_ids_match_the_signed_source_artifacts():
    schemas = EXPECTED | {
        relative: value
        for relative, value in TRADE_SAFETY_ARTIFACTS.items()
        if relative.endswith(".schema.json")
    }
    for relative, (canonical_url, digest) in schemas.items():
        path = ROOT / relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"] == canonical_url


def test_machine_catalog_routes_every_contract_without_authority_widening():
    catalog = json.loads(_read("protocol/catalog.json"))
    assert catalog["license"] == "Apache-2.0"
    assert catalog["financialAuthority"] == "none"
    assert catalog["repository"] == (
        "https://github.com/beepboop2025/liquilens-evidence-carrier"
    )
    assert catalog["releaseCommit"] == (
        "a74274236e177404c2d254541e6a4110a4ce8a0d"
    )
    assert catalog["releaseTagObject"] == (
        "8844ee4556d59472a587cb9ceb412112c23543db"
    )
    assert catalog["pythonDistributionSha256"] == (
        "dec2751fa2f20d09a1a77b5f25ae99f28fa49484ea1bf5ede7ca2bcdd86610ea"
    )
    assert catalog["mcpBundleSha256"] == (
        "4d6c409f2c69588fad6fe13bf2f78ed1b72d3555d81082d5da638d037b0307a1"
    )
    assert catalog["browserVerifier"] == (
        "https://beepboop2025.github.io/liquilens-evidence-carrier/"
    )
    assert catalog["browserVerifierSource"].endswith(
        "/68e5eead7ad7a78e3c379820a499cf3c7c34048b/browser"
    )
    assert {
        row["url"]: row["sha256"] for row in catalog["artifacts"]
    } == {
        canonical_url: digest
        for canonical_url, digest in (EXPECTED | TRADE_SAFETY_ARTIFACTS).values()
    }


def test_human_and_agent_discovery_surfaces_link_the_protocol():
    page = _read("protocol/index.html")
    assert '<link rel="canonical" href="https://liquilens.in/protocol/">' in page
    assert page.count("<h1") == 1
    assert "Financial authority: none" in page
    assert "Apache-2.0" in page
    assert "https://beepboop2025.github.io/liquilens-evidence-carrier/" in page
    assert "https://liquilens.in/protocol/" in _read("sitemap.xml")
    assert "https://liquilens.in/protocol/catalog.json" in _read("llms.txt")

    discovery = json.loads(_read(".well-known/ai-catalog.json"))
    entry = next(
        row for row in discovery["entries"]
        if row["identifier"] == "urn:air:liquilens.in:protocol:evidence-carrier"
    )
    assert entry["url"] == "https://liquilens.in/protocol/catalog.json"
    assert entry["metadata"]["financialAuthority"] == "none"
    assert entry["metadata"]["browserVerifier"] == (
        "https://beepboop2025.github.io/liquilens-evidence-carrier/"
    )

    product = json.loads(_read("product-card.json"))
    assert product["access"]["evidence_carrier"] == (
        "https://liquilens.in/protocol/"
    )
    assert product["access"]["evidence_carrier_catalog"] == (
        "https://liquilens.in/protocol/catalog.json"
    )
    assert product["access"]["evidence_carrier_browser_verifier"] == (
        "https://beepboop2025.github.io/liquilens-evidence-carrier/"
    )


def test_consumer_channel_matrix_preserves_receipts_and_status_boundaries():
    catalog = json.loads(_read("protocol/catalog.json"))
    channels = catalog["consumerChannels"]
    assert len(channels) == len(EXPECTED_CHANNELS)
    assert len({channel["id"] for channel in channels}) == len(channels)
    assert {
        channel["id"]: (channel["status"], channel["url"])
        for channel in channels
    } == EXPECTED_CHANNELS

    by_id = {channel["id"]: channel for channel in channels}
    assert by_id["browser-verifier"]["sha256"] == (
        "27b30a224d11afb53dec13db214f0ac04d2f2d14a0b2172b623b14453d34a306"
    )
    assert by_id["exact-sha-cdn-module"]["sha256"] == (
        "76bcc3a8a0b4378e206fac769265eb631b765bbffbd290cbbfe7f86c72d6e16e"
    )
    assert by_id["research-notebook"]["sha256"] == (
        "5f4b731f76de0e85c00c373e3849553425d3102c75545183bdb090b66f88768c"
    )
    assert by_id["agent-skill"]["sha256"] == (
        "adef1a05e047457b752543633536b4e857532b194bf83396175f3f625bc87379"
    )
    assert by_id["agent-skill"]["discoverCommand"].endswith(
        "beepboop2025/liquilens-evidence-carrier --list"
    )
    assert by_id["agent-skill"]["directoryUrl"] == (
        "https://skills.sh/beepboop2025/liquilens-evidence-carrier/"
        "liquilens-evidence"
    )
    assert by_id["codex-plugin"]["sourceCommit"] == (
        "1531a60192728253283459287e9afecfa825f3e0"
    )
    assert by_id["codex-plugin"]["sha256"] == (
        "50cfa5b4ce3f974fb0af43d9eaa75014c44f97de03dcec30abab1ac2e99fa301"
    )
    assert "--ref plugin-v0.14.1" in by_id["codex-plugin"]["marketplaceCommand"]
    assert by_id["codex-plugin"]["command"] == (
        "codex plugin add liquilens-evidence@liquilens"
    )
    assert by_id["vscode-vsix"]["sourceCommit"] == (
        "aa1941b0d14152f7de43eb9acac41c10e68bc70d"
    )
    assert by_id["vscode-vsix"]["protectedMainCommit"] == (
        "f7bf6cd5b20c50e08ae3076ced5dea3456b49b24"
    )
    assert by_id["vscode-vsix"]["bytes"] == 16612
    assert by_id["vscode-vsix"]["sha256"] == (
        "ebc17ca1aa54d3e6c93494bb19f82df2f6460f314c40074a4f6b41d94170d6cf"
    )
    assert by_id["vscode-vsix"]["visualStudioMarketplaceStatus"] == (
        "publisher_auth_gated_not_listed"
    )
    assert by_id["vscode-vsix"]["openVsxStatus"] == (
        "publisher_auth_gated_not_listed"
    )
    assert by_id["oci"]["image"].endswith(
        "@sha256:9ec0646269357e971a67e88c8076c3c52c1561b094c1f2093ee19882a33294d1"
    )
    assert by_id["mcp-oci"]["image"].endswith(
        "@sha256:d55f69e55e579603ae8b510de76b1191047427a92569424a17729ea7f7e3e2f7"
    )
    assert by_id["mcp-oci"]["sourceCommit"] == (
        "25d2fbcf180c70816d9e60c3590854f887449c79"
    )
    assert "--network none --read-only" in by_id["mcp-oci"]["command"]
    assert by_id["devcontainer-feature"]["feature"].endswith(
        "@sha256:79ac17d7c3f91dc9360c6aa63cb9e4fa0081d5c81e1a1492b2198a8280f5b22d"
    )
    assert by_id["devcontainer-feature"]["sourceCommit"] == (
        "1c10ab6f88810bc323c75c73a9fe00288dd518a4"
    )
    assert by_id["devcontainer-feature"]["upstreamDirectory"] == {
        "status": "submitted_not_listed",
        "url": "https://github.com/devcontainers/devcontainers.github.io/pull/729",
    }
    assert "#sha256=" in by_id["uvx-immutable-wheel"]["command"]
    assert "/3c97b71093f8bca201e74bb5cc7ddbe50d9fa052" in (
        by_id["nix-flake"]["command"]
    )
    assert by_id["fdc3-evidence-inspector"]["upstreamDirectory"] == {
        "status": "submitted_not_listed",
        "url": "https://github.com/finos-labs/FDC3-App-Directory/pull/40",
    }
    assert by_id["openbb-extension"]["sourceCommit"] == (
        "05a77927496bf22c8bfdb7cbce2d6f43054911d0"
    )
    assert by_id["openbb-extension"]["interface"] == (
        "obb.liquilens.verify(data=...)"
    )
    assert "#subdirectory=integrations/openbb" in (
        by_id["openbb-extension"]["command"]
    )
    assert by_id["airflow-provider"]["sourceCommit"] == (
        "03d125b032aaec4a39cc10cc795ef48d4f605c68"
    )
    assert by_id["airflow-provider"]["protectedMainCommit"] == (
        "c4ccff491d48501379a49e6ea71494db27c42da1"
    )
    assert by_id["airflow-provider"]["sha256"] == (
        "aa91a2528ebf2e1583c379a08ce60f9aa52fc33d9d89da0bab9876d5720956bf"
    )
    assert "#sha256=" in by_id["airflow-provider"]["command"]

    serialized = json.dumps(channels).lower()
    for unsupported in ("conda", "schemastore"):
        assert unsupported not in serialized


def test_agent_and_product_metadata_are_projections_of_the_channel_catalog():
    catalog = json.loads(_read("protocol/catalog.json"))
    discovery = json.loads(_read(".well-known/ai-catalog.json"))
    entry = next(
        row for row in discovery["entries"]
        if row["identifier"] == "urn:air:liquilens.in:protocol:evidence-carrier"
    )
    assert entry["metadata"]["consumerChannelCatalog"] == (
        "https://liquilens.in/protocol/catalog.json"
    )
    assert entry["metadata"]["consumerChannelCount"] == len(
        catalog["consumerChannels"]
    )
    assert entry["metadata"]["consumerChannelStatuses"] == (
        "16 live; 1 live reference consumer; 1 fetched/rendered only"
    )

    product = json.loads(_read("product-card.json"))["access"]
    assert product["evidence_carrier_mcp_registry"] == (
        EXPECTED_CHANNELS["official-mcp-registry"][1]
    )
    assert product["evidence_carrier_cdn_module"] == (
        EXPECTED_CHANNELS["exact-sha-cdn-module"][1]
    )
    assert product["evidence_carrier_mcp_oci_image"].endswith(
        "@sha256:d55f69e55e579603ae8b510de76b1191047427a92569424a17729ea7f7e3e2f7"
    )
    assert product["evidence_carrier_devcontainer_feature"].endswith(
        "@sha256:79ac17d7c3f91dc9360c6aa63cb9e4fa0081d5c81e1a1492b2198a8280f5b22d"
    )
    assert product["evidence_carrier_agent_skill"] == (
        EXPECTED_CHANNELS["agent-skill"][1]
    )
    assert "skill-v0.15.0" in product["evidence_carrier_agent_skill_install"]
    assert product["evidence_carrier_agent_skill_directory"] == (
        "https://skills.sh/beepboop2025/liquilens-evidence-carrier/"
        "liquilens-evidence"
    )
    assert product["evidence_carrier_codex_plugin"] == (
        EXPECTED_CHANNELS["codex-plugin"][1]
    )
    assert "plugin-v0.14.1" in product["evidence_carrier_codex_plugin_install"]
    assert product["evidence_carrier_vscode_vsix"] == (
        EXPECTED_CHANNELS["vscode-vsix"][1]
    )
    assert product["evidence_carrier_vscode_vsix_sha256"] == (
        "ebc17ca1aa54d3e6c93494bb19f82df2f6460f314c40074a4f6b41d94170d6cf"
    )
    assert product["evidence_carrier_notebook"] == (
        EXPECTED_CHANNELS["research-notebook"][1]
    )
    assert product["evidence_carrier_binder"] == EXPECTED_CHANNELS["mybinder"][1]
    assert product["evidence_carrier_colab_view"] == EXPECTED_CHANNELS["colab"][1]
    assert "not executed" in product["evidence_carrier_colab_status"]
    assert product["evidence_carrier_fdc3_reference_consumer"] == (
        EXPECTED_CHANNELS["fdc3-evidence-inspector"][1]
    )
    assert product["evidence_carrier_openbb"] == (
        EXPECTED_CHANNELS["openbb-extension"][1]
    )
    assert "05a77927496bf22c8bfdb7cbce2d6f43054911d0" in (
        product["evidence_carrier_openbb_install"]
    )
    assert product["evidence_carrier_airflow_provider"] == (
        EXPECTED_CHANNELS["airflow-provider"][1]
    )
    assert "#sha256=aa91a252" in product["evidence_carrier_airflow_install"]


def test_protocol_page_has_accessible_matrix_and_conservative_json_ld():
    page = _read("protocol/index.html")
    assert '<section id="consumer-channels">' in page
    assert "<caption>Consumer paths verified through 2 September 2026.</caption>" in page
    assert page.count('scope="col"') == 4
    assert "Fetched / rendered only" in page
    assert "submitted, not listed" in page
    for channel_id in (
        "official-mcp-registry",
        "agent-skill",
        "codex-plugin",
        "vscode-vsix",
        "browser-verifier",
        "exact-sha-cdn-module",
        "mcp-oci",
        "devcontainer-feature",
        "research-notebook",
        "mybinder",
        "colab",
        "openbb-extension",
        "airflow-provider",
        "fdc3-evidence-inspector",
    ):
        assert EXPECTED_CHANNELS[channel_id][1] in page
    assert "brew install beepboop2025/tap/liquilens-evidence" in page
    assert "ghcr.io/beepboop2025/liquilens-evidence-carrier@sha256:" in page
    assert "nix run github:beepboop2025/liquilens-evidence-carrier/3c97b710" in page

    match = re.search(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
        page,
        flags=re.DOTALL,
    )
    assert match
    structured = json.loads(match.group(1))
    assert structured["@type"] == "SoftwareSourceCode"
    assert structured["version"] == "0.17.1"
    assert structured["codeRepository"] == (
        "https://github.com/beepboop2025/liquilens-evidence-carrier"
    )
    assert structured["license"] == "https://www.apache.org/licenses/LICENSE-2.0"
    assert structured["runtimePlatform"] == [
        "Python 3.11 or newer",
        "modern web browsers",
        "OCI on linux/amd64 and linux/arm64",
        "Nix on Linux and Darwin",
        "VS Code desktop, remote, web and Codespaces",
    ]
    assert "aggregateRating" not in structured
    assert "downloadCount" not in structured
