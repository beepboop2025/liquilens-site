#!/usr/bin/env python3
"""Build contextual social cards for LiquiLens's non-detail public routes.

Article and replay detail pages remain owned by their native generators.  This
builder owns the root, collection, data-routing, guide, product, and policy
routes.  It also completes metadata around the existing reviewed investigation
image without changing that image's bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import pathlib
import re
from dataclasses import dataclass
from typing import Any

try:
    from scripts.social_cards import (
        CardFact,
        RenderedCard,
        render_card,
        route_card_spec,
        write_card,
    )
except ModuleNotFoundError:  # direct execution
    from social_cards import (
        CardFact,
        RenderedCard,
        render_card,
        route_card_spec,
        write_card,
    )


ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://liquilens.in"
BOARD_RECEIPT = ROOT / "research" / "share-card-board.json"
INVESTIGATION_PATH = "/investigations/the-5-64x-private-credit-concentration/"
SOCIAL_START = "<!-- SOCIAL-CARD:START -->"
SOCIAL_END = "<!-- SOCIAL-CARD:END -->"


@dataclass(frozen=True)
class RouteDefinition:
    path: str
    slug: str
    eyebrow: str
    subject: str
    title: str
    role_label: str
    role_value: str
    role_detail: str
    clock_label: str
    clock: str
    status: str
    source: str
    signature_label: str = "ROUTE"
    signature_file: str | None = None
    signature: str | None = None
    og_type: str = "website"


ROUTES = (
    RouteDefinition(
        "/banking/", "banking", "LIQUILENS / FREE BANK RESEARCH", "NPA / SFB / UCB",
        "A smaller NPA balance is not the same as cash recovered.",
        "EVIDENCE CONTRACT", "CITED FILINGS / EXPLICIT GAPS",
        "CASH RECOVERIES / UPGRADES / WRITE-OFFS", "PAGE CUT", "2026-09-05",
        "RESEARCH / NOT A RATING", "ACCEPTED BANK FILINGS",
    ),
    RouteDefinition(
        "/about/", "about", "LIQUILENS / PUBLIC IDENTITY", "ABOUT LIQUILENS",
        "A failure radar built for readers who ask what the evidence cannot prove.",
        "PRODUCT IDENTITY", "LIQUILENS / AI.DE",
        "PUBLIC-EVIDENCE SOFTWARE / JAIPUR, INDIA", "PAGE CUT", "2026-08-04",
        "PUBLIC IDENTITY", "ABOUT PAGE",
    ),
    RouteDefinition(
        "/access/", "access", "LIQUILENS / ACCESS", "NAMED-LIST SOFTWARE",
        "Start with institutions you already review; move to private-book proof only by agreement.",
        "ACCESS LADDER", "PUBLIC / NAMED LIST / PILOT",
        "NO CUSTOMER BOOK REQUIRED UNTIL PILOT", "PAGE CUT", "2026-08-18",
        "PUBLIC + REQUEST GATES", "ACCESS PAGE",
    ),
    RouteDefinition(
        "/access/sample/", "access-sample", "LIQUILENS / GENERATED SAMPLE",
        "NAMED-LIST PACK", "A live pack shape with missing evidence disclosed, never painted calm.",
        "SAMPLE CONTRACT", "GENERATED IN THE BROWSER",
        "PUBLIC SOURCES / NO HANDWRITTEN VERDICTS", "PAGE CUT", "2026-08-18",
        "ABSENCE IS NOT CALM", "PUBLIC BOARD + SEICHE",
    ),
    RouteDefinition(
        "/capital-markets/", "capital-markets", "EVIDENCE ROUTE / CAPITAL MARKETS",
        "EXIT CAPACITY IS ITS OWN CLAIM", "Market liquidity, system funding and counterparty health stay separate.",
        "PRIMARY EVIDENCE", "UNDERTOW / EXIT CAPACITY",
        "SEICHE FUNDING / LIQUILENS COUNTERPARTY", "PAGE CUT", "2026-08-24",
        "NO BLENDED SCORE", "EVIDENCE CATALOG",
        signature_file="world-economy/evidence-catalog.json",
    ),
    RouteDefinition(
        "/china-economy/", "china-economy", "EVIDENCE ROUTE / CHINA ECONOMY",
        "THE REVISION RECORD MATTERS", "Release, collection and revision clocks answer different questions.",
        "PRIMARY EVIDENCE", "PALIMPSEST / REVISIONS",
        "OFFICIAL PUBLISHERS REMAIN AUTHORITATIVE", "PAGE CUT", "2026-08-29",
        "AUTHORITY NONE", "EVIDENCE CATALOG",
        signature_file="world-economy/evidence-catalog.json",
    ),
    RouteDefinition(
        "/desk/", "desk", "LIQUILENS / INTELLIGENCE DESK", "THE FINDING IS THE PRODUCT",
        "Four desks, one rule: show the evidence boundary beside the claim.",
        "EDITORIAL NETWORK", "FOUR DESKS / ONE STANDARD",
        "LIQUILENS / SEICHE / PALIMPSEST / UNDERTOW", "LATEST CUT", "2026-08-29",
        "OPEN / EVIDENCE-BOUND", "PUBLISHED DESK INDEX",
    ),
    RouteDefinition(
        "/developers/", "developers", "LIQUILENS / DEVELOPERS", "PUBLIC API + MCP",
        "Give an agent a source-clocked failure radar, not an unbounded hunch.",
        "INTERFACE CONTRACT", "READ-ONLY EVIDENCE",
        "BOUNDED OUTPUTS / PUBLIC SOURCES / NO EXECUTION", "PAGE CUT", "2026-08-21",
        "PUBLIC READ-ONLY", "PROTOCOL CATALOG", signature_file="protocol/catalog.json",
    ),
    RouteDefinition(
        "/guides/rbi-nbfc-early-warning-system/", "rbi-nbfc-guide",
        "LIQUILENS / IMPLEMENTATION GUIDE", "RBI-ALIGNED NBFC EWS",
        "Coverage, clocks and escalation come before model sophistication.",
        "GUIDE CONTRACT", "COVERAGE BEFORE SCORING",
        "EVIDENCE GAPS / VALIDATION / HUMAN REVIEW", "PAGE CUT", "2026-08-21",
        "NOT REGULATORY", "PUBLIC GUIDE",
    ),
    RouteDefinition(
        "/investigations/", "investigations", "LIQUILENS / ARTICLES",
        "EVIDENCE-BOUNDED EDITORIAL", "Investigations, daily analysis and case files from public institutional evidence.",
        "EDITORIAL FORMATS", "REVIEWED / DAILY / REPLAY",
        "SOURCES / COUNTERCASE / LIMITS", "PAGE CUT", "2026-08-12",
        "BOUNDARIES PUBLISHED", "ARTICLE INDEX",
    ),
    RouteDefinition(
        "/money-markets/", "money-markets", "EVIDENCE ROUTE / MONEY MARKETS",
        "SYSTEM FUNDING IS NOT A BANK SCORE", "Ask who owns the evidence before collapsing the pressure chain.",
        "PRIMARY EVIDENCE", "SEICHE / FUNDING PLUMBING",
        "LIQUILENS INSTITUTIONS / UNDERTOW EXITS", "PAGE CUT", "2026-08-24",
        "NO BLENDED SCORE", "EVIDENCE CATALOG",
        signature_file="world-economy/evidence-catalog.json",
    ),
    RouteDefinition(
        "/pilot/", "pilot", "LIQUILENS / CONTROLLED PILOT", "PARALLEL PROOF",
        "Pre-register success on your lender book before any production decision.",
        "PILOT CONTRACT", "SIX-WEEK PARALLEL RUN",
        "FIXED CRITERIA / SELF-HOSTED / REVERSIBLE", "PAGE CUT", "2026-08-08",
        "NO PRODUCTION USE", "PILOT PAGE",
    ),
    RouteDefinition(
        "/privacy/", "privacy", "LIQUILENS / PRIVACY", "DATA MINIMIZATION",
        "Public browsing stays small; private-product handling stays explicitly bounded.",
        "DATA PRACTICE", "NO AD TRACKERS / NO DATA SALES",
        "PRIVATE CONNECTORS DO NOT LIVE ON THIS SITE", "PAGE CUT", "2026-08-21",
        "MINIMIZED", "PRIVACY NOTICE",
    ),
    RouteDefinition(
        "/protocol/", "protocol", "LIQUILENS / OPEN PROTOCOL", "EVIDENCE CARRIER",
        "Provenance, rights, clocks and authority travel with the number.",
        "CARRIER CONTRACT", "IDENTITY / CLOCKS / RIGHTS / REVISION",
        "UNKNOWN RIGHTS FAIL CLOSED", "PAGE CUT", "2026-09-02",
        "OPEN / AUTHORITY NONE", "PROTOCOL CATALOG", "CATALOG",
        signature_file="protocol/catalog.json",
    ),
    RouteDefinition(
        "/protocol/trade-safety/", "trade-safety",
        "LIQUIDITY LAB / TRADE SAFETY", "ORDER-BOUND RECEIPT",
        "One exact order, one short-lived pre-trade check.",
        "REQUIRED CONTEXT", "SEICHE / UNDERTOW",
        "LIQUILENS CONDITIONAL / OPERATOR POLICY", "PROTOCOL CUT", "2026-09-02",
        "NO EXECUTION AUTHORITY", "SIGNED V0.18.0 CONTRACT", "RECEIPT",
        signature_file="protocol/liquilens-trade-safety-receipt-v1.schema.json",
    ),
    RouteDefinition(
        "/research/", "research", "LIQUILENS / RESEARCH RECORD", "MISSES INCLUDED",
        "Historical evidence stays published with its eligibility gates and corrections.",
        "REVIEW CONTRACT", "VALIDATED, NOT COMPLETE",
        "ZERO MODEL CHANGES / CLAIM BLOCKERS REMAIN", "REVIEWED CUT", "2026-08-09",
        "VALIDATED / INCOMPLETE", "STATUS RECEIPT", "STATUS",
        signature="2a726eeec94d364abfed05584951141c0f2481f4e219ea55184504a994eb6c86",
    ),
    RouteDefinition(
        "/security/", "security", "LIQUILENS / SECURITY", "POSTURE, NOT A SEAL",
        "Transport, tenancy, testing and open items stated in plain language.",
        "SECURITY BOUNDARY", "CONTROLS / DISCLOSURE / OPEN ITEMS",
        "NO BADGE REPLACES VERIFIABLE PRACTICE", "PAGE CUT", "2026-08-09",
        "PUBLIC POSTURE", "SECURITY PAGE",
    ),
    RouteDefinition(
        "/ship-log/", "ship-log", "LIQUILENS / SHIP LOG", "DATED BY GIT",
        "Releases, corrections and boundaries remain in one public chronology.",
        "RELEASE RECORD", "SHIPPED / CORRECTED / GATED",
        "HISTORICAL ENTRIES STAY VISIBLE", "LATEST CUT", "2026-09-02",
        "DATED RELEASE LOG", "SHIP LOG",
    ),
    RouteDefinition(
        "/status/", "status", "LIQUILENS / STATUS", "RELEASE BOUNDARIES",
        "Live, gated and paper-only states stay visibly different.",
        "STATUS CONTRACT", "LIVE / GATED / PAPER-ONLY",
        "REACHABILITY IS NOT RELEASE IDENTITY", "PAGE CUT", "2026-09-02",
        "EXPLICIT MODES", "STATUS LEDGER", "STATUS",
        signature="2a726eeec94d364abfed05584951141c0f2481f4e219ea55184504a994eb6c86",
    ),
    RouteDefinition(
        "/terms/", "terms", "LIQUILENS / TERMS", "RESEARCH, NOT A RATING",
        "Public evidence, private access and pilot agreements keep separate boundaries.",
        "USE BOUNDARY", "NO CREDIT RATING / NO ADVICE",
        "PILOT AGREEMENTS SUPERSEDE SITE TERMS", "PAGE CUT", "2026-08-04",
        "PUBLIC TERMS", "TERMS PAGE",
    ),
    RouteDefinition(
        "/tools/ews-coverage-check/", "ews-coverage-check", "LIQUILENS / FREE TOOL",
        "EARLY-WARNING COVERAGE CHECK", "Can the process defend its evidence after the fact?",
        "CHECK CONTRACT", "EVIDENCE / CLOCKS / VALIDATION / REVIEW",
        "NO PORTFOLIO DATA UPLOAD", "PAGE CUT", "2026-08-21",
        "FIVE-MINUTE SELF-AUDIT", "COVERAGE CHECK",
    ),
    RouteDefinition(
        "/us/", "us", "LIQUILENS / UNITED STATES", "US BANK FAILURE RECORD",
        "Current screens plus a 552-failure diagnostic, with recent misses named.",
        "HISTORICAL CONTRACT", "552 FAILURE REPLAYS",
        "2 OF 4 IN 2026 FLAGGED / 2 MISSES NAMED", "REVIEWED CUT", "2026-08-09",
        "AMENDED C-PIT", "US PUBLIC RECORD",
    ),
    RouteDefinition(
        "/use-cases/", "use-cases", "LIQUILENS / USE CASES", "INSTITUTION EARLY WARNING",
        "Use public filings, funding structure and market evidence as a review screen.",
        "PRODUCT BOUNDARY", "BANKS / NBFCS / MFIS",
        "SCREEN, NOT RATING OR FAILURE PREDICTION", "PAGE CUT", "2026-08-21",
        "PUBLIC EVIDENCE", "USE-CASE MAP",
    ),
    RouteDefinition(
        "/world-economy/", "world-economy", "LIQUIDITY LAB / WORLD ECONOMY",
        "FOUR INDEPENDENT EVIDENCE LAYERS", "Route the claim; do not blend unlike signals into one house score.",
        "CLAIM ROUTER", "FUNDING / BANKS / EXITS / REVISIONS",
        "SEICHE / LIQUILENS / UNDERTOW / PALIMPSEST", "CATALOG CUT", "2026-08-29",
        "NO BLENDED SCORE", "EVIDENCE CATALOG", "CATALOG",
        signature_file="world-economy/evidence-catalog.json",
    ),
)


META_TAG_RE = re.compile(r"<meta\b[^>]*>", re.I | re.S)
SOCIAL_BLOCK_RE = re.compile(
    re.escape(SOCIAL_START) + r".*?" + re.escape(SOCIAL_END) + r"\s*",
    re.S,
)


def _file_signature(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()[:12]


def _definition_card(row: RouteDefinition) -> RenderedCard:
    signature = row.signature or (
        _file_signature(row.signature_file) if row.signature_file else None
    )
    spec = route_card_spec(
        slug=row.slug, canonical_path=row.path, eyebrow=row.eyebrow,
        subject=row.subject, title=row.title, role_label=row.role_label,
        role_value=row.role_value, role_detail=row.role_detail,
        clock_label=row.clock_label, clock=row.clock, status=row.status,
        source=row.source, signature_label=row.signature_label,
        signature=signature,
    )
    return render_card(spec, SITE + row.path)


def _root_card() -> RenderedCard:
    receipt = json.loads(BOARD_RECEIPT.read_text(encoding="utf-8"))
    tiers = receipt.get("tiers")
    if (
        receipt.get("schema") != "liquilens.share-card-board.v1"
        or not isinstance(tiers, dict)
        or sum(tiers.get(key, -1) for key in ("red", "orange", "yellow", "green"))
        != receipt.get("screened_rows")
        or not re.fullmatch(r"[a-f0-9]{64}", str(receipt.get("board_signature") or ""))
        or not re.fullmatch(r"[a-f0-9]{64}", str(receipt.get("source_response_sha256") or ""))
    ):
        raise ValueError("root share-card board receipt failed its identity contract")
    screened = str(receipt["screened_rows"])
    excluded = str(receipt["excluded_stale_rows"])
    spec = route_card_spec(
        slug="home", canonical_path="/", kind="overview",
        eyebrow="LIQUILENS / FAILURE RADAR", subject="CURRENT PUBLIC BOARD",
        title=f"{screened} institutions screened; {excluded} stale dossiers excluded, not scored.",
        clock_label="AS OF", clock=receipt["as_of"], status="SCREEN / NOT RATING",
        source="FAILURE RADAR BOARD", signature_label="BOARD",
        signature=receipt["board_signature"], role_label="BOARD",
        role_value="CURRENT PUBLIC SCREEN", role_detail="MISSING IS NOT CALM",
        metric_label="CURRENT PUBLIC BOARD", metric_value=screened,
        metric_detail=f"{excluded} STALE DOSSIERS EXCLUDED / MISSING NEVER BECOMES ZERO",
        facts=tuple(CardFact(key, str(tiers[key])) for key in (
            "red", "orange", "yellow", "green"
        )),
    )
    return render_card(spec, SITE + "/")


def _investigation_card() -> RenderedCard:
    path = ROOT / "investigations" / "the-5-64x-private-credit-concentration" / "share.png"
    payload = path.read_bytes()
    return RenderedCard(
        png=payload,
        revision=hashlib.sha256(payload).hexdigest()[:16],
        url=(SITE + INVESTIGATION_PATH + "share.png?v="
             + hashlib.sha256(payload).hexdigest()[:16]),
        alt=("LiquiLens investigation card: the 5.64x private-credit concentration "
             "in a public call report; concentration is not evidence of distress."),
    )


def cards() -> dict[str, tuple[RenderedCard, str, bool]]:
    """Return route -> (card, OG type, image is generated by this builder)."""
    rows = {"/": (_root_card(), "website", True)}
    for route in ROUTES:
        rows[route.path] = (_definition_card(route), route.og_type, True)
    rows[INVESTIGATION_PATH] = (_investigation_card(), "article", False)
    return rows


def _html_path(route: str) -> pathlib.Path:
    return ROOT / ("index.html" if route == "/" else route.strip("/") + "/index.html")


def _image_path(route: str) -> pathlib.Path:
    return ROOT / ("share.png" if route == "/" else route.strip("/") + "/share.png")


def _text_content(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", value)).strip()


def _page_title(source: str) -> str:
    match = re.search(r"<title>(.*?)</title>", source, re.I | re.S)
    if not match:
        raise ValueError("shareable page is missing a title")
    return html.unescape(_text_content(match.group(1)))


def _social_title(source: str) -> str:
    match = re.search(r"<h1\b[^>]*>(.*?)</h1>", source, re.I | re.S)
    if match:
        heading = html.unescape(_text_content(match.group(1)))
        if heading:
            return heading
    return _page_title(source)


def _page_description(source: str) -> str:
    for tag in META_TAG_RE.findall(source):
        if re.search(r"\bname\s*=\s*['\"]description['\"]", tag, re.I):
            match = re.search(r"\bcontent\s*=\s*(['\"])(.*?)\1", tag, re.I | re.S)
            if match:
                return html.unescape(re.sub(r"\s+", " ", match.group(2)).strip())
    raise ValueError("shareable page is missing a description")


def _without_social_meta(source: str) -> str:
    def keep_or_remove(match: re.Match[str]) -> str:
        tag = match.group(0)
        if (
            re.search(r"\bproperty\s*=\s*['\"]og:", tag, re.I)
            or re.search(r"\bname\s*=\s*['\"]twitter:", tag, re.I)
        ):
            return ""
        return tag
    cleaned = META_TAG_RE.sub(keep_or_remove, SOCIAL_BLOCK_RE.sub("", source))
    return re.sub(r"(?m)^[ \t]+$", "", cleaned)


def _json_script(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":")).replace(
        "<", "\\u003c"
    ).replace(">", "\\u003e").replace("&", "\\u0026")


def inject_metadata(source: str, *, route: str, card: RenderedCard,
                    og_type: str) -> str:
    title = _social_title(source)
    description = _page_description(source)
    canonical = SITE + route
    esc = lambda value: html.escape(str(value), quote=True)
    block = f"""{SOCIAL_START}
<meta property="og:type" content="{esc(og_type)}">
<meta property="og:site_name" content="LiquiLens">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:image" content="{esc(card.url)}">
<meta property="og:image:secure_url" content="{esc(card.url)}">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{esc(card.alt)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(description)}">
<meta name="twitter:image" content="{esc(card.url)}">
<meta name="twitter:image:alt" content="{esc(card.alt)}">
<script type="application/ld+json" data-social-card>{_json_script({
        "@context": "https://schema.org", "@type": "WebPage",
        "@id": canonical + "#social-card", "url": canonical,
        "image": card.url,
        "primaryImageOfPage": {
            "@type": "ImageObject", "contentUrl": card.url,
            "width": 1200, "height": 630, "caption": card.alt,
        },
    })}</script>
{SOCIAL_END}
"""
    cleaned = _without_social_meta(source)
    if "</head>" not in cleaned:
        raise ValueError("shareable page is missing </head>")
    return cleaned.replace("</head>", block + "</head>", 1)


def refresh(*, check: bool = False) -> list[str]:
    changed: list[str] = []
    for route, (card, og_type, generated) in cards().items():
        html_path = _html_path(route)
        source = html_path.read_text(encoding="utf-8")
        expected = inject_metadata(source, route=route, card=card, og_type=og_type)
        image_path = _image_path(route)
        image_matches = image_path.exists() and image_path.read_bytes() == card.png
        html_matches = source == expected
        if check:
            if (generated and not image_matches) or not html_matches:
                changed.append(route)
            continue
        if generated and write_card(image_path, card):
            changed.append(str(image_path.relative_to(ROOT)))
        if not html_matches:
            html_path.write_text(expected, encoding="utf-8")
            changed.append(str(html_path.relative_to(ROOT)))
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build contextual static social cards")
    parser.add_argument("--check", action="store_true",
                        help="fail when a card or metadata block is stale")
    args = parser.parse_args(argv)
    changed = refresh(check=args.check)
    if args.check and changed:
        print("stale contextual social cards: " + ", ".join(changed))
        return 1
    if not args.check:
        print(f"refreshed contextual social cards ({len(changed)} files changed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
