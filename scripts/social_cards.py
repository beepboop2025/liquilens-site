#!/usr/bin/env python3
"""Render deterministic, evidence-bound social cards for LiquiLens pages.

The renderer is intentionally static.  It accepts reviewed article sidecars or
published replay records, never request parameters, tenant data, or arbitrary
remote text.  Each card is a 1200x630 PNG whose byte digest becomes the cache
revision used by the page's Open Graph and Twitter metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import pathlib
import re
import unicodedata
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1200
HEIGHT = 630
PNG_TYPE = "image/png"
REVISION_LENGTH = 16
SITE_HOST = "liquilens.in"
CANVAS_BOUNDS = (0, 0, WIDTH - 1, HEIGHT - 1)
TEXT_SAFE_BOUNDS = (32, 28, WIDTH - 32, HEIGHT - 24)

INK = "#07131E"
INK_2 = "#0B1B28"
INK_3 = "#102635"
LINE = "#1A3A49"
GOLD = "#F2C66D"
GOLD_DIM = "#9E814C"
TEAL = "#28D7C0"
PAPER = "#EAF2F4"
MUTED = "#8DA6B0"
CORAL = "#FF7A66"

SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
HEX_SHA_RE = re.compile(r"(?:sha256:)?([a-f0-9]{64})", re.I)
ACRONYMS = {"ilfs": "IL&FS", "pmc": "PMC", "ckp": "CKP"}


class BoundsCheckedDraw:
    """ImageDraw proxy that fails before anything can cross the card bounds."""

    def __init__(self, image: Image.Image):
        self._draw = ImageDraw.Draw(image)

    @staticmethod
    def _coordinate_bounds(xy: Any) -> tuple[float, float, float, float]:
        coordinates: list[float] = []

        def walk(value: Any) -> None:
            if isinstance(value, (int, float)):
                coordinates.append(float(value))
            else:
                for child in value:
                    walk(child)

        walk(xy)
        if len(coordinates) < 2 or len(coordinates) % 2:
            raise ValueError(f"invalid drawing coordinates: {xy!r}")
        xs = coordinates[::2]
        ys = coordinates[1::2]
        return min(xs), min(ys), max(xs), max(ys)

    @staticmethod
    def _assert_within(
            label: str, bounds: tuple[float, float, float, float],
            allowed: tuple[int, int, int, int]) -> None:
        left, top, right, bottom = bounds
        safe_left, safe_top, safe_right, safe_bottom = allowed
        if (
            left < safe_left or top < safe_top
            or right > safe_right or bottom > safe_bottom
        ):
            raise ValueError(
                f"social-card {label} crossed its safe area: "
                f"{bounds!r} outside {allowed!r}"
            )

    def text(self, xy: Any, value: str, **kwargs: Any) -> None:
        bbox = self._draw.textbbox(
            xy, value, font=kwargs.get("font"), anchor=kwargs.get("anchor"),
            stroke_width=kwargs.get("stroke_width", 0),
        )
        self._assert_within("text", bbox, TEXT_SAFE_BOUNDS)
        self._draw.text(xy, value, **kwargs)

    def textlength(self, value: str, **kwargs: Any) -> float:
        return self._draw.textlength(value, **kwargs)

    def line(self, xy: Any, **kwargs: Any) -> None:
        self._assert_within("line", self._coordinate_bounds(xy), CANVAS_BOUNDS)
        self._draw.line(xy, **kwargs)

    def rectangle(self, xy: Any, **kwargs: Any) -> None:
        self._assert_within("rectangle", self._coordinate_bounds(xy), CANVAS_BOUNDS)
        self._draw.rectangle(xy, **kwargs)

    def rounded_rectangle(self, xy: Any, **kwargs: Any) -> None:
        self._assert_within(
            "rounded rectangle", self._coordinate_bounds(xy), CANVAS_BOUNDS,
        )
        self._draw.rounded_rectangle(xy, **kwargs)

    def ellipse(self, xy: Any, **kwargs: Any) -> None:
        self._assert_within("ellipse", self._coordinate_bounds(xy), CANVAS_BOUNDS)
        self._draw.ellipse(xy, **kwargs)


@dataclass(frozen=True)
class CardLane:
    label: str
    verdict: str
    detail: str


@dataclass(frozen=True)
class CardFact:
    label: str
    value: str


@dataclass(frozen=True)
class CardSpec:
    kind: str
    slug: str
    eyebrow: str
    subject: str
    title: str
    evidence_as_of: str
    status: str
    source: str
    signature_label: str
    signature: str
    canonical_path: str | None = None
    clock_label: str = "AS OF"
    metric_value: str | None = None
    metric_label: str | None = None
    metric_detail: str | None = None
    role_label: str | None = None
    role_value: str | None = None
    role_detail: str | None = None
    facts: tuple[CardFact, ...] = ()
    lanes: tuple[CardLane, ...] = ()
    fraud_masked: bool = False


@dataclass(frozen=True)
class RenderedCard:
    png: bytes
    revision: str
    url: str
    alt: str
    width: int = WIDTH
    height: int = HEIGHT
    mime_type: str = PNG_TYPE


def safe_text(value: Any, *, limit: int = 280) -> str:
    """Return bounded LTR-safe text supported by Pillow's embedded font.

    Financial names in this product are Latin-script public records.  Control,
    bidi, and zero-width characters are removed; non-Latin glyphs that the
    embedded deterministic font cannot promise are transliterated or replaced.
    This prevents hostile metadata from changing visual reading order.
    """
    raw = unicodedata.normalize("NFKC", str(value or ""))
    raw = raw.translate(str.maketrans({
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u2212": "-", "\u2026": "...",
        "\u00b7": "/", "\u2022": "/", "\u00a0": " ",
    }))
    out: list[str] = []
    for char in raw:
        category = unicodedata.category(char)
        if category.startswith("C"):
            continue
        if category.startswith("Z") or char in "\r\n\t":
            out.append(" ")
            continue
        if 32 <= ord(char) <= 255:
            out.append(char)
            continue
        folded = unicodedata.normalize("NFKD", char).encode("ascii", "ignore").decode()
        out.append(folded or "?")
    return re.sub(r"\s+", " ", "".join(out)).strip()[:limit]


def _slug(value: Any) -> str:
    held = str(value or "")
    if not SLUG_RE.fullmatch(held):
        raise ValueError(f"unsafe social-card slug: {held!r}")
    return held


def _humanize_slug(slug: str) -> str:
    words = []
    for word in _slug(slug).split("-"):
        words.append(ACRONYMS.get(word, word if word in {"of", "the"} else word.title()))
    return " ".join(words).replace("Co Operative", "Co-operative")


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    held = float(value)
    return held if math.isfinite(held) else None


def _signature(value: Any) -> str:
    match = HEX_SHA_RE.fullmatch(str(value or "").strip())
    return match.group(1).lower()[:12] if match else "NOT PROVIDED"


def _compact_status(value: Any, *, fallback: str = "NOT PROVIDED") -> str:
    held = safe_text(value, limit=80).upper()
    if not held:
        return fallback
    if "PERIOD_END_PROXY_CONSTRUCTION_PIT" in held:
        return "CONSTRUCTION-PIT"
    if "CURRENT_AMENDED_CONSTRUCTION_PIT" in held:
        return "AMENDED CONSTRUCTION-PIT"
    return held.replace("_", " ")


def article_card_spec(article: dict[str, Any]) -> CardSpec:
    """Select only public article fields that are allowed onto the card."""
    slug = _slug(article.get("slug"))
    article_type = str(article.get("article_type") or "").lower()
    if article_type not in {"current_analysis", "historical_replay"}:
        raise ValueError(f"unsupported article card type: {article_type!r}")
    subject = article.get("subject") if isinstance(article.get("subject"), dict) else {}
    subject_name = safe_text(subject.get("name") or _humanize_slug(
        str(article.get("topic") or slug)), limit=90)

    metric_value = metric_label = metric_detail = None
    if article_type == "current_analysis":
        score = _number(subject.get("score"))
        if score is not None:
            metric_value = f"{score:.1f}"
            metric_label = "PUBLIC SCREEN SCORE"
            tier = safe_text(subject.get("tier"), limit=24).upper()
            metric_detail = f"{tier + ' / ' if tier else ''}SCREEN, NOT RATING"
    else:
        leads: list[tuple[float, str]] = []
        for key, label in (("pca", "ACTION-ZONE LENS"), ("funding", "FUNDING LENS")):
            row = subject.get(key) if isinstance(subject.get(key), dict) else {}
            lead = _number(row.get("lead_months"))
            if lead is not None and lead >= 0:
                leads.append((lead, label))
        if leads:
            lead, label = max(leads, key=lambda row: row[0])
            lead_text = f"{lead:.1f}".rstrip("0").rstrip(".")
            metric_value = f"{lead_text} MO"
            metric_label = "LONGEST PUBLISHED LEAD"
            metric_detail = f"{label} / HISTORICAL, NOT FORECAST"

    quality = article.get("quality_gate")
    quality_status = quality.get("status") if isinstance(quality, dict) else None
    evidence = None
    hazard = subject.get("hazard") if isinstance(subject.get("hazard"), dict) else {}
    historical = hazard.get("historical_evidence") \
        if isinstance(hazard.get("historical_evidence"), dict) else {}
    evidence = historical.get("status")
    status = _compact_status(quality_status or evidence)

    return CardSpec(
        kind="article",
        slug=slug,
        eyebrow=("INSTITUTION RISK / CURRENT ANALYSIS" if article_type == "current_analysis"
                 else "INSTITUTION RISK / HISTORICAL REPLAY"),
        subject=subject_name or "SUBJECT NOT PROVIDED",
        title=safe_text(article.get("headline"), limit=220) or "Headline not provided",
        evidence_as_of=safe_text(article.get("evidence_as_of"), limit=32) or "NOT PROVIDED",
        status=status,
        source="FAILURE RADAR BOARD",
        signature_label="BOARD",
        signature=_signature(article.get("board_signature")),
        metric_value=metric_value,
        metric_label=metric_label,
        metric_detail=metric_detail,
        fraud_masked=bool(subject.get("fraud_masked")),
    )


def _lane_verdict(value: Any) -> str:
    held = safe_text(value, limit=32).upper().replace("_", " ")
    if held in {"VOID", "NOT SCOREABLE", "UNSCOREABLE"}:
        return "NOT SCOREABLE"
    if held in {"HIT", "MISS"}:
        return held
    raise ValueError(f"unknown replay verdict: {value!r}")


def replay_card_spec(record: dict[str, Any]) -> CardSpec:
    """Build a card from the public case-file record, preserving each lane."""
    slug = _slug(record.get("slug"))
    verdicts = record.get("verdicts")
    if not isinstance(verdicts, dict):
        raise ValueError("replay card requires structured verdicts")
    action = _lane_verdict(verdicts.get("action_zone"))
    funding = _lane_verdict(verdicts.get("funding_fragility"))
    subject = record.get("subject")
    if isinstance(subject, dict):
        subject_name = subject.get("name")
    else:
        subject_name = subject
    subject_name = safe_text(subject_name or _humanize_slug(slug), limit=90)
    status = _compact_status(record.get("evidence_status"))
    identity = {
        "slug": slug,
        "evidence_as_of": record.get("evidence_as_of"),
        "evidence_status": record.get("evidence_status"),
        "verdicts": {"action_zone": action, "funding_fragility": funding},
        "fraud_masked": bool(record.get("fraud_masked")),
    }
    record_signature = hashlib.sha256(json.dumps(
        identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()[:12]

    def detail(verdict: str, lens: str) -> str:
        if verdict == "HIT":
            return "PRE-FAILURE SIGNAL ON RECORD"
        if verdict == "MISS":
            return "NO PRE-FAILURE SIGNAL ON RECORD"
        if lens == "funding":
            return "INSUFFICIENT LIABILITY-SIDE DATA"
        return "LENS NOT SCOREABLE ON THIS RECORD"

    return CardSpec(
        kind="replay",
        slug=slug,
        eyebrow="FAILURE REPLAY / CASE FILE",
        subject=subject_name,
        title=safe_text(record.get("headline"), limit=220) or "Historical replay",
        evidence_as_of=safe_text(record.get("evidence_as_of"), limit=32) or "NOT PROVIDED",
        status=status,
        source="VALIDATION API",
        signature_label="RECORD",
        signature=record_signature,
        lanes=(
            CardLane("ACTION-ZONE LENS", action, detail(action, "action")),
            CardLane("FUNDING-FRAGILITY LENS", funding, detail(funding, "funding")),
        ),
        fraud_masked=bool(record.get("fraud_masked")),
    )


def route_card_spec(
        *, slug: str, canonical_path: str, eyebrow: str, subject: str,
        title: str, clock_label: str, clock: str, status: str, source: str,
        role_label: str, role_value: str, role_detail: str,
        signature_label: str = "ROUTE", signature: str | None = None,
        kind: str = "route", metric_value: str | None = None,
        metric_label: str | None = None, metric_detail: str | None = None,
        facts: tuple[CardFact, ...] = (),
) -> CardSpec:
    """Build a non-detail card from an explicit public route definition."""
    held_slug = _slug(slug)
    if (
        not canonical_path.startswith("/") or not canonical_path.endswith("/")
        or "?" in canonical_path or "#" in canonical_path or "//" in canonical_path
    ):
        raise ValueError(f"unsafe static social-card path: {canonical_path!r}")
    if kind not in {"route", "overview"}:
        raise ValueError(f"unsupported static card kind: {kind!r}")
    identity = {
        "slug": held_slug, "canonical_path": canonical_path, "eyebrow": eyebrow,
        "subject": subject, "title": title, "clock_label": clock_label,
        "clock": clock, "status": status, "source": source,
        "role_label": role_label, "role_value": role_value,
        "role_detail": role_detail, "kind": kind, "metric_value": metric_value,
        "metric_label": metric_label, "metric_detail": metric_detail,
        "facts": [(fact.label, fact.value) for fact in facts],
    }
    held_signature = signature or hashlib.sha256(json.dumps(
        identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()[:12]
    signature_text = safe_text(held_signature, limit=64)
    if re.fullmatch(r"[a-fA-F0-9]{12,64}", signature_text):
        signature_text = signature_text[:12].upper()
    return CardSpec(
        kind=kind,
        slug=held_slug,
        canonical_path=canonical_path,
        eyebrow=safe_text(eyebrow, limit=90),
        subject=safe_text(subject, limit=100),
        title=safe_text(title, limit=220),
        clock_label=safe_text(clock_label, limit=24) or "PAGE CUT",
        evidence_as_of=safe_text(clock, limit=32) or "NOT PROVIDED",
        status=_compact_status(status),
        source=safe_text(source, limit=60),
        signature_label=safe_text(signature_label, limit=20) or "ROUTE",
        signature=signature_text,
        metric_value=safe_text(metric_value, limit=32) if metric_value else None,
        metric_label=safe_text(metric_label, limit=60) if metric_label else None,
        metric_detail=safe_text(metric_detail, limit=100) if metric_detail else None,
        role_label=safe_text(role_label, limit=60),
        role_value=safe_text(role_value, limit=100),
        role_detail=safe_text(role_detail, limit=160),
        facts=tuple(CardFact(
            safe_text(fact.label, limit=28), safe_text(fact.value, limit=24)
        ) for fact in facts),
    )


def article_archive_card(index: list[dict[str, Any]]) -> RenderedCard:
    if not index:
        raise ValueError("article archive card requires published articles")
    latest = max(str(row.get("date") or "") for row in index)
    signature = hashlib.sha256(json.dumps([
        {key: row.get(key) for key in ("slug", "date", "article_type", "board_signature")}
        for row in index
    ], sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()[:12]
    spec = route_card_spec(
        slug="articles", canonical_path="/articles/",
        eyebrow="LIQUILENS / DAILY ARTICLES", subject="INSTITUTION-RISK DESK",
        title="Current analysis when evidence moves; historical replay when it does not.",
        clock_label="LATEST EDITION", clock=latest, status="EVIDENCE-BOUND",
        source="ARTICLE SIDECARS", role_label="ARCHIVE CONTRACT",
        role_value="ANALYSIS / REPLAY", role_detail="SOURCES, COUNTERCASE, LIMITS, MISSES",
        signature_label="ARCHIVE", signature=signature,
    )
    return render_card(spec, "https://liquilens.in/articles/")


def replay_archive_card(index: dict[str, Any]) -> RenderedCard:
    rows = index.get("articles") if isinstance(index, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ValueError("replay archive card requires published case files")
    evidence_dates = [str(row.get("evidence_as_of") or "") for row in rows]
    signature = hashlib.sha256(json.dumps([
        {key: row.get(key) for key in ("slug", "verdicts", "fraud_masked", "evidence_as_of")}
        for row in rows
    ], sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()[:12]
    spec = route_card_spec(
        slug="replay", canonical_path="/replay/",
        eyebrow="FAILURE REPLAY / PUBLISHED RECORD", subject="HISTORICAL CASE FILES",
        title=f"{len(rows)} cases. Hits, misses and unscoreable lenses stay separate.",
        clock_label="EVIDENCE AS OF", clock=max(evidence_dates),
        status="CONSTRUCTION-PIT", source="VALIDATION API",
        role_label="REPLAY CONTRACT", role_value="HIT / MISS / NOT SCOREABLE",
        role_detail="FRAUD-MASKED RECORDS REMAIN VISIBLE",
        signature_label="ARCHIVE", signature=signature,
    )
    return render_card(spec, "https://liquilens.in/replay/")


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    # Pillow embeds Aileron Regular.  Pinning Pillow pins the font bytes and
    # avoids machine-specific font substitution in CI or local builds.
    return ImageFont.load_default(size=size)


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> float:
    return draw.textlength(text, font=font)


def _ellipsize(draw: ImageDraw.ImageDraw, value: str, font: ImageFont.ImageFont,
               max_width: int) -> str:
    text = safe_text(value)
    if _text_width(draw, text, font) <= max_width:
        return text
    suffix = "..."
    while text and _text_width(draw, text + suffix, font) > max_width:
        text = text[:-1]
    return text.rstrip() + suffix


def _wrap(draw: ImageDraw.ImageDraw, value: str, font: ImageFont.ImageFont,
          max_width: int, max_lines: int) -> list[str]:
    words = safe_text(value).split()
    lines: list[str] = []
    held = ""
    for word in words:
        if _text_width(draw, word, font) > max_width:
            pieces: list[str] = []
            piece = ""
            for char in word:
                if piece and _text_width(draw, piece + char, font) > max_width:
                    pieces.append(piece)
                    piece = char
                else:
                    piece += char
            if piece:
                pieces.append(piece)
        else:
            pieces = [word]
        for piece in pieces:
            candidate = f"{held} {piece}".strip()
            if held and _text_width(draw, candidate, font) > max_width:
                lines.append(held)
                held = piece
            else:
                held = candidate
    if held:
        lines.append(held)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = _ellipsize(draw, lines[-1] + "...", font, max_width)
    return lines or [""]


def _draw_lines(draw: ImageDraw.ImageDraw, lines: list[str], xy: tuple[int, int],
                font: ImageFont.ImageFont, fill: str, spacing: int) -> int:
    x, y = xy
    line_height = int(font.size if hasattr(font, "size") else 20) + spacing
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y


def _trace(draw: ImageDraw.ImageDraw) -> None:
    points = [(648, 116), (758, 82), (872, 112), (984, 62), (1142, 92)]
    for idx, (left, right) in enumerate(zip(points, points[1:])):
        ratio = idx / max(1, len(points) - 2)
        color = (
            round(242 + (40 - 242) * ratio),
            round(198 + (215 - 198) * ratio),
            round(109 + (192 - 109) * ratio),
        )
        draw.line((left, right), fill=color, width=3)
    for idx, point in enumerate(points):
        fill = GOLD if idx < 2 else TEAL
        draw.ellipse((point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5),
                     fill=INK, outline=fill, width=3)


def _draw_footer(draw: ImageDraw.ImageDraw, spec: CardSpec) -> None:
    y = 520
    draw.rectangle((0, y, WIDTH - 1, HEIGHT - 1), fill=INK_2)
    draw.line((0, y, WIDTH - 1, y), fill=GOLD_DIM, width=2)
    cells = (
        (spec.clock_label, spec.evidence_as_of),
        ("STATUS", spec.status),
        ("SOURCE", spec.source),
        (spec.signature_label, spec.signature),
    )
    label_font = _font(14)
    value_font = _font(18)
    cell_width = WIDTH // 4
    for idx, (label, value) in enumerate(cells):
        x = idx * cell_width + 36
        if idx:
            draw.line((idx * cell_width, y + 23, idx * cell_width, HEIGHT - 23),
                      fill=LINE, width=1)
        draw.text((x, y + 24), safe_text(label).upper(), font=label_font, fill=GOLD)
        shown = _ellipsize(draw, safe_text(value).upper(), value_font, cell_width - 72)
        draw.text((x, y + 55), shown, font=value_font, fill=PAPER)


def _draw_brand(draw: ImageDraw.ImageDraw, spec: CardSpec) -> None:
    draw.rounded_rectangle((58, 38, 100, 80), radius=9, fill=GOLD)
    draw.text((73, 45), "L", font=_font(24), fill=INK)
    draw.text((118, 42), "LIQUILENS", font=_font(20), fill=PAPER)
    draw.text((118, 68), "RISK TRACE", font=_font(12), fill=GOLD)
    kind = {
        "replay": "CASE FILE",
        "article": "EVIDENCE ARTICLE",
        "route": "EVIDENCE MAP",
        "overview": "PUBLIC BOARD",
    }[spec.kind]
    badge_font = _font(13)
    badge_width = int(_text_width(draw, kind, badge_font)) + 34
    draw.rounded_rectangle((WIDTH - 58 - badge_width, 38, WIDTH - 58, 74),
                           radius=18, outline=LINE, width=2, fill=INK_2)
    draw.text((WIDTH - 41 - badge_width, 49), kind, font=badge_font, fill=TEAL)


def _draw_article(draw: ImageDraw.ImageDraw, spec: CardSpec) -> None:
    left_x = 60
    draw.text((left_x, 126), safe_text(spec.eyebrow), font=_font(14), fill=GOLD)
    subject_font = _font(21)
    subject = _ellipsize(
        draw, safe_text(spec.subject).upper(), subject_font, 610,
    )
    draw.text((left_x, 158), subject, font=subject_font, fill=TEAL)
    title_font = _font(42)
    title_lines = _wrap(draw, spec.title, title_font, 610, 4)
    _draw_lines(draw, title_lines, (left_x, 202), title_font, PAPER, 9)

    panel = (742, 150, 1140, 430)
    draw.rounded_rectangle(panel, radius=22, fill=INK_2, outline=LINE, width=2)
    draw.line((774, 184, 1106, 184), fill=GOLD_DIM, width=2)
    if spec.metric_value:
        draw.text((774, 210), safe_text(spec.metric_label), font=_font(14), fill=GOLD)
        metric_font = _font(76 if len(spec.metric_value) < 7 else 60)
        draw.text((774, 247), safe_text(spec.metric_value), font=metric_font, fill=PAPER)
        detail = _wrap(draw, spec.metric_detail or "", _font(15), 330, 2)
        _draw_lines(draw, detail, (774, 353), _font(15), TEAL, 6)
    else:
        draw.text((774, 214), "NO SUPPORTED", font=_font(18), fill=MUTED)
        draw.text((774, 250), "HERO METRIC", font=_font(36), fill=PAPER)
        draw.line((774, 317, 1106, 317), fill=CORAL, width=2)
        draw.text((774, 344), "MISSING IS NOT CALM", font=_font(18), fill=CORAL)
        draw.text((774, 380), "THE CARD WILL NOT INVENT ZERO", font=_font(13), fill=MUTED)

    if spec.fraud_masked:
        draw.rounded_rectangle((60, 448, 1140, 493), radius=12,
                               fill="#2B1C20", outline=CORAL, width=2)
        draw.text((82, 461), "FRAUD-MASKED RECORD / REPORTED BOOKS MAY HIDE DISTRESS",
                  font=_font(16), fill=CORAL)


def _draw_replay(draw: ImageDraw.ImageDraw, spec: CardSpec) -> None:
    draw.text((60, 126), safe_text(spec.eyebrow), font=_font(14), fill=GOLD)
    subject_font = _font(39)
    subject_lines = _wrap(draw, spec.subject.upper(), subject_font, 570, 2)
    y = _draw_lines(draw, subject_lines, (60, 166), subject_font, PAPER, 7)
    title_lines = _wrap(draw, spec.title, _font(22), 570, 4)
    _draw_lines(draw, title_lines, (60, y + 22), _font(22), MUTED, 7)

    if len(spec.lanes) != 2:
        raise ValueError("replay cards require exactly two verdict lanes")
    lane_y = (148, 292)
    for lane, y0 in zip(spec.lanes, lane_y):
        verdict_color = TEAL if lane.verdict == "HIT" else (
            CORAL if lane.verdict == "MISS" else GOLD)
        draw.rounded_rectangle((680, y0, 1140, y0 + 118), radius=18,
                               fill=INK_2, outline=LINE, width=2)
        draw.rectangle((680, y0, 688, y0 + 118), fill=verdict_color)
        draw.text((716, y0 + 19), safe_text(lane.label), font=_font(14), fill=MUTED)
        verdict_font = _font(37 if lane.verdict == "NOT SCOREABLE" else 48)
        draw.text((716, y0 + 45), lane.verdict, font=verdict_font, fill=verdict_color)
        detail = _ellipsize(draw, lane.detail, _font(12), 385)
        draw.text((716, y0 + 96), detail, font=_font(12), fill=PAPER)

    if spec.fraud_masked:
        draw.rounded_rectangle((680, 435, 1140, 493), radius=12,
                               fill="#2B1C20", outline=CORAL, width=2)
        draw.text((704, 447), "FRAUD-MASKED BOOKS", font=_font(15), fill=CORAL)
        draw.text((704, 472), "MISSES STAY VISIBLE; THEY ARE NOT RECLASSIFIED",
                  font=_font(12), fill=PAPER)
    else:
        draw.text((680, 452), "HIT / MISS / NOT SCOREABLE STAY SEPARATE",
                  font=_font(14), fill=MUTED)


def _draw_route(draw: ImageDraw.ImageDraw, spec: CardSpec) -> None:
    draw.text((60, 126), safe_text(spec.eyebrow), font=_font(14), fill=GOLD)
    subject_lines = _wrap(draw, spec.subject.upper(), _font(21), 610, 2)
    y = _draw_lines(draw, subject_lines, (60, 160), _font(21), TEAL, 6)
    title_lines = _wrap(draw, spec.title, _font(39), 610, 5)
    _draw_lines(draw, title_lines, (60, y + 25), _font(39), PAPER, 9)

    draw.rounded_rectangle((742, 150, 1140, 430), radius=22,
                           fill=INK_2, outline=LINE, width=2)
    draw.line((774, 184, 1106, 184), fill=GOLD_DIM, width=2)
    draw.text((774, 211), safe_text(spec.role_label), font=_font(14), fill=GOLD)
    role_lines = _wrap(draw, spec.role_value or "", _font(35), 330, 3)
    role_y = _draw_lines(draw, role_lines, (774, 250), _font(35), PAPER, 8)
    draw.line((774, min(role_y + 13, 366), 1106, min(role_y + 13, 366)),
              fill=LINE, width=1)
    detail_lines = _wrap(draw, spec.role_detail or "", _font(14), 330, 3)
    _draw_lines(draw, detail_lines, (774, min(role_y + 34, 385)),
                _font(14), TEAL, 5)


def _draw_overview(draw: ImageDraw.ImageDraw, spec: CardSpec) -> None:
    draw.text((60, 126), safe_text(spec.eyebrow), font=_font(14), fill=GOLD)
    draw.text((60, 160), safe_text(spec.subject).upper(), font=_font(21), fill=TEAL)
    title_lines = _wrap(draw, spec.title, _font(40), 610, 5)
    _draw_lines(draw, title_lines, (60, 205), _font(40), PAPER, 9)

    draw.rounded_rectangle((742, 148, 1140, 436), radius=22,
                           fill=INK_2, outline=LINE, width=2)
    draw.text((774, 178), safe_text(spec.metric_label), font=_font(14), fill=GOLD)
    draw.text((774, 207), safe_text(spec.metric_value), font=_font(67), fill=PAPER)
    draw.text((905, 248), "SCREENED", font=_font(16), fill=TEAL)
    draw.line((774, 292, 1106, 292), fill=GOLD_DIM, width=2)
    if len(spec.facts) != 4:
        raise ValueError("overview cards require four facts")
    for idx, fact in enumerate(spec.facts):
        x = 774 + (idx % 2) * 168
        y = 316 + (idx // 2) * 57
        color = CORAL if fact.label.upper() == "RED" else (
            GOLD if fact.label.upper() in {"ORANGE", "YELLOW"} else TEAL)
        draw.text((x, y), fact.label.upper(), font=_font(12), fill=MUTED)
        draw.text((x + 95, y - 6), fact.value, font=_font(24), fill=color)
    detail_lines = _wrap(draw, spec.metric_detail or "", _font(13), 610, 2)
    _draw_lines(draw, detail_lines, (60, 452), _font(13), CORAL, 4)


def render_png(spec: CardSpec) -> bytes:
    """Return deterministic PNG bytes for one validated card specification."""
    if spec.kind not in {"article", "replay", "route", "overview"}:
        raise ValueError(f"unsupported card kind: {spec.kind!r}")
    _slug(spec.slug)
    image = Image.new("RGB", (WIDTH, HEIGHT), INK)
    draw = BoundsCheckedDraw(image)
    for x in range(0, WIDTH, 60):
        draw.line((x, 0, x, 520), fill="#0A1A26", width=1)
    for y in range(0, 521, 60):
        draw.line((0, y, WIDTH - 1, y), fill="#0A1A26", width=1)
    draw.rectangle((0, 0, 14, 520), fill=GOLD)
    draw.rectangle((14, 0, 21, 520), fill=TEAL)
    _trace(draw)
    _draw_brand(draw, spec)
    draw.line((58, 104, 1142, 104), fill=LINE, width=1)
    if spec.kind == "article":
        _draw_article(draw, spec)
    elif spec.kind == "replay":
        _draw_replay(draw, spec)
    elif spec.kind == "route":
        _draw_route(draw, spec)
    else:
        _draw_overview(draw, spec)
    _draw_footer(draw, spec)
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=False, compress_level=9)
    return output.getvalue()


def _card_alt(spec: CardSpec) -> str:
    if spec.kind == "replay":
        lanes = "; ".join(f"{lane.label}: {lane.verdict}" for lane in spec.lanes)
        warning = "; fraud-masking warning shown" if spec.fraud_masked else ""
        value = (f"LiquiLens historical replay card for {spec.subject}. {lanes}{warning}. "
                 f"Evidence as of {spec.evidence_as_of}.")
    elif spec.kind == "article":
        metric = (f" {spec.metric_label}: {spec.metric_value}." if spec.metric_value
                  else " No supported hero metric; missing is not calm.")
        warning = " Fraud-masking warning shown." if spec.fraud_masked else ""
        value = (f"LiquiLens evidence card for {spec.subject}: {spec.title}.{metric}"
                 f"{warning} Evidence as of {spec.evidence_as_of}; status {spec.status}.")
    elif spec.kind == "overview":
        facts = "; ".join(f"{fact.label} {fact.value}" for fact in spec.facts)
        value = (f"LiquiLens public board overview: {spec.title} {facts}. "
                 f"As of {spec.evidence_as_of}; status {spec.status}.")
    else:
        value = (f"LiquiLens route card for {spec.subject}: {spec.title} "
                 f"{spec.role_label}: {spec.role_value}. {spec.role_detail}. "
                 f"{spec.clock_label} {spec.evidence_as_of}; status {spec.status}.")
    return safe_text(value, limit=420)


def render_card(spec: CardSpec, canonical_url: str) -> RenderedCard:
    """Render a card and bind its byte revision to a canonical page URL."""
    parsed = urlsplit(str(canonical_url))
    if (
        parsed.scheme != "https" or parsed.netloc != SITE_HOST
        or parsed.query or parsed.fragment or not parsed.path.endswith("/")
    ):
        raise ValueError("social-card canonical URL must be a clean LiquiLens HTTPS page URL")
    if spec.kind in {"article", "replay"}:
        expected_path = f"/{'articles' if spec.kind == 'article' else 'replay'}/{spec.slug}/"
    else:
        expected_path = spec.canonical_path
    if parsed.path != expected_path:
        raise ValueError("social-card canonical URL does not match its structured page identity")
    png = render_png(spec)
    revision = hashlib.sha256(png).hexdigest()[:REVISION_LENGTH]
    return RenderedCard(
        png=png,
        revision=revision,
        url=f"{canonical_url}share.png?v={revision}",
        alt=_card_alt(spec),
    )


def render_article_card(article: dict[str, Any]) -> RenderedCard:
    return render_card(article_card_spec(article), str(article.get("canonical_url") or ""))


def render_replay_card(record: dict[str, Any]) -> RenderedCard:
    return render_card(replay_card_spec(record), str(record.get("canonical_url") or ""))


def write_card(path: pathlib.Path, card: RenderedCard) -> bool:
    """Atomically write a card only when its deterministic bytes changed."""
    if path.exists() and path.read_bytes() == card.png:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_bytes(card.png)
    os.replace(temporary, path)
    return True


def _refresh_articles(article_dir: pathlib.Path) -> int:
    index = json.loads((article_dir / "index.json").read_text(encoding="utf-8"))
    count = 0
    for row in index:
        slug = _slug(row.get("slug"))
        sidecar = json.loads((article_dir / f"{slug}.json").read_text(encoding="utf-8"))
        card = render_article_card(sidecar)
        write_card(article_dir / slug / "share.png", card)
        count += 1
    return count


def _refresh_replays(index_path: pathlib.Path) -> int:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    rows = index.get("articles") if isinstance(index, dict) else None
    if not isinstance(rows, list):
        raise ValueError("replay index does not contain an articles list")
    count = 0
    for record in rows:
        card = render_replay_card(record)
        write_card(index_path.parent / _slug(record.get("slug")) / "share.png", card)
        count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render social cards from reviewed local LiquiLens artifacts",
    )
    parser.add_argument("--articles", type=pathlib.Path,
                        help="articles directory containing index.json and reviewed sidecars")
    parser.add_argument("--replay-index", type=pathlib.Path,
                        help="published replay/index.json case-file feed")
    args = parser.parse_args(argv)
    if not args.articles and not args.replay_index:
        parser.error("choose --articles and/or --replay-index")
    if args.articles:
        print(f"rendered {_refresh_articles(args.articles)} article cards")
    if args.replay_index:
        print(f"rendered {_refresh_replays(args.replay_index)} replay cards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
