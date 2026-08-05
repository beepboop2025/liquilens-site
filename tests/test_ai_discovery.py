import json
import os


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as handle:
        return handle.read()


def test_product_card_has_stable_identity_and_public_entrypoints():
    card = json.loads(read("product-card.json"))
    assert card["schema"] == "liquidity-lab.product-card.v1"
    assert card["product"]["name"] == "LiquiLens"
    assert card["product"]["canonical_url"] == "https://liquilens.in/"
    assert card["access"]["mcp"] == "https://api.liquilens.in/mcp"
    assert card["access"]["api_catalog"] == "https://api.liquilens.in/api"
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
    assert 'href="/use-cases/"' in read("index.html")


def test_search_and_answer_crawlers_are_explicitly_welcome():
    robots = read("robots.txt")
    for agent in ("OAI-SearchBot", "ChatGPT-User", "Claude-SearchBot",
                  "Claude-User", "PerplexityBot", "Google-Extended"):
        assert f"User-agent: {agent}\nAllow: /" in robots
