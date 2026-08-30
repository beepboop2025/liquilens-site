"""Deterministic, evidence-bound social cards for articles and case files."""

from __future__ import annotations

import copy
import hashlib
import html as html_lib
import json
from pathlib import Path
import re
import struct
from urllib.parse import parse_qs, urlsplit
import xml.etree.ElementTree as ET

import pytest
from PIL import Image

from scripts import (
    build_replay_pages,
    daily_article,
    social_cards,
    static_social_cards,
)


ROOT = Path(__file__).resolve().parents[1]


def article_record(**overrides):
    article = {
        "slug": "2026-08-30-example-bank-evidence",
        "article_type": "current_analysis",
        "topic": "example-bank",
        "headline": "Example Bank's public screen moved while one lens stayed dark",
        "dek": "A bounded public-data reading with missing liability evidence disclosed.",
        "canonical_url": (
            "https://liquilens.in/articles/2026-08-30-example-bank-evidence/"
        ),
        "published_at": "2026-08-30T08:00:00Z",
        "date": "2026-08-30",
        "evidence_as_of": "2026-06-30",
        "board_signature": "a" * 64,
        "subject": {
            "slug": "example-bank",
            "name": "Example Bank",
            "score": 71.4,
            "tier": "orange",
            "fraud_masked": False,
        },
        "body_md": "Public evidence only.\n",
        "word_count": 3,
        "quality_gate": {"status": "PASS"},
        "generation": {"mode": "deterministic_fallback", "passes": 0},
    }
    article.update(overrides)
    return article


def png_size(payload: bytes) -> tuple[int, int]:
    assert payload[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", payload[16:24])


ATTR_RE = re.compile(r"([\w:-]+)\s*=\s*(['\"])(.*?)\2", re.S)


def tag_attrs(tag: str) -> dict[str, str]:
    return {
        key.lower(): html_lib.unescape(value)
        for key, _, value in ATTR_RE.findall(tag)
    }


def tags(source: str, name: str) -> list[dict[str, str]]:
    return [
        tag_attrs(tag)
        for tag in re.findall(fr"<{name}\b[^>]*>", source, re.I | re.S)
    ]


def meta_values(source: str, key: str) -> list[str]:
    return [
        row.get("content", "")
        for row in tags(source, "meta")
        if row.get("property", "").lower() == key.lower()
        or row.get("name", "").lower() == key.lower()
    ]


def jsonld_contains(value, expected: str) -> bool:
    if value == expected:
        return True
    if isinstance(value, dict):
        return any(jsonld_contains(child, expected) for child in value.values())
    if isinstance(value, list):
        return any(jsonld_contains(child, expected) for child in value)
    return False


def shareable_pages() -> list[tuple[Path, str, str]]:
    rows = []
    for page in sorted(ROOT.rglob("index.html")):
        if "node_modules" in page.parts:
            continue
        source = page.read_text(encoding="utf-8")
        canonicals = [
            row.get("href", "") for row in tags(source, "link")
            if "canonical" in row.get("rel", "").lower().split()
        ]
        if not canonicals:
            continue
        assert len(canonicals) == 1, page
        canonical = canonicals[0]
        parsed = urlsplit(canonical)
        robots = " ".join(meta_values(source, "robots")).lower()
        if parsed.netloc != "liquilens.in" or "noindex" in robots:
            continue
        rows.append((page, canonical, source))
    return rows


def expected_shareable_paths() -> set[str]:
    article_index = json.loads(
        (ROOT / "articles" / "index.json").read_text(encoding="utf-8")
    )
    replay_index = json.loads(
        (ROOT / "replay" / "index.json").read_text(encoding="utf-8")
    )
    return (
        set(static_social_cards.cards())
        | {"/articles/", "/replay/"}
        | {f"/articles/{row['slug']}/" for row in article_index}
        | {f"/replay/{row['slug']}/" for row in replay_index["articles"]}
    )


def test_article_png_is_deterministic_and_exact_social_size():
    article = article_record()
    first = social_cards.render_article_card(article)
    second = social_cards.render_article_card(copy.deepcopy(article))

    assert first.png == second.png
    assert first.revision == second.revision
    assert png_size(first.png) == (1200, 630)
    assert first.url == (
        article["canonical_url"] + f"share.png?v={first.revision}"
    )
    assert re.fullmatch(r"[a-f0-9]{16}", first.revision)


def test_missing_metric_is_not_coerced_to_explicit_zero():
    missing = article_record(subject={
        "slug": "example-bank", "name": "Example Bank", "score": None,
    })
    zero = article_record(subject={
        "slug": "example-bank", "name": "Example Bank", "score": 0.0,
        "tier": "green",
    })

    missing_spec = social_cards.article_card_spec(missing)
    zero_spec = social_cards.article_card_spec(zero)
    assert missing_spec.metric_value is None
    assert zero_spec.metric_value == "0.0"
    assert "missing is not calm" in social_cards.render_article_card(missing).alt.lower()
    assert social_cards.render_article_card(missing).revision != \
        social_cards.render_article_card(zero).revision


def test_cache_revision_changes_with_visible_evidence_and_not_runtime_state():
    article = article_record()
    baseline = social_cards.render_article_card(article)
    changed = copy.deepcopy(article)
    changed["evidence_as_of"] = "2026-08-31"
    refreshed = social_cards.render_article_card(changed)
    irrelevant = copy.deepcopy(article)
    irrelevant["private_tenant_note"] = "must never enter the card"

    assert refreshed.revision != baseline.revision
    assert refreshed.url != baseline.url
    assert social_cards.render_article_card(irrelevant).png == baseline.png


def test_article_page_has_complete_page_specific_og_and_twitter_metadata():
    article = article_record()
    card = social_cards.render_article_card(article)
    page = daily_article.render_article(article, social_card=card)

    for required in (
        f'<meta property="og:image" content="{card.url}">',
        f'<meta property="og:image:secure_url" content="{card.url}">',
        '<meta property="og:image:type" content="image/png">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:image:alt" content="{daily_article.esc(card.alt)}">',
        f'<meta name="twitter:image" content="{card.url}">',
        f'<meta name="twitter:image:alt" content="{daily_article.esc(card.alt)}">',
    ):
        assert required in page
    assert f'"image": "{card.url}"' in page


@pytest.mark.parametrize(
    ("action", "funding", "expected"),
    [
        ("HIT", "MISS", ("HIT", "MISS")),
        ("MISS", "HIT", ("MISS", "HIT")),
        ("MISS", "VOID", ("MISS", "NOT SCOREABLE")),
    ],
)
def test_replay_lanes_keep_hit_miss_and_unscoreable_separate(
        action, funding, expected):
    record = {
        "slug": "example-bank",
        "subject": {"name": "Example Bank"},
        "headline": "The two public replay lenses reached different outcomes",
        "canonical_url": "https://liquilens.in/replay/example-bank/",
        "evidence_as_of": "2026-08-09",
        "evidence_status": "PERIOD_END_PROXY_CONSTRUCTION_PIT",
        "verdicts": {"action_zone": action, "funding_fragility": funding},
        "fraud_masked": False,
    }
    spec = social_cards.replay_card_spec(record)
    assert tuple(lane.verdict for lane in spec.lanes) == expected
    assert png_size(social_cards.render_replay_card(record).png) == (1200, 630)


def test_replay_fraud_warning_and_page_metadata_are_bound_to_case_record():
    pca = {
        "slug": "example-bank", "inst_type": "bank",
        "default_date": "2020-01-01", "first_action_zone": None,
        "lead_months": None,
    }
    funding = {
        "slug": "example-bank", "inst_type": "bank", "scoreable": False,
        "first_signal": None, "lead_months": None,
    }
    record = build_replay_pages.case_file_record(
        "example-bank", pca, funding, True, "2026-08-09T20:27:48+05:30",
    )
    card = social_cards.render_replay_card(record)
    page = build_replay_pages.inst_page(
        "example-bank", pca, funding, True, social_card=card,
    )

    assert "fraud-masking warning shown" in card.alt.lower()
    assert "NOT SCOREABLE" in card.alt
    assert f'<meta property="og:image" content="{card.url}">' in page
    assert f'<meta property="og:image:secure_url" content="{card.url}">' in page
    assert '<meta property="og:image:width" content="1200">' in page
    assert f'<meta name="twitter:image:alt" content="{card.alt}">' in page


def test_hostile_unicode_and_markup_are_bounded_and_cannot_change_reading_order():
    hostile = "Bank\u202e<script>\x00\n" + "x" * 900 + " \U0001f4a3"
    article = article_record(
        headline=hostile,
        subject={"slug": "example-bank", "name": hostile, "score": None},
    )
    spec = social_cards.article_card_spec(article)
    card = social_cards.render_article_card(article)
    page = daily_article.render_article(article, social_card=card)

    assert "\u202e" not in spec.title
    assert "\x00" not in spec.title
    assert len(spec.title) <= 220
    assert png_size(card.png) == (1200, 630)
    assert "<script>" not in page
    assert "&lt;script&gt;" in page


def test_renderer_fails_closed_when_a_primitive_crosses_the_safe_area():
    draw = social_cards.BoundsCheckedDraw(
        Image.new("RGB", (social_cards.WIDTH, social_cards.HEIGHT))
    )
    with pytest.raises(ValueError, match="text crossed its safe area"):
        draw.text((0, 0), "unsafe")
    with pytest.raises(ValueError, match="rectangle crossed its safe area"):
        draw.rectangle((-1, 0, 20, 20), fill="#000000")


def test_social_card_rejects_query_driven_or_cross_host_identity():
    spec = social_cards.article_card_spec(article_record())
    with pytest.raises(ValueError, match="clean LiquiLens HTTPS"):
        social_cards.render_card(
            spec, "https://liquilens.in/articles/2026-08-30-example-bank-evidence/?q=secret",
        )
    with pytest.raises(ValueError, match="clean LiquiLens HTTPS"):
        social_cards.render_card(
            spec, "https://customer.example/articles/2026-08-30-example-bank-evidence/",
        )


def test_every_published_article_and_replay_page_binds_its_exact_png_revision():
    observed = {"articles": 0, "replay": 0}
    for family in observed:
        for share in sorted((ROOT / family).glob("*/share.png")):
            observed[family] += 1
            payload = share.read_bytes()
            revision = hashlib.sha256(payload).hexdigest()[:16]
            page = (share.parent / "index.html").read_text(encoding="utf-8")
            image_url = f"https://liquilens.in/{family}/{share.parent.name}/share.png?v={revision}"
            assert png_size(payload) == (1200, 630)
            assert f'<meta property="og:image" content="{image_url}">' in page
            assert f'<meta property="og:image:secure_url" content="{image_url}">' in page
            assert '<meta property="og:image:type" content="image/png">' in page
            assert '<meta property="og:image:width" content="1200">' in page
            assert '<meta property="og:image:height" content="630">' in page
            assert '<meta property="og:image:alt" content="LiquiLens ' in page
            assert f'<meta name="twitter:image" content="{image_url}">' in page
            assert '<meta name="twitter:image:alt" content="LiquiLens ' in page
    expected = {
        "articles": len(json.loads(
            (ROOT / "articles" / "index.json").read_text(encoding="utf-8")
        )),
        "replay": len(json.loads(
            (ROOT / "replay" / "index.json").read_text(encoding="utf-8")
        )["articles"]),
    }
    assert observed == expected


def test_static_card_builder_is_current_and_preserves_reviewed_investigation():
    assert static_social_cards.refresh(check=True) == []
    investigation = (
        ROOT / "investigations" / "the-5-64x-private-credit-concentration"
        / "share.png"
    )
    assert hashlib.sha256(investigation.read_bytes()).hexdigest() == (
        "b672d06cfc0c8ba00295e371fef86c218f174393ef12fbe0b87aed721997b671"
    )


def test_every_shareable_public_html_has_a_contextual_cache_bound_card():
    pages = shareable_pages()
    canonical_paths = {urlsplit(canonical).path for _, canonical, _ in pages}
    assert len(canonical_paths) == len(pages)
    assert canonical_paths == expected_shareable_paths()

    sitemap = ET.parse(ROOT / "sitemap.xml").getroot()
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    sitemap_urls = {
        node.findtext("sm:loc", default="", namespaces=namespace)
        for node in sitemap.findall("sm:url", namespace)
    }

    for page, canonical, source in pages:
        assert canonical in sitemap_urls, page
        canonical_path = urlsplit(canonical).path
        expected_page = ROOT / (
            "index.html" if canonical_path == "/"
            else canonical_path.strip("/") + "/index.html"
        )
        assert page == expected_page

        for key in (
            "og:type", "og:site_name", "og:url", "og:title", "og:description",
            "og:image", "og:image:secure_url", "og:image:type",
            "og:image:width", "og:image:height", "og:image:alt",
            "twitter:card", "twitter:title", "twitter:description",
            "twitter:image", "twitter:image:alt",
        ):
            values = meta_values(source, key)
            assert len(values) == 1, (page, key, values)
            assert values[0].strip(), (page, key)

        image_url = meta_values(source, "og:image")[0]
        assert meta_values(source, "og:url") == [canonical]
        assert meta_values(source, "og:image:secure_url") == [image_url]
        assert meta_values(source, "og:image:type") == ["image/png"]
        assert meta_values(source, "og:image:width") == ["1200"]
        assert meta_values(source, "og:image:height") == ["630"]
        assert meta_values(source, "twitter:card") == ["summary_large_image"]
        assert meta_values(source, "twitter:image") == [image_url]
        assert meta_values(source, "twitter:image:alt") == \
            meta_values(source, "og:image:alt")

        image = urlsplit(image_url)
        assert (image.scheme, image.netloc) == ("https", "liquilens.in")
        assert image.path.endswith("/share.png") or image.path == "/share.png"
        assert image.path not in {"/og.png", "/og-radar.png", "/og-network.png"}
        image_path = ROOT / image.path.lstrip("/")
        assert image_path.exists(), (page, image_path)
        payload = image_path.read_bytes()
        assert png_size(payload) == (1200, 630)
        revision = hashlib.sha256(payload).hexdigest()[:16]
        assert parse_qs(image.query, strict_parsing=True) == {"v": [revision]}

        scripts = re.findall(
            r"<script\b([^>]*)>(.*?)</script>", source, re.I | re.S,
        )
        structured = [
            json.loads(body)
            for attributes, body in scripts
            if tag_attrs("<script " + attributes + ">").get("type", "").lower()
            == "application/ld+json"
        ]
        assert structured, page
        assert any(jsonld_contains(row, image_url) for row in structured), page
