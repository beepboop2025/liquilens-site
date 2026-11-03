"""Regression checks for the homepage's progressive motion layer."""

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import india_record_copy  # noqa: E402


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_product_motion_is_bounded_and_respects_reduced_motion():
    home = read("index.html")
    css = read("research-ui/research.css")
    flow = read("research-ui/flow.js")
    assert 'id="main"' in home
    assert '<research-flow product="liquilens">' in home
    assert 'Illustration connecting institutions, funding and market liquidity.' in flow
    assert 'prefers-reduced-motion:reduce' in css
    assert 'animation: none !important' in css
    assert 'Pause motion' in flow and 'aria-pressed' in flow
    assert 'paused||media.matches' in flow
    assert 'animation-play-state:paused' in css


def test_warning_horizon_is_exact_and_progressively_enhanced():
    home = read("index.html")
    css = read("experience.css")

    chapters = re.findall(
        r'class="tminus__chapter[^"]*" data-month="([^"]+)" '
        r'data-progress="([^"]+)" data-phase="([^"]+)"',
        home,
    )
    # The cohort-median chapter is the served India median lead, rendered by
    # scripts/india_record_copy.py from the captured evidence record.
    india = india_record_copy.figures(india_record_copy.load("india-evidence.json"),
                                      india_record_copy.load("india-alert-modes.json"))
    assert [chapter[0] for chapter in chapters] == ["41", "27", india["lead"], "17", "8", "0"]
    assert [chapter[1] for chapter in chapters] == [
        "0", ".341", india["lead_progress"], ".585", ".805", "1"]
    assert f'style="left:{india["lead_mark"]}%"' in home
    assert home.count('class="tminus__mark') == 6
    assert "Math.round(m)" not in home
    assert "tmCap" not in home
    assert "sec.setAttribute('data-enhanced', 'true')" in read("evidence-library.js")
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
    assert 'src="/product-home.js"' in home
    assert 'src="/evidence-library.js"' not in home
    assert "library?.addEventListener('toggle', loadEvidence)" in read("product-home.js")
