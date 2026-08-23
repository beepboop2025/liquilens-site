from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_x_bridge_is_noindex_first_party_and_has_a_no_script_fallback() -> None:
    page = (ROOT / "go" / "x" / "index.html").read_text(encoding="utf-8")

    assert 'name="robots" content="noindex,nofollow,noarchive"' in page
    assert 'name="referrer" content="no-referrer"' in page
    assert 'script defer src="/go/x/app.js"' in page
    assert 'href="https://x.com/LiquiLens"' in page
    assert "api.liquilens.in" in page
    assert "<noscript>" in page
    assert "/go/x/" not in (ROOT / "sitemap.xml").read_text(encoding="utf-8")


def test_x_bridge_maps_input_to_a_finite_property_free_event_enum() -> None:
    script = (ROOT / "go" / "x" / "app.js").read_text(encoding="utf-8")

    for source in (
        "nicegram", "adsgram", "telegram_ads", "x_return", "web",
        "organic", "crypto_channel",
    ):
        assert f'"{source}"' in script
    assert "operator_rehearsal: null" in script
    assert 'surface: "community_growth", event: eventName' in script
    assert "window.location.search" not in script.split("JSON.stringify", 1)[1]
    assert 'action === "share" ? "share_composer" : "profile"' in script


def test_x_bridge_redirect_is_fast_but_never_depends_on_analytics() -> None:
    script = (ROOT / "go" / "x" / "app.js").read_text(encoding="utf-8")

    assert 'PROFILE = "https://x.com/LiquiLens"' in script
    assert 'new URL("https://twitter.com/intent/tweet")' in script
    assert "https://t.me/liquilens_crypto_bot?start=x26_crypto_share_market" in script
    assert "Nothing is posted automatically" in script
    assert "Promise.race" in script
    assert "window.location.replace(destination)" in script
    assert "window.setTimeout(navigate, 700)" in script
