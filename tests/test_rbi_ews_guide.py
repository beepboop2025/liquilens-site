import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "guides" / "rbi-nbfc-early-warning-system" / "index.html"
CANONICAL = "https://liquilens.in/guides/rbi-nbfc-early-warning-system/"
RBI_SOURCES = {
    "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12704",
    "https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=58294",
    "https://www.rbi.org.in/Scripts/FAQView.aspx?Id=172",
}


def _page() -> str:
    return PAGE.read_text(encoding="utf-8")


def _schema() -> dict:
    match = re.search(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
        _page(),
        flags=re.S,
    )
    assert match
    return json.loads(match.group(1))


def test_guide_is_indexable_dated_and_analytics_enabled():
    page = _page()

    assert '<title>RBI Early Warning System for NBFCs: Validation Guide</title>' in page
    assert f'<link rel="canonical" href="{CANONICAL}">' in page
    assert '<meta name="robots" content="index, follow, max-image-preview:large">' in page
    assert '<time datetime="2026-08-21">21 August 2026</time>' in page
    assert "Content-Security-Policy" in page
    assert "static.cloudflareinsights.com/beacon.min.js" in page
    assert 'aria-label="On this page"' in page
    assert 'class="skip" href="#guide"' in page


def test_guide_uses_only_named_primary_rbi_sources():
    page = _page()
    external_urls = {
        url
        for url in re.findall(r'href="(https?://[^"]+)"', page)
        if not url.startswith("https://liquilens.in/")
    }

    assert external_urls == RBI_SOURCES
    assert all("rbi.org.in" in url for url in external_urls)
    assert "RBI/DOS/2024-25/120" in page
    assert "15 July 2024" in page
    assert "22 April 2025" in page
    assert "Chapter III" in page
    assert "Upper-Layer and Middle-Layer NBFCs" in page
    assert "₹500 crore and above" in page


def test_article_and_faq_schema_match_visible_content():
    page = _page()
    graph = _schema()["@graph"]
    article, faq = graph

    assert article["@type"] == "Article"
    assert article["mainEntityOfPage"] == CANONICAL
    assert article["datePublished"] == "2026-08-21"
    assert article["dateModified"] == "2026-08-21"
    assert set(article["citation"]) == RBI_SOURCES
    assert faq["@type"] == "FAQPage"
    assert len(faq["mainEntity"]) == 5
    for question in faq["mainEntity"]:
        assert question["name"] in page
        assert question["acceptedAnswer"]["text"] in page


def test_guide_keeps_regulatory_and_product_boundaries_explicit():
    page = _page()
    lower = page.lower()

    assert "in this rbi framework, ews means fraud-risk detection" in lower
    assert "an alert is a prompt for investigation, not a finding" in lower
    assert "not approved, endorsed or certified by rbi" in lower
    assert "does not establish regulatory compliance" in lower
    assert "not a complete fraud-monitoring solution" in lower
    assert "does not monitor an nbfc’s customer transactions" in lower
    assert "implementation interpretation" in lower
    assert "not an rbi-issued checklist" in lower
    assert "educational information, not legal or compliance advice" in lower
    assert "rbi-compliant" not in lower
    assert "guarantees compliance" not in lower


def test_guide_has_contextual_internal_paths_and_honest_campaign_attribution():
    page = _page()

    for path in (
        "/tools/ews-coverage-check/",
        "/research/",
        "/replay/",
    ):
        assert f'href="{path}"' in page

    assert (
        'href="/access/?utm_source=liquilens&amp;utm_medium=organic_guide&amp;'
        'utm_campaign=rbi_nbfc_ews&amp;utm_content=validation_guide"'
    ) in page


def test_guide_contains_a_substantial_validation_framework():
    page = _page()

    assert len(re.findall(r'class="check"', page)) == 8
    for concept in (
        "Data lineage and clocks",
        "Rule reproducibility",
        "Outcome usefulness",
        "Capacity and timeliness",
        "Stability and coverage",
        "Overrides and investigations",
        "Independent challenge",
        "Look-ahead leakage",
        "Revision leakage",
    ):
        assert concept in page


def test_guide_is_linked_from_public_discovery_and_navigation_surfaces():
    assert CANONICAL in (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    assert CANONICAL in (ROOT / "llms.txt").read_text(encoding="utf-8")
    for path in (ROOT / "index.html", ROOT / "use-cases" / "index.html"):
        assert "/guides/rbi-nbfc-early-warning-system/" in path.read_text(
            encoding="utf-8"
        )
