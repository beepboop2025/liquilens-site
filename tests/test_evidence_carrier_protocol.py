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
    "protocol/fdc3/com.liquilens.evidence.schema.json": (
        "https://liquilens.in/protocol/fdc3/com.liquilens.evidence.schema.json",
        "9519474a4d0bf3a77834320d9aa43a88d5df96d49f691110154050212c7511b7",
    ),
    "protocol/openlineage/liquilens-evidence-facet.schema.json": (
        "https://liquilens.in/protocol/openlineage/liquilens-evidence-facet.schema.json",
        "e4c6035452d75be280a7b717f85da87319a078dbf5563e62ac3a3cb83486e9a5",
    ),
}
EXPECTED_CHANNELS = {
    "official-mcp-registry": (
        "live",
        "https://registry.modelcontextprotocol.io/v0/servers/"
        "io.github.beepboop2025%2Fliquilens-evidence-carrier/versions/0.14.0",
    ),
    "agent-skill": (
        "live",
        "https://github.com/beepboop2025/liquilens-evidence-carrier/tree/"
        "skill-v0.14.0/skills/liquilens-evidence",
    ),
    "codex-plugin": (
        "live",
        "https://github.com/beepboop2025/liquilens-evidence-carrier/tree/"
        "plugin-v0.14.1/.agents/plugins/plugins/liquilens-evidence",
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
        "download/v0.14.0/liquilens_evidence-0.14.0-py3-none-any.whl"
        "#sha256=f0162affab57307c8e20acf91dcefc33840f91e8cf9969a8d5ec8d8df860cd24",
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
    for relative, (canonical_url, digest) in EXPECTED.items():
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
        "8683351bd72c2a4b46d6913cd5e75c5536a410f1"
    )
    assert catalog["pythonDistributionSha256"] == (
        "f0162affab57307c8e20acf91dcefc33840f91e8cf9969a8d5ec8d8df860cd24"
    )
    assert catalog["mcpBundleSha256"] == (
        "e57e3039d7ae53b6feb3638dbc2f7ba413ff437e5c3a1b62172cad6f3b98e6ea"
    )
    assert catalog["browserVerifier"] == (
        "https://beepboop2025.github.io/liquilens-evidence-carrier/"
    )
    assert catalog["browserVerifierSource"].endswith(
        "/68e5eead7ad7a78e3c379820a499cf3c7c34048b/browser"
    )
    assert {
        row["url"]: row["sha256"] for row in catalog["artifacts"]
    } == {canonical_url: digest for canonical_url, digest in EXPECTED.values()}


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
        "50cfa5b4ce3f974fb0af43d9eaa75014c44f97de03dcec30abab1ac2e99fa301"
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
        "15 live; 1 live reference consumer; 1 fetched/rendered only"
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
    assert "skill-v0.14.0" in product["evidence_carrier_agent_skill_install"]
    assert product["evidence_carrier_agent_skill_directory"] == (
        "https://skills.sh/beepboop2025/liquilens-evidence-carrier/"
        "liquilens-evidence"
    )
    assert product["evidence_carrier_codex_plugin"] == (
        EXPECTED_CHANNELS["codex-plugin"][1]
    )
    assert "plugin-v0.14.1" in product["evidence_carrier_codex_plugin_install"]
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
    assert "<caption>Consumer paths verified on 24 August 2026.</caption>" in page
    assert page.count('scope="col"') == 4
    assert "Fetched / rendered only" in page
    assert "submitted, not listed" in page
    for channel_id in (
        "official-mcp-registry",
        "agent-skill",
        "codex-plugin",
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
    assert structured["version"] == "0.14.0"
    assert structured["codeRepository"] == (
        "https://github.com/beepboop2025/liquilens-evidence-carrier"
    )
    assert structured["license"] == "https://www.apache.org/licenses/LICENSE-2.0"
    assert structured["runtimePlatform"] == [
        "Python 3.11 or newer",
        "modern web browsers",
        "OCI on linux/amd64 and linux/arm64",
        "Nix on Linux and Darwin",
    ]
    assert "aggregateRating" not in structured
    assert "downloadCount" not in structured
