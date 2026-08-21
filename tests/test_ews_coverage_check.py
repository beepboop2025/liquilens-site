import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "tools" / "ews-coverage-check" / "index.html"
APP = ROOT / "tools" / "ews-coverage-check" / "app.js"
CANONICAL = "https://liquilens.in/tools/ews-coverage-check/"


def test_coverage_check_is_indexable_useful_and_bounded():
    page = PAGE.read_text(encoding="utf-8")

    assert f'<link rel="canonical" href="{CANONICAL}">' in page
    assert "Bank Early-Warning System Checklist" in page
    assert len(re.findall(r'name="control"', page)) == 12
    assert "not a credit rating" in page.lower()
    assert "prediction of failure" in page.lower()
    assert "selections stay in this browser" in page.lower()
    assert '<input type="email"' not in page
    assert "Content-Security-Policy" in page
    assert "static.cloudflareinsights.com/beacon.min.js" in page


def test_coverage_check_schema_matches_visible_copy():
    page = PAGE.read_text(encoding="utf-8")
    match = re.search(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
        page,
        flags=re.S,
    )
    assert match
    schema = json.loads(match.group(1))
    graph = schema["@graph"]
    assert graph[0]["@type"] == "WebApplication"
    assert graph[0]["url"] == CANONICAL
    assert graph[0]["isAccessibleForFree"] is True
    assert graph[1]["@type"] == "FAQPage"
    assert len(graph[1]["mainEntity"]) == 3
    for question in graph[1]["mainEntity"]:
        assert question["name"] in page
        assert question["acceptedAnswer"]["text"] in page


def test_coverage_check_is_private_by_design_and_has_bounded_events():
    app = APP.read_text(encoding="utf-8")

    assert 'surface: "coverage_check"' in app
    for event in (
        "tool_viewed",
        "report_copied",
        "report_printed",
        "access_cta_clicked",
    ):
        assert f'track("{event}")' in app
    assert "localStorage" not in app
    assert "sessionStorage" not in app
    assert "URLSearchParams" not in app
    assert "email" not in app.lower()
    assert "JSON.stringify({surface: \"coverage_check\", event: eventName})" in app


def test_coverage_check_is_linked_from_discovery_surfaces():
    assert CANONICAL in (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    assert CANONICAL in (ROOT / "llms.txt").read_text(encoding="utf-8")
    assert "/tools/ews-coverage-check/" in (
        ROOT / "use-cases" / "index.html"
    ).read_text(encoding="utf-8")
