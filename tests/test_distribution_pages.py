"""High-intent discovery pages are useful, bounded, and machine discoverable."""

import json
import re
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "use-cases/bank-counterparty-screening": "Bank Counterparty Risk Screening",
    "use-cases/model-risk-validation": "Early-Warning Model Risk Validation",
    "use-cases/ai-agent-financial-evidence": "Financial Evidence for AI Agents",
    "alternatives/manual-spreadsheets": "LiquiLens vs Manual Counterparty Spreadsheets",
    "alternatives/credit-ratings": "LiquiLens and Credit Ratings: Different Jobs",
    "alternatives/market-data-terminals": "LiquiLens vs a Market Data Terminal",
    "integrations/mcp": "LiquiLens MCP Integration",
    "integrations/rest-api": "LiquiLens REST API Integration",
    "integrations/evidence-carrier": "LiquiLens Evidence Carrier Integration",
}


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def json_ld(page: str) -> list[dict]:
    return [
        json.loads(block)
        for block in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', page, re.S
        )
    ]


def test_every_high_intent_page_has_one_answer_and_one_boundary():
    for slug, schema_name in PAGES.items():
        page = read(f"{slug}/index.html")
        canonical = f"https://liquilens.in/{slug}/"
        assert page.count("<h1") == 1, slug
        assert f'<link rel="canonical" href="{canonical}">' in page, slug
        assert '<link rel="stylesheet" href="/discovery-page.css">' in page, slug
        assert "Content-Security-Policy" in page, slug
        assert "frame-ancestors 'none'" in page, slug
        assert "connect-src https://cloudflareinsights.com" in page, slug
        assert "boundary" in page.lower(), slug
        assert "dateModified" in page and "2026-08-26" in page, slug
        blocks = json_ld(page)
        primary = blocks[0]
        assert primary["url"] == canonical, slug
        assert primary.get("name", primary.get("headline")) == schema_name, slug
        faq = next(block for block in blocks if block.get("@type") == "FAQPage")
        assert len(faq["mainEntity"]) == 2, slug
        for item in faq["mainEntity"]:
            assert item["name"] in page, slug
            assert item["acceptedAnswer"]["text"] in page, slug


def test_pages_are_in_sitemap_llms_and_product_card():
    sitemap = ElementTree.fromstring(read("sitemap.xml"))
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = {
        node.findtext("sm:loc", namespaces=ns)
        for node in sitemap.findall("sm:url", ns)
    }
    llms = read("llms.txt")
    card_urls = set(json.loads(read("product-card.json"))["access"].values())
    for slug in PAGES:
        canonical = f"https://liquilens.in/{slug}/"
        assert canonical in urls, slug
        assert canonical in llms, slug
        assert canonical in card_urls, slug


def test_category_comparisons_do_not_make_named_vendor_claims():
    for slug in (
        "alternatives/manual-spreadsheets",
        "alternatives/credit-ratings",
        "alternatives/market-data-terminals",
    ):
        page = read(f"{slug}/index.html")
        assert "Category comparison, not a claim about any named" in page
        for named_vendor in ("Bloomberg", "Refinitiv", "Moody's", "S&P", "Fitch"):
            assert named_vendor not in page


def test_media_kit_has_current_clean_assets_and_no_unproved_social_proof():
    page = read("media-kit/index.html")
    kit = json.loads(read("media-kit/media-kit.json"))
    assert kit["schema"] == "liquilens.media-kit.v1"
    assert kit["updated"] == "2026-08-26"
    assert kit["activation"] == {
        "evidence_desk": "https://liquilens.in/evidence-desk/",
        "price": "0 USD",
        "authentication": "none",
        "pricing": "https://liquilens.in/pricing/",
    }
    for asset in (
        "media-kit/assets/evidence-desk-desktop.png",
        "media-kit/assets/evidence-desk-mobile.png",
        "media-kit/assets/pricing-desktop.png",
    ):
        assert (ROOT / asset).stat().st_size > 50_000
        assert f'/{asset}' in page
    assert "localhost" not in page.lower()
    assert "customer count" not in kit["product"]["description"].lower()
    assert "https://liquilens.in/media-kit/" in read("sitemap.xml")
    assert "https://liquilens.in/media-kit/" in read("llms.txt")
    assert "style-src 'self' 'unsafe-inline'" in page
    assert "connect-src https://cloudflareinsights.com" in page


def test_root_and_developer_pages_advertise_both_article_feeds():
    for path in ("index.html", "developers/index.html"):
        page = read(path)
        assert 'type="application/feed+json" href="/articles/feed.json"' in page
        assert 'type="application/atom+xml" href="/articles/feed.xml"' in page
