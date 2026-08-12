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
    assert manifest["articles"][0]["editorial_status"] == "reviewed"
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
