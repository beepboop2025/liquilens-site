"""Reviewed investigations must remain discoverable, visual and evidence-bounded."""

from __future__ import annotations

import json
import importlib.util
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT / "investigations" / "index.html"
STORY = ROOT / "investigations" / "the-5-64x-private-credit-concentration" / "index.html"


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


def test_investigation_has_article_metadata_and_evidence_sections():
    page = STORY.read_text()
    for required in (
        'rel="canonical"',
        'property="og:image"',
        '"@type":"AnalysisNewsArticle"',
        "THE STRONGEST COUNTER-CASE",
        "WHAT CHANGES OUR MIND",
        "Sources and method",
        "not evidence of loss or distress",
        "not investment advice",
    ):
        assert required in page


def test_network_links_connect_all_three_editorial_desks():
    for page in (HUB.read_text(), STORY.read_text()):
        assert "https://seiche.info/investigations/" in page
        assert "https://liquilens-undertow.com/investigations/" in page


def test_manifest_and_share_assets_are_publication_ready():
    manifest = json.loads((ROOT / "investigations" / "index.json").read_text())
    assert manifest["publication_policy"] == "reviewed_longform"
    article = manifest["articles"][0]
    assert article["editorial_status"] == "reviewed"
    assert article["article_type"] == "investigation"
    assert article["publication_status"] == "PUBLISHED"
    assert article["canonical_url"].startswith("https://liquilens.in/investigations/")
    assert article["dek"] and article["limitations"]
    assert article["evidence_status"] == "CURRENT_AMENDED_CONSTRUCTION_PIT"
    assert article["clocks"]["event_time"] <= article["clocks"]["knowledge_time"]
    asset_dir = STORY.parent
    assert _png_size(asset_dir / "ndfi-ranking.png") == (1600, 900)
    assert _png_size(asset_dir / "share.png") == (1200, 630)


def test_investigation_is_reachable_from_human_and_machine_navigation():
    home = (ROOT / "index.html").read_text()
    sitemap = (ROOT / "sitemap.xml").read_text()
    llms = (ROOT / "llms.txt").read_text()
    assert 'href="/investigations/"' in home
    assert "https://liquilens.in/investigations/" in sitemap
    assert "the-5-64x-private-credit-concentration" in sitemap
    assert "Reviewed investigations" in llms


def test_replay_rebuild_keeps_investigation_routes_in_the_sitemap():
    script = ROOT / "scripts" / "build_replay_pages.py"
    spec = importlib.util.spec_from_file_location("build_replay_pages", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    paths = {row[0] for row in module.BASE_SITEMAP}
    assert "/investigations/" in paths
    assert "/investigations/the-5-64x-private-credit-concentration/" in paths
    assert "/research/replay-atlas-2026-08-09.json" in paths
    assert "/desk/" in paths
    assert "/replay/index.json" in paths


def test_case_file_feed_keeps_lens_level_hits_misses_and_voids_separate():
    script = ROOT / "scripts" / "build_replay_pages.py"
    spec = importlib.util.spec_from_file_location("build_replay_case_files", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = {
        "pca_replay": {"failures": [
            {"slug": "caught", "default_date": "2020-01-01",
             "first_action_zone": {"period_end": "2019-01-01"}, "lead_months": 12},
            {"slug": "missed", "default_date": "2020-01-01",
             "first_action_zone": None, "lead_months": None},
        ]},
        "funding_replay": {"failures": [
            {"slug": "caught", "scoreable": True, "first_signal": None,
             "lead_months": None},
            {"slug": "missed", "scoreable": False, "first_signal": None,
             "lead_months": None},
        ]},
    }
    pca = {row["slug"]: row for row in payload["pca_replay"]["failures"]}
    funding = {row["slug"]: row for row in payload["funding_replay"]["failures"]}
    feed = module.case_file_index(["caught", "missed"], pca, funding, set())

    assert feed["schema"] == "liquilens.case-file-index.v1"
    assert feed["articles"][0]["verdicts"] == {
        "action_zone": "HIT", "funding_fragility": "MISS"}
    assert feed["articles"][1]["verdicts"] == {
        "action_zone": "MISS", "funding_fragility": "VOID"}
    for article in feed["articles"]:
        assert article["article_type"] == "case_file"
        assert article["point_in_time_status"] == "RECONSTRUCTED_LATER"
        assert article["limitations"]
