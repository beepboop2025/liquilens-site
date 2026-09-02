"""Current India market-DD claims preserve API clocks and authority."""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_market_dd_copy_does_not_promise_a_daily_or_live_refresh():
    surfaces = {
        path: read(path)
        for path in (
            "index.html",
            "replay/index.html",
            "llms.txt",
            "scripts/build_replay_pages.py",
        )
    }
    forbidden = (
        "daily market implied distance to default",
        "repriced daily from live equity prices",
        "market layer reprices daily",
        "Merton distance to default from live equity prices",
    )
    for path, surface in surfaces.items():
        lowered = surface.lower()
        for claim in forbidden:
            assert claim.lower() not in lowered, (path, claim)


def test_human_and_machine_copy_names_the_api_freshness_contract():
    for path in (
        "index.html",
        "replay/index.html",
        "llms.txt",
        "scripts/build_replay_pages.py",
    ):
        surface = read(path)
        for field in ("as_of", "stale", "tier_authority"):
            assert field in surface, (path, field)

    home = read("index.html")
    machine_copy = read("llms.txt")
    assert "A daily-capable price source is not proof of a daily refresh" in home
    assert "A daily-capable source is not proof" in machine_copy
    assert "absent fields leave freshness or authority unstated" in machine_copy
    assert "`observation_at`" in machine_copy
    assert "`retrieved_at`" in machine_copy
    assert "`liability_available_at`" in machine_copy


def test_homepage_renders_absent_market_governance_as_unstated():
    home = read("index.html")
    assert "m.stale === false" in home
    assert "m.tier_authority === false" in home
    assert "freshness unstated" in home
    assert "tier authority unstated" in home
    assert "m.future_dated === true" in home
    assert "m.authority_reason" in home
    assert "m.observation_at || m.as_of" in home
    assert "m.admission_authority === false" in home
    assert "public API response · clocks, freshness and tier authority" in home


def test_generated_and_checked_in_replay_copy_stay_aligned():
    script = ROOT / "scripts" / "build_replay_pages.py"
    spec = importlib.util.spec_from_file_location(
        "build_replay_pages_market_freshness", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    generated = module.complementarity_note({
        "pca_replay": {"failures": []},
        "funding_replay": {"failures": []},
    })
    checked_in = read("replay/index.html")
    shared = (
        "not source cadence, determine freshness; tier_authority states "
        "whether the reading may affect the tier."
    )
    assert shared in generated
    assert shared in checked_in
