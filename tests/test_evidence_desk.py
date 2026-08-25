"""The public Evidence Desk is discoverable and states its authority boundary."""

import json
import re
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_evidence_desk_has_static_answer_schema_and_visible_boundaries():
    page = read("evidence-desk/index.html")
    visible = re.sub(r"<[^>]+>", " ", page)

    assert '<link rel="canonical" href="https://liquilens.in/evidence-desk/">' in page
    assert page.count("<h1") == 1
    assert "Successful retrieval is not treated as complete" in visible
    assert "not investment advice" in visible.lower()
    assert "not performed" in visible.lower()
    assert "no account or api key" in visible.lower()
    assert "Content-Security-Policy" in page
    assert "frame-ancestors 'none'" in page
    assert 'type="module" src="/evidence-desk/app.mjs"' in page

    blocks = [
        json.loads(block)
        for block in re.findall(
            r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
            page,
            flags=re.S,
        )
    ]
    graph = next(block["@graph"] for block in blocks if "@graph" in block)
    app = next(node for node in graph if node.get("@type") == "WebApplication")
    assert app["offers"]["price"] == "0"
    assert app["offers"]["priceCurrency"] == "USD"
    assert next(block for block in blocks if block.get("@type") == "FAQPage")


def test_evidence_desk_is_linked_from_human_and_machine_discovery():
    canonical = "https://liquilens.in/evidence-desk/"
    assert canonical in read("sitemap.xml")
    assert canonical in read("llms.txt")
    assert canonical in json.loads(read("product-card.json"))["access"].values()
    catalog = {
        item["identifier"]: item
        for item in json.loads(read(".well-known/ai-catalog.json"))["entries"]
    }
    entry = catalog["urn:air:liquilens.in:app:financial-evidence-desk"]
    assert entry["url"] == canonical
    assert entry["metadata"] == {
        "access": "public-read-only",
        "authentication": "none",
        "price": "0 USD",
        "mcpEndpoint": "https://liquilens.in/mcp/financial-evidence",
        "financialAuthority": "none",
        "evidenceStatusSemantics": "not-evaluated-unless-explicit",
        "carrierVerification": "not-performed-unless-explicit",
    }
    mcp = catalog["urn:air:liquilens.in:mcp:financial-evidence"]
    assert mcp["data"]["version"] == "0.1.5"
    assert mcp["data"]["remotes"] == [
        {"type": "streamable-http", "url": "https://liquilens.in/mcp/financial-evidence"}
    ]
    assert mcp["metadata"]["statusSemantics"] == "transport_only"
    assert mcp["metadata"]["evidenceStatus"] == "not_evaluated"

    sitemap = ElementTree.fromstring(read("sitemap.xml"))
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = {
        node.findtext("sm:loc", namespaces=ns)
        for node in sitemap.findall("sm:url", ns)
    }
    assert canonical in urls
    home = read("index.html")
    assert '<a class="nav-link" href="/evidence-desk/">Evidence Desk</a>' in home
    assert "Use the Financial Evidence Desk" in home


def test_pricing_is_explicit_without_fabricating_a_paid_quote():
    page = read("pricing/index.html")
    markdown = read("pricing.md")
    for content in (page, markdown):
        assert "$0" in content
        assert "proposal" in content.lower()
        assert "mrinal@liquilens.in" in content
    assert "No public list price or implied quote" in page
    assert "has not published a list price" in markdown
    assert "https://liquilens.in/pricing/" in read("sitemap.xml")
    assert "https://liquilens.in/pricing/" in read("llms.txt")
