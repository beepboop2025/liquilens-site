"""Regression checks for the homepage's progressive motion layer."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_sticky_surfaces_share_a_safe_measured_chrome_offset():
    home = read("index.html")
    css = read("experience.css")
    js = read("experience.js")

    body_rule = re.search(r"body\s*\{(?P<body>.*?)\}", home, re.S)
    assert body_rule
    assert "overflow-x:clip" in body_rule.group("body")
    assert "overflow-x:hidden" not in body_rule.group("body")
    assert "overflow-x: clip;" in css
    assert "--site-chrome-height" in css
    assert "top: var(--site-chrome-height);" in css
    assert "height: calc(100svh - var(--site-chrome-height));" in css
    assert "function siteChrome()" in js
    assert "ResizeObserver" in js


def test_warning_horizon_is_exact_and_progressively_enhanced():
    home = read("index.html")
    css = read("experience.css")

    chapters = re.findall(
        r'class="tminus__chapter[^"]*" data-month="([^"]+)" '
        r'data-progress="([^"]+)" data-phase="([^"]+)"',
        home,
    )
    assert [chapter[0] for chapter in chapters] == ["41", "27", "21.5", "17", "8", "0"]
    assert [chapter[1] for chapter in chapters] == ["0", ".341", ".476", ".585", ".805", "1"]
    assert home.count('class="tminus__mark') == 6
    assert "Math.round(m)" not in home
    assert "tmCap" not in home
    assert "sec.setAttribute('data-enhanced', 'true')" in home
    assert ".tminus[data-enhanced] .tminus__stage" in css
    assert ".tminus[data-enhanced] .tminus__chapter" in css


def test_motion_never_mutates_audited_totals_and_has_accessible_fallbacks():
    home = read("index.html")
    css = read("experience.css")
    js = read("experience.js")

    assert "count-up numbers on reveal" not in home
    assert "function atlasCounters()" not in js
    assert 'id="lcrOut" role="status" aria-live="polite"' in home
    assert ".badge.st-alarm" in css
    assert "animation: none !important;" in css
    assert "revealSelection(initial, false);" in js
    assert "function motionGovernor()" in js
    assert "/experience.css?v=20260809e" in home
    assert "/experience.js?v=20260809e" in home
