"""The public Evidence Carrier endpoints remain exact, licensed, and discoverable."""

import hashlib
import json
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
    assert {
        row["url"]: row["sha256"] for row in catalog["artifacts"]
    } == {canonical_url: digest for canonical_url, digest in EXPECTED.values()}


def test_human_and_agent_discovery_surfaces_link_the_protocol():
    page = _read("protocol/index.html")
    assert '<link rel="canonical" href="https://liquilens.in/protocol/">' in page
    assert page.count("<h1") == 1
    assert "Financial authority: none" in page
    assert "Apache-2.0" in page
    assert "https://liquilens.in/protocol/" in _read("sitemap.xml")
    assert "https://liquilens.in/protocol/catalog.json" in _read("llms.txt")

    discovery = json.loads(_read(".well-known/ai-catalog.json"))
    entry = next(
        row for row in discovery["entries"]
        if row["identifier"] == "urn:air:liquilens.in:protocol:evidence-carrier"
    )
    assert entry["url"] == "https://liquilens.in/protocol/catalog.json"
    assert entry["metadata"]["financialAuthority"] == "none"

    product = json.loads(_read("product-card.json"))
    assert product["access"]["evidence_carrier"] == (
        "https://liquilens.in/protocol/"
    )
    assert product["access"]["evidence_carrier_catalog"] == (
        "https://liquilens.in/protocol/catalog.json"
    )
