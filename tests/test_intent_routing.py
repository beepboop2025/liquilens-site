"""Intent pages remain useful, bounded and machine-discoverable."""

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
SKILL_REVISION = "34549a5bcc2a42c7760c04c95bd449f1d10a18fc"
SKILL_DIRECTORY = (
    "https://github.com/beepboop2025/financial-evidence-skills/"
    "tree/main/financial-evidence"
)
SKILL_RAW_URL = (
    "https://raw.githubusercontent.com/beepboop2025/"
    f"financial-evidence-skills/{SKILL_REVISION}/"
    "financial-evidence/SKILL.md"
)
ROUTES = {
    "money-markets": ("Seiche", "liquilens_money_markets"),
    "capital-markets": ("Undertow", "liquilens_capital_markets"),
    "china-economy": ("Palimpsest", "liquilens_china_economy"),
}


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def json_ld_blocks(page: str) -> list[dict]:
    return [
        json.loads(match)
        for match in re.findall(
            r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
            page,
            flags=re.S,
        )
    ]


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def visible_text(page: str) -> str:
    parser = _VisibleText()
    parser.feed(page)
    return " ".join(" ".join(parser.parts).split())


def test_intent_pages_have_canonical_schema_faq_and_visible_boundaries():
    for slug, (primary, _) in ROUTES.items():
        page = read(f"{slug}/index.html")
        visible = visible_text(page)
        canonical = f"https://liquilens.in/{slug}/"
        assert f'<link rel="canonical" href="{canonical}">' in page
        assert '<link rel="stylesheet" href="/intent-router.css">' in page
        assert '<script src="/ai-referral.js" defer></script>' in page
        assert "static.cloudflareinsights.com/beacon.min.js" in page
        assert "43b422e63bb44fb5975c7bb39bd0ba24" in page

        blocks = json_ld_blocks(page)
        graph = next(block["@graph"] for block in blocks if "@graph" in block)
        webpage = next(node for node in graph if node.get("@type") == "WebPage")
        routes = next(node for node in graph if node.get("@type") == "ItemList")
        assert webpage["url"] == canonical
        assert webpage["dateModified"] == "2026-08-24"
        assert routes["numberOfItems"] == 4
        assert primary in routes["itemListElement"][0]["name"]
        assert {"Seiche", "LiquiLens", "Undertow", "Palimpsest"} == {
            item["name"].split(" — ")[-1]
            for item in routes["itemListElement"]
        }

        faq = next(block for block in blocks if block.get("@type") == "FAQPage")
        assert len(faq["mainEntity"]) == 4
        for item in faq["mainEntity"]:
            assert item["name"] in visible
            assert item["acceptedAnswer"]["text"] in visible

        assert page.count('class="citation') == 4
        assert "not investment advice" in visible.lower()
        assert "financial authority" in visible.lower()


def test_each_intent_router_has_distinct_bounded_cta_attribution():
    sources = set()
    for slug, (_, utm_source) in ROUTES.items():
        page = read(f"{slug}/index.html")
        source = f"utm_source={utm_source}"
        assert page.count(source) >= 4
        assert page.count("utm_medium=intent_router") >= 4
        assert page.count("utm_campaign=universal_financial_evidence") >= 4
        assert len(set(re.findall(r"utm_content=([a-z_]+)", page))) >= 4
        sources.add(source)
    assert len(sources) == len(ROUTES)


def test_intent_routes_are_discoverable_across_machine_surfaces():
    sitemap = ElementTree.fromstring(read("sitemap.xml"))
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    sitemap_urls = {
        node.findtext("sm:loc", namespaces=namespace)
        for node in sitemap.findall("sm:url", namespace)
    }
    card = json.loads(read("product-card.json"))
    catalog = {
        entry["identifier"]: entry
        for entry in json.loads(read(".well-known/ai-catalog.json"))["entries"]
    }

    for slug in ROUTES:
        canonical = f"https://liquilens.in/{slug}/"
        assert canonical in sitemap_urls
        assert canonical in read("llms.txt")
        assert canonical in card["access"].values()
        assert catalog[f"urn:air:liquilens.in:intent:{slug}"]["url"] == canonical
        metadata = catalog[f"urn:air:liquilens.in:intent:{slug}"]["metadata"]
        assert "primaryEvidenceRoute" in metadata
        assert metadata["financialAuthority"] == "none"


def test_existing_access_surface_and_pinned_agent_skill_are_discoverable():
    for path in (
        "llms.txt",
        "product-card.json",
        "world-economy/index.html",
        "money-markets/index.html",
        "capital-markets/index.html",
        "china-economy/index.html",
    ):
        assert SKILL_DIRECTORY in read(path), path
        assert "access.md" not in read(path), path

    catalog = {
        entry["identifier"]: entry
        for entry in json.loads(read(".well-known/ai-catalog.json"))["entries"]
    }
    skill = catalog["urn:air:liquilens.in:skill:financial-evidence"]
    assert skill["url"] == SKILL_RAW_URL
    assert skill["version"] == SKILL_REVISION
    assert skill["metadata"]["canonicalDirectory"] == SKILL_DIRECTORY
    assert skill["metadata"]["contentSha256"].startswith("sha256:")

    card = json.loads(read("product-card.json"))
    assert "Paid named-list software" in card["product"]["access_model"]
    assert card["access"]["named_list"] == "https://liquilens.in/access/"
