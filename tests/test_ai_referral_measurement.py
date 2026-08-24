import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_ai_referral_classifier_is_bounded_and_property_free():
    script = read("ai-referral.js")
    for source in (
        "chatgpt",
        "claude",
        "copilot",
        "gemini",
        "other_ai",
        "perplexity",
    ):
        assert f'"{source}"' in script
    assert 'JSON.stringify({surface: "ai_referral", event: source})' in script
    assert "document.referrer" in script
    assert "referrer:" not in script
    assert "localStorage" not in script
    assert "sessionStorage" not in script
    assert "document.cookie" not in script
    assert "URLSearchParams" not in script


def test_ai_referral_measurement_is_loaded_on_primary_citation_landings():
    for path in (
        "index.html",
        "developers/index.html",
        "use-cases/index.html",
        "world-economy/index.html",
        "money-markets/index.html",
        "capital-markets/index.html",
        "china-economy/index.html",
        "replay/index.html",
    ):
        assert '<script src="/ai-referral.js" defer></script>' in read(path), path

    assert '<script src="/ai-referral.js" defer></script>' in read(
        "scripts/daily_article.py"
    )
    assert '<script src="/ai-referral.js" defer></script>' in read(
        "scripts/build_replay_pages.py"
    )


def test_every_ai_referral_landing_permits_the_bounded_event_endpoint():
    loaders = []
    for path in ROOT.rglob("*.html"):
        page = path.read_text(encoding="utf-8")
        if '<script src="/ai-referral.js" defer></script>' not in page:
            continue
        loaders.append(path)
        match = re.search(
            r'Content-Security-Policy" content="([^"]+)"', page
        )
        assert match, path.relative_to(ROOT)
        connect_src = next(
            (
                directive
                for directive in match.group(1).split(";")
                if directive.strip().startswith("connect-src ")
            ),
            "",
        )
        assert "https://api.liquilens.in" in connect_src, path.relative_to(ROOT)

    assert loaders, "no AI referral landing pages were found"


def test_replay_regeneration_preserves_new_discovery_and_article_routes():
    script = read("scripts/build_replay_pages.py")
    for route in (
        "/world-economy/",
        "/money-markets/",
        "/capital-markets/",
        "/china-economy/",
        "/tools/ews-coverage-check/",
        "/guides/rbi-nbfc-early-warning-system/",
        "/access/",
        "/access/sample/",
    ):
        assert f'("{route}",' in script
    assert "DAILY-ARTICLES:START" in script
    assert "DAILY-ARTICLES:END" in script


def test_privacy_copy_discloses_bounded_ai_attribution():
    privacy = read("privacy/index.html")
    assert "bounded source label" in privacy
    assert "raw referrer URL, query and prompt are never sent" in privacy
