from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_handoff_pages_are_noindex_first_party_and_have_safe_fallbacks() -> None:
    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")

    for route in ("x", "telegram"):
        page = (ROOT / "go" / route / "index.html").read_text(encoding="utf-8")
        assert 'name="robots" content="noindex,nofollow,noarchive"' in page
        assert 'name="referrer" content="no-referrer"' in page
        assert f'script defer src="/go/{route}/app.js"' in page
        assert "connect-src https://api.liquilens.in" in page
        assert "frame-ancestors 'none'" in page
        assert "<noscript>" in page
        assert f"/go/{route}/" not in sitemap
        assert "cloudflareinsights" not in page.lower()

    x_page = (ROOT / "go" / "x" / "index.html").read_text(encoding="utf-8")
    assert 'href="https://x.com/intent/follow?screen_name=LiquiLens"' in x_page

    telegram_page = (ROOT / "go" / "telegram" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "https://t.me/liquilens_crypto_bot?start=x26_crypto_qa_market" in telegram_page
    assert 'property="og:title"' in telegram_page
    assert 'property="og:description"' in telegram_page
    assert 'property="og:image"' in telegram_page
    assert 'name="twitter:card" content="summary_large_image"' in telegram_page
    assert 'name="twitter:title"' in telegram_page
    assert 'name="twitter:description"' in telegram_page
    assert 'name="twitter:image"' in telegram_page


def test_x_bridge_has_finite_inputs_fixed_copy_and_safelisted_delivery() -> None:
    script = (ROOT / "go" / "x" / "app.js").read_text(encoding="utf-8")

    for source in (
        "nicegram",
        "adsgram",
        "telegram_ads",
        "x",
        "web",
        "organic",
        "crypto_channel",
        "operator_rehearsal",
    ):
        assert f"{source}: true" in script
    for topic in ("market", "movers", "funding", "defi", "pump", "rails", "paper"):
        assert f'{topic}: "' in script
    assert "getAll(name)" in script
    assert 'ACTIONS = Object.freeze({ follow: true, share: true })' in script
    assert 'new URL("https://x.com/intent/follow")' in script
    assert 'new URL("https://x.com/intent/tweet")' in script
    assert 'new URL("https://liquilens.in/go/telegram/")' in script
    assert "Nothing is posted automatically" in script
    assert '"Content-Type": "text/plain;charset=UTF-8"' in script
    assert "application/json" not in script
    assert 'JSON.stringify({ surface: "community_growth", event: eventName })' in script


def test_telegram_return_has_the_fleet_ref_contract_and_no_free_text() -> None:
    script = (ROOT / "go" / "telegram" / "app.js").read_text(encoding="utf-8")

    for source, short in (
        ("nicegram", "ng"),
        ("adsgram", "ag"),
        ("telegram_ads", "tg"),
        ("x", "xr"),
        ("web", "wb"),
        ("organic", "or"),
        ("crypto_channel", "ch"),
        ("operator_rehearsal", "qa"),
    ):
        assert f'{source}: "{short}"' in script
    for topic, intent in (
        ("market", "market"),
        ("movers", "movers"),
        ("funding", "derivatives"),
        ("defi", "defi"),
        ("pump", "pump"),
        ("rails", "rails"),
        ("paper", "paper"),
    ):
        assert f'{topic}: "{intent}"' in script
    assert '"x26_crypto_" + SHORT_SOURCE[source] + "_" + TOPIC_INTENT[topic]' in script
    assert 'deliver("x_return_telegram_" + source + "_" + topic + "_redirect")' in script
    assert '"Content-Type": "text/plain;charset=UTF-8"' in script
    assert "window.location.search" not in script.split("JSON.stringify", 1)[1]


def test_both_bridges_navigate_without_waiting_for_analytics() -> None:
    for route in ("x", "telegram"):
        script = (ROOT / "go" / route / "app.js").read_text(encoding="utf-8")
        assert "Promise.race" not in script
        assert "window.location.replace(destination)" in script
        assert "window.setTimeout(navigate, 700)" in script
        assert script.rfind("navigate();") > script.rfind("deliver(")
