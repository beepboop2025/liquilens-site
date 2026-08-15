#!/usr/bin/env python3
"""Publish LiquiLens's daily institution-risk article.

The job reads the public Failure Radar, historical validation record, market
evidence, US bank layer, and the sibling Seiche/Undertow boards.  It publishes
current analysis only when the evidence fingerprint changes and a material
institution-level tension is present.  Otherwise it opens one unused failure
record and writes a labelled historical replay.

An optional OpenAI-compatible model performs a writer pass and a separate
standards-editor rewrite.  The model sees a compact evidence dossier, never raw
internet access.  A deterministic gate checks its numbers, links, structure,
and disclosures.  Any model or gate failure falls back to a fully sourced daily
edition, so credentials can improve the prose but can never control cadence.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import os
import pathlib
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://liquilens.in"
ARTICLE_DIR = ROOT / "articles"
INDEX_PATH = ARTICLE_DIR / "index.json"
SCHEMA = "liquilens.daily-article.v1"
EDITORIAL_MEMORY_URL = "https://api.seiche.info/editorial/memory.json"

EDITORIAL_DIRECTIVES = frozenset({
    "strengthen_thesis", "show_mechanism", "tighten_evidence_boundary",
    "surface_countercase", "name_falsifier", "reduce_template_reuse",
    "improve_reader_payoff", "soften_funnel", "preserve_current_standard",
})
EDITORIAL_MEMORY_AUTHORITY = {
    "styleGuidanceOnly": True,
    "maySupplyFacts": False,
    "maySupplyNumbers": False,
    "mayAuthorizePublication": False,
    "trainingAllowed": False,
}

ENDPOINTS = {
    "board": "https://api.liquilens.in/api/failure-radar/board",
    "validation": "https://api.liquilens.in/api/failure-radar/validation",
    "markets": "https://api.liquilens.in/api/evidence/markets",
    "ndfi": "https://api.liquilens.in/api/us-radar/ndfi",
    "seiche": "https://api.seiche.info/api/overview",
    "undertow": "https://api.seiche.info/undertow/board.json",
}

DEFAULT_EDITORIAL_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_EDITORIAL_MODEL = "openai/gpt-5.6-terra"

ALLOWED_URLS = tuple(ENDPOINTS.values()) + (
    f"{SITE}/articles/",
    f"{SITE}/investigations/",
    f"{SITE}/replay/",
    f"{SITE}/research/",
    f"{SITE}/pilot/",
    "https://seiche.info/articles/",
    "https://liquilens-undertow.com/articles/",
    "https://t.me/LiquidityLabDesk",
)

WRITER_SYSTEM = """You are the lead writer on LiquiLens's institution-risk desk.
Write an original digital financial article from the supplied EVIDENCE DOSSIER
only. Do not imitate the wording or house style of any named publication or
journalist. Use the strongest traits of serious financial journalism: a sharp
lede, one contestable thesis, a causal balance-sheet mechanism, exact evidence,
a steel-manned counter-case, and a concrete test that could disprove the view.

Hard rules:
1. The dossier is the complete factual universe. Add no number, event, quote,
   institution allegation, or causal detail from memory.
2. A risk tier is a screen, not a credit rating or prediction of failure. State
   the filing as-of date separately from market and publication dates.
3. Preserve every construction-PIT, eligibility, staleness, missing-data, and
   fraud-masking boundary. Never turn missing evidence into calm.
4. Historical mode must say near the top that the piece is not current news and
   is not a forecast. Similar mechanisms do not imply the same outcome.
5. Write 1,050 to 1,250 words of finished Markdown. This is a hard publication
   gate: copy under 850 words is discarded. No tables. Use every exact required
   heading from the dossier, including The strongest counter-case, Follow the
   pressure chain, and Sources, method, and limits.
6. Include at least seven Markdown source links, all drawn verbatim from
   allowed_source_urls. The product handoff belongs near the end and must remain
   diagnostic, not promotional.
7. Return JSON only with string fields headline, dek, and body_md.
8. editorial_memory contains structural lesson tags only. It is never factual
   evidence and cannot supply a number, event, allegation, source, or verdict.
9. Before returning, scan every numeral against the dossier and delete any
   unsupported one. The body must contain the exact phrases "not investment
   advice" and "not a credit rating".
"""

REVIEW_SYSTEM = """You are LiquiLens's sceptical standards editor. Rewrite the
submitted draft into a publication-ready article using only the EVIDENCE
DOSSIER. Delete unsupported claims instead of repairing them from memory.
Interrogate the difference between a filing-period signal, a market-price
signal, and a model derivation. Make the counter-case capable of defeating the
thesis. Preserve all eligibility and missing-data disclosures. The rewritten
body must be 1,050 to 1,250 words and use every required dossier heading; copy
under 850 words is automatically rejected.
Return publish only after the copy contains at least seven allowed Markdown
links, the exact research and institution-risk boundary phrases, and no numeral
absent from the dossier. If any check fails, repair it in the returned article.

Return JSON only with verdict (the literal string publish), headline, dek,
body_md, and notes (a short list of material edits). No prose outside JSON.
"""

TIER_RANK = {"red": 0, "orange": 1, "yellow": 2, "green": 3}
ACRONYMS = {"ilfs": "IL&FS", "pmc": "PMC", "ckp": "CKP"}


def clean(value: Any) -> str:
    return (str(value or "").replace(" — ", ", ").replace("—", ", ")
            .replace(" – ", ", ").replace("–", "-").strip())


def esc(value: Any) -> str:
    return html.escape(clean(value), quote=True)


def memory_sha(value: dict) -> str:
    body = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(body).hexdigest()


def validate_editorial_memory(payload: dict, *, product: str = "liquilens",
                              now: datetime | None = None) -> dict:
    required = {
        "schema", "generated_at", "source_run_id", "source_manifest_sha256",
        "rubric_version", "global_directives", "products", "authority",
        "memory_fingerprint",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("editorial memory has an invalid field set")
    if (
        payload.get("schema") != "mqdnse.editorial-memory.v1"
        or payload.get("rubric_version") != "mqdnse.editorial-rubric.v1"
        or payload.get("authority") != EDITORIAL_MEMORY_AUTHORITY
    ):
        raise ValueError("editorial memory has an invalid contract or authority")
    for field in ("source_run_id", "source_manifest_sha256", "memory_fingerprint"):
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", str(payload.get(field) or "")):
            raise ValueError(f"editorial memory has an invalid {field}")
    identity = {
        key: value for key, value in payload.items() if key != "memory_fingerprint"
    }
    if memory_sha(identity) != payload["memory_fingerprint"]:
        raise ValueError("editorial memory fingerprint does not match its content")
    generated_at = datetime.fromisoformat(
        payload["generated_at"].replace("Z", "+00:00")
    )
    if generated_at.tzinfo is None:
        raise ValueError("editorial memory generation clock lacks a timezone")
    held_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    age_seconds = (held_now - generated_at.astimezone(timezone.utc)).total_seconds()
    if age_seconds < -300 or age_seconds > 72 * 60 * 60:
        raise ValueError("editorial memory is future-dated or stale")

    def directives(value: object, field: str) -> list[str]:
        if (
            not isinstance(value, list)
            or len(value) > 3
            or len(set(value)) != len(value)
            or any(row not in EDITORIAL_DIRECTIVES for row in value)
        ):
            raise ValueError(f"editorial memory has invalid {field}")
        return list(value)

    global_rows = directives(payload["global_directives"], "global directives")
    products = payload.get("products")
    if not isinstance(products, dict):
        raise ValueError("editorial memory products must be an object")
    product_rows: list[str] = []
    held = products.get(product)
    if held is not None:
        expected = {
            "articleId", "articleRevisionSha256", "criticStatus", "verdict",
            "score", "directives",
        }
        if not isinstance(held, dict) or set(held) != expected:
            raise ValueError("editorial memory product receipt is malformed")
        if not re.fullmatch(
            r"sha256:[a-f0-9]{64}",
            str(held.get("articleRevisionSha256") or ""),
        ):
            raise ValueError("editorial memory product revision is invalid")
        product_rows = directives(held["directives"], "product directives")
        if held.get("criticStatus") != "validated_shadow_critique" and product_rows:
            raise ValueError("unvalidated editorial memory carries directives")
    combined = list(dict.fromkeys([*product_rows, *global_rows]))[:3]
    return {
        "status": "applied" if combined else "empty",
        "source_run_id": payload["source_run_id"],
        "memory_fingerprint": payload["memory_fingerprint"],
        "rubric_version": payload["rubric_version"],
        "directives": combined,
    }


def fetch_editorial_memory(url: str = EDITORIAL_MEMORY_URL) -> dict:
    if url != EDITORIAL_MEMORY_URL:
        raise ValueError("editorial memory URL is not allowlisted")
    try:
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "liquilens-editorial/1",
            },
        )
        with urlopen(request, timeout=15) as response:  # noqa: S310 - fixed URL
            if int(getattr(response, "status", 200)) != 200:
                raise ValueError("editorial memory returned a non-200 response")
            body = response.read(256 * 1024 + 1)
        if len(body) > 256 * 1024:
            raise ValueError("editorial memory exceeded its byte budget")
        return validate_editorial_memory(json.loads(body))
    except Exception as exc:
        return {
            "status": "unavailable",
            "source_run_id": None,
            "memory_fingerprint": None,
            "rubric_version": "mqdnse.editorial-rubric.v1",
            "directives": [],
            "reason": f"{type(exc).__name__}: {str(exc)[:180]}",
        }


def number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None


def fmt(value: Any, digits: int = 1) -> str:
    result = number(value)
    return "unavailable" if result is None else f"{result:,.{digits}f}"


def percent(value: Any, digits: int = 2) -> str:
    result = number(value)
    return "unavailable" if result is None else f"{result * 100:.{digits}f}%"


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:76].rstrip("-")


def name_from_slug(slug: str) -> str:
    if slug in ACRONYMS:
        return ACRONYMS[slug]
    return " ".join(ACRONYMS.get(word, word.capitalize()) for word in slug.split("-")) \
        .replace("Co Operative", "Co-operative")


def fetch_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "liquilens-daily-editorial/1.0"})
    with urlopen(request, timeout=60) as response:  # noqa: S310 - fixed public endpoints
        value = json.loads(response.read())
    if not isinstance(value, dict):
        raise RuntimeError(f"{url} returned a non-object")
    return value


def fetch_datasets() -> dict[str, dict]:
    datasets = {key: fetch_json(url) for key, url in ENDPOINTS.items()}
    if not isinstance(datasets["board"].get("rows"), list):
        raise RuntimeError("Failure Radar board is missing rows")
    if not isinstance((datasets["validation"].get("pca_replay") or {}).get("failures"), list):
        raise RuntimeError("validation record is missing PCA failures")
    if not isinstance(datasets["markets"].get("markets"), list):
        raise RuntimeError("market evidence index is missing markets")
    return datasets


def model_config() -> dict[str, str] | None:
    key = os.environ.get("EDITORIAL_LLM_API_KEY")
    base = os.environ.get("EDITORIAL_LLM_BASE_URL")
    if not key and not base:
        return None
    return {
        "key": key or "",
        "base_url": (base or DEFAULT_EDITORIAL_BASE_URL).rstrip("/"),
        "model": os.environ.get("EDITORIAL_LLM_MODEL") or DEFAULT_EDITORIAL_MODEL,
        "review_model": (
            os.environ.get("EDITORIAL_REVIEW_MODEL")
            or os.environ.get("EDITORIAL_LLM_MODEL")
            or DEFAULT_EDITORIAL_MODEL
        ),
    }


def parse_json_object(text: str) -> dict:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.I)
        candidate = re.sub(r"\s*```$", "", candidate)
    value = json.loads(candidate)
    if not isinstance(value, dict):
        raise ValueError("editorial model returned a non-object")
    return value


def complete_json(config: dict[str, str], messages: list[dict], max_tokens: int) -> dict:
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "liquilens-daily-editorial/1.0",
    }
    if config["key"]:
        headers["Authorization"] = f"Bearer {config['key']}"
    payload = {
        "model": config["model"], "messages": messages,
        "temperature": 0.35, "max_tokens": max_tokens,
        "reasoning_effort": os.environ.get("EDITORIAL_REASONING_EFFORT", "low"),
        "response_format": {"type": "json_object"},
    }
    endpoint = f"{config['base_url']}/chat/completions"

    def call(body: dict) -> dict:
        for attempt in range(3):
            request = Request(endpoint, data=json.dumps(body).encode(), headers=headers, method="POST")
            try:
                with urlopen(request, timeout=150) as response:  # noqa: S310 - operator-configured endpoint
                    return json.loads(response.read())
            except HTTPError as exc:
                if exc.code != 429 or attempt == 2:
                    raise
                detail = exc.read().decode(errors="replace")
                match = re.search(r"try again in\s+([0-9.]+)s", detail, flags=re.I)
                retry_after = number(exc.headers.get("Retry-After"))
                delay = retry_after if retry_after is not None else (
                    float(match.group(1)) if match else 20.0 * (attempt + 1)
                )
                time.sleep(min(60.0, max(2.0, delay + 1.0)))
        raise RuntimeError("editorial model retry loop exhausted")

    try:
        envelope = call(payload)
    except HTTPError as exc:
        if exc.code not in {400, 404, 422}:
            raise
        payload.pop("response_format")
        envelope = call(payload)
    return parse_json_object(envelope["choices"][0]["message"]["content"])


def load_index(path: pathlib.Path = INDEX_PATH) -> list[dict]:
    try:
        rows = json.loads(path.read_text())
    except (OSError, ValueError):
        return []
    return rows if isinstance(rows, list) else []


def board_signature(board: dict) -> str:
    """Hash only decision-relevant fields, excluding rebuild timestamps."""
    rows = []
    for row in board.get("rows") or []:
        rows.append({
            "slug": row.get("slug"), "as_of": row.get("as_of"),
            "tier": row.get("tier"), "score": row.get("score"),
            "movement": row.get("movement"), "signals_fired": row.get("signals_fired"),
            "pca": {
                "status": (row.get("pca") or {}).get("status"),
                "breaches": (row.get("pca") or {}).get("breaches"),
                "headroom": (row.get("pca") or {}).get("headroom"),
            },
            "funding": {
                "index": (row.get("funding") or {}).get("index"),
                "band": (row.get("funding") or {}).get("band"),
                "flags": (row.get("funding") or {}).get("flags"),
            },
            "market": {
                "dd": (row.get("market") or {}).get("dd"),
                "pd_merton_1y": (row.get("market") or {}).get("pd_merton_1y"),
                "as_of": (row.get("market") or {}).get("as_of"),
            },
        })
    payload = {"as_of": board.get("as_of"), "tiers": board.get("tiers"), "rows": rows}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def row_interest(row: dict) -> float:
    pca = row.get("pca") or {}
    funding = row.get("funding") or {}
    market = row.get("market") or {}
    movement = number((row.get("movement") or {}).get("delta_pd_12m")) or 0.0
    score = 100 - TIER_RANK.get(str(row.get("tier") or "green"), 3) * 20
    score += 80 if pca.get("breaches") else 0
    score += 50 if row.get("signals_fired") else 0
    score += 30 if funding.get("flags") else 0
    dd = number(market.get("dd"))
    score += 35 if dd is not None and dd < 2 else 0
    score += min(25, abs(movement) * 10_000)
    score -= min(24, number(row.get("age_months")) or 0)
    return score


def choose_current_subject(board: dict) -> dict | None:
    material = []
    for row in board.get("rows") or []:
        pca = row.get("pca") or {}
        funding = row.get("funding") or {}
        market = row.get("market") or {}
        dd = number(market.get("dd"))
        if (
            row.get("tier") in {"red", "orange"}
            or row.get("signals_fired")
            or pca.get("breaches")
            or funding.get("flags")
            or (dd is not None and dd < 2)
        ):
            material.append(row)
    return max(material, key=row_interest) if material else None


def choose_historical(validation: dict, date: str, recent_topics: list[str]) -> dict:
    pca_rows = {
        row.get("slug"): row for row in (validation.get("pca_replay") or {}).get("failures") or []
        if row.get("slug")
    }
    funding_rows = {
        row.get("slug"): row for row in (validation.get("funding_replay") or {}).get("failures") or []
        if row.get("slug")
    }
    candidates = []
    for slug in sorted(set(pca_rows) | set(funding_rows)):
        pca, funding = pca_rows.get(slug, {}), funding_rows.get(slug, {})
        candidates.append({
            "slug": slug,
            "name": name_from_slug(slug),
            "inst_type": pca.get("inst_type") or funding.get("inst_type"),
            "default_date": pca.get("default_date"),
            "fraud_masked": bool(pca.get("fraud_masked")),
            "pca": pca,
            "funding": funding,
        })
    if not candidates:
        raise RuntimeError("validation record has no historical candidates")
    recent = set(recent_topics)
    unused = [row for row in candidates if row["slug"] not in recent] or candidates
    # Prefer cases with at least one observed signal, and rotate deterministically.
    signalled = [row for row in unused if row["pca"].get("first_action_zone") or row["funding"].get("first_signal")]
    pool = signalled or unused
    seed = int(hashlib.sha256(f"liquilens-history:{date}".encode()).hexdigest(), 16)
    return pool[seed % len(pool)]


def compact_evidence_status(value: dict | None) -> dict:
    row = value or {}
    return {
        key: row.get(key)
        for key in (
            "status", "validated_backtest_eligible", "real_money_eligible",
            "bitemporal_input_contract", "filing_lag_days",
            "availability_time_basis", "lead_times_optimistic",
        )
    }


def compact_board(board: dict, subject_slug: str) -> dict:
    selected = sorted(board.get("rows") or [], key=row_interest, reverse=True)
    comparisons = []
    for row in selected:
        if row.get("slug") == subject_slug:
            continue
        comparisons.append({
            "slug": row.get("slug"), "name": row.get("name"),
            "as_of": row.get("as_of"), "age_months": row.get("age_months"),
            "tier": row.get("tier"), "score": row.get("score"),
            "signals_fired": row.get("signals_fired"),
            "market_dd": (row.get("market") or {}).get("dd"),
        })
        if len(comparisons) == 3:
            break
    return {
        "as_of": board.get("as_of"), "tiers": board.get("tiers"),
        "comparison_rows": comparisons,
        "excluded_stale_count": len(board.get("excluded_stale") or []),
        "historical_evidence": compact_evidence_status(board.get("historical_evidence")),
        "market_layer": board.get("market_layer"), "method_note": board.get("method_note"),
        "quadrant_rule": board.get("quadrant_rule"),
    }


def compact_undertow(board: dict) -> dict:
    segments = {}
    for key, row in (board.get("segments") or {}).items():
        segments[key] = {
            "tier": row.get("tier"), "score": row.get("score"),
            "candidate_tier": row.get("candidate_tier"),
            "n_measures": row.get("n_measures"), "n_qualifying": row.get("n_qualifying"),
        }
    freshness = ((board.get("provenance") or {}).get("freshness") or {}).get("upstream_inputs") or {}
    return {
        "asof": board.get("asof"), "segment_tiers": segments,
        "upstream_observation_range": {
            "oldest_measure_asof": freshness.get("oldest_measure_asof"),
            "newest_measure_asof": freshness.get("newest_measure_asof"),
            "coverage": freshness.get("coverage"),
        },
    }


def build_dossier(datasets: dict[str, dict], *, date: str, article_type: str,
                  subject: dict, changed: bool,
                  editorial_memory: dict | None = None) -> dict:
    seiche = datasets["seiche"]
    ndfi = datasets["ndfi"]
    allowed = list(ALLOWED_URLS)
    if article_type == "historical_replay":
        allowed.append(f"{SITE}/replay/{subject['slug']}/")
    return {
        "schema": "liquilens.editorial-dossier.v1",
        "desk": "LiquiLens",
        "desk_question": "Which institution balance sheet should feel financial stress first, and why?",
        "publication_date": date,
        "article_type": article_type,
        "editorial_memory": {
            key: (editorial_memory or {}).get(key)
            for key in (
                "status", "source_run_id", "memory_fingerprint",
                "rubric_version", "directives",
            )
        },
        "evidence_changed_since_previous_article": changed,
        "subject": subject,
        "failure_radar": compact_board(datasets["board"], str(subject.get("slug") or "")),
        "historical_validation": {
            "historical_evidence": compact_evidence_status(datasets["validation"].get("historical_evidence")),
            "pca_summary": (datasets["validation"].get("pca_replay") or {}).get("summary"),
            "funding_summary": (datasets["validation"].get("funding_replay") or {}).get("summary"),
            "hazard": {
                "panel": (datasets["validation"].get("hazard") or {}).get("panel"),
                "loio": (datasets["validation"].get("hazard") or {}).get("loio"),
                "temporal": (datasets["validation"].get("hazard") or {}).get("temporal"),
                "diagnostic_gates": (datasets["validation"].get("hazard") or {}).get("diagnostic_gates"),
            },
        },
        "market_evidence_index": [{
            "key": row.get("key"), "name": row.get("name"), "kind": row.get("kind"),
            "headline": row.get("headline"), "institutions": row.get("institutions"),
            "historical_evidence": compact_evidence_status(row.get("historical_evidence")),
        } for row in datasets["markets"].get("markets") or []],
        "us_context": {
            "as_of": ndfi.get("as_of"),
            "historical_evidence": compact_evidence_status(ndfi.get("historical_evidence")),
            "system_context": ndfi.get("system_context"),
            "ndfi_watch_top": [{
                key: row.get(key)
                for key in ("bank", "assets_usd_k", "ndfi_to_tier1", "undertow_score_v02")
            } for row in (ndfi.get("ndfi_watch") or [])[:3]],
        },
        "system_context_seiche": {
            "generated_at": seiche.get("generated_at"),
            "editorial": {
                key: (seiche.get("editorial") or {}).get(key)
                for key in ("thesis", "standfirst", "confidence", "confidence_note")
            },
            "composite": {
                key: ((seiche.get("engines") or {}).get("composite") or {}).get(key)
                for key in ("value", "regime", "coverage_pct", "dead_inputs")
            },
        },
        "market_exit_context_undertow": compact_undertow(datasets["undertow"]),
        "required_sections": (
            ["The finding", "The mechanism", "What the filings say", "What the market says",
             "The strongest counter-case", "The evidence that is dark", "What would change the call",
             "Follow the pressure chain", "Sources, method, and limits"]
            if article_type == "current_analysis"
            else ["The record before the event", "What the lenses saw", "Why the warning mattered",
                  "The strongest counter-case", "What today's board shares", "The next falsifiable test",
                  "Follow the pressure chain", "Sources, method, and limits"]
        ),
        "allowed_source_urls": allowed,
        "product_boundaries": {
            "Seiche": "system dollar-funding capacity",
            "LiquiLens": "institution and lender balance-sheet risk",
            "Undertow": "market liquidity and executable exit capacity",
        },
    }


def join_items(values: list[Any], empty: str = "none published") -> str:
    items = [clean(value) for value in values if clean(value)]
    if not items:
        return empty
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + ", and " + items[-1]


def current_fallback(dossier: dict) -> tuple[str, str, str]:
    row = dossier["subject"]
    radar = dossier["failure_radar"]
    name = clean(row.get("name") or name_from_slug(str(row.get("slug") or "institution")))
    tier = clean(row.get("tier") or "unclassified").upper()
    as_of = clean(row.get("as_of") or "date unavailable")
    quarter = clean(row.get("quarter") or "period unavailable")
    age = fmt(row.get("age_months"), 0)
    hazard = row.get("hazard") or {}
    movement = row.get("movement") or {}
    pca = row.get("pca") or {}
    funding = row.get("funding") or {}
    market = row.get("market") or {}
    forensics = row.get("forensics") or {}
    market_dd = number(market.get("dd"))
    market_asof = clean(market.get("as_of") or "not available")
    filing_pd = number(hazard.get("pd_12m"))
    pd_move = number(movement.get("delta_pd_12m"))
    tiers = radar.get("tiers") or {}
    signals = join_items(row.get("signals_fired") or [])
    funding_basis = join_items(funding.get("basis") or [])
    market_basis = join_items(market.get("basis") or [])
    dark = join_items(funding.get("dark_lenses") or [])
    fired_raw = forensics.get("fired")
    forensic_fired = (
        join_items(fired_raw) if isinstance(fired_raw, list)
        else clean(fired_raw) or "none published"
    )
    pca_headroom = join_items([
        f"{item.get('indicator')} {fmt(item.get('headroom_pp'))} percentage points"
        for item in pca.get("headroom") or []
    ])
    system = dossier.get("system_context_seiche") or {}
    seiche_editorial = system.get("editorial") or {}
    undertow = dossier.get("market_exit_context_undertow") or {}

    if market_dd is not None:
        headline = f"{name}'s market warning is fresher than its filing"
        dek = (
            f"LiquiLens places {name} in {tier}, but the useful story is the clock mismatch: "
            f"accounts dated {as_of} beside a market distance-to-default reading dated {market_asof}."
        )
    else:
        headline = f"What LiquiLens's {tier} screen for {name} actually says"
        dek = (
            f"A filing-led risk screen dated {as_of}, the balance-sheet mechanism behind it, "
            "the missing evidence, and the observation that would overturn the call."
        )

    body = f"""LiquiLens is not publishing a verdict that **{name} will fail**. It is publishing a narrower and more useful finding: the institution sits in the **{tier}** risk-screen tier, and the evidence does not all run on the same clock. The vetted accounts are labelled **{quarter}**, with a period end of **{as_of}** and an age of **{age} months** on the board. The market layer, where available, is dated **{market_asof}**. A reader who collapses those dates into one apparently current score loses the most important fact in the story.

That clock mismatch is the thesis. Filed capital, asset quality and funding structure describe a balance sheet at a reporting date. Equity volatility and market value can reprice between filings. Neither source automatically wins. The filing can be stale; the market can be noisy. LiquiLens keeps them beside each other so disagreement remains visible and testable.

## The finding

The live [Failure Radar board]({ENDPOINTS['board']}) contains **{fmt(tiers.get('red'), 0)} red, {fmt(tiers.get('orange'), 0)} orange, {fmt(tiers.get('yellow'), 0)} yellow and {fmt(tiers.get('green'), 0)} green** rows among institutions with a sufficiently recent vetted dossier. {name} is not isolated because a dramatic adjective was chosen. It was selected for this article because its published evidence creates the strongest current tension across tier, movement, regulatory distance, funding structure and market repricing.

Its disclosure-based 12-month monitoring probability is **{percent(filing_pd)}**. The change against the named reference period is **{percent(pd_move)}**, with the sign preserved. That number is a corpus-fitted monitoring probability, not a credit rating and not a calibrated promise about this institution. The board itself says exactly that. The fired signals are: **{signals}**.

## The mechanism

A lender can weaken through several paths that look similar only at the end. Asset-quality deterioration consumes earnings and then capital. A deposit run or expensive wholesale refinancing can create a cash problem before booked credit losses arrive. Thin regulatory headroom can turn another deterioration into supervisory constraints. A falling equity value and rising volatility can reduce a market-implied distance to a simple liability barrier even while the last accounts still look serviceable.

LiquiLens does not blend those paths into a story after the fact. The screen keeps the hazard, regulatory, funding, forensic and market lenses named separately. For {name}, the regulatory headroom rows currently read: **{pca_headroom}**. The funding index is **{fmt(funding.get('index'))}**, its band is **{clean(funding.get('band') or 'not scored')}**, and its published basis is **{funding_basis}**. Those are different observations with different failure modes.

## What the filings say

The filing layer's score is **{fmt(row.get('score'))}**, with display grade **{clean(row.get('grade') or 'unavailable')}**. The hazard basis says: **{join_items(hazard.get('basis') or [])}**. Its historical status is **{clean((hazard.get('historical_evidence') or {}).get('status') or (radar.get('historical_evidence') or {}).get('status'))}**. That label matters because the historical dossiers do not preserve a complete archive of every originally published value and revision.

The regulator-distance lens reports **{clean(pca.get('status') or 'not assessed')}** under **{clean(pca.get('framework') or 'no applicable framework published')}**. Published breaches are **{join_items(pca.get('breaches') or [])}**. Items not assessed are **{join_items(pca.get('not_assessed') or [])}**. The correct reading is not that unassessed fields passed; it is that the public dossier did not support those tests.

## What the market says

The market-implied distance to default is **{fmt(market_dd, 3)}**, and the corresponding Merton-form one-year probability is **{percent(market.get('pd_merton_1y'), 3)}**, dated **{market_asof}**. Its published basis is: **{market_basis}**. This layer uses a simple barrier and realised equity volatility. It is a repricing and ranking signal, not a frequency-calibrated Indian failure probability.

That distinction prevents a seductive but invalid comparison. The disclosure hazard and Merton-form number do not estimate the same object on the same sample. If they disagree, one should investigate the balance-sheet and price channels; one should not average them into a more impressive decimal.

## The strongest counter-case

The strongest counter-case is that the screen may be reacting to a volatile market input or an old comparison while the institution retains ample regulatory headroom and stable funding. The published PCA status is **{clean(pca.get('status') or 'not assessed')}**; the funding flags are **{join_items(funding.get('flags') or [])}**; and the forensic lens fired is **{forensic_fired}**. Those facts can defeat the alarmist version of the thesis.

There is a second counter-case: the current board includes only institutions with vetted dossiers no older than its stated limit, but “inside the limit” is not the same as fresh. A filing aged **{age} months** may simply be too slow for a current institution call. That is why this article describes a screen and a clock mismatch, not an undisclosed change in the bank.

## The evidence that is dark

The funding lens explicitly marks these fields dark: **{dark}**. The board also excludes **{fmt(radar.get('excluded_stale_count'), 0)}** stale dossiers from current presentation. Missing wholesale reliance, certificate-of-deposit strain or liquidity-coverage headroom cannot be read as benign. It reduces what the screen can know.

The forensic layer is also bounded. Honest deterioration may appear in published accounts; fabricated reporting can hide it. LiquiLens publishes fraud-masked historical cases as a separate cohort because a balance-sheet model cannot discover information that was not truthfully disclosed.

## What would change the call

The next useful evidence is not another adjective. A newer vetted filing could show whether asset quality, capital and deposits confirmed or reversed the older direction. A fresh market print could move distance-to-default back above the screen's threshold. A disclosed funding series could illuminate one of the dark lenses. Any of those observations can change the tier or make this article's emphasis obsolete.

The system layer is context only. Seiche currently says: **{clean(seiche_editorial.get('thesis') or 'system reading unavailable')}** That reading does not enter {name}'s score. Undertow's public board is dated **{clean(undertow.get('asof') or 'unavailable')}** and can test whether traded-market exit capacity is broadly impaired; it does not prove an institution-specific funding problem.

## Follow the pressure chain

[Read Seiche](https://seiche.info/articles/) for the system question: is dollar-funding capacity tightening? Stay with [LiquiLens]({SITE}/articles/) for the institution question: which balance sheet carries the exposure and what evidence is missing? Then [read Undertow](https://liquilens-undertow.com/articles/) for the execution question: can risk be transferred without moving the market? The sequence is a diagnostic funnel, not three votes on the same claim.

For the deeper conversion path, the [six-week LiquiLens proof pilot]({SITE}/pilot/) tests these public screening rules against a controlled counterparty book. The public article remains fully readable whether or not the reader takes that step.

## Sources, method, and limits

- [Failure Radar board]({ENDPOINTS['board']}), the source of the institution row, clocks, tiers and missing lenses.
- [Historical validation record]({ENDPOINTS['validation']}), including PCA, funding and hazard diagnostics with misses preserved.
- [Three-market evidence index]({ENDPOINTS['markets']}), which states the construction-PIT status and eligibility boundary for India, the US and Europe.
- [US NDFI watch]({ENDPOINTS['ndfi']}), used only as a cross-market institution context.
- [Seiche live overview]({ENDPOINTS['seiche']}) and [Undertow public board]({ENDPOINTS['undertow']}), displayed as system and market context, never institution-score inputs.
- [LiquiLens research record]({SITE}/research/) and [reviewed investigations]({SITE}/investigations/).

The board is a public-data risk screen, not a credit rating, allegation, recommendation, or prediction that an institution will fail. Its historical record is construction-PIT and is not eligible as a validated backtest or real-money evidence. Filing availability is proxied where the original publication clock is absent; lead times can therefore be optimistic. Market-derived values can move quickly and use simplified barriers. Research and market data, not investment advice.
"""
    return headline, dek, body


def historical_fallback(dossier: dict) -> tuple[str, str, str]:
    case = dossier["subject"]
    name = clean(case["name"])
    slug = clean(case["slug"])
    pca = case.get("pca") or {}
    funding = case.get("funding") or {}
    pca_signal = pca.get("first_action_zone") or {}
    fund_signal = funding.get("first_signal") or {}
    default_date = clean(case.get("default_date") or "date unavailable")
    fraud = bool(case.get("fraud_masked"))
    radar = dossier["failure_radar"]
    tiers = radar.get("tiers") or {}
    validation = dossier["historical_validation"]

    headline = f"Before the event: what {name}'s filings did and did not reveal"
    dek = (
        f"A construction-PIT replay of {name}: the first published regulatory or funding signal, "
        "the disclosure clock, the miss, and the boundary that survives into today's screen."
    )
    body = f"""Nothing in today's Failure Radar evidence cleared the bar for a fresh institution story. This is therefore a historical replay, **not current news and not a forecast**. It opens the public {name} record because a quiet daily tape is better used to examine what an early-warning system could actually have known than to manufacture a new alarm.

The recorded outcome date is **{default_date}**. LiquiLens's reconstruction asks two narrower questions. Did the disclosed ratios enter a published regulatory action zone? Did the disclosed liability structure enter a funding-fragility band? It does not ask whether a modern model, armed with later revisions and hindsight, can draw a persuasive line through the event.

## The record before the event

The first regulatory action-zone row is dated **{clean(pca_signal.get('period_end') or 'not observed')}**, with a conservative knowledge-time proxy of **{clean(pca_signal.get('knowledge_time_proxy') or 'not available')}**. Its status is **{clean(pca_signal.get('status') or 'no action-zone entry in the record')}**, its breached fields are **{join_items(pca_signal.get('breaches') or [])}**, and its recorded lead is **{fmt(pca.get('lead_months'), 0)} months**.

The funding replay is independently scoreable: **{clean(funding.get('scoreable'))}**. Its first signal is dated **{clean(fund_signal.get('period_end') or 'not observed')}**, with knowledge-time proxy **{clean(fund_signal.get('knowledge_time_proxy') or 'not available')}**, index **{fmt(fund_signal.get('index'))}**, band **{clean(fund_signal.get('band') or 'not observed')}**, flags **{join_items(fund_signal.get('flags') or [])}**, and lead **{fmt(funding.get('lead_months'), 0)} months**.

Those two rows are allowed to disagree. Regulatory thresholds look for capital and asset-quality boundaries. Funding fragility looks for liability dependence and rollover exposure. One can fire while the other stays silent because they describe different failure physics.

## What the lenses saw

The [public replay page]({SITE}/replay/{slug}/) preserves the observed entries and misses side by side. The regulatory lens reports the institution against the framework's own tripwires. The funding lens requires liability disclosures and abstains when a usable series is absent. The hazard model excludes fraud-masked failures from fitting because fabricated disclosures carry no honest deterioration signal.

Across the full India record, the regulatory replay summary contains **{fmt((validation.get('pca_summary') or {}).get('failed_institutions'), 0)}** failed institutions and **{fmt((validation.get('pca_summary') or {}).get('entered_action_zone_first'), 0)}** first action-zone entries, with a median recorded lead of **{fmt((validation.get('pca_summary') or {}).get('median_lead_months'), 0)} months**. The funding replay contains **{fmt((validation.get('funding_summary') or {}).get('with_liability_disclosures'), 0)}** institutions with liability disclosures and **{fmt((validation.get('funding_summary') or {}).get('funding_signal_fired_first'), 0)}** first funding signals.

Those are diagnostic counts, not a validated backtest. The dossiers use explicit publication time when it exists and otherwise a conservative period-end-plus-filing-lag proxy. The source record says that the missing complete revision archive can make reconstructed lead times optimistic.

## Why the warning mattered

An early warning matters only if it names a mechanism and leaves time to test it. An action-zone breach says capital or asset quality crossed a supervisory boundary. A funding flag says the liability structure may be exposed to rollover or withdrawal. Neither statement proves the eventual outcome; both can tell a risk team what evidence to demand next.

For {name}, the useful question is which lens spoke first and which stayed silent. The answer above is more valuable than a blended retrospective score because it preserves responsibility. A ratio model should not take credit for a funding signal, and a funding model should not claim to have seen fabricated assets.

## The strongest counter-case

The strongest counter-case is the historical construction itself. A period-end metric is not necessarily what a decision-maker saw on that date. Later amendments may overwrite the original. A fixed filing-lag proxy is conservative about immediate availability but cannot reconstruct every revision. That makes this a mechanism diagnostic, not proof of live foresight.

The record's fraud-masked flag for this case is **{clean(fraud)}**. If true, honest-looking published ratios can be a false negative for any disclosure-based engine. If false, the absence of a signal can still be a real miss. LiquiLens keeps both categories visible because removing them would turn research into marketing.

## What today's board shares

Today's board contains **{fmt(tiers.get('red'), 0)} red, {fmt(tiers.get('orange'), 0)} orange, {fmt(tiers.get('yellow'), 0)} yellow and {fmt(tiers.get('green'), 0)} green** rows. That is not evidence that any current institution is “the next {name}.” No similarity model is asserted here. The legitimate connection is methodological: current filings, market prices, regulatory distance and funding coverage still arrive on different clocks and can still disagree.

The board also excludes **{fmt(radar.get('excluded_stale_count'), 0)}** stale dossiers from current presentation. That abstention is part of the signal. An institution missing from the current table is not thereby safe; it may simply lack a fresh vetted record.

## The next falsifiable test

For a current name, record the filing period, knowledge-time proxy and market date before reading the tier. Then ask whether a newer filing confirms the same asset-quality, capital or funding direction. If it reverses, the old screen should fall. If a dark funding lens becomes observable, grade whether it confirms or contradicts the tier. If the model cannot state what would change its mind, the historical lesson has not been learned.

## Follow the pressure chain

[Seiche](https://seiche.info/articles/) asks whether system funding capacity is tightening. [LiquiLens]({SITE}/articles/) asks which institution balance sheet would transmit that pressure. [Undertow](https://liquilens-undertow.com/articles/) asks whether the risk can be exited in traded markets. The three layers may disagree, and that disagreement is often the finding.

Readers who need the rule tested on their own counterparties can use the [six-week proof pilot]({SITE}/pilot/). The public replay, including this case's misses and voids, stays open.

## Sources, method, and limits

- [LiquiLens historical validation record]({ENDPOINTS['validation']}), the structured source for every case value quoted above.
- [The {name} replay]({SITE}/replay/{slug}/), a human-readable case file generated from that record.
- [Three-market evidence index]({ENDPOINTS['markets']}), which states why India, US and Europe evidence has different status.
- [Current Failure Radar board]({ENDPOINTS['board']}), used only for today's tier counts and coverage boundary.
- [Seiche overview]({ENDPOINTS['seiche']}) and [Undertow public board]({ENDPOINTS['undertow']}), sibling layers not used to score this case.
- [LiquiLens research record]({SITE}/research/) and [reviewed investigations]({SITE}/investigations/).

This article reports a construction-PIT historical diagnostic. It is not a validated backtest, a publication-vintage reconstruction or real-money evidence. It is **not a credit rating** or a prediction. Where an exact publication timestamp is absent, the record uses a filing-availability proxy. Fraud-masked cases expose a hard limit of honest-disclosure models. Similar mechanisms do not imply a repeated outcome. Research and market data, not investment advice.
"""
    return headline, dek, body


def draft_with_model(dossier: dict, config: dict[str, str]) -> dict:
    try:
        writer = complete_json(
            config,
            [
                {"role": "system", "content": WRITER_SYSTEM},
                {"role": "user", "content": "EVIDENCE DOSSIER:\n" + json.dumps(dossier, ensure_ascii=False)},
            ],
            2600,
        )
    except Exception as exc:
        raise RuntimeError(f"writer pass failed: {type(exc).__name__}: {str(exc)[:160]}") from exc
    for field in ("headline", "dek", "body_md"):
        if not isinstance(writer.get(field), str) or not writer[field].strip():
            raise ValueError(f"writer omitted {field}")
    review_config = {**config, "model": config.get("review_model") or config["model"]}
    try:
        reviewer = complete_json(
            review_config,
            [
                {"role": "system", "content": REVIEW_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        "EVIDENCE DOSSIER:\n" + json.dumps(dossier, ensure_ascii=False)
                        + "\n\nDRAFT TO AUDIT AND REWRITE:\n" + json.dumps(writer, ensure_ascii=False)
                    ),
                },
            ],
            2800,
        )
    except Exception as exc:
        raise RuntimeError(f"standards pass failed: {type(exc).__name__}: {str(exc)[:160]}") from exc
    if str(reviewer.get("verdict") or "").lower() != "publish":
        raise ValueError("standards editor did not return publish")
    for field in ("headline", "dek", "body_md"):
        if not isinstance(reviewer.get(field), str) or not reviewer[field].strip():
            raise ValueError(f"standards editor omitted {field}")
    return {
        "headline": reviewer["headline"].strip(), "dek": reviewer["dek"].strip(),
        "body_md": reviewer["body_md"].strip(),
        "review_notes": reviewer.get("notes") if isinstance(reviewer.get("notes"), list) else [],
    }


def repair_with_model(dossier: dict, candidate: dict, failures: list[str],
                      config: dict[str, str]) -> dict:
    """Run one standards pass targeted at deterministic gate failures."""
    repair_config = {**config, "model": config.get("review_model") or config["model"]}
    try:
        repaired = complete_json(
            repair_config,
            [
                {"role": "system", "content": REVIEW_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        "The deterministic publication gate rejected this copy. Repair every "
                        "listed failure using only the dossier; do not weaken or argue with "
                        "the gate. Return the complete article, not a patch.\n\n"
                        "GATE FAILURES:\n" + json.dumps(failures, ensure_ascii=False)
                        + "\n\nEVIDENCE DOSSIER:\n" + json.dumps(dossier, ensure_ascii=False)
                        + "\n\nREJECTED COPY:\n" + json.dumps(candidate, ensure_ascii=False)
                    ),
                },
            ],
            2800,
        )
    except Exception as exc:
        raise RuntimeError(f"repair pass failed: {type(exc).__name__}: {str(exc)[:160]}") from exc
    if str(repaired.get("verdict") or "").lower() != "publish":
        raise ValueError("repair editor did not return publish")
    for field in ("headline", "dek", "body_md"):
        if not isinstance(repaired.get(field), str) or not repaired[field].strip():
            raise ValueError(f"repair editor omitted {field}")
    prior_notes = candidate.get("review_notes")
    repair_notes = repaired.get("notes")
    return {
        "headline": repaired["headline"].strip(),
        "dek": repaired["dek"].strip(),
        "body_md": repaired["body_md"].strip(),
        "review_notes": (
            (prior_notes if isinstance(prior_notes, list) else [])
            + (repair_notes if isinstance(repair_notes, list) else [])
        ),
    }


URL_RE = re.compile(r"https?://[^\s)>\]]+")
NUMBER_RE = re.compile(r"(?<![A-Za-z])[-+]?\$?\d[\d,]*(?:\.\d+)?(?:%|bps?|bp|x|cr|bn|tn|[BMK])?", re.I)


def numeric_values(value: Any) -> set[float]:
    found: set[float] = set()

    def add(item: float) -> None:
        if item == item and abs(item) != float("inf"):
            found.add(round(item, 8))
            if 0 <= item <= 1:
                found.add(round(item * 100, 8))

    def walk(item: Any) -> None:
        if item is None or isinstance(item, bool):
            return
        if isinstance(item, (int, float)):
            add(float(item))
        elif isinstance(item, dict):
            for child in item.values():
                walk(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                walk(child)
        elif isinstance(item, str):
            for match in NUMBER_RE.finditer(URL_RE.sub("", item)):
                raw = re.sub(r"[^0-9.+-]", "", match.group(0).replace(",", ""))
                try:
                    add(float(raw))
                except ValueError:
                    continue

    walk(value)
    return found


def grounding_issues(copy: dict, dossier: dict) -> list[str]:
    combined = "\n".join(str(copy.get(key) or "") for key in ("headline", "dek", "body_md"))
    allowed_numbers = numeric_values(dossier)
    unsupported_numbers = []
    for match in NUMBER_RE.finditer(URL_RE.sub("", combined)):
        raw = re.sub(r"[^0-9.+-]", "", match.group(0).replace(",", ""))
        try:
            value = round(float(raw), 8)
        except ValueError:
            continue
        if value not in allowed_numbers:
            unsupported_numbers.append(match.group(0))
    allowed_urls = set(dossier.get("allowed_source_urls") or [])
    unsupported_urls = sorted({url.rstrip(".,;") for url in URL_RE.findall(combined)} - allowed_urls)
    issues = []
    if unsupported_numbers:
        issues.append("unsupported numbers: " + ", ".join(sorted(set(unsupported_numbers))[:8]))
    if unsupported_urls:
        issues.append("unsupported links: " + ", ".join(unsupported_urls[:5]))
    return issues


def quality_issues(article: dict) -> list[str]:
    body = str(article.get("body_md") or "")
    word_count = len(re.findall(r"\b[\w$%+.-]+\b", body))
    issues = []
    if word_count < 850:
        issues.append(f"article is too thin ({word_count} words; need 850)")
    if word_count > 1_750:
        issues.append(f"article is unfocused ({word_count} words; maximum 1750)")
    if len(str(article.get("headline") or "")) > 125:
        issues.append("headline is longer than 125 characters")
    if len(str(article.get("dek") or "")) > 280:
        issues.append("dek is longer than 280 characters")
    for heading in (
        "## The strongest counter-case",
        "## Follow the pressure chain",
        "## Sources, method, and limits",
    ):
        if heading not in body:
            issues.append(f"missing section: {heading[3:]}")
    if body.count("https://") < 7:
        issues.append("fewer than seven traceable links")
    if len(re.findall(r"\d", body)) < 12:
        issues.append("too little quantified evidence")
    if "not investment advice" not in body.lower():
        issues.append("missing research boundary")
    if "not a credit rating" not in body.lower():
        issues.append("missing institution-risk boundary")
    if article.get("article_type") == "historical_replay":
        lower = body.lower()
        if "not current news" not in lower or "not a forecast" not in lower:
            issues.append("historical replay is not clearly labelled")
    if re.search(r"\b(?:nan|TODO|TBD|null)\b", body, flags=re.I):
        issues.append("placeholder leaked into article")
    lede = body.split("\n## ", 1)[0]
    if len(re.findall(r"\b\w+\b", lede)) < 60:
        issues.append("lede does not establish thesis, evidence clock and stakes")
    if any(phrase in body.lower() for phrase in (
        "in today's fast-paced", "it is important to note", "delve into",
        "game-changer", "as an ai",
    )):
        issues.append("generic or AI-meta language leaked into article")
    memory = article.get("editorial_memory") or {}
    directives = set(memory.get("directives") or [])
    lowered = body.lower()
    if "strengthen_thesis" in directives and not any(
        token in lede.lower() for token in ("argument", "thesis", "finding", "**")
    ):
        issues.append("editorial memory requires an explicit thesis in the lede")
    if "show_mechanism" in directives and not (
        "## the mechanism" in lowered or "## why the warning mattered" in lowered
    ):
        issues.append("editorial memory requires a visible balance-sheet mechanism")
    if "tighten_evidence_boundary" in directives and not all(
        token in lowered
        for token in ("## sources, method, and limits", "not a credit rating")
    ):
        issues.append("editorial memory requires a stronger evidence boundary")
    if "surface_countercase" in directives and "## the strongest counter-case" not in lowered:
        issues.append("editorial memory requires a load-bearing countercase")
    if "name_falsifier" in directives and not any(
        token in lowered for token in ("falsif", "what would change", "next falsifiable")
    ):
        issues.append("editorial memory requires an observable falsifier")
    if "soften_funnel" in directives:
        funnel = body.split("## Follow the pressure chain", 1)[-1].split("\n## ", 1)[0]
        if len(re.findall(r"\b\w+\b", funnel)) > 190:
            issues.append("editorial memory requires a shorter product handoff")
    return issues


def candidate_publish_issues(candidate: dict, dossier: dict, *,
                             article_type: str,
                             editorial_memory: dict | None) -> list[str]:
    """Apply identical immutable gates after review and after repair."""
    issues = grounding_issues(candidate, dossier)
    issues.extend(quality_issues({
        **candidate,
        "article_type": article_type,
        "editorial_memory": editorial_memory or {},
    }))
    return issues


def build_article(datasets: dict[str, dict], *, date: str,
                  recent_index: list[dict] | None = None,
                  configured_model: dict[str, str] | None | bool = False,
                  editorial_memory: dict | None = None,
                  published_at: datetime | None = None) -> dict:
    publication_clock = published_at or datetime.now(timezone.utc)
    if publication_clock.tzinfo is None:
        raise ValueError("published_at must include a timezone")
    publication_clock = publication_clock.astimezone(timezone.utc).replace(microsecond=0)
    publication_timestamp = publication_clock.isoformat().replace("+00:00", "Z")
    index = recent_index or []
    signature = board_signature(datasets["board"])
    previous_signature = str(index[0].get("board_signature") or "") if index else ""
    changed = not previous_signature or previous_signature != signature
    current_subject = choose_current_subject(datasets["board"])
    if changed and current_subject is not None:
        article_type = "current_analysis"
        subject = current_subject
        topic = str(subject.get("slug") or "institution-risk")
    else:
        article_type = "historical_replay"
        recent_topics = [str(row.get("topic") or "") for row in index[:10]]
        subject = choose_historical(datasets["validation"], date, recent_topics)
        topic = subject["slug"]

    dossier = build_dossier(
        datasets, date=date, article_type=article_type, subject=subject, changed=changed,
        editorial_memory=editorial_memory,
    )
    dossier_hash = hashlib.sha256(json.dumps(dossier, sort_keys=True, default=str).encode()).hexdigest()
    generation = {
        "mode": "deterministic_fallback", "model": None, "passes": 0,
        "dossier_sha256": dossier_hash, "fallback_reason": "editorial model is not configured",
        "editorial_memory": copy.deepcopy(editorial_memory or {
            "status": "not_requested", "source_run_id": None,
            "memory_fingerprint": None,
            "rubric_version": "mqdnse.editorial-rubric.v1", "directives": [],
        }),
    }
    config = model_config() if configured_model is False else configured_model
    model_copy = None
    if isinstance(config, dict):
        passes = 0
        try:
            candidate = draft_with_model(dossier, config)
            passes = 2
            issues = candidate_publish_issues(
                candidate, dossier, article_type=article_type,
                editorial_memory=editorial_memory,
            )
            for _repair_attempt in range(2):
                if not issues:
                    break
                candidate = repair_with_model(dossier, candidate, issues, config)
                passes += 1
                issues = candidate_publish_issues(
                    candidate, dossier, article_type=article_type,
                    editorial_memory=editorial_memory,
                )
            if issues:
                raise ValueError("; ".join(issues))
            model_copy = candidate
            generation = {
                "mode": "model_assisted", "model": config["model"], "passes": passes,
                "dossier_sha256": dossier_hash, "fallback_reason": None,
                "review_notes": candidate.get("review_notes") or [],
                "editorial_memory": generation["editorial_memory"],
            }
        except Exception as exc:  # noqa: BLE001 - safe copy still publishes
            generation["passes"] = passes
            generation["fallback_reason"] = f"{type(exc).__name__}: {str(exc)[:240]}"

    if model_copy:
        headline, dek, body = model_copy["headline"], model_copy["dek"], model_copy["body_md"]
    elif article_type == "current_analysis":
        headline, dek, body = current_fallback(dossier)
    else:
        headline, dek, body = historical_fallback(dossier)

    slug = f"{date}-{slugify(headline)}"
    article = {
        "schema": SCHEMA, "id": f"liquilens:article:{slug}", "product": "liquilens",
        "slug": slug, "date": date, "article_type": article_type, "topic": topic,
        "headline": headline, "dek": dek, "canonical_url": f"{SITE}/articles/{slug}/",
        "published_at": publication_timestamp,
        "evidence_as_of": datasets["board"].get("as_of"),
        "board_signature": signature, "subject": subject,
        "body_md": body.strip() + "\n",
        "word_count": len(re.findall(r"\b[\w$%+.-]+\b", body)),
        "editorial_memory": copy.deepcopy(generation["editorial_memory"]),
        "generation": generation,
        "funnel": [
            {"product": "seiche", "job": "system funding", "url": "https://seiche.info/articles/"},
            {"product": "undertow", "job": "market exits", "url": "https://liquilens-undertow.com/articles/"},
            {"product": "liquilens-pilot", "job": "private-book proof", "url": f"{SITE}/pilot/"},
        ],
    }
    issues = quality_issues(article)
    if issues:
        raise SystemExit("article failed quality gate: " + "; ".join(issues))
    article["quality_gate"] = {
        "status": "PASS",
        "checks": [
            "depth", "structure", "lede", "countercase", "sources", "funnel",
            "numeric_grounding", "link_grounding", "institution_boundary", "evidence_status",
        ],
    }
    return article


def inline_markdown(value: str) -> str:
    rendered = html.escape(value, quote=True)
    rendered = re.sub(r"`([^`]+)`", r"<code>\1</code>", rendered)
    rendered = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", rendered)

    def link(match: re.Match) -> str:
        label, url = match.group(1), html.unescape(match.group(2).strip())
        safe = url if re.match(r"^(?:https?:|/|#)", url, flags=re.I) else "#"
        return f'<a href="{html.escape(safe, quote=True)}">{label}</a>'

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, rendered)


def markdown_to_html(markdown: str) -> str:
    lines = markdown.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for line in lines:
        if not line.strip():
            close_list()
            continue
        if line.startswith("## "):
            close_list()
            out.append(f"<h2>{inline_markdown(line[3:])}</h2>")
        elif re.match(r"^[-*]\s+", line):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline_markdown(re.sub(r'^[-*]\\s+', '', line))}</li>")
        else:
            close_list()
            out.append(f"<p>{inline_markdown(line)}</p>")
    close_list()
    return "\n".join(out)


ARTICLE_CSS = """
:root{--ink:#080d18;--panel:#0e1524;--line:#24304a;--gold:#e3b778;--gold2:#f1d399;--text:#edf0f6;--muted:#9aa4ba;--mono:'IBM Plex Mono',monospace;--serif:'Newsreader',Georgia,serif;--sans:'Manrope',system-ui,sans-serif;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--ink);color:var(--text);font:16px/1.72 var(--sans);-webkit-font-smoothing:antialiased}a{color:var(--gold2);text-decoration:none}a:hover{text-decoration:underline}.wrap{width:min(760px,calc(100% - 40px));margin:auto}.mast{border-bottom:1px solid var(--line);padding:21px 0}.mast .wrap{display:flex;justify-content:space-between;align-items:center;gap:20px}.brand{font:600 19px var(--serif);color:var(--text)}.brand b{display:inline-grid;place-items:center;width:29px;height:29px;margin-right:9px;border-radius:7px;background:var(--gold);color:#181106}.nav{display:flex;gap:18px;font:11px var(--mono);color:var(--muted)}.hero{padding:64px 0 35px}.kicker{font:10px var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--gold)}h1{font:500 clamp(38px,6vw,63px)/1.03 var(--serif);letter-spacing:-.035em;margin:15px 0 18px}.dek{font:20px/1.5 var(--serif);color:#c1c6d2}.meta{font:10px var(--mono);letter-spacing:.08em;color:var(--muted);margin-top:22px;text-transform:uppercase}.copy{padding:12px 0 70px}.copy>p:first-child{font:20px/1.58 var(--serif);color:#dfe2e9}.copy p{margin:0 0 20px}.copy h2{font:500 31px/1.15 var(--serif);letter-spacing:-.018em;margin:52px 0 17px;padding-top:20px;border-top:1px solid var(--line)}.copy strong{font-weight:600;color:#fff}.copy ul{padding-left:20px;margin:0 0 24px}.copy li{margin:0 0 10px}.copy code{font:13px var(--mono);background:var(--panel);padding:2px 5px}.receipt{border:1px solid var(--line);background:var(--panel);padding:19px 21px;margin:0 0 55px;font:11px/1.7 var(--mono);color:var(--muted)}footer{border-top:1px solid var(--line);padding:30px 0 45px;font:11px/1.8 var(--mono);color:var(--muted)}.cards{display:grid;gap:15px;padding:15px 0 70px}.card{display:block;border:1px solid var(--line);background:var(--panel);padding:23px}.card:hover{border-color:#655a42;text-decoration:none}.card small{font:10px var(--mono);letter-spacing:.11em;text-transform:uppercase;color:var(--gold)}.card h2{font:500 28px/1.18 var(--serif);margin:10px 0}.card p{color:var(--muted);margin:0}.intro{padding:70px 0 25px}.intro h1{max-width:690px}.formats{border:1px solid var(--line);padding:18px 20px;color:var(--muted);margin:0 0 26px}@media(max-width:620px){.nav a:nth-child(n+3){display:none}.hero{padding-top:45px}h1{font-size:42px}.copy h2{font-size:27px}}
"""


def page_shell(*, title: str, description: str, canonical: str, jsonld: dict,
               body: str, feed: bool = True) -> str:
    feed_link = (
        '<link rel="alternate" type="application/feed+json" href="/articles/feed.json" title="LiquiLens articles JSON Feed">'
        '<link rel="alternate" type="application/atom+xml" href="/articles/feed.xml" title="LiquiLens articles">'
        if feed else ""
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline' https://static.cloudflareinsights.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: https:; connect-src 'self' https://cloudflareinsights.com; object-src 'none'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests">
<title>{esc(title)}</title><meta name="description" content="{esc(description)}"><link rel="canonical" href="{esc(canonical)}">{feed_link}
<meta name="robots" content="index, follow, max-image-preview:large"><meta name="theme-color" content="#080d18">
<meta property="og:type" content="article"><meta property="og:site_name" content="LiquiLens"><meta property="og:url" content="{esc(canonical)}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:image" content="{SITE}/og-radar.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&amp;family=Manrope:wght@400;500;600&amp;family=Newsreader:opsz,wght@6..72,400;6..72,500&amp;display=swap">
<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script><style>{ARTICLE_CSS}</style>
<!-- Cloudflare Web Analytics --><script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{{"token":"43b422e63bb44fb5975c7bb39bd0ba24"}}'></script><!-- End Cloudflare Web Analytics -->
</head><body><header class="mast"><div class="wrap"><a class="brand" href="/"><b>L</b>LiquiLens</a><nav class="nav"><a href="/articles/">Daily articles</a><a href="/investigations/">Investigations</a><a href="/replay/">Case files</a><a href="/research/">Research</a></nav></div></header>{body}<footer><div class="wrap">Every article separates observed filings, market inputs and LiquiLens derivations. Screens are not credit ratings or predictions of failure. <a href="/research/">Evidence record</a> · <a href="/pilot/">Proof pilot</a> · not investment advice.</div></footer></body></html>"""


def render_article(article: dict) -> str:
    url = article["canonical_url"]
    jsonld = {
        "@context": "https://schema.org", "@type": "AnalysisNewsArticle",
        "headline": article["headline"], "description": article["dek"],
        "datePublished": article["published_at"], "dateModified": article["published_at"],
        "articleSection": "Institution risk", "isAccessibleForFree": True,
        "wordCount": article["word_count"], "mainEntityOfPage": url,
        "author": {"@type": "Organization", "name": "LiquiLens", "url": f"{SITE}/"},
        "publisher": {"@type": "Organization", "name": "LiquiLens", "url": f"{SITE}/"},
        "image": f"{SITE}/og-radar.png",
    }
    mode = str(article["article_type"]).replace("_", " ")
    generation = article.get("generation") or {}
    receipt = (
        f"Evidence as of {esc(article.get('evidence_as_of'))} · "
        f"{esc(generation.get('mode'))} · two-pass model: "
        f"{esc('yes' if generation.get('passes') == 2 else 'no')} · quality gate PASS"
    )
    body = (
        f'<main><section class="hero"><div class="wrap"><p class="kicker">{esc(article["date"])} · {esc(mode)}</p>'
        f'<h1>{esc(article["headline"])}</h1><p class="dek">{esc(article["dek"])}</p>'
        f'<p class="meta">{esc(article["word_count"])} words · institution risk · open evidence</p></div></section>'
        f'<article class="copy wrap">{markdown_to_html(article["body_md"])}</article>'
        f'<aside class="receipt wrap">{receipt}</aside></main>'
    )
    return page_shell(title=f"{article['headline']} | LiquiLens", description=article["dek"],
                      canonical=url, jsonld=jsonld, body=body)


def render_archive(index: list[dict]) -> str:
    cards = "".join(
        f'<a class="card" href="/articles/{esc(row["slug"])}/"><small>{esc(row["date"])} · {esc(str(row["article_type"]).replace("_", " "))}</small><h2>{esc(row["headline"])}</h2><p>{esc(row["dek"])}</p></a>'
        for row in index
    )
    jsonld = {
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": "LiquiLens daily institution-risk articles", "url": f"{SITE}/articles/",
        "hasPart": [{"@type": "AnalysisNewsArticle", "headline": row["headline"],
                     "url": row["canonical_url"], "datePublished": row["published_at"]} for row in index],
    }
    body = (
        '<main class="wrap"><section class="intro"><p class="kicker">LIQUILENS / DAILY ARTICLES</p>'
        '<h1>Follow the balance sheet, not the adjective.</h1><p class="dek">One institution-risk argument every day. Material new evidence gets current analysis; a quiet board opens a historical failure record and shows what the filings caught, missed, or could not know.</p></section>'
        '<p class="formats">Long-form investigations remain in the <a href="/investigations/">reviewed investigations archive</a>. Historical hits, misses and fraud-masked voids remain in the <a href="/replay/">case-file record</a>.</p>'
        f'<section class="cards">{cards}</section></main>'
    )
    return page_shell(title="Daily institution-risk articles | LiquiLens",
                      description="Daily evidence-led analysis of bank and lender balance sheets, with historical failure replays when the current board is quiet.",
                      canonical=f"{SITE}/articles/", jsonld=jsonld, body=body)


def render_feed(index: list[dict], bodies: dict[str, str]) -> str:
    updated = index[0]["published_at"] if index else "2026-01-01T00:00:00Z"
    entries = []
    for row in index[:50]:
        entries.append(
            "<entry>"
            f"<title>{html.escape(row['headline'])}</title><link href=\"{html.escape(row['canonical_url'], quote=True)}\"/>"
            f"<id>{html.escape(row['canonical_url'])}</id><published>{html.escape(row['published_at'])}</published>"
            f"<updated>{html.escape(row['published_at'])}</updated><summary>{html.escape(row['dek'])}</summary>"
            f"<content type=\"html\">{html.escape(markdown_to_html(bodies.get(row['slug'], '')))}</content></entry>"
        )
    return (
        '<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom">'
        '<title>LiquiLens daily institution-risk articles</title>'
        f'<link href="{SITE}/articles/"/><link rel="self" href="{SITE}/articles/feed.xml"/>'
        f'<id>{SITE}/articles/</id><updated>{updated}</updated><author><name>LiquiLens</name></author>'
        + "".join(entries) + "</feed>\n"
    )


def render_json_feed(index: list[dict], bodies: dict[str, str],
                     metadata: dict[str, dict]) -> str:
    """Full-text JSON Feed shared by MCP, Telegram and syndicators."""
    items = []
    for row in index[:50]:
        slug = row["slug"]
        meta = metadata.get(slug) or {}
        generation = meta.get("generation") or {}
        quality = meta.get("quality_gate") or {}
        items.append({
            "id": str(meta.get("id") or f"liquilens:article:{slug}"),
            "url": row["canonical_url"],
            "title": row["headline"],
            "summary": row["dek"],
            "content_text": bodies.get(slug, ""),
            "date_published": row["published_at"],
            "tags": [str(row.get("article_type") or "analysis"), "institution risk"],
            "_liquidity_lab": {
                "schema": "liquidity-lab.editorial-item.v1",
                "product": "liquilens",
                "article_type": row.get("article_type"),
                "evidence_as_of": row.get("evidence_as_of"),
                "word_count": row.get("word_count"),
                "evidence_fingerprint": generation.get("dossier_sha256"),
                "generation_mode": generation.get("mode"),
                "quality_gate": {
                    "status": quality.get("status"),
                    "checks": list(quality.get("checks") or []),
                },
                "authority": {
                    "factual_authority": "published_article_only",
                    "training_allowed": False,
                },
            },
        })
    return json.dumps({
        "version": "https://jsonfeed.org/version/1.1",
        "title": "LiquiLens daily institution-risk articles",
        "home_page_url": f"{SITE}/articles/",
        "feed_url": f"{SITE}/articles/feed.json",
        "description": (
            "Evidence-led bank and lender analysis, with historical failure "
            "replays when the current board is quiet."
        ),
        "authors": [{"name": "LiquiLens", "url": f"{SITE}/"}],
        "items": items,
    }, indent=2, ensure_ascii=False) + "\n"


def replace_marked_block(text: str, start: str, end: str, block: str,
                         before: str | None = None) -> str:
    marked = f"{start}\n{block.rstrip()}\n{end}"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), flags=re.S)
    if pattern.search(text):
        return pattern.sub(marked, text)
    if before and before in text:
        return text.replace(before, marked + "\n" + before)
    return text.rstrip() + "\n\n" + marked + "\n"


def update_discovery_files(index: list[dict], root: pathlib.Path) -> None:
    sitemap_path = root / "sitemap.xml"
    sitemap = sitemap_path.read_text()
    sitemap_rows = [
        f"  <url><loc>{SITE}/articles/</loc><lastmod>{index[0]['date'] if index else ''}</lastmod><changefreq>daily</changefreq><priority>0.9</priority></url>"
    ]
    sitemap_rows.extend(
        f"  <url><loc>{row['canonical_url']}</loc><lastmod>{row['date']}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>"
        for row in index
    )
    sitemap_path.write_text(replace_marked_block(
        sitemap, "<!-- DAILY-ARTICLES:START -->", "<!-- DAILY-ARTICLES:END -->",
        "\n".join(sitemap_rows), before="</urlset>",
    ))

    llms_path = root / "llms.txt"
    llms = llms_path.read_text()
    llms_rows = [
        "## Daily institution-risk articles",
        "",
        f"Archive and full-text feeds: {SITE}/articles/, {SITE}/articles/feed.json (JSON Feed 1.1), and {SITE}/articles/feed.xml (Atom)",
        "",
    ]
    llms_rows.extend(
        f"- [{row['headline']}]({SITE}/articles/{row['slug']}.md): {row['date']}, {row['article_type'].replace('_', ' ')}. {row['dek']}"
        for row in index
    )
    llms_path.write_text(replace_marked_block(
        llms, "<!-- DAILY-ARTICLES:START -->", "<!-- DAILY-ARTICLES:END -->",
        "\n".join(llms_rows),
    ))


def write_article(article: dict, *, root: pathlib.Path = ROOT) -> list[str]:
    article_dir = root / "articles"
    article_dir.mkdir(parents=True, exist_ok=True)
    index_path = article_dir / "index.json"
    index = load_index(index_path)
    replaced = [
        row for row in index
        if row.get("date") == article["date"] and row.get("slug") != article["slug"]
    ]
    index = [row for row in index if row.get("date") != article["date"] and row.get("slug") != article["slug"]]
    index_fields = (
        "slug", "date", "article_type", "topic", "headline", "dek", "canonical_url",
        "published_at", "evidence_as_of", "board_signature", "word_count",
    )
    index.append({key: article.get(key) for key in index_fields})
    index.sort(key=lambda row: (str(row.get("date") or ""), str(row.get("published_at") or "")), reverse=True)

    slug = article["slug"]
    md_path = article_dir / f"{slug}.md"
    json_path = article_dir / f"{slug}.json"
    page_dir = article_dir / slug
    page_dir.mkdir(parents=True, exist_ok=True)
    page_path = page_dir / "index.html"
    md_path.write_text(article["body_md"])
    sidecar = {key: value for key, value in article.items() if key != "body_md"}
    json_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n")
    page_path.write_text(render_article(article))
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")

    # A forced same-day rewrite replaces exactly the generated artifacts named
    # by the old index row. Slugs are validated before any unlink so a corrupt
    # index cannot broaden the deletion target.
    for old in replaced:
        old_slug = str(old.get("slug") or "")
        if not re.fullmatch(r"[a-z0-9-]+", old_slug):
            raise SystemExit(f"unsafe replaced article slug: {old_slug!r}")
        for old_path in (
            article_dir / f"{old_slug}.md",
            article_dir / f"{old_slug}.json",
            article_dir / old_slug / "index.html",
        ):
            if old_path.exists():
                old_path.unlink()
        old_dir = article_dir / old_slug
        if old_dir.exists() and not any(old_dir.iterdir()):
            old_dir.rmdir()

    derived = refresh_article_surfaces(root=root)
    return [
        str(md_path), str(json_path), str(index_path), *derived,
    ]


def refresh_article_surfaces(*, root: pathlib.Path = ROOT) -> list[str]:
    """Rebuild every derived article surface from reviewed local artifacts.

    This migration path is intentionally offline: it never fetches evidence or
    writes new prose. It is also useful after a new syndication surface lands,
    because today's already-published revision can be redistributed verbatim.
    """
    article_dir = root / "articles"
    index = load_index(article_dir / "index.json")
    if not index:
        raise SystemExit("article surface refresh requires a non-empty index")
    bodies = {}
    metadata = {}
    pages = []
    for row in index:
        slug = str(row.get("slug") or "")
        if not re.fullmatch(r"[a-z0-9-]+", slug):
            raise SystemExit(f"unsafe article slug in index: {slug!r}")
        md_path = article_dir / f"{slug}.md"
        sidecar_path = article_dir / f"{slug}.json"
        if not md_path.exists() or not sidecar_path.exists():
            raise SystemExit(
                f"article index lists {slug} but its markdown or sidecar is missing")
        meta = json.loads(sidecar_path.read_text())
        if meta.get("slug") != slug or \
                meta.get("quality_gate", {}).get("status") != "PASS":
            raise SystemExit(f"article sidecar failed identity/quality gate: {sidecar_path}")
        body = md_path.read_text()
        bodies[slug] = body
        metadata[slug] = meta
        page_path = article_dir / slug / "index.html"
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text(render_article({**meta, "body_md": body}))
        pages.append(str(page_path))

    learning_path = write_learning_feed(article_dir, index, bodies)
    archive_path = article_dir / "index.html"
    feed_path = article_dir / "feed.xml"
    json_feed_path = article_dir / "feed.json"
    archive_path.write_text(render_archive(index))
    feed_path.write_text(render_feed(index, bodies))
    json_feed_path.write_text(render_json_feed(index, bodies, metadata))
    update_discovery_files(index, root)
    return [
        *pages, str(learning_path), str(archive_path), str(feed_path),
        str(json_feed_path), str(root / "sitemap.xml"), str(root / "llms.txt"),
    ]


def write_learning_feed(article_dir: pathlib.Path, index: list[dict],
                        bodies: dict[str, str]) -> pathlib.Path:
    articles = []
    for row in index[:30]:
        sidecar = json.loads((article_dir / f"{row['slug']}.json").read_text())
        generation = sidecar.get("generation") or {}
        quality = sidecar.get("quality_gate") or {}
        evidence_fingerprint = str(
            generation.get("dossier_sha256") or sidecar.get("board_signature") or ""
        )
        if not re.fullmatch(r"[a-f0-9]{64}", evidence_fingerprint):
            raise SystemExit(
                f"article learning feed lacks an evidence fingerprint for {row['slug']}"
            )
        body = bodies[row["slug"]]
        articles.append({
            "schema": "editorial.learning-article.v1",
            "id": sidecar["id"],
            "product": "liquilens",
            "slug": sidecar["slug"],
            "article_type": sidecar["article_type"],
            "headline": sidecar["headline"],
            "dek": sidecar["dek"],
            "canonical_url": sidecar["canonical_url"],
            "published_at": sidecar["published_at"],
            "evidence_as_of": sidecar["evidence_as_of"],
            "body_markdown": body,
            "word_count": len(re.findall(r"\b[\w$%+.-]+\b", body)),
            "evidence_fingerprint": evidence_fingerprint,
            "generation_mode": generation.get("mode") or "deterministic_fallback",
            "quality_gate": {
                "status": quality.get("status"),
                "checks": list(quality.get("checks") or []),
            },
        })
    if not articles:
        raise SystemExit("article learning feed cannot be empty")
    feed = {
        "schema": "editorial.learning-feed.v1",
        "product": "liquilens",
        "generated_at": max(row["published_at"] for row in articles),
        "articles": articles,
        "authority": {
            "shadow_review_allowed": True,
            "training_allowed": False,
            "factual_authority": "published_article_only",
        },
    }
    path = article_dir / "learning.json"
    temporary = article_dir / f".learning.json.tmp-{os.getpid()}"
    temporary.write_text(json.dumps(feed, indent=2, ensure_ascii=False) + "\n")
    os.replace(temporary, path)
    return path


def datasets_from_dir(path: pathlib.Path) -> dict[str, dict]:
    datasets = {}
    for key in ENDPOINTS:
        candidate = path / f"{key}.json"
        if not candidate.exists():
            raise SystemExit(f"offline dataset is missing {candidate}")
        datasets[key] = json.loads(candidate.read_text())
    return datasets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write today's LiquiLens institution-risk article")
    parser.add_argument("--date", help="publication day, YYYY-MM-DD")
    parser.add_argument("--force", action="store_true", help="replace today's article")
    parser.add_argument("--input-dir", type=pathlib.Path, help="read named JSON datasets instead of live APIs")
    parser.add_argument(
        "--refresh-surfaces", action="store_true",
        help="rebuild pages and feeds from reviewed local articles without fetching",
    )
    args = parser.parse_args(argv)
    if args.refresh_surfaces:
        for path in refresh_article_surfaces():
            print(f"wrote {path}")
        return 0
    date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    index = load_index()
    if not args.force and any(row.get("date") == date for row in index):
        print(f"article for {date} already published, nothing to do")
        return 0
    datasets = datasets_from_dir(args.input_dir) if args.input_dir else fetch_datasets()
    # A forced rewrite should make the same newsroom choice the original run
    # made. Today's outgoing row is not evidence of a prior-day unchanged board.
    selection_index = [row for row in index if row.get("date") != date]
    article = build_article(
        datasets,
        date=date,
        recent_index=selection_index,
        editorial_memory=fetch_editorial_memory(),
    )
    for path in write_article(article):
        print(f"wrote {path}")
    print(
        f"article ready: {article['slug']} [{article['article_type']}] "
        f"{article['word_count']} words, {article['generation']['mode']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
