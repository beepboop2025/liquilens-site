"""RFC 9727 discovery stays exact, useful, and honest about live surfaces."""

import json
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads(
    (ROOT / ".well-known/api-catalog.json").read_text(encoding="utf-8")
)


def test_api_catalog_uses_linkset_json_and_unique_https_anchors():
    assert set(CATALOG) == {"linkset"}
    linkset = CATALOG["linkset"]
    assert len(linkset) == 19
    anchors = [item["anchor"] for item in linkset]
    assert len(anchors) == len(set(anchors))
    assert all(urlparse(anchor).scheme == "https" for anchor in anchors)

    for item in linkset:
        assert set(item) <= {
            "anchor",
            "api-catalog",
            "service-desc",
            "service-doc",
            "service-meta",
            "status",
        }
        assert (
            item.get("api-catalog")
            or item.get("service-doc")
            or item.get("service-meta")
        )
        for relation, links in item.items():
            if relation == "anchor":
                continue
            assert links and isinstance(links, list)
            for link in links:
                assert set(link) <= {"href", "type", "hreflang", "title"}
                assert urlparse(link["href"]).scheme == "https"
                assert link.get("type")


def test_catalog_covers_every_verified_remote_mcp_boundary():
    anchors = {item["anchor"] for item in CATALOG["linkset"]}
    assert {
        "https://api.liquilens.in/mcp",
        "https://liquilens.in/mcp/financial-evidence",
        "https://trade-safety.liquilens.in/mcp",
        "https://api.seiche.info/mcp",
        "https://api.seiche.info/undertow/mcp",
        "https://api.seiche.info/riptide/mcp",
        "https://api.seiche.info/palimpsest/mcp",
        "https://myquantdoesntspeakenglish.com/mcp",
        "https://myquant-app.vercel.app/mcp",
        "https://narcoscope.com/mcp",
    } <= anchors


def test_live_product_catalogs_use_the_registered_federation_relation():
    by_anchor = {item["anchor"]: item for item in CATALOG["linkset"]}
    federation = by_anchor["https://liquilens.in/.well-known/api-catalog"]
    expected = {
        "https://liquilens-undertow.com/.well-known/api-catalog",
        "https://api.seiche.info/riptide/.well-known/api-catalog",
        "https://narcoscope.com/.well-known/api-catalog",
    }
    assert {link["href"] for link in federation["api-catalog"]} == expected
    assert all(
        link["type"] == "application/linkset+json"
        for link in federation["api-catalog"]
    )

    for anchor in (
        "https://api.seiche.info/riptide/",
        "https://api.seiche.info/riptide/mcp",
        "https://narcoscope.com/api/v1",
        "https://narcoscope.com/mcp",
    ):
        assert expected.isdisjoint(
            {link["href"] for link in by_anchor[anchor].get("service-meta", [])}
        )


def test_openapi_is_only_advertised_for_real_rest_descriptions():
    by_anchor = {item["anchor"]: item for item in CATALOG["linkset"]}
    expected_rest = {
        "https://api.liquilens.in/api": (
            "https://api.liquilens.in/api/openapi.json",
            "application/json",
        ),
        "https://api.seiche.info/api": (
            "https://api.seiche.info/api/openapi.json",
            "application/json",
        ),
        "https://api.seiche.info/undertow/x402/": (
            "https://api.seiche.info/undertow/x402/openapi.json",
            "application/json",
        ),
        "https://api.seiche.info/riptide/": (
            "https://api.seiche.info/riptide/openapi.json",
            "application/json",
        ),
        "https://myquantdoesntspeakenglish.com/api/v1": (
            "https://myquantdoesntspeakenglish.com/openapi.json",
            "application/json",
        ),
        "https://myquant-app.vercel.app/api/v1": (
            "https://myquant-app.vercel.app/openapi.json",
            "application/vnd.oai.openapi+json",
        ),
        "https://narcoscope.com/api/v1": (
            "https://narcoscope.com/openapi.json",
            "application/json",
        ),
        "https://trade-safety.liquilens.in/v1/check": (
            "https://trade-safety.liquilens.in/openapi.json",
            "application/json",
        ),
    }
    for anchor, (document, media_type) in expected_rest.items():
        assert by_anchor[anchor]["service-desc"] == [
            {
                "href": document,
                "type": media_type,
            }
        ]
    assert "service-desc" not in by_anchor[
        "https://api.seiche.info/palimpsest/mcp"
    ]


def test_catalog_never_promotes_planned_or_private_surfaces_to_live():
    serialized = json.dumps(CATALOG).lower()
    assert "drug-price-observatory.vercel.app" not in serialized
    assert "scamshield" not in serialized
    assert "/.well-known/mcp.json" not in serialized
    assert "agent-card" not in serialized
    assert "a2a" not in serialized
