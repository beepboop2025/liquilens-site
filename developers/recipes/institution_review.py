#!/usr/bin/env python3
"""Build a public institution review with separately dated Seiche context.

Keep financial_research.py beside this file. Uses Python's standard library.
No retries, scheduling, credentials, telemetry or automatic filesystem writes.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
import sys
import unicodedata

from financial_research import Client, ENDPOINTS, ResearchError, exchange


def clock():
    return datetime.now(timezone.utc).isoformat()


def normalized(value):
    text = unicodedata.normalize("NFKC", value).casefold()
    return " ".join("".join(c if c.isalnum() else " " for c in text).split())


def validate_packet(packet, query):
    if packet.get("schema") != "liquilens.review-packet.v1":
        raise ResearchError("institution packet schema is incompatible")
    if packet.get("status") not in ("covered", "not_covered", "ambiguous"):
        raise ResearchError("institution packet status is incompatible")
    if packet.get("human_review_required") is not True:
        raise ResearchError("institution packet is missing its human-review boundary")
    if packet["status"] != "covered":
        if packet.get("query") != query:
            raise ResearchError("resolution result belongs to a different query")
        return
    entity = packet.get("entity") or {}
    if not isinstance(entity, dict) or not entity.get("slug") or not entity.get("name"):
        raise ResearchError("institution packet has no usable entity identity")
    if (query.casefold() != str(entity.get("slug", "")).casefold()
            and normalized(query) != normalized(str(entity.get("name", "")))):
        raise ResearchError("institution identity does not match the request")
    body = {key: value for key, value in packet.items() if key != "content_sha256"}
    actual = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False,
                                      allow_nan=False, separators=(",", ":")).encode()).hexdigest()
    if packet.get("content_sha256") != actual:
        raise ResearchError("institution packet content hash does not match")


def review(*, institution=None, bank_slug=None, jurisdiction="unspecified",
           institution_type="unspecified", verification=False, transport=exchange):
    if bool(institution) == bool(bank_slug):
        raise ValueError("supply exactly one institution name/slug or bank slug")
    raw_query = institution or bank_slug
    query = raw_query.strip()
    if not query or not normalized(query) or len(query) > 160 or any(ord(c) < 32 for c in raw_query):
        raise ValueError("use one nonempty institution identifier, at most 160 characters")
    if bank_slug and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", query):
        raise ValueError("use an exact bank slug from the coverage tool")
    sections = []

    def read(product, client, tool, arguments, validator=None):
        entry = {"product": product, "endpoint": client.endpoint, "tool": tool,
                 "arguments": arguments}
        try:
            evidence = client.call(tool, arguments)
            if validator:
                validator(evidence)
            entry.update(status="returned", evidence=evidence)
        except (ResearchError, ValueError, TypeError) as exc:
            entry.update(status="error", reason=str(exc))
        entry["retrieved_at"] = clock()
        sections.append(entry)
        return entry

    institution_client = Client(ENDPOINTS["bank-review"], verification=verification, transport=transport)
    try:
        institution_client.initialize()
        if bank_slug:
            def coverage_shape(data):
                if not isinstance(data.get("rows"), list):
                    raise ResearchError("bank coverage has no rows")
            coverage = read("LiquiLens", institution_client, "banking_specialisation_coverage", {}, coverage_shape)
            rows = coverage.get("evidence", {}).get("rows", [])
            if coverage["status"] == "returned" and any(isinstance(row, dict) and row.get("slug") == query for row in rows):
                def bank_identity(data):
                    if data.get("slug") != query or data.get("schema") != "liquilens.bank-specialisation.v1":
                        raise ResearchError("bank review identity or schema does not match")
                read("LiquiLens", institution_client, "bank_asset_quality_review",
                     {"slug": query, "include_history": True}, bank_identity)
            else:
                sections.append({"product": "LiquiLens", "status": "not_requested",
                                 "requested_slug": query, "retrieved_at": clock(),
                                 "reason": "No confirmed exact coverage match; no bank dossier was guessed."})
        else:
            read("LiquiLens", institution_client, "institution_review_packet",
                 {"institution": query}, lambda data: validate_packet(data, query))
    except ResearchError as exc:
        sections.append({"product": "LiquiLens", "endpoint": institution_client.endpoint,
                         "status": "error", "reason": str(exc), "retrieved_at": clock()})

    funding_client = Client(ENDPOINTS["funding-brief"], verification=verification, transport=transport)
    try:
        funding_client.initialize()
        read("Seiche", funding_client, "data_health", {})
        def funding_shape(data):
            if data.get("schema") != "seiche.public.v2" and data.get("available") is not False and data.get("status") not in ("unavailable", "restricted"):
                raise ResearchError("funding state schema is incompatible")
        read("Seiche", funding_client, "funding_stress_now", {}, funding_shape)
        def desk_shape(data):
            if data.get("schema") != "seiche.money-market-desk.v1" or type(data.get("ok")) is not bool:
                raise ResearchError("money-market context schema is incompatible")
        read("Seiche", funding_client, "money_market_context", {"section": "summary"}, desk_shape)
    except ResearchError as exc:
        sections.append({"product": "Seiche", "endpoint": funding_client.endpoint,
                         "status": "error", "reason": str(exc), "retrieved_at": clock()})

    # Retrieval completeness is separate from analytical or regulatory eligibility.
    def unavailable(entry):
        evidence = entry.get("evidence", {})
        return (entry["status"] != "returned" or evidence.get("available") is False
                or evidence.get("ok") is False
                or evidence.get("status") in ("not_covered", "ambiguous", "unavailable", "restricted", "stale", "failed"))
    return {
        "schema": "liquilens.institution-workflow.v1", "prepared_at": clock(),
        "query": query, "verification": verification,
        "retrieval_outcome": "partial_or_unavailable" if any(unavailable(s) for s in sections) else "responses_returned",
        "declared_scope": {"jurisdiction": jurisdiction, "institution_type": institution_type,
                           "verification": "caller-supplied labels, not validated coverage"},
        "regulatory_assessment": {"status": "not_assessed", "reason": "No private-book reconciliation, versioned rule evaluation or regulatory sign-off was performed."},
        "human_review_required": True, "execution_authority": False,
        "interpretation": "Keep source clocks, units, freshness, counterevidence and gaps in each section. Responses returned is not a freshness, coverage, compliance or default-prediction verdict. No combined score is computed. A matching packet hash detects alteration; it is not a signature or attestation.",
        "sections": sections,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    identity = parser.add_mutually_exclusive_group(required=True)
    identity.add_argument("--institution", help="exact Failure Radar slug or full legal name")
    identity.add_argument("--bank-slug", help="exact banking_specialisation_coverage slug")
    parser.add_argument("--jurisdiction", default="unspecified", help="reviewer-declared scope; not a coverage assertion")
    parser.add_argument("--institution-type", default="unspecified", help="reviewer-declared institution class")
    parser.add_argument("--verification", action="store_true", help="label operator/test requests separately from adoption")
    args = parser.parse_args(argv)
    try:
        output = review(**vars(args))
        print(json.dumps(output, indent=2, allow_nan=False))
        return 0 if output["retrieval_outcome"] == "responses_returned" else 2
    except (ResearchError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
