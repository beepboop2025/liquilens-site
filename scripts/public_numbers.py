#!/usr/bin/env python3
"""Generate the public evidence figures from the reviewed evidence capture.

The site is static and has no build step, so its pages used to carry the
headline evidence figures as typed text, and they drifted from the API that
owns them. This script is the build step for those figures. It writes every
registered figure into the committed pages from research/evidence-figures.json,
a reviewed capture of two production evidence responses:

    https://api.liquilens.in/api/evidence/us       (MCP tool evidence_us)
    https://api.liquilens.in/api/evidence/summary  (MCP tool evidence_india)

The Railway PR check, whose success Pages requires before it deploys, runs the
same verification through scripts/verify_public_claims.py and
tests/test_public_numbers.py. It refuses when:

  * the capture is missing, malformed, or outside its contract;
  * a registered figure on a page differs from what the capture renders;
  * an evidence-shaped figure, or a current or retired figure value near
    evidence words, appears on a page without a registration or a reviewed
    exemption, which is what a hand-typed number looks like; or
  * the India ex-fraud recall appears outside the qualified label.

There is no fallback. A capture that cannot be read or validated stops the
build. A refresh writes nothing unless both live responses validate and the
regenerated tree passes every check above, so a refused refresh leaves the
committed capture and pages byte for byte as they were.

    python3 scripts/public_numbers.py --fetch   capture the live API, then write
    python3 scripts/public_numbers.py           write figures from the capture
    python3 scripts/public_numbers.py --check   refuse stale or hand-typed figures
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
CAPTURE_PATH = "research/evidence-figures.json"
SCHEMA = "liquilens.public-evidence-figures.v1"
SOURCES = {
    "us": "https://api.liquilens.in/api/evidence/us",
    "india": "https://api.liquilens.in/api/evidence/summary",
}
US_STATUS = "CURRENT_AMENDED_CONSTRUCTION_PIT"
INDIA_STATUS = "PERIOD_END_PROXY_CONSTRUCTION_PIT"
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
FETCH_TIMEOUT_SECONDS = 30
_VALUE = r"\d[\d,]*(?:\.\d+)?"

# ======================================================================
# WORDING FOR MRINAL TO DECIDE (fleet audit M9 / P2).
#
# This is the only place the India recall wording lives. {ex_fraud} and
# {overall} are filled from the capture (india.summary.recall_ex_fraud_pct
# and india.summary.recall_pct) in each page's number style, so choosing a
# different wording is a change to this one line. The audit proposed
# "88.9% excluding fraud-concealed books (76.2% overall)"; it sits after the
# word "recall" that the pages already used.
#
# Read before choosing: the served ex-fraud figure sets aside only the
# fraud-concealed books that were MISSED. Fraud-concealed books that were
# flagged stay in both its numerator and its denominator, so "excluding
# fraud-concealed books" describes a wider exclusion than the API applies.
INDIA_RECALL_LABEL = (
    "{ex_fraud} recall excluding fraud-concealed books ({overall} overall)")
# ======================================================================


class ContractError(ValueError):
    """The capture or a live response is not what the pages may print."""


# ---------------------------------------------------------------- JSON


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ContractError(f"duplicate JSON key {key!r}")
        out[key] = value
    return out


def _reject_constant(token: str) -> None:
    raise ContractError(f"non-finite JSON value {token}")


def strict_loads(raw: bytes | str) -> Any:
    try:
        return json.loads(raw, object_pairs_hook=_reject_duplicate_keys,
                          parse_constant=_reject_constant)
    except ContractError:
        raise
    except (ValueError, UnicodeDecodeError) as exc:
        raise ContractError(f"not valid JSON: {exc}") from exc


# ------------------------------------------------------------ contract


def _is_number(value: Any) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def _integer(value: Any, where: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ContractError(f"{where} must be an integer >= {minimum}, "
                            f"got {value!r}")
    return value


def _number(value: Any, where: str, low: float, high: float,
            places: int) -> float:
    if not _is_number(value) or not low <= value <= high:
        raise ContractError(f"{where} must be a number in [{low}, {high}], "
                            f"got {value!r}")
    if round(value, places) != value:
        raise ContractError(
            f"{where} is served as {value!r}, finer than the {places} "
            f"decimal place(s) the pages print; refusing to re-round it")
    return float(value)


def _flag_false(value: Any, where: str) -> None:
    if value is not False:
        raise ContractError(
            f"{where} is {value!r}; the pages state NO, so a served change "
            f"needs a copy review before it can publish")


def _exact_keys(value: Any, keys: set[str], where: str) -> dict:
    if not isinstance(value, dict):
        raise ContractError(f"{where} must be an object")
    if set(value) != keys:
        missing = sorted(keys - set(value))
        extra = sorted(set(value) - keys)
        raise ContractError(f"{where} keys differ; missing={missing} "
                            f"extra={extra}")
    return value


def _date(value: Any, where: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",
                                                      value):
        raise ContractError(f"{where} must be a YYYY-MM-DD date")
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ContractError(f"{where} is not a calendar date") from exc


def _evidence_boundary(value: Any, where: str, status: str) -> None:
    _exact_keys(value, {"status", "validated_backtest_eligible",
                        "real_money_eligible"}, where)
    if value["status"] != status:
        raise ContractError(f"{where}.status is {value['status']!r}, the "
                            f"pages print {status}")
    _flag_false(value["validated_backtest_eligible"],
                f"{where}.validated_backtest_eligible")
    _flag_false(value["real_money_eligible"], f"{where}.real_money_eligible")


def validate(capture: Any) -> dict:
    """Raise ContractError unless the capture is exactly in contract."""
    _exact_keys(capture, {"schema", "captured_at", "us", "india", "retired"},
                "capture")
    if capture["schema"] != SCHEMA:
        raise ContractError(f"capture schema is {capture['schema']!r}")
    stamp = capture["captured_at"]
    if not isinstance(stamp, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", stamp):
        raise ContractError("captured_at must be a UTC YYYY-MM-DDTHH:MM:SSZ")

    us = _exact_keys(capture["us"], {
        "source_url", "response_sha256", "market", "provenance", "summary",
        "historical_evidence"}, "us")
    india = _exact_keys(capture["india"], {
        "source_url", "response_sha256", "summary", "uncertainty",
        "ensemble_fisher", "historical_evidence"}, "india")
    for key, section in (("us", us), ("india", india)):
        if section["source_url"] != SOURCES[key]:
            raise ContractError(f"{key}.source_url must be {SOURCES[key]}")
        if not isinstance(section["response_sha256"], str) or \
                not re.fullmatch(r"[0-9a-f]{64}", section["response_sha256"]):
            raise ContractError(f"{key}.response_sha256 must be 64 hex digits")

    if us["market"] != "united_states":
        raise ContractError(f"us.market is {us['market']!r}")
    provenance = _exact_keys(us["provenance"], {
        "panel_bank_quarters", "panel_last_quarter", "exported"},
        "us.provenance")
    _integer(provenance["panel_bank_quarters"],
             "us.provenance.panel_bank_quarters", 1)
    _date(provenance["panel_last_quarter"], "us.provenance.panel_last_quarter")
    _date(provenance["exported"], "us.provenance.exported")
    _evidence_boundary(us["historical_evidence"], "us.historical_evidence",
                       US_STATUS)
    s = _exact_keys(us["summary"], {
        "failures_with_data", "recall_pct", "recall_ci95_pct",
        "median_lead_months", "auc_pooled_24m", "min_lead_months"},
        "us.summary")
    _integer(s["failures_with_data"], "us.summary.failures_with_data", 1)
    recall = _number(s["recall_pct"], "us.summary.recall_pct", 0, 100, 1)
    ci = s["recall_ci95_pct"]
    if not isinstance(ci, list) or len(ci) != 2:
        raise ContractError("us.summary.recall_ci95_pct must be [low, high]")
    low = _number(ci[0], "us.summary.recall_ci95_pct[0]", 0, 100, 1)
    high = _number(ci[1], "us.summary.recall_ci95_pct[1]", 0, 100, 1)
    if not low <= recall <= high:
        raise ContractError("us recall lies outside its own 95% interval")
    floor = _number(s["min_lead_months"], "us.summary.min_lead_months",
                    0, 120, 1)
    median = _number(s["median_lead_months"], "us.summary.median_lead_months",
                     0, 240, 1)
    if median < floor:
        raise ContractError("us median lead is below the served minimum lead")
    _number(s["auc_pooled_24m"], "us.summary.auc_pooled_24m", 0, 1, 3)

    _evidence_boundary(india["historical_evidence"],
                       "india.historical_evidence", INDIA_STATUS)
    t = _exact_keys(india["summary"], {
        "institutions", "failed_with_data", "flagged", "missed_fraud_masked",
        "recall_pct", "recall_ex_fraud_pct", "median_lead_months",
        "discrimination_auc"}, "india.summary")
    institutions = _integer(t["institutions"], "india.summary.institutions", 1)
    failed = _integer(t["failed_with_data"], "india.summary.failed_with_data", 1)
    flagged = _integer(t["flagged"], "india.summary.flagged")
    masked = _integer(t["missed_fraud_masked"],
                      "india.summary.missed_fraud_masked")
    if failed > institutions or flagged + masked > failed:
        raise ContractError("india counts are inconsistent: flagged plus "
                            "fraud-masked misses exceed failures with data")
    overall = _number(t["recall_pct"], "india.summary.recall_pct", 0, 100, 1)
    ex_fraud = _number(t["recall_ex_fraud_pct"],
                       "india.summary.recall_ex_fraud_pct", 0, 100, 1)
    if overall != round(100.0 * flagged / failed, 1):
        raise ContractError("india.summary.recall_pct is not flagged / "
                            "failed_with_data")
    if ex_fraud != round(100.0 * flagged / (failed - masked), 1):
        raise ContractError("india.summary.recall_ex_fraud_pct is not flagged "
                            "/ (failed_with_data - missed_fraud_masked)")
    _number(t["median_lead_months"], "india.summary.median_lead_months",
            0, 240, 1)
    _number(t["discrimination_auc"], "india.summary.discrimination_auc",
            0, 1, 3)
    u = _exact_keys(india["uncertainty"], {"recall_ex_fraud",
                                           "recall_all_failed"},
                    "india.uncertainty")
    for key, k, n, rate in (
            ("recall_ex_fraud", flagged, failed - masked, ex_fraud),
            ("recall_all_failed", flagged, failed, overall)):
        row = _exact_keys(u[key], {"k", "n", "rate_pct"},
                          f"india.uncertainty.{key}")
        if row["k"] != k or row["n"] != n or row["rate_pct"] != rate or \
                type(row["k"]) is not int or type(row["n"]) is not int:
            raise ContractError(f"india.uncertainty.{key} disagrees with the "
                                f"summary counts")
    fisher = _exact_keys(india["ensemble_fisher"], {"p_value_one_sided"},
                         "india.ensemble_fisher")
    p = fisher["p_value_one_sided"]
    if not _is_number(p) or not 0 <= p <= 1:
        raise ContractError("india.ensemble_fisher.p_value_one_sided must be "
                            "a probability")

    # Figures the pages printed before, kept so a stale copy anywhere is
    # caught. --fetch appends each superseded value; nobody edits this.
    retired = capture["retired"]
    current = values(capture)
    if not isinstance(retired, dict) or not set(retired) <= set(current):
        raise ContractError("retired must map published figure keys to lists")
    for key, olds in retired.items():
        if not isinstance(olds, list) or not olds or \
                len(set(olds)) != len(olds) or not all(
                    isinstance(old, str) and re.fullmatch(_VALUE, old)
                    for old in olds):
            raise ContractError(f"retired.{key} must list distinct figures")
        if current[key] in olds:
            raise ContractError(f"retired.{key} lists the current value "
                                f"{current[key]}")
    return capture


def read_capture(path: Path | str) -> dict:
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise ContractError(f"cannot read the evidence capture: {exc}") from exc
    return validate(strict_loads(raw))


def load_capture(root: Path | str = ROOT) -> dict:
    return read_capture(Path(root) / CAPTURE_PATH)


# ------------------------------------------------------------- capture


def _get(payload: Any, *path: str) -> Any:
    value = payload
    for key in path:
        if not isinstance(value, dict) or key not in value:
            raise ContractError(f"response has no {'.'.join(path)}")
        value = value[key]
    return value


def project(us: Any, india: Any, *, us_sha256: str, india_sha256: str,
            captured_at: str,
            retired: dict[str, list[str]] | None = None) -> dict:
    """The capture: the served fields the pages print, nothing else."""
    return validate({
        "schema": SCHEMA,
        "captured_at": captured_at,
        "retired": {} if retired is None else retired,
        "us": {
            "source_url": SOURCES["us"],
            "response_sha256": us_sha256,
            "market": _get(us, "market"),
            "provenance": {
                key: _get(us, "provenance", key)
                for key in ("panel_bank_quarters", "panel_last_quarter",
                            "exported")},
            "summary": {
                key: _get(us, "summary", key)
                for key in ("failures_with_data", "recall_pct",
                            "recall_ci95_pct", "median_lead_months",
                            "auc_pooled_24m", "min_lead_months")},
            "historical_evidence": {
                key: _get(us, "historical_evidence", key)
                for key in ("status", "validated_backtest_eligible",
                            "real_money_eligible")},
        },
        "india": {
            "source_url": SOURCES["india"],
            "response_sha256": india_sha256,
            "summary": {
                **{key: _get(india, "summary", key)
                   for key in ("institutions", "failed_with_data", "flagged",
                               "missed_fraud_masked", "recall_pct",
                               "recall_ex_fraud_pct", "median_lead_months")},
                "discrimination_auc": _get(india, "summary", "discrimination",
                                           "auc"),
            },
            "uncertainty": {
                key: {field: _get(india, "uncertainty", key, field)
                      for field in ("k", "n", "rate_pct")}
                for key in ("recall_ex_fraud", "recall_all_failed")},
            "ensemble_fisher": {
                "p_value_one_sided": _get(india, "ensemble_fisher",
                                          "p_value_one_sided")},
            "historical_evidence": {
                key: _get(india, "historical_evidence", key)
                for key in ("status", "validated_backtest_eligible",
                            "real_money_eligible")},
        },
    })


def as_served(capture: dict) -> dict[str, dict]:
    """The smallest API-shaped responses that project back to the capture.

    Tests use these as the live API, so a refreshed capture never needs a
    second hand-maintained copy of the same figures.
    """
    us, india = capture["us"], capture["india"]
    india_summary = {key: value for key, value in india["summary"].items()
                     if key != "discrimination_auc"}
    india_summary["discrimination"] = {
        "auc": india["summary"]["discrimination_auc"]}
    return {
        SOURCES["us"]: {
            "market": us["market"],
            "provenance": dict(us["provenance"]),
            "summary": {key: (list(value) if isinstance(value, list)
                              else value)
                        for key, value in us["summary"].items()},
            "historical_evidence": dict(us["historical_evidence"]),
        },
        SOURCES["india"]: {
            "summary": india_summary,
            "uncertainty": {key: dict(value)
                            for key, value in india["uncertainty"].items()},
            "ensemble_fisher": dict(india["ensemble_fisher"]),
            "historical_evidence": dict(india["historical_evidence"]),
        },
    }


def fetch_response(url: str) -> tuple[bytes, Any]:
    request = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "liquilens-site-evidence-capture/1",
    })
    try:
        with urllib.request.urlopen(request,
                                    timeout=FETCH_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise ContractError(f"{url} answered HTTP {response.status}")
            if response.geturl() != url:
                raise ContractError(f"{url} redirected to {response.geturl()}")
            content_type = response.headers.get("Content-Type", "")
            if "json" not in content_type.lower():
                raise ContractError(f"{url} served {content_type!r}, not JSON")
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except ContractError:
        raise
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise ContractError(f"{url} could not be fetched: {exc}") from exc
    if len(body) > MAX_RESPONSE_BYTES:
        raise ContractError(f"{url} exceeded {MAX_RESPONSE_BYTES} bytes")
    return body, strict_loads(body)


def _retire(previous: dict | None, fresh: dict) -> dict[str, list[str]]:
    """Carry the retired figures forward and add every superseded one."""
    if previous is None:
        return {}
    old, new = values(previous), values(fresh)
    retired = {key: list(olds) for key, olds in previous["retired"].items()}
    for key, value in old.items():
        if value != new[key] and value not in retired.setdefault(key, []):
            retired[key].append(value)
    return {key: [value for value in retired[key] if value != new[key]]
            for key in sorted(retired)
            if any(value != new[key] for value in retired[key])}


def fetch_capture(fetch: Callable[[str], tuple[bytes, Any]] | None = None,
                  now: Callable[[], datetime] | None = None,
                  previous: dict | None = None) -> dict:
    """Capture both responses, or raise without producing anything."""
    fetch = fetch_response if fetch is None else fetch
    us_body, us = fetch(SOURCES["us"])
    india_body, india = fetch(SOURCES["india"])
    stamp = (now or (lambda: datetime.now(timezone.utc)))()
    fresh = project(
        us, india,
        us_sha256=hashlib.sha256(us_body).hexdigest(),
        india_sha256=hashlib.sha256(india_body).hexdigest(),
        captured_at=stamp.astimezone(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"))
    return validate({**fresh, "retired": _retire(previous, fresh)})


def capture_bytes(capture: dict) -> bytes:
    return (json.dumps(capture, indent=2, ensure_ascii=False) + "\n").encode()


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=path.parent, prefix=".figures-")
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(data)
        os.chmod(temp, 0o644)
        os.replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.unlink(temp)
        raise


def write_capture(root: Path | str, capture: dict) -> None:
    _write_atomic(Path(root) / CAPTURE_PATH, capture_bytes(validate(capture)))


def drift(capture: dict, us: Any, india: Any) -> list[str]:
    """Where the live responses have moved past the committed capture."""
    try:
        live = project(us, india, us_sha256="0" * 64, india_sha256="0" * 64,
                       captured_at=capture["captured_at"])
    except ContractError as exc:
        return [f"the live evidence API is out of the capture contract, so "
                f"{CAPTURE_PATH} cannot be refreshed: {exc}"]
    out = []
    sections = {"us": ("summary", "historical_evidence"),
                "india": ("summary", "uncertainty", "ensemble_fisher",
                          "historical_evidence")}
    for market, names in sections.items():
        for section in names:
            for key, value in live[market][section].items():
                kept = capture[market][section][key]
                if kept != value:
                    out.append(
                        f"{CAPTURE_PATH} is behind {SOURCES[market]}: "
                        f"{market}.{section}.{key} is {kept!r} in the capture "
                        f"and {value!r} live; run python3 "
                        f"scripts/public_numbers.py --fetch")
    return out


# -------------------------------------------------------------- values


def _fixed(value: float, places: int) -> str:
    return f"{value:.{places}f}"


def values(capture: dict) -> dict[str, str]:
    us = capture["us"]["summary"]
    india = capture["india"]["summary"]
    ex_fraud = capture["india"]["uncertainty"]["recall_ex_fraud"]
    return {
        "us.failures": str(us["failures_with_data"]),
        "us.recall": _fixed(us["recall_pct"], 1),
        "us.recall_ci_low": _fixed(us["recall_ci95_pct"][0], 1),
        "us.recall_ci_high": _fixed(us["recall_ci95_pct"][1], 1),
        "us.median_lead": _fixed(us["median_lead_months"], 1),
        "us.auc": _fixed(us["auc_pooled_24m"], 3),
        "india.institutions": str(india["institutions"]),
        "india.recall": _fixed(india["recall_pct"], 1),
        "india.recall_ex_fraud": _fixed(india["recall_ex_fraud_pct"], 1),
        "india.median_lead": _fixed(india["median_lead_months"], 1),
        "india.ex_fraud_flagged": str(ex_fraud["k"]),
        "india.ex_fraud_failed": str(ex_fraud["n"]),
        "india.auc": _fixed(india["discrimination_auc"], 3),
    }


LABEL = "india.recall_label"
LABEL_STYLES = {"", "percent", "tile", "head", "tail"}
_SLOT = re.compile(r"\{(ex_fraud|overall)\}")


def india_label(figures: dict[str, str], style: str = "",
                wording: str | None = None) -> str:
    """The India recall label, in one page style.

    "" and "percent" are prose ("88.9%" / "88.9 percent"); "tile" bolds the
    first figure; "head" and "tail" split a stat tile into its bold number
    and its caption.
    """
    wording = INDIA_RECALL_LABEL if wording is None else wording
    if style not in LABEL_STYLES:
        raise ContractError(f"unknown India label style {style!r}")
    if set(_SLOT.findall(wording)) != {"ex_fraud", "overall"} or \
            len(_SLOT.findall(wording)) != 2 or \
            re.search(r"\{(?!ex_fraud\}|overall\})", wording):
        raise ContractError("the India recall wording must name {ex_fraud} "
                            "and {overall} exactly once and nothing else")
    unit = " percent" if style == "percent" else "%"
    slot = {"ex_fraud": figures["india.recall_ex_fraud"] + unit,
            "overall": figures["india.recall"] + unit}
    first = _SLOT.search(wording)
    prefix = wording[:first.start()]
    figure = slot[first.group(1)]
    rest = _SLOT.sub(lambda m: slot[m.group(1)], wording[first.end():])
    if style == "tile":
        return f"{prefix}<b>{figure}</b>{rest}"
    if style == "head":
        return prefix + figure
    if style == "tail":
        return rest
    return prefix + figure + rest


# ---------------------------------------------------------- registries


@dataclass(frozen=True)
class Figure:
    """One registered occurrence: a page, its text, and how often."""
    path: str
    template: str
    count: int = 1
    requires: tuple[str, ...] = ()


@dataclass(frozen=True)
class Exempt:
    """Evidence-shaped text that is deliberately not generated."""
    path: str
    text: str
    reason: str
    count: int = 1


FIGURES: tuple[Figure, ...] = (
    # ---- homepage: warning horizon, chapter 03 (India median)
    Figure("index.html", '<span class="tminus__chapter-index">03 / 06 '
           '<b>{india.median_lead} months</b></span>'),
    Figure("index.html", "<p>The {india.institutions}-institution "
           "construction-PIT diagnostic records a <b>{india.median_lead}-month"
           " median alert</b> across the replayed warning set.</p>"),
    Figure("index.html",
           "<code>{india.institutions} INSTITUTIONS · MEDIAN ALERT</code>"),
    # ---- homepage: market truth cards
    Figure("index.html", '<div class="market">India · {india.institutions} '
           'institutions</div>'),
    Figure("index.html", '<div class="truth-card__metrics"><span>'
           '{india.recall_label:tile}</span><span><b>{india.median_lead} mo'
           '</b> median lead</span></div><code>PERIOD_END_PROXY_CONSTRUCTION_'
           'PIT</code>'),
    Figure("index.html", '<div class="market">United States · {us.failures} '
           'failures since 2008</div>'),
    Figure("index.html", '<div class="truth-card__metrics"><span><b>'
           '{us.recall}%</b> recall</span><span><b>{us.auc}</b> pooled AUC'
           '</span><span><b>{us.median_lead} mo</b> median lead</span></div>'),
    Figure("index.html", "Its construction-PIT diagnostics report "
           "{india.recall_label} across {india.institutions} Indian "
           "institutions and {us.recall}% recall across {us.failures} US "
           "failures since 2008;"),
    Figure("index.html", "The live board runs now; its {india.institutions}-"
           "institution history is a filing-availability-proxied"),
    # ---- homepage: evidence-status passports
    Figure("index.html", "<h3>{india.institutions} replayed</h3>"),
    Figure("index.html", "Filing-availability-proxied diagnostic over "
           "{india.institutions} institutions; {india.recall_label} and "
           "{india.median_lead}-month median lead."),
    Figure("index.html", "<h3>{us.failures} failures since 2008</h3>"),
    Figure("index.html", "Current-amended-vintage diagnostic: {us.recall}% "
           "recall, {us.median_lead}-month median lead and AUC {us.auc}, "
           "with misses named."),
    # ---- homepage: India construction-PIT study
    Figure("index.html", '<h2 class="reveal">A {india.institutions}-'
           'institution construction-PIT study</h2>'),
    Figure("index.html", '<div class="num">{india.ex_fraud_flagged} of '
           '{india.ex_fraud_failed}</div>'),
    Figure("index.html", "<p>Failures flagged ahead of the record, excluding "
           "books concealed by outright fraud, at a median lead of "
           "{india.median_lead} months. Significant at p &lt; 0.001, "
           "discriminating at AUC {india.auc} against healthy controls,",
           requires=("india_fisher_p_below_0.001",)),
    Figure("index.html", '<span class="src">{india.institutions}-institution '
           'construction-PIT diagnostic across two decades'),
    Figure("index.html", "The separate {india.institutions} institution "
           "balance-sheet diagnostic reports a median of {india.median_lead} "
           "months."),
    # ---- homepage: about and FAQ (visible copy and JSON-LD)
    Figure("index.html", "Historical diagnostics cover {india.institutions} "
           "Indian institutions, {us.failures} US failures since 2008 and "
           "seven European case files,"),
    Figure("index.html", "a current-amended construction-PIT diagnostic over "
           "{us.failures} failures since 2008."),
    Figure("index.html", "The India diagnostic covers <b>{india.institutions}"
           " institutions</b> and currently reports {india.recall_label} with"
           " a {india.median_lead}-month median lead;"),
    Figure("index.html", "The US diagnostic covers <b>{us.failures} failures "
           "since 2008</b>, reports {us.recall}% recall and AUC {us.auc}, and "
           "is"),
    Figure("index.html", "historical diagnostics for {india.institutions} "
           "Indian institutions, {us.failures} US failures since 2008 and "
           "seven European case files."),
    Figure("index.html", "India is PERIOD_END_PROXY_CONSTRUCTION_PIT over "
           "{india.institutions} institutions; the US is "
           "CURRENT_AMENDED_CONSTRUCTION_PIT over {us.failures} failures since "
           "2008;"),
    # ---- US page
    Figure("us/index.html", "historical diagnostic over {us.failures} "
           "failures since 2008, with misses and eligibility flags published.",
           count=3),
    Figure("us/index.html", "CURRENT_AMENDED_CONSTRUCTION_PIT diagnostic over "
           "{us.failures} FDIC receiverships from 2008 to 2026. The served "
           "record reports recall {us.recall} percent,"),
    Figure("us/index.html", "false positive rate 9.7 percent, median lead "
           "{us.median_lead} months and named misses."),
    Figure("us/index.html", 'construction-PIT diagnostic · recall <span '
           'class="live">{us.recall}%</span> of {us.failures} failures since '
           '2008 · median lead <span class="live">{us.median_lead} months'
           '</span>', count=2),
    Figure("us/index.html", '<div class="stat"><div class="num">{us.recall}%'
           '</div><p>served recall among {us.failures} failures since 2008 in '
           'the construction-PIT diagnostic</p></div>'),
    Figure("us/index.html", '<div class="stat"><div class="num">'
           '{us.median_lead} mo</div><p>median lead in the retrospective '
           'diagnostic</p></div>'),
    Figure("us/index.html", '<tr><td class="rowlab">pooled AUC</td><td>'
           '{us.auc}</td></tr>'),
    Figure("us/index.html", '<tr><td class="rowlab">recall, 95% interval</td>'
           '<td>{us.recall_ci_low}% to {us.recall_ci_high}%</td></tr>'),
    # ---- research page
    Figure("research/index.html", "Replays, studies and method notes from "
           "LiquiLens and Seiche. {us.failures} US bank failures since 2008, "
           "{india.institutions} Indian institutions and 7 European case "
           "files, with misses named.", count=3),
    Figure("research/index.html", "<h3>The United States: <em>{us.failures} "
           "failures since 2008, quarter by quarter</em></h3>"),
    Figure("research/index.html", '<div class="stat"><b>{us.recall}%</b>'
           '<span>recall ({us.recall_ci_low} to {us.recall_ci_high})</span>'
           '</div>\n        <div class="stat"><b>{us.median_lead} mo</b><span>'
           'median lead</span></div>\n        <div class="stat"><b>{us.auc}'
           '</b><span>AUC</span></div>'),
    Figure("research/index.html", "of the industry on watch while reporting "
           "{us.recall} percent recall."),
    Figure("research/index.html", "<h3>India: <em>{india.institutions} "
           "institutions, two decades</em></h3>"),
    Figure("research/index.html", "sit in one {india.institutions}-institution"
           " diagnostic."),
    Figure("research/index.html", "<p>The served headline is "
           "{india.recall_label:percent} and a {india.median_lead}-month "
           "median lead."),
    Figure("research/index.html", '<div class="stat"><b>'
           '{india.recall_label:head}</b><span>served{india.recall_label:tail}'
           '</span></div>\n        <div class="stat"><b>{india.median_lead} mo'
           '</b><span>median lead</span></div>'),
    Figure("research/index.html", "method notes from LiquiLens and Seiche: "
           "{us.failures} US failures since 2008, {india.institutions} Indian "
           "institutions and 7 European case files,"),
    Figure("research/index.html", '"name":"The United States: {us.failures} '
           'failures since 2008, quarter by quarter"'),
    Figure("research/index.html", '"name":"India: {india.institutions} '
           'institutions, two decades"'),
    # ---- machine-readable index
    Figure("llms.txt", "construction-PIT diagnostic over {india.institutions} "
           "institutions. Validated-backtest eligible: false. Real-money "
           "eligible: false. The served headline reports "
           "{india.recall_label:percent} and {india.median_lead}-month median"
           " lead."),
    Figure("llms.txt", "- United States: CURRENT_AMENDED_CONSTRUCTION_PIT over"
           " all {us.failures} FDIC failures since 2008. Validated-backtest "
           "eligible: false. Real-money eligible: false. The current "
           "diagnostic reports {us.recall} percent recall, {us.median_lead}-"
           "month median lead, and pooled 24-month AUC {us.auc}; misses are "
           "named."),
    # ---- other routes and assets
    Figure("access/index.html", "India is a construction-PIT record over "
           "{india.institutions} institutions. The United States is a "
           "current-amended construction-PIT record over {us.failures} FDIC "
           "failures since 2008 ({us.recall} percent recall on the served "
           "validation)."),
    Figure("use-cases/index.html", "a current-amended construction-PIT US "
           "diagnostic over {us.failures} failures since 2008,"),
    Figure("brand/_x-banner.html", '<div class="stat"><b>{us.failures}</b>'
           '<span>US FAILURES REPLAYED</span></div>\n  <div class="stat"><b>'
           '{us.recall}%</b><span>RECALL, POINT IN TIME</span></div>\n  <div '
           'class="stat"><b>{us.median_lead} mo</b><span>MEDIAN LEAD</span>'
           '</div>'),
    Figure("evidence-library.js", "count.textContent = '{india.median_lead} "
           "mo median diagnostic lead';"),
)

# Figures that are evidence-shaped but are not the served headline: studies
# on an earlier cut, a dated card, and figures from other study records.
# Each is pinned verbatim, so any edit to it surfaces in the guard again.
EXEMPT: tuple[Exempt, ...] = (
    Exempt("us/index.html", "it catches <b>64.7 percent of the 552 failures "
           "since 2008 by itself</b>, and adding it lifts the full engine from "
           "72.0 to 75.5 percent recall at the same alarm budget",
           "July 2026 deposit-desperation study on its own 552-failure cut; "
           "not served by the API, so it cannot be regenerated"),
    Exempt("research/index.html", "Added to the score, recall rises from 72.0"
           " to 75.5 percent at the same alarm budget",
           "the same July 2026 study card"),
    Exempt("research/index.html", '<div class="stat"><b>72.0 → 75.5%</b><span>'
           'recall, same budget</span></div>', "the same July 2026 study card"),
    Exempt("research/index.html", '<p class="src">study on 552 failures, 2008'
           ' to 2026', "the same July 2026 study card"),
    Exempt("us/index.html", "Current screens plus a 552-failure diagnostic, "
           "with recent misses named. HISTORICAL CONTRACT: 552 FAILURE "
           "REPLAYS. 2026 REPLAY: 2 OF 4 FLAGGED / 2 MISSES. REVIEWED CUT "
           "2026-08-09",
           "the /us/ route card is dated REVIEWED CUT 2026-08-09 and drawn by "
           "scripts/static_social_cards.py; its 2026 replay line has no "
           "served source, so the card is refreshed as a whole or not at all",
           count=3),
    Exempt("index.html", "the RBI's own PCA tripwires fired a median of "
           "<b>41 months</b>", "PCA tripwire lead, not part of the served "
           "India summary"),
    Exempt("index.html", "those public tripwires fired a median of 41 months",
           "the same PCA tripwire lead, in the engine list"),
    Exempt("index.html", "were flagged at a median of 6.5 months",
           "rating-timeline case study, a separate record"),
    Exempt("index.html", "Conservative mode caught 11 of 16 with zero false "
           "alarms on healthy controls. Sensitive mode adds the funding lens "
           "and caught 16 of 18,",
           "both alert modes come from /api/evidence/alert-modes, which the "
           "capture does not hold; the sensitive count repeats the ex-fraud "
           "recall without its qualifier"),
    Exempt("us/index.html", "Score variants are printed separately: the "
           "frozen policy reads 72.8 percent, adding private-credit exposure "
           "reads 72.0 percent, and adding deposit desperation reads 75.5 "
           "percent at the same alarm budget.",
           "July 2026 score-variant study: its frozen-policy figure is the "
           "earlier cut's recall and is compared with variants that are not "
           "served, so it cannot move alone"),
    Exempt("world-economy/index.html", "48 · 552 · 7<small>India "
           "institutions · US failures · Europe case files</small>",
           "dated discovery snapshot of 21 August 2026; the section says the "
           "live ledgers win when the numbers change"),
)

# Dated or separately generated history. These are records of what was
# published when, not current claims, and their own generators own them.
DATED_PREFIXES = (
    "articles/",
    "ship-log/",
    "protocol/discovery-observations/",
    "protocol/release-evidence/",
    "banking/institutions/",
    "questions/evidence-",
)
DATED_BLOCKS = (
    ("<!-- DAILY-ARTICLES:START -->", "<!-- DAILY-ARTICLES:END -->"),
)
SKIP_ROOTS = {"scripts", "tests", "ops", "edge", "node_modules"}
SKIP_DIRS = {".git", ".github", "node_modules"}
BINARY_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".ico",
                   ".pdf", ".woff", ".woff2", ".ttf", ".otf", ".eot", ".zip",
                   ".gz", ".mp4", ".webm", ".mp3", ".wav")

# A figure and its words may sit in neighbouring inline elements (a stat
# tile's number and caption), but never across a line or more than two tags:
# that is the next element, not the same claim. Spaces include a literal
# no-break space (\s) and its entity spellings.
_SPACE = r"(?:\s(?<!\n)|&nbsp;|&#160;|&#xa0;)*"
_WS = r"(?:\s|&nbsp;|&#160;|&#xa0;)+"
_GAP = _SPACE + r"(?:<[^>\n]*>" + _SPACE + r"){0,2}"
_NUM = r"(?P<n>\d{1,3}(?:\.\d+)?)"
_PCT = r"\s?(?:%|percent\b|per" + _SPACE + r"cent\b)"
_MONTHS = r"(?:-|" + _GAP + r")(?:mo|months?)\b"
SHAPES: tuple[tuple[str, re.Pattern[str]], ...] = (
    # Plural nouns only: "a 503 failure" is an HTTP error, not a cohort.
    ("a US failure count", re.compile(
        r"(?<![\d,.])(?P<n>\d{3,4})(?:-failure\b|" + _GAP +
        r"(?:(?:US|U\.S\.|FDIC|bank)" + _WS + r")*"
        r"(?:failures|collapses|receiverships|failed" + _WS + r"banks|"
        r"failure" + _WS + r"replays)\b)", re.I)),
    ("a recall percentage", re.compile(
        r"(?<![\d.])" + _NUM + _PCT + _GAP +
        r"(?:served" + _WS + r"|overall" + _WS + r")?recall\b", re.I)),
    ("a recall percentage", re.compile(
        r"\brecall\b(?:" + _WS + r"rate)?" + _GAP +
        r"(?:(?:of|is|was|reads|at|stood" + _WS + r"at)" + _WS + r"|:" +
        _SPACE + r"|rises" + _WS + r"from" + _WS + r"\d{1,3}(?:\.\d+)?" +
        _WS + r"to" + _WS + r")?" + _GAP + _NUM + _PCT, re.I)),
    ("a recall interval", re.compile(
        r"\b(?:recall|interval|CI)\b[^<>\n]{0,16}?" + _GAP +
        r"\(?(?P<n>\d{2}\.\d)%?" + _SPACE + r"(?:to|-|\u2013)" + _SPACE +
        r"\d{2}\.\d", re.I)),
    ("an AUC", re.compile(
        r"(?<![\d.])(?P<n>0\.\d{2,3})" + _GAP +
        r"(?:pooled" + _WS + r")?(?:24-month" + _WS + r")?AU(?:RO)?C\b",
        re.I)),
    ("an AUC", re.compile(
        r"\bAU(?:RO)?C\b" + _GAP + r"(?:(?:of|is|was|at)" + _WS + r"|:" +
        _SPACE + r")?" + _GAP + r"(?P<n>0\.\d{2,3})", re.I)),
    ("a median lead", re.compile(
        r"(?<![\d.])(?P<n>\d{1,3}(?:\.\d+)?)" + _MONTHS + _GAP +
        r"(?:diagnostic" + _WS + r")?median\b", re.I)),
    # The figure must carry a time unit: "the median alert of 12 venues" is
    # not a lead.
    ("a median lead", re.compile(
        r"\bmedian\b(?:" + _WS + r"[a-z]+){0,3}?" + _WS +
        r"(?:lead|alert)(?:" + _WS + r"time)?(?:" + _WS +
        r"(?:of|was|is))?" + _GAP + r"(?P<n>\d{1,3}(?:\.\d+)?)" + _MONTHS,
        re.I)),
    ("a median lead", re.compile(
        r"\bmedian" + _WS + r"of\b" + _GAP + r"(?P<n>\d{1,3}(?:\.\d+)?)" +
        _MONTHS, re.I)),
    # Singular "institution" is the cohort adjective ("48-institution
    # diagnostic"), not "12 institution types" or "institution-level".
    ("an India cohort size", re.compile(
        r"(?<![\d,.])(?P<n>\d{2,3})(?:" + _WS + r"|-)(?:Indian" + _WS +
        r"(?:institutions?|lenders?|banks?)\b|institution\b"
        r"(?![\s-]*(?:types?\b|level\b|s\b)))", re.I)),
    ("an India cohort size", re.compile(
        r"\bIndia" + _SPACE + r"(?:·|:)" + _GAP + r"(?P<n>\d{2,3})" + _WS +
        r"(?:institutions|lenders)\b", re.I)),
)
YEAR = re.compile(r"(?:19|20)\d{2}")
# Words that make a bare figure an evidence claim when they sit close by.
_EVIDENCE_WORDS = re.compile(
    r"recall|AUC|AUROC|median|lead|failure|diagnostic|flagged|fraud|India|"
    r"receivership|FDIC", re.I)
_CONTEXT = 160

_PLACEHOLDER = re.compile(r"\{([a-z_.]+)(?::([a-z]+))?\}")
_NUMBER_REGION = r"(?<![\d.,])\d[\d,]*(?:\.\d+)?(?![\d])"
# A label region never crosses a sentence or clause boundary, so an edit next
# to a label cannot widen it over neighbouring prose.
_IN_CLAUSE = r"(?!\.\s|;\s|:\s)"
_LABEL_REGIONS = {
    "": r"(?:" + _IN_CLAUSE + r"[^<>\n]){1,200}?",
    "percent": r"(?:" + _IN_CLAUSE + r"[^<>\n]){1,200}?",
    "tile": r"(?:(?!</span>)" + _IN_CLAUSE + r"[^\n]){1,240}?",
    "head": r"[^<>\n]{1,80}?",
    "tail": r"(?:" + _IN_CLAUSE + r"[^<>\n]){0,200}?",
}
# What may be replaced: a region that already holds a percentage.
_LABEL_LIKE = re.compile(r"\d(?:\.\d+)?(?:%|\s?percent)")


def _compile(template: str) -> tuple[re.Pattern[str], list[tuple[str, str]]]:
    pattern, slots, position = [], [], 0
    for match in _PLACEHOLDER.finditer(template):
        key, style = match.group(1), match.group(2) or ""
        pattern.append(re.escape(template[position:match.start()]))
        if key == LABEL:
            if style not in _LABEL_REGIONS:
                raise ContractError(f"unknown India label style {style!r}")
            region = _LABEL_REGIONS[style]
        elif style:
            raise ContractError(f"{key} takes no style")
        else:
            region = _NUMBER_REGION
        pattern.append(f"(?P<s{len(slots)}>{region})")
        slots.append((key, style))
        position = match.end()
    pattern.append(re.escape(template[position:]))
    return re.compile("".join(pattern)), slots


def _render(key: str, style: str, figures: dict[str, str], path: str) -> str:
    if key == LABEL:
        text = india_label(figures, style)
        if path.endswith((".html", ".htm")):
            # The label carries its own <b> in the tile style only.
            parts = re.split(r"(</?b>)", text)
            return "".join(part if part in ("<b>", "</b>")
                           else html.escape(part, quote=True)
                           for part in parts)
        if path.endswith(".txt"):
            return text
        raise ContractError(f"{path}: the India label is only for HTML and "
                            f"plain-text pages")
    if key not in figures:
        raise ContractError(f"unknown figure {key!r}")
    return figures[key]


def _blocks(text: str) -> list[tuple[int, int]]:
    spans = []
    for start_marker, end_marker in DATED_BLOCKS:
        for match in re.finditer(re.escape(start_marker) + r".*?" +
                                 re.escape(end_marker), text, re.S):
            spans.append(match.span())
    return spans


def _exempt_spans(path: str, text: str) -> tuple[list[tuple[int, int]],
                                                 list[str]]:
    spans, problems = [], []
    for item in EXEMPT:
        if item.path != path:
            continue
        found = [m.span() for m in re.finditer(re.escape(item.text), text)]
        if len(found) != item.count:
            problems.append(
                f"{path}: the exempt text {item.text[:70]!r} appears "
                f"{len(found)} time(s), expected {item.count}; an edited "
                f"exemption must be reviewed again in scripts/public_numbers.py")
        spans.extend(found)
    return spans, problems


def mask_exempt(path: str, text: str) -> str:
    """Blank exempt and dated text so a scanner cannot count it."""
    spans, _ = _exempt_spans(path, text)
    return _mask(text, spans + _blocks(text))


def _mask(text: str, spans: list[tuple[int, int]]) -> str:
    chars = list(text)
    for start, end in spans:
        for index in range(start, end):
            if chars[index] != "\n":
                chars[index] = "#"
    return "".join(chars)


def _requirement(name: str, capture: dict) -> str | None:
    if name == "india_fisher_p_below_0.001":
        p = capture["india"]["ensemble_fisher"]["p_value_one_sided"]
        if not p < 0.001:
            return (f"the homepage says p < 0.001 and the served one-sided "
                    f"Fisher p is {p}")
        return None
    raise ContractError(f"unknown requirement {name!r}")


def rewrite(path: str, text: str, capture: dict,
            figures: dict[str, str] | None = None) -> tuple[str, list[str],
                                                            list[tuple[int,
                                                                       int]]]:
    """Return the page with its figures generated, problems, claimed spans."""
    figures = values(capture) if figures is None else figures
    problems: list[str] = []
    edits: dict[tuple[int, int], str] = {}
    for figure in FIGURES:
        if figure.path != path:
            continue
        pattern, slots = _compile(figure.template)
        matches = list(pattern.finditer(text))
        if len(matches) != figure.count:
            problems.append(
                f"{path}: the registered figure {figure.template[:80]!r} "
                f"appears {len(matches)} time(s), expected {figure.count}")
            continue
        for match in matches:
            for index, (key, style) in enumerate(slots):
                span = match.span(f"s{index}")
                rendered = _render(key, style, figures, path)
                held = text[span[0]:span[1]]
                if key == LABEL and style != "tail" and held != rendered and \
                        not _LABEL_LIKE.search(held):
                    line = text.count("\n", 0, span[0]) + 1
                    problems.append(
                        f"{path}:{line}: the India label slot holds "
                        f"{held[:60]!r}, which is not a recall figure; "
                        f"refusing to overwrite it")
                    continue
                if edits.get(span, rendered) != rendered:
                    problems.append(f"{path}: two registrations disagree at "
                                    f"offset {span[0]}")
                edits[span] = rendered
        for name in figure.requires:
            problem = _requirement(name, capture)
            if problem:
                problems.append(f"{path}: {problem}")
    ordered = sorted(edits)
    for (_, end), (start, _) in zip(ordered, ordered[1:]):
        if start < end:
            problems.append(f"{path}: two registered figures overlap at "
                            f"offset {start}")
    out, position = [], 0
    for start, end in ordered:
        out.append(text[position:start])
        out.append(edits[(start, end)])
        position = end
    out.append(text[position:])
    return "".join(out), problems, ordered


def stale(path: str, text: str, capture: dict,
          figures: dict[str, str] | None = None) -> list[str]:
    """Each registered figure the page publishes differently from the capture."""
    figures = values(capture) if figures is None else figures
    _, found, spans = rewrite(path, text, capture, figures)
    if found:
        return found
    out = []
    for figure in FIGURES:
        if figure.path != path:
            continue
        pattern, slots = _compile(figure.template)
        for match in pattern.finditer(text):
            for index, (key, style) in enumerate(slots):
                start, end = match.span(f"s{index}")
                published = text[start:end]
                expected = _render(key, style, figures, path)
                if published != expected:
                    line = text.count("\n", 0, start) + 1
                    out.append(f"{path}:{line}: publishes {published!r} where "
                               f"{CAPTURE_PATH} renders {expected!r} for "
                               f"{key}")
    return sorted(set(out), key=lambda item: (int(item.split(":")[1]), item))


_DECIMAL_KEYS = ("us.recall", "us.recall_ci_low", "us.recall_ci_high",
                 "us.median_lead", "us.auc", "india.recall",
                 "india.recall_ex_fraud", "india.median_lead", "india.auc")


def _line(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def hand_typed(path: str, text: str, claimed: list[tuple[int, int]],
               figures: dict[str, str],
               retired: dict[str, list[str]] | None = None) -> list[str]:
    """Evidence figures on the page that nothing generates.

    Two nets. SHAPES catch any number in an evidence phrasing. The value
    nets catch the current and every retired figure in any phrasing, when
    evidence words sit close by.
    """
    retired = retired or {}
    exempt, problems = _exempt_spans(path, text)
    masked = _mask(text, claimed + exempt + _blocks(text))
    for label, pattern in SHAPES:
        for match in pattern.finditer(masked):
            value = match.group("n")
            if label == "a US failure count" and YEAR.fullmatch(value):
                continue
            problems.append(
                f"{path}:{_line(masked, match.start())}: {label} {value} is "
                f"typed into the page; register it in scripts/public_numbers.py"
                f" so it is generated from {CAPTURE_PATH}, or exempt it with a "
                f"reason")

    def near(start: int, end: int, words: re.Pattern[str], reach: int) -> bool:
        return bool(words.search(masked[max(0, start - reach):end + reach]))

    def report(match: re.Match[str], key: str, value: str) -> None:
        line = _line(masked, match.start())
        if value != figures[key]:
            problems.append(
                f"{path}:{line}: {value} was the published {key} before the "
                f"current capture and is still on the page; register or exempt "
                f"it in scripts/public_numbers.py")
        elif key == "india.recall_ex_fraud":
            problems.append(
                f"{path}:{line}: the India ex-fraud recall {value} appears "
                f"outside the qualified label; use {{{LABEL}}} so it carries "
                f"its qualifier")
        else:
            problems.append(
                f"{path}:{line}: {key} {value} is typed into the page; register"
                f" it in scripts/public_numbers.py")

    for key in _DECIMAL_KEYS:
        for value in [figures[key], *retired.get(key, [])]:
            for match in re.finditer(r"(?<![\d.,])" + re.escape(value) +
                                     r"(?![\d])", masked):
                if near(match.start(), match.end(), _EVIDENCE_WORDS, _CONTEXT):
                    report(match, key, value)
    failure_words = re.compile(r"failure|FDIC|receivership|replay", re.I)
    for value in [figures["us.failures"], *retired.get("us.failures", [])]:
        for match in re.finditer(r"(?<![\d,.])" + re.escape(value) +
                                 r"(?![\d,])", masked):
            if near(match.start(), match.end(), failure_words, 60):
                report(match, "us.failures", value)
    for value in [figures["india.institutions"],
                  *retired.get("india.institutions", [])]:
        for match in re.finditer(r"(?<![\d,.])" + re.escape(value) +
                                 r"(?:-|" + _GAP + r")(?:replayed\b|Indian\b|"
                                 r"institutions?\b|lenders?\b)", masked, re.I):
            report(match, "india.institutions", value)
    pair = (r"(?<!\d)" + re.escape(figures["india.ex_fraud_flagged"]) +
            _WS + r"of" + _WS + re.escape(figures["india.ex_fraud_failed"]) +
            r"(?!\d)")
    for match in re.finditer(pair, masked):
        problems.append(
            f"{path}:{_line(masked, match.start())}: the India ex-fraud count "
            f"{match.group(0)} is typed into the page; register it in "
            f"scripts/public_numbers.py")
    return problems


_CHAPTER = re.compile(
    r'class="tminus__chapter[^"]*" data-month="(?P<m>[^"]+)" '
    r'data-progress="(?P<p>[^"]+)" data-phase="(?P<phase>[^"]+)"')
_MARK = re.compile(r'class="tminus__mark[^"]*" style="left:(?P<l>[^%"]+)%"')


def countdown_spans(text: str) -> list[tuple[int, int]]:
    """The India median the horizon draws, verified by countdown_problems."""
    return [match.span("m") for match in _CHAPTER.finditer(text)
            if match.group("phase") == "Cohort median"]


def countdown_problems(text: str, figures: dict[str, str]) -> list[str]:
    """The homepage warning horizon draws the India median to scale.

    Its geometry is a design decision, so it is verified rather than moved:
    a new median refuses with the exact attributes to set.
    """
    chapters = [(m.group("m"), m.group("p"), m.group("phase"))
                for m in _CHAPTER.finditer(text)]
    marks = [m.group("l") for m in _MARK.finditer(text)]
    median = [c for c in chapters if c[2] == "Cohort median"]
    if len(median) != 1 or len(marks) != len(chapters) or not chapters:
        return ["index.html: the warning horizon no longer has exactly one "
                "'Cohort median' chapter with a matching track mark"]
    expected = figures["india.median_lead"]
    if median[0][0] != expected:
        try:
            top = float(chapters[0][0])
            share = (top - float(expected)) / top
            where = (f'set data-month="{expected}" data-progress='
                     f'"{f"{share:.3f}".lstrip("0")}" and its mark to '
                     f'left:{100 * share:.1f}%')
        except (ValueError, ZeroDivisionError):
            where = "move the chapter and its mark"
        return [f"index.html: the warning horizon draws the India median at "
                f"data-month=\"{median[0][0]}\" and the capture serves "
                f"{expected}; {where} (the track is linear from "
                f"{chapters[0][0]} months to 0), keeping chapters in order"]
    try:
        months = [float(c[0]) for c in chapters]
        top = months[0]
        for (month, progress, _), left in zip(chapters, marks):
            share = (top - float(month)) / top
            if abs(float(progress) - share) > 0.0006 or \
                    abs(float(left) - 100 * share) > 0.06:
                return [f"index.html: the warning horizon chapter at "
                        f"{month} months is not drawn to scale"]
    except (ValueError, ZeroDivisionError):
        return ["index.html: the warning horizon geometry is unreadable"]
    if months != sorted(months, reverse=True):
        return ["index.html: the warning horizon chapters are out of order "
                "for the served India median"]
    return []


def _publishable(root: Path) -> list[str]:
    out = []
    for directory, names, files in os.walk(root):
        relative = Path(directory).relative_to(root)
        # Dot directories never enter the Pages artifact except .well-known
        # (scripts/stage_pages_artifact.py), so only that one is scanned.
        names[:] = sorted(
            name for name in names
            if name not in SKIP_DIRS
            and (not name.startswith(".") or name == ".well-known")
            and not (relative == Path(".") and name in SKIP_ROOTS))
        for name in sorted(files):
            if name.lower().endswith(BINARY_SUFFIXES):
                continue
            path = (relative / name).as_posix()
            if path == CAPTURE_PATH or path.startswith(DATED_PREFIXES):
                continue
            out.append(path)
    return out


def _read(root: Path, path: str,
          overlay: dict[str, str] | None = None) -> str | None:
    """The page as text; None only for bytes (a NUL), never for an encoding.

    A page served in another encoding still carries its figures, so it is
    read as Latin-1 rather than skipped.
    """
    if overlay and path in overlay:
        return overlay[path]
    blob = (root / path).read_bytes()
    if b"\x00" in blob:
        return None
    try:
        return blob.decode("utf-8")
    except UnicodeDecodeError:
        return blob.decode("latin-1")


def _registered_paths() -> list[str]:
    return sorted({figure.path for figure in FIGURES})


def problems(root: Path | str = ROOT, *, scan: bool = True,
             capture: dict | None = None,
             overlay: dict[str, str] | None = None) -> list[str]:
    """Every reason the pages may not publish as they are.

    capture and overlay let a refresh verify the tree it is about to write
    (the new capture and the planned pages) before writing any of it.
    """
    root = Path(root)
    try:
        capture = load_capture(root) if capture is None else validate(capture)
    except ContractError as exc:
        return [f"REFUSING without a valid evidence capture: {exc}"]
    figures = values(capture)
    out: list[str] = []
    for path in _registered_paths():
        try:
            text = _read(root, path, overlay)
        except OSError as exc:
            out.append(f"{path}: registered page cannot be read: {exc}")
            continue
        if text is None:
            out.append(f"{path}: registered page is not text")
            continue
        out.extend(stale(path, text, capture, figures))
        if path == "index.html":
            out.extend(countdown_problems(text, figures))
    if scan:
        for path in _publishable(root):
            text = _read(root, path, overlay)
            if text is None:
                continue
            _, _, claimed = rewrite(path, text, capture, figures)
            if path == "index.html":
                claimed = claimed + countdown_spans(text)
            out.extend(hand_typed(path, text, claimed, figures,
                                  capture["retired"]))
    return out


def plan(root: Path | str, capture: dict) -> dict[str, str]:
    """The registered pages as the capture renders them; writes nothing."""
    root = Path(root)
    figures = values(validate(capture))
    pending: dict[str, str] = {}
    for path in _registered_paths():
        try:
            text = (root / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ContractError(f"{path}: registered page cannot be read: "
                                f"{exc}") from exc
        expected, found, _ = rewrite(path, text, capture, figures)
        if found:
            raise ContractError("; ".join(found))
        if expected != text:
            pending[path] = expected
    return pending


def apply(root: Path | str, capture: dict, *,
          write_capture_file: bool = False) -> list[str]:
    """Write the planned pages (and the capture) only if all of it passes.

    Nothing is written when any check fails, so a refused refresh leaves the
    committed capture and every page byte for byte as they were.
    """
    root = Path(root)
    pending = plan(root, capture)
    found = problems(root, capture=capture, overlay=pending)
    if found:
        raise ContractError("the result would not publish:\n  - " +
                            "\n  - ".join(found))
    for path, text in pending.items():
        _write_atomic(root / path, text.encode("utf-8"))
    if write_capture_file:
        write_capture(root, capture)
    return sorted(pending)


def render(root: Path | str = ROOT) -> list[str]:
    """Write every registered figure from the committed capture."""
    return apply(root, load_capture(root))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="refuse stale, unregistered or unqualified figures")
    mode.add_argument("--fetch", action="store_true",
                      help="capture the live evidence API, then write figures")
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)
    root = Path(args.root)
    try:
        if args.fetch:
            previous = None
            if (root / CAPTURE_PATH).exists():
                # The retired figures ride forward from the committed capture,
                # so an unreadable one stops the refresh instead of losing them.
                previous = load_capture(root)
            capture = fetch_capture(previous=previous)
            changed = apply(root, capture, write_capture_file=True)
            print(f"captured {SOURCES['us']} and {SOURCES['india']} at "
                  f"{capture['captured_at']}; wrote figures into "
                  f"{len(changed)} page(s): {', '.join(changed) or 'none'}")
        elif not args.check:
            changed = render(root)
            print(f"wrote figures into {len(changed)} page(s): "
                  f"{', '.join(changed) or 'none changed'}")
    except (ContractError, OSError) as exc:
        print(f"REFUSING: {exc}", file=sys.stderr)
        return 1
    found = problems(root)
    if found:
        print("REFUSING: the public figures do not follow the evidence capture",
              file=sys.stderr)
        for problem in found:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    capture = load_capture(root)
    print(f"public figures follow {CAPTURE_PATH} (captured "
          f"{capture['captured_at']}): {len(FIGURES)} registrations, "
          f"{len(EXEMPT)} reviewed exemptions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
