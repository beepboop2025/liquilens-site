#!/usr/bin/env python3
"""Prepare and record local human reviews of saved three-product research briefs.

Python 3.11+, standard library only. Keep trading_brief.py and
financial_research.py beside this file. All commands are offline and print to
stdout. A worksheet or acknowledgement grants no financial authority.
"""
import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

from financial_research import ENDPOINTS, ResearchError
from trading_brief import SCHEMA as BRIEF_SCHEMA, compare, digest, _fenced_json

WORKSHEET_SCHEMA = "liquilens.treasury-review-worksheet.v1"
RECORD_SCHEMA = "liquilens.treasury-review-record.v1"
MAX_FILE_BYTES = 24 * 1024 * 1024
MAX_SIGNALS = 64
MAX_NODES = 20000
MAX_DEPTH = 32
PRODUCTS = {"funding-brief": "Seiche", "bank-review": "LiquiLens", "exit-brief": "Undertow"}
QUESTIONS = {
    "funding-brief": "Which funding observations changed, and are their source dates suitable for this review?",
    "bank-review": "Which disclosed institution facts support or contradict the concern, and what is missing?",
    "exit-brief": "Does the published BTC depth estimate match the stated size and review horizon?",
}
DISPOSITIONS = ("reviewed", "follow_up", "deferred")
SOURCE_STATES = {
    "stale", "unavailable", "restricted", "unknown", "missing", "blocked",
    "source_review_hold", "partial", "degraded", "failed", "error", "not_covered",
    "not_assessed", "metadata_only", "structural", "ambiguous", "not_disclosed", "historical",
}
STATE_FIELDS = {"status", "state", "freshness", "freshness_status", "source_status",
                "evidence_status", "rights_status", "publication_status", "availability"}
MARKER_FIELDS = {"observed_at", "observation_date", "period_end", "event_time", "knowledge_time",
                 "as_of", "generated_at", "snapshot_generated_at", "source_url", "publisher",
                 "rights", "license", "source_observed_at", "freshness_limit_days"}
BOUNDARIES = {
    "human_review_required": True,
    "execution_authority": False,
    "credit_rating_authority": False,
    "regulatory_approval": False,
    "deposit_safety_assurance": False,
}


def timestamp(value):
    if not isinstance(value, str):
        raise ResearchError("a timezone-aware timestamp is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ResearchError("invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise ResearchError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def read_json(path):
    """Bound local inputs and reject ambiguous keys and non-finite numbers."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def invalid(_value):
        raise ValueError("non-finite JSON number")

    with Path(path).open("rb") as source:
        raw = source.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ResearchError("input exceeds the 24 MiB limit")
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
        digest(value)  # Also rejects numeric overflow such as 1e999.
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ResearchError("input must be finite, unambiguous JSON") from exc
    return value


def validate_brief(brief):
    if not isinstance(brief, dict) or brief.get("schema") != BRIEF_SCHEMA:
        raise ResearchError("input must be a saved trading brief")
    request = brief.get("request")
    if not isinstance(request, dict) or set(request) != {"bank_slug", "size_usd"}:
        raise ResearchError("brief request is incompatible")
    slug = request["bank_slug"]
    if (not isinstance(slug, str) or len(slug) > 128
            or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug)):
        raise ResearchError("this three-product worksheet requires an explicit covered bank slug")
    if type(request["size_usd"]) is not int or request["size_usd"] not in (1000, 10000, 100000, 1000000):
        raise ResearchError("brief must use a supported explicit BTC example size")
    if type(brief.get("verification")) is not bool or brief.get("execution_authority") is not False:
        raise ResearchError("brief must retain its verification and authority fields")
    started, retrieved = timestamp(brief.get("started_at")), timestamp(brief.get("retrieved_at"))
    if retrieved < started:
        raise ResearchError("brief retrieval precedes its start")
    sections = brief.get("sections")
    if (not isinstance(sections, list) or len(sections) != len(PRODUCTS)
            or any(not isinstance(row, dict) or row.get("recipe") not in PRODUCTS for row in sections)
            or {row["recipe"] for row in sections} != set(PRODUCTS)):
        raise ResearchError("brief requires exactly one section for each product")
    for row in sections:
        if row.get("endpoint") != ENDPOINTS[row["recipe"]]:
            raise ResearchError("brief section endpoint does not match its product")
        if row.get("outcome") not in ("evidence_returned", "error", "unavailable", "not_covered", "restricted"):
            raise ResearchError("brief section outcome is incompatible")
        evidence = row.get("evidence")
        if "evidence" in row and not isinstance(evidence, dict):
            raise ResearchError("section evidence must be an object when present")
        if row["outcome"] == "evidence_returned":
            if not evidence:
                raise ResearchError("a returned section must contain evidence")
            if row["recipe"] == "funding-brief":
                funding = evidence.get("money_market")
                if (not isinstance(funding, dict) or funding.get("schema") != "seiche.money-market-desk.v1"
                        or type(funding.get("ok")) is not bool):
                    raise ResearchError("funding evidence does not match the desk contract")
            if row["recipe"] == "bank-review":
                review = evidence.get("review")
                if not isinstance(review, dict) or review.get("slug") != slug:
                    raise ResearchError("bank evidence does not match the requested institution")
            if row["recipe"] == "exit-brief":
                exit_cost = evidence.get("exit_cost")
                if (not isinstance(exit_cost, dict) or exit_cost.get("asset") != "BTC"
                        or type(exit_cost.get("requested_size_usd")) not in (int, float)
                        or exit_cost["requested_size_usd"] != request["size_usd"]):
                    raise ResearchError("exit evidence does not match the requested asset and size")
    return brief


def source_signals(evidence):
    """Index explicit source flags; never infer freshness from a fetch clock.

    This is a bounded inspection aid, not a complete source-specific validator.
    The original evidence, including all clocks, nulls and rights, stays intact.
    """
    found, markers, stack, nodes = [], [], [(evidence, "", 0)], 0
    truncated = False
    markers_truncated = False
    while stack:
        value, path, depth = stack.pop()
        nodes += 1
        if nodes > MAX_NODES or len(found) >= MAX_SIGNALS:
            truncated = True
            break
        if isinstance(value, (dict, list)):
            if depth >= MAX_DEPTH and value:
                truncated = True
                continue
            entries = sorted(value.items()) if isinstance(value, dict) else list(enumerate(value))
            for key, child in reversed(entries):
                pointer = path + "/" + str(key).replace("~", "~0").replace("/", "~1")
                stack.append((child, pointer, depth + 1))
                normalized = child.casefold() if isinstance(child, str) else None
                if key in MARKER_FIELDS and not isinstance(child, (dict, list)):
                    if len(markers) < MAX_SIGNALS:
                        markers.append({"path": pointer, "value": child})
                    else:
                        markers_truncated = True
                if ((key in STATE_FIELDS and normalized in SOURCE_STATES)
                        or (key in ("available", "ok", "publication_eligible") and child is False)):
                    if len(found) < MAX_SIGNALS:
                        found.append({"path": pointer, "value": child})
                    else:
                        truncated = True
    return {"signals": sorted(found, key=lambda row: row["path"]), "inspection_truncated": truncated,
            "source_markers": sorted(markers, key=lambda row: row["path"]),
            "source_markers_truncated": markers_truncated or truncated}


def triage_priority(has_gaps: bool, change_status: str) -> int:
    """Order human review: 0 first, 1 next, 2 routine; never authorize action.

    Pilot policy: incomplete evidence competes with newly changed evidence for
    reviewer attention. This affects ordering only; every section stays visible.
    """
    if has_gaps:
        return 0
    if change_status != "unchanged_payload":
        return 1
    return 2


def prepare(brief, previous=None):
    validate_brief(brief)
    if previous is not None:
        validate_brief(previous)
        if timestamp(previous["retrieved_at"]) >= timestamp(brief["started_at"]):
            raise ResearchError("baseline must finish before the current brief starts")
        if previous["verification"] != brief["verification"]:
            raise ResearchError("operator checks and ordinary reviews require separate baselines")
    # Ignore a supplied comparison summary and recompute from both actual inputs.
    comparison = compare(brief, previous)
    changes = {row["recipe"]: row for row in comparison["sections"]}
    queue = []
    for row in brief["sections"]:
        inspection = source_signals(row.get("evidence", {}))
        delta = changes.get(row["recipe"], {"status": "no_baseline"})
        gaps = (row["outcome"] != "evidence_returned" or bool(inspection["signals"])
                or inspection["inspection_truncated"] or delta.get("changes_truncated", False)
                or delta["status"] == "not_comparable")
        queue.append({
            "recipe": row["recipe"], "product": PRODUCTS[row["recipe"]],
            "priority": triage_priority(gaps, delta["status"]),
            "retrieval_outcome": row["outcome"], "source_inspection": inspection,
            "comparison": delta, "review_question": QUESTIONS[row["recipe"]],
            "freshness_assessment": "human_review_required",
            "evidence_sha256": digest(row["evidence"]) if "evidence" in row else None,
        })
    packet = {
        "schema": WORKSHEET_SCHEMA, "verification": brief["verification"],
        "request": copy.deepcopy(brief["request"]), "evidence_retrieved_at": brief["retrieved_at"],
        "brief_sha256": digest(brief), "previous_brief_sha256": digest(previous) if previous else None,
        "review_queue": sorted(queue, key=lambda row: (row["priority"], row["recipe"])),
        "source_brief": copy.deepcopy(brief), "previous_brief": copy.deepcopy(previous),
        "boundaries": BOUNDARIES.copy(),
        "limitations": [
            "Worksheet hashes detect inconsistent JSON content; they do not authenticate a publisher or reviewer.",
            "Priority orders inspection, not market risk. No combined score or bank-run probability is produced.",
            "Source-state inspection is incomplete by design; inspect original clocks, rights and missingness.",
            "Private deposit flows, withdrawal mandates and institution liquidity buffers are not supplied by this brief.",
            "Undertow's BTC depth example is relevant only to a separately scoped BTC exposure; it is not bank funding or an executable quote.",
        ],
    }
    packet["worksheet_sha256"] = digest(packet)
    return packet


def validate_worksheet(packet):
    if not isinstance(packet, dict) or packet.get("schema") != WORKSHEET_SCHEMA:
        raise ResearchError("input is not a treasury review worksheet")
    expected = prepare(packet.get("source_brief"), packet.get("previous_brief"))
    if digest(packet) != digest(expected):
        raise ResearchError("worksheet was modified or does not match its source briefs")
    return packet


def acknowledge(packet, *, reviewer, assessments, reviewed_at, now=None):
    validate_worksheet(packet)
    if not isinstance(reviewer, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}", reviewer):
        raise ResearchError("use a local reviewer alias of 1-64 letters, digits, dots, dashes or underscores")
    reviewed = timestamp(reviewed_at)
    current = now if now is not None else datetime.now(timezone.utc)
    if reviewed < timestamp(packet["evidence_retrieved_at"]) or reviewed > current:
        raise ResearchError("review time must follow collection and cannot be in the future")
    if not isinstance(assessments, dict) or set(assessments) != set(PRODUCTS):
        raise ResearchError("record one assessment for each of the three product sections")
    for assessment in assessments.values():
        if not isinstance(assessment, dict) or set(assessment) != {"disposition", "note"}:
            raise ResearchError("each assessment needs exactly disposition and note")
        if assessment["disposition"] not in DISPOSITIONS:
            raise ResearchError("disposition must be reviewed, follow_up or deferred")
        note = assessment["note"]
        if (not isinstance(note, str) or not note.strip() or len(note) > 2000
                or any(ord(c) < 32 and c not in "\n\t" for c in note)):
            raise ResearchError("each assessment needs a human note of 1-2000 characters")
    record = {
        "schema": RECORD_SCHEMA, "reviewer_alias": reviewer,
        "reviewed_at": reviewed.isoformat(), "verification": packet["verification"],
        "worksheet_sha256": packet["worksheet_sha256"], "worksheet": copy.deepcopy(packet),
        "assessments": copy.deepcopy(assessments), "boundaries": BOUNDARIES.copy(),
        "measurement_class": "local_self_reported_review",
        "meaning": "A local acknowledgement, not an authenticated sign-off, source-freshness verdict or financial approval.",
    }
    record["record_sha256"] = digest(record)
    return record


def validate_record(record):
    if not isinstance(record, dict) or record.get("schema") != RECORD_SCHEMA:
        raise ResearchError("input is not a treasury review record")
    expected = acknowledge(record.get("worksheet"), reviewer=record.get("reviewer_alias"),
                           assessments=record.get("assessments"), reviewed_at=record.get("reviewed_at"))
    if digest(record) != digest(expected):
        raise ResearchError("review record was modified or no longer matches its worksheet")
    return record


def measure(records):
    """Count local use only, excluding operator checks and repeated acknowledgements."""
    if not 1 <= len(records) <= 100:
        raise ResearchError("measure 1-100 explicitly selected local records")
    accepted, operator_checks, duplicates = {}, 0, 0
    for record in records:
        validate_record(record)
        if record["verification"]:
            operator_checks += 1
            continue
        # Rewording a note, changing its date, or submitting again is not another use.
        key = (record["reviewer_alias"], record["worksheet"]["brief_sha256"])
        if key in accepted:
            duplicates += 1
            if timestamp(record["reviewed_at"]) < timestamp(accepted[key]["reviewed_at"]):
                accepted[key] = record
        else:
            accepted[key] = record
    days = {}
    counts = {disposition: 0 for disposition in DISPOSITIONS}
    for record in accepted.values():
        day = timestamp(record["reviewed_at"]).date().isoformat()
        days.setdefault(record["reviewer_alias"], set()).add(day)
        for assessment in record["assessments"].values():
            counts[assessment["disposition"]] += 1
    return {
        "schema": "liquilens.treasury-review-measurement.v1",
        "measurement_class": "local_self_reported_review", "input_records": len(records),
        "operator_records_excluded": operator_checks, "duplicate_records_excluded": duplicates,
        "distinct_review_acknowledgements": len(accepted), "reviewer_aliases": len(days),
        "aliases_reviewing_on_multiple_utc_days": sum(len(value) > 1 for value in days.values()),
        "section_dispositions": counts, "verified_external_users": None,
        "customer_retention": None, "paid_adoption": None,
        "limitations": "Aliases and notes are local self-reports, not verified people, customers, regulatory approvals, retention cohorts or payments.",
    }


def markdown(packet):
    validate_worksheet(packet)
    lines = ["# Treasury evidence review", "", "Review status: awaiting human assessment.", "",
             "Evidence retrieved: " + packet["evidence_retrieved_at"], "",
             "Worksheet: " + packet["worksheet_sha256"], "",
             "Test traffic: " + str(packet["verification"]).lower(), "",
             "## Requested scope", "", *_fenced_json(packet["request"])]
    for row in packet["review_queue"]:
        lines += ["", "## " + row["product"], "", row["review_question"], "", *_fenced_json(row)]
    lines += ["", "## Source evidence", "",
              "Use the JSON worksheet for the exact current and previous briefs, clocks, rights and source URLs.",
              "", "## Review boundaries", "", *["- " + line for line in packet["limitations"]], ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare", help="prepare a worksheet from saved research")
    prepare_parser.add_argument("brief")
    prepare_parser.add_argument("--previous", help="earlier brief for exactly the same request")
    prepare_parser.add_argument("--format", choices=("json", "markdown"), default="json")
    ack_parser = commands.add_parser("acknowledge", help="record actual human assessments locally")
    ack_parser.add_argument("worksheet")
    ack_parser.add_argument("--reviewer", required=True, help="local alias, never sent to a service")
    ack_parser.add_argument("--assessments", required=True, help="JSON containing three human-written assessments")
    ack_parser.add_argument("--reviewed-at", required=True, help="actual review time including timezone")
    measure_parser = commands.add_parser("measure", help="summarize local records without claiming adoption")
    measure_parser.add_argument("records", nargs="+")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(read_json(args.brief), read_json(args.previous) if args.previous else None)
            if args.format == "markdown":
                print(markdown(result))
                return 0
        elif args.command == "acknowledge":
            result = acknowledge(read_json(args.worksheet), reviewer=args.reviewer,
                                 assessments=read_json(args.assessments), reviewed_at=args.reviewed_at)
        else:
            if len(args.records) > 100:
                raise ResearchError("measure accepts at most 100 local records")
            result = measure([read_json(path) for path in args.records])
        encoded = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)
        if len(encoded.encode()) > MAX_FILE_BYTES:
            raise ResearchError("output exceeds the 24 MiB limit; use smaller source briefs")
        print(encoded)
        return 0
    except (ResearchError, ValueError, TypeError, OSError, RecursionError) as exc:
        print(json.dumps({"status": "error", "reason": str(exc)[:500]}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
