from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_homepage_describes_current_conformal_gate_authority():
    page = (ROOT / "index.html").read_text(encoding="utf-8")

    assert "The first has now crossed that product gate" not in page
    assert "conformal alarms with finite sample guarantees" not in page
    assert "CLOSED_REVALIDATION_REQUIRED" in page
    assert "no score or tier authority pending prospective revalidation" in page
    assert "linked machine gate is the current authority" in page

    machine = (ROOT / "llms.txt").read_text(encoding="utf-8")
    assert "Dated gate correction, 2026-08-10" in machine
    assert "diagnostic/display only" in machine
    assert "`tier_authority` is false" in machine


def test_ship_log_preserves_history_and_records_suspension():
    page = (ROOT / "ship-log" / "index.html").read_text(encoding="utf-8")

    assert '<span class="d">10 Aug</span><span class="tag red">CORRECTION</span>' in page
    assert "Conformal watchlist wiring is suspended" in page
    assert "15 July entry below is retained as historical release state" in page
    assert "CLOSED_REVALIDATION_REQUIRED" in page
    assert page.index('<span class="d">10 Aug</span>') < page.index(
        '<span class="d">15 Jul</span><span class="tag">RADAR</span>')
