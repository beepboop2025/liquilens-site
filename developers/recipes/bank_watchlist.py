#!/usr/bin/env python3
"""Review 1–20 explicitly selected bank slugs in one caller-triggered MCP session.

Keep financial_research.py beside this file. Python 3.11+; standard library only.
JSON goes to stdout, including completed evidence if a later request fails.
"""
import argparse
from datetime import datetime, timezone
import json
import re
import sys
from uuid import RFC_4122, UUID

from financial_research import CLIENT_INFO, ENDPOINTS, Client, ResearchError, exchange


def validate_inputs(slugs, client_id):
    if not isinstance(slugs, (list, tuple)) or not 1 <= len(slugs) <= 20:
        raise ResearchError("select 1–20 explicit bank slugs")
    if any(not isinstance(slug, str) or len(slug) > 128
           or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) for slug in slugs):
        raise ResearchError("use exact bank slugs from coverage, at most 128 characters each")
    if len(set(slugs)) != len(slugs):
        raise ResearchError("duplicate bank slugs are not allowed")
    if client_id is None:
        return None
    try:
        parsed = UUID(client_id)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ResearchError("--client-id must be an explicitly supplied UUID4") from exc
    if parsed.version != 4 or parsed.variant != RFC_4122 or str(parsed) != client_id.lower():
        raise ResearchError("--client-id must be an explicitly supplied hyphenated UUID4")
    return str(parsed)


def now():
    return datetime.now(timezone.utc).isoformat()


def watchlist(slugs, *, verification=False, client_id=None, transport=exchange):
    """Retain server evidence unchanged; retrieval time never establishes freshness."""
    client_id = validate_inputs(slugs, client_id)
    client = Client(ENDPOINTS["bank-review"], verification=verification, transport=transport)
    if client_id is not None:
        client.headers["X-Liquilens-Client-Id"] = client_id
    report = {
        "schema": "liquilens.bank-watchlist.v1", "client": CLIENT_INFO,
        "endpoint": client.endpoint, "verification": verification,
        "execution_authority": False, "started_at": now(),
        "requested_slugs": list(slugs), "complete": False,
        "outcome": "error", "evidence": {}, "results": [],
    }
    stage = "initialize"
    current_slug = None
    try:
        client.initialize()
        stage = "coverage"
        coverage = client.call("banking_specialisation_coverage", {})
        report["evidence"]["coverage"] = coverage
        if not isinstance(coverage.get("rows"), list):
            raise ResearchError("bank coverage has no rows; no slug can be established")
        covered = {row["slug"] for row in coverage["rows"]
                   if isinstance(row, dict) and isinstance(row.get("slug"), str)}
        stage = "review"
        for slug in slugs:
            current_slug = slug
            if slug not in covered:
                report["results"].append({
                    "requested_slug": slug, "outcome": "not_covered",
                    "reason": "No exact coverage match; no bank review was requested.",
                })
                continue
            review = client.call("bank_asset_quality_review", {"slug": slug, "include_history": True})
            if review.get("slug") != slug:
                raise ResearchError("bank review identity does not match the requested slug")
            outcome = review.get("status")
            report["results"].append({
                "requested_slug": slug,
                "outcome": outcome if outcome in ("unavailable", "not_covered") else "evidence_returned",
                "retrieved_at": now(), "evidence": {"review": review},
            })
        report["complete"] = True
        report["outcome"] = ("evidence_returned"
                             if all(row["outcome"] == "evidence_returned" for row in report["results"])
                             else "unavailable")
    except (ResearchError, ValueError, TypeError) as exc:
        report["error"] = {"stage": stage, "reason": str(exc)}
        if stage == "review" and current_slug is not None:
            report["results"].append({"requested_slug": current_slug, "outcome": "error",
                                      "reason": str(exc)})
        for slug in slugs[len(report["results"]):]:
            report["results"].append({"requested_slug": slug, "outcome": "not_attempted",
                                      "reason": "Run stopped after a request or tool failed."})
    report["retrieved_at"] = now()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slugs", nargs="+", help="1–20 distinct exact slugs from bank coverage")
    parser.add_argument("--verification", action="store_true",
                        help="mark operator/testing traffic as synthetic, excluded from adoption")
    parser.add_argument("--client-id", help="optional UUID4 for opt-in repeat-client measurement")
    args = parser.parse_args(argv)
    try:
        report = watchlist(args.slugs, verification=args.verification, client_id=args.client_id)
        print(json.dumps(report, indent=2, allow_nan=False))
        return {"evidence_returned": 0, "unavailable": 2, "error": 1}[report["outcome"]]
    except (ResearchError, ValueError, TypeError) as exc:
        print(json.dumps({"outcome": "error", "reason": str(exc)}, allow_nan=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
