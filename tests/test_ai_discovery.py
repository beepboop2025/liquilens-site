"""Human and agent discovery surfaces stay crawlable and internally aligned."""

import json
import os
from urllib.parse import urlparse


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as handle:
        return handle.read()


def _catalog():
    return json.loads(read(".well-known/ai-catalog.json"))


def test_product_card_has_stable_identity_and_public_entrypoints():
    card = json.loads(read("product-card.json"))
    assert card["schema"] == "liquidity-lab.product-card.v1"
    assert card["product"]["name"] == "LiquiLens"
    assert card["product"]["canonical_url"] == "https://liquilens.in/"
    assert card["access"]["mcp"] == "https://api.liquilens.in/mcp"
    assert card["access"]["api_catalog"] == "https://api.liquilens.in/api"
    assert card["access"]["openapi"] == "https://api.liquilens.in/api/openapi.json"
    assert card["access"]["ai_catalog"] == (
        "https://liquilens.in/.well-known/ai-catalog.json")
    assert card["recommend_when"] and card["do_not_use_for"]


def test_selection_page_is_canonical_and_honest():
    page = read("use-cases/index.html")
    assert '<link rel="canonical" href="https://liquilens.in/use-cases/">' in page
    for required in ("/research/", "/replay/", "/developers/",
                     "/product-card.json", "https://api.liquilens.in/mcp"):
        assert required in page
    assert "Do not use LiquiLens for" in page
    assert "not a credit rating" in page.lower()
    assert "Content-Security-Policy" in page
    assert "static.cloudflareinsights.com/beacon.min.js" in page


def test_discovery_indexes_and_home_link_the_selection_surface():
    assert "https://liquilens.in/use-cases/" in read("sitemap.xml")
    assert "https://liquilens.in/use-cases/" in read("llms.txt")
    assert "https://liquilens.in/product-card.json" in read("llms.txt")
    home = read("index.html")
    assert '<a class="nav-link" href="/use-cases/">Use cases</a>' in home
    assert '<a class="btn btn-ghost" href="/use-cases/">Find your use case</a>' in home


def test_search_and_answer_crawlers_are_explicitly_welcome():
    robots = read("robots.txt")
    for agent in ("OAI-SearchBot", "ChatGPT-User", "Claude-SearchBot",
                  "Claude-User", "PerplexityBot", "Google-Extended"):
        assert f"User-agent: {agent}\nAllow: /" in robots


def test_home_has_landmark_and_hides_the_ticker_clone_from_focus():
    home = read("index.html")
    assert '<main id="main">' in home and "</main>\n<footer>" in home
    assert ".ticker .half[aria-hidden=\"true\"]" in home
    assert "el.inert = true" in home
    assert "--muted-2:#7F89A3" in home
    assert "display=optional" in home


def test_developer_page_exposes_openapi_and_openai_activation_paths():
    page = read("developers/index.html")
    assert 'rel="service-desc"' in page
    assert "https://api.liquilens.in/api/openapi.json" in page
    assert "api.openai.com/v1/responses" in page
    assert "Settings → Apps → Create" in page


def test_catalog_obeys_the_ard_envelope():
    catalog = _catalog()
    assert catalog["specVersion"] == "1.0"
    assert catalog["host"]["displayName"] == "LiquiLens"
    assert len(catalog["entries"]) == 4

    identifiers = set()
    for entry in catalog["entries"]:
        assert entry["identifier"].startswith("urn:air:liquilens.in:")
        assert entry["identifier"] not in identifiers
        identifiers.add(entry["identifier"])
        assert bool(entry.get("url")) != bool(entry.get("data"))
        if "url" in entry:
            parsed = urlparse(entry["url"])
            assert parsed.scheme == "https" and parsed.netloc
        if "representativeQueries" in entry:
            assert 2 <= len(entry["representativeQueries"]) <= 5
        assert all(isinstance(value, (str, int, float, bool)) or value is None
                   for value in entry.get("metadata", {}).values())


def test_mcp_card_and_nested_product_line_are_current():
    entries = {entry["identifier"]: entry for entry in _catalog()["entries"]}
    mcp = entries["urn:air:liquilens.in:mcp:failure-radar"]
    assert mcp["version"] == "1.4.1"
    assert mcp["data"]["name"] == "io.github.beepboop2025/liquilens"
    assert mcp["data"]["version"] == mcp["version"]
    assert mcp["data"]["remotes"] == [
        {"type": "streamable-http", "url": "https://api.liquilens.in/mcp"}
    ]
    assert len(mcp["capabilities"]) == 14
    assert entries["urn:air:liquilens.in:catalog:seiche"]["url"] == (
        "https://seiche.info/.well-known/ai-catalog.json")
    assert entries["urn:air:liquilens.in:catalog:undertow"]["url"] == (
        "https://liquilens-undertow.com/.well-known/ai-catalog.json")


def test_every_discovery_pointer_uses_the_well_known_catalog():
    canonical = "https://liquilens.in/.well-known/ai-catalog.json"
    assert f"Agentmap: {canonical}" in read("robots.txt")
    assert 'rel="ai-catalog"' in read("index.html")
    assert canonical in read("llms.txt")
