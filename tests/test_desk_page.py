"""The public intelligence desk exposes all four evidence lanes safely."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "desk" / "index.html").read_text()
JS = (ROOT / "desk" / "app.js").read_text()


def test_desk_names_and_links_all_four_products():
    for label in ("LiquiLens", "Seiche", "Palimpsest", "LiquiLens—Undertow"):
        assert label in HTML
    for endpoint in (
        "https://api.liquilens.in/api/experimental/v1/desk/bits",
        "https://seiche.info/dispatches/news.json",
        "https://palimpsest.info/readings/newsroom-latest.json",
        "https://api.seiche.info/undertow/dispatch.json",
        "https://api.seiche.info/undertow/sealed_calls.json",
    ):
        assert endpoint in HTML + JS


def test_csp_allows_only_the_named_public_feed_origins():
    csp = next(line for line in HTML.splitlines() if "Content-Security-Policy" in line)
    for origin in ("https://api.liquilens.in", "https://seiche.info",
                   "https://palimpsest.info", "https://liquilens-undertow.com"):
        assert origin in csp
    assert "'unsafe-eval'" not in csp


def test_renderer_uses_text_nodes_and_constrains_outbound_hosts():
    assert ".innerHTML" not in JS
    assert "textContent" in JS and "replaceChildren" in JS
    assert "ALLOWED_HOSTS" in JS
    assert 'url.protocol === "https:"' in JS
    assert ".slice(0, 24)" not in JS  # every supplied qualifying item reaches the wire
    assert "liquilens-undertow:" in JS  # legacy retained letters still receive unique IDs
    assert "leadEligible" in JS  # a missing/stale finding remains visible but does not auto-lead


def test_page_states_originality_and_missingness_rules():
    for phrase in ("No rewritten press releases", "Longitudinal delta",
                   "Evidence braid", "Revision or absence", "Forward adjudication"):
        assert phrase in HTML
    assert "No calm state inferred" in JS
    assert "CONTEXT ONLY" in HTML


def test_home_and_sitemap_discover_the_desk():
    assert '<a class="nav-link" href="/desk/">Intelligence desk</a>' in (ROOT / "index.html").read_text()
    assert "https://liquilens.in/desk/" in (ROOT / "sitemap.xml").read_text()
