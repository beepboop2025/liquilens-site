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
    assert card["access"]["pilot"] == "https://liquilens.in/pilot/"
    assert card["access"]["cli"] == (
        "https://github.com/beepboop2025/liquilens-cli")
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
    assert "npx --yes github:beepboop2025/liquilens-cli" in page
    assert 'data-event="cli_install_copied"' in page
    assert "https://api.liquilens.in/api/events" in read("developers/app.js")


def test_paid_pilot_has_a_bounded_offer_and_replaces_the_401_as_primary_cta():
    pilot = read("pilot/index.html")
    for required in ("₹2.5 lakh", "₹12 lakh/yr", "six weeks",
                     "credited toward", "Runs in your environment",
                     "Alerts per catch"):
        assert required.lower() in pilot.lower()
    assert "mailto:mrinal@liquilens.in" in pilot
    assert 'data-event="email_clicked"' in pilot
    assert "https://api.liquilens.in/api/events" in read("pilot/app.js")
    assert "within 30 days" not in pilot

    home = read("index.html")
    assert 'data-funnel="pilot_cta_clicked" href="/pilot/"' in home
    assert "Design partner pilots are free" not in home
    assert "https://liquilens.in/pilot/" in read("sitemap.xml")
    assert "https://liquilens.in/pilot/" in read("llms.txt")

    for surface in ("index.html", "about/index.html", "pilot/index.html"):
        copy = read(surface)
        assert "₹2.5 lakh" in copy
        assert "₹12 lakh" in copy

    machine_copy = read("llms.txt")
    assert "INR 250,000" in machine_copy
    assert "INR 1,200,000 per year" in machine_copy


def test_aggregate_funnel_events_are_documented_as_property_free():
    privacy = read("privacy/index.html")
    assert "short allow-listed event name" in privacy
    assert "no email address, free text, device ID or user property" in privacy
    assert "cli_install_copied" in privacy


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
