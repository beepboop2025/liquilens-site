#!/usr/bin/env python3
"""Free, source-separated funding, bank and exit research. Python 3.11+, no packages.

Keep financial_research.py beside this file. A run is finite and caller-triggered;
there are no background calls or automatic retries. Evidence is never an order.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

from financial_research import Client, ENDPOINTS, ResearchError, exchange, parse_json, research

SCHEMA = "liquilens.trading-brief.v1"
MAX_PREVIOUS_BYTES = 8 * 1024 * 1024
MAX_CHANGES = 64
MAX_CHANGE_DEPTH = 16
MAX_CHANGE_BYTES = 16 * 1024
REQUIRED = {
    "funding-brief": ("money_market_context",),
    "exit-brief": ("exit_cost",),
    "bank-review": ("banking_specialisation_coverage", "bank_asset_quality_review"),
}
LIMITS = [
    "Research only. No trade, credit, deposit-safety or compliance decision is authorized.",
    "Retrieval time is not source freshness. Read each section's source dates and status.",
    "BTC exit costs are published depth estimates, not executable quotes.",
    "Changed source payloads can reflect revisions or coverage changes, not market moves.",
]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def evidence_changes(previous, current):
    """Bounded structural differences; pointers address the section's evidence.

    Added/removed containers and type changes are represented at their own path.
    Arrays are positional. No source values or clocks are discarded or rewritten.
    """
    changes, reasons = [], set()
    encoded_bytes = 2  # JSON list brackets.
    stopped = False

    def add(path, kind):
        nonlocal encoded_bytes, stopped
        change = {"path": path, "kind": kind}
        size = len(json.dumps(change, separators=(",", ":")).encode()) + bool(changes)
        if len(changes) >= MAX_CHANGES:
            reasons.add("max_changes")
        elif encoded_bytes + size > MAX_CHANGE_BYTES:
            reasons.add("max_bytes")
        else:
            changes.append(change)
            encoded_bytes += size
            return
        stopped = True

    def visit(before, after, path, depth):
        if stopped:
            return
        if type(before) is not type(after):
            add(path, "changed")
        elif isinstance(before, (dict, list)):
            if depth >= MAX_CHANGE_DEPTH:
                if digest(before) != digest(after):
                    reasons.add("max_depth")
                    add(path, "changed")
                return
            keys = sorted(before.keys() | after.keys()) if isinstance(before, dict) else range(max(len(before), len(after)))
            for key in keys:
                child = path + "/" + str(key).replace("~", "~0").replace("/", "~1")
                old_present = key in before if isinstance(before, dict) else key < len(before)
                new_present = key in after if isinstance(after, dict) else key < len(after)
                if not old_present:
                    add(child, "added")
                elif not new_present:
                    add(child, "removed")
                else:
                    visit(before[key], after[key], child, depth + 1)
                if stopped:
                    break
        elif digest(before) != digest(after):
            # JSON distinctions include false versus 0, 0 versus 0.0 and -0.0.
            add(path, "changed")

    visit(previous, current, "", 0)
    return {"changes": changes, "changes_truncated": bool(reasons),
            "truncation_reasons": sorted(reasons)}


def previous_report(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_PREVIOUS_BYTES + 1)
    if len(raw) > MAX_PREVIOUS_BYTES:
        raise ResearchError("previous brief exceeds the 8 MiB limit")
    value = parse_json(raw)
    if (not isinstance(value, dict) or value.get("schema") != SCHEMA
            or not isinstance(value.get("sections"), list)
            or not isinstance(value.get("request"), dict)):
        raise ResearchError("previous file is not a trading brief")
    return value


def compare(current, previous):
    """Compare the same request and evidence bytes, never retrieval timestamps."""
    if previous is None:
        return {"status": "no_baseline", "sections": []}
    if previous.get("schema") != SCHEMA or previous.get("request") != current["request"]:
        raise ResearchError("previous brief has a different request; compare the same bank and size")
    rows = previous.get("sections")
    expected = {row["recipe"] for row in current["sections"]}
    if (not isinstance(rows, list) or len(rows) != len(expected)
            or any(not isinstance(row, dict) or row.get("recipe") not in expected for row in rows)
            or len({row["recipe"] for row in rows}) != len(expected)):
        raise ResearchError("previous brief has incomplete or duplicate sections")
    old = {row["recipe"]: row for row in rows}
    changes = []
    for row in current["sections"]:
        prior = old[row["recipe"]]
        previous_digest = digest(prior["evidence"]) if "evidence" in prior else None
        current_digest = digest(row["evidence"]) if "evidence" in row else None
        delta = {"changes": [], "changes_truncated": False, "truncation_reasons": []}
        if previous_digest is None or current_digest is None:
            state = "not_comparable"
        else:
            state = "unchanged_payload" if previous_digest == current_digest else "changed_payload"
            if state == "changed_payload":
                delta = evidence_changes(prior["evidence"], row["evidence"])
        changes.append({"recipe": row["recipe"], "status": state,
                        "previous_outcome": prior.get("outcome"), "outcome": row["outcome"],
                        "outcome_changed": prior.get("outcome") != row["outcome"],
                        "previous_evidence_sha256": previous_digest,
                        "current_evidence_sha256": current_digest, **delta})
    return {"status": "compared", "sections": changes,
            "change_limits": {"max_changes": MAX_CHANGES, "max_depth": MAX_CHANGE_DEPTH,
                              "max_bytes": MAX_CHANGE_BYTES},
            "meaning": "Exact source payload comparison; includes source clocks and revisions."}


def brief(*, slug=None, size_usd=100000, verification=False, previous=None, transport=exchange):
    if slug is not None and (not isinstance(slug, str) or len(slug) > 128
                             or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug)):
        raise ResearchError("use an exact bank slug from coverage")
    if type(size_usd) is not int or size_usd not in (1000, 10000, 100000, 1000000):
        raise ResearchError("size must be 1000, 10000, 100000 or 1000000 USD")
    recipes = ["funding-brief", "exit-brief"] + (["bank-review"] if slug else [])
    report = {"schema": SCHEMA, "request": {"bank_slug": slug, "size_usd": size_usd},
              "verification": verification, "execution_authority": False,
              "started_at": datetime.now(timezone.utc).isoformat(), "sections": [],
              "limits": LIMITS.copy()}
    # Validate comparison identity before making any network requests.
    if previous is not None:
        compare({**report, "sections": [{"recipe": r, "outcome": "not_attempted"} for r in recipes]}, previous)

    def run(recipe):
        try:
            return research(recipe, slug if recipe == "bank-review" else None,
                            size_usd=size_usd, verification=verification, transport=transport)
        except (ResearchError, ValueError, TypeError, OSError) as exc:
            return {"recipe": recipe, "endpoint": ENDPOINTS[recipe], "outcome": "error",
                    "reason": str(exc)[:500]}

    with ThreadPoolExecutor(max_workers=len(recipes)) as pool:
        report["sections"] = list(pool.map(run, recipes))
    report["complete"] = all(row["outcome"] == "evidence_returned" for row in report["sections"])
    report["outcome"] = "evidence_returned" if report["complete"] else "partial"
    report["comparison"] = compare(report, previous)
    report["retrieved_at"] = datetime.now(timezone.utc).isoformat()
    return report


def doctor(*, verification=False, transport=exchange):
    """One handshake and one tools/list per service; no research calls."""
    results = []
    for recipe, required in REQUIRED.items():
        try:
            client = Client(ENDPOINTS[recipe], verification=verification, transport=transport)
            client.initialize()
            tools = client.request("tools/list")
            if not isinstance(tools.get("tools"), list):
                raise ResearchError("invalid tool catalog")
            names = {row.get("name") for row in tools["tools"] if isinstance(row, dict)}
            missing = sorted(set(required) - names)
            results.append({"recipe": recipe, "endpoint": client.endpoint,
                            "status": "missing_tools" if missing else "ready",
                            "required_tools": list(required), "missing_tools": missing})
        except (ResearchError, ValueError, TypeError, OSError) as exc:
            results.append({"recipe": recipe, "endpoint": ENDPOINTS[recipe],
                            "status": "error", "reason": str(exc)[:500]})
    return {"schema": "liquilens.agent-doctor.v1", "verification": verification,
            "ready": all(row["status"] == "ready" for row in results),
            "research_calls": 0, "services": results}


def _fenced_json(value):
    # Source values and field names stay data, including Markdown and backticks.
    body = json.dumps(value, indent=2, ensure_ascii=False)
    fence = "`" * max(3, max((len(m.group()) + 1 for m in re.finditer(r"`+", body)), default=3))
    return [fence + "json", body, fence]


def markdown(report):
    lines = ["# Trading research brief", "", "Retrieved: " + report["retrieved_at"], "",
             "Result: " + report["outcome"], "", *["- " + limit for limit in report["limits"]]]
    for row in report["sections"]:
        lines += ["", "## " + row["recipe"], "", "Endpoint: " + row["endpoint"],
                  "", "Outcome: " + row["outcome"], ""]
        lines += _fenced_json(row.get("evidence", {"reason": row.get("reason")}))
    lines += ["", "## Changes since the previous brief", "", *_fenced_json(report["comparison"]), ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("doctor", "run"))
    parser.add_argument("--slug", help="optional exact covered bank slug")
    parser.add_argument("--size-usd", type=int, default=100000, choices=(1000, 10000, 100000, 1000000))
    parser.add_argument("--previous", help="previous JSON brief for the same request")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--verification", action="store_true", help="exclude operator tests from adoption")
    args = parser.parse_args(argv)
    if args.command == "doctor" and (args.slug or args.previous or args.format != "json"):
        parser.error("doctor accepts only --verification")
    try:
        if args.command == "doctor":
            report = doctor(verification=args.verification)
            code = 0 if report["ready"] else 2
        else:
            report = brief(slug=args.slug, size_usd=args.size_usd, verification=args.verification,
                           previous=previous_report(args.previous) if args.previous else None)
            code = 0 if report["complete"] else 2
        print(markdown(report) if args.format == "markdown" else json.dumps(report, indent=2, allow_nan=False))
        return code
    except (ResearchError, ValueError, TypeError, OSError) as exc:
        print(json.dumps({"outcome": "error", "reason": str(exc)[:500]}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
