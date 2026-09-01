"""Exercise the homepage's market renderer against authority edge cases."""

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _render(payload: dict) -> str:
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    start = home.index("    function marketState(m){")
    end = home.index("\n\n    function marketLayerState", start)
    function_source = home[start:end]
    script = "\n".join((
        "function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\\\"/g,'&quot;').replace(/'/g,'&#39;'); }",
        "function fmtDate(s){ return String(s); }",
        function_source,
        f"process.stdout.write(marketState({json.dumps(payload)}));",
    ))
    return subprocess.run(
        ["node", "-e", script], check=True, capture_output=True, text=True,
        cwd=ROOT,
    ).stdout


def test_renderer_prints_fresh_authoritative_value():
    rendered = _render({
        "dd": 1.234, "observation_at": "2026-09-01", "stale": False,
        "clock_authority": True, "knowledge_authority": True,
        "admission_authority": True, "tier_authority": True,
    })
    assert rendered.startswith("1.23")
    assert "observed 2026-09-01" in rendered
    assert "within API freshness policy" in rendered


def test_renderer_explains_stale_and_future_uncomputed_values():
    stale = _render({
        "dd": 0.9, "observation_at": "2026-08-01", "stale": True,
        "clock_authority": False, "admission_authority": False,
        "tier_authority": False, "authority_reason": "observation too old",
    })
    assert "stale" in stale and "context only" in stale

    future = _render({
        "not_computed": "market observation is later than the evaluation date",
        "observation_at": "2026-09-02", "future_dated": True, "stale": False,
        "clock_authority": False, "tier_authority": False,
    })
    assert future.startswith("n/a")
    assert "future-dated" in future
    assert "later than the evaluation date" in future


def test_renderer_keeps_legacy_and_unlisted_missingness_explicit():
    legacy = _render({"not_computed": "missing market observation clock"})
    assert legacy.startswith("n/a")
    assert "observation date unstated" in legacy
    assert "freshness unstated" in legacy
    assert "tier authority unstated" in legacy

    unlisted = _render({
        "not_computed": "unlisted — no traded equity to imply a default distance from",
        "tier_authority": False,
    })
    assert "unlisted" in unlisted and "context only" in unlisted
