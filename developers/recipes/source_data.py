#!/usr/bin/env python3
"""Read a bounded page of official-source funding, bank or settlement evidence.

Python 3.11+, standard library only. No API key, model call, automatic pagination
or filesystem write. Each response preserves the source's clocks and receipts.
"""
import argparse
import json
import sys

from financial_research import Client, RESEARCH_DATA_ENDPOINT, ResearchError, exchange

COMMANDS = {
    "catalog": ({"product"}, set()),
    "analysis": ({"product"}, set()),
    "series": ({"dataset", "q", "limit", "offset"}, {"dataset"}),
    "entities": ({"dataset", "q", "limit", "offset"}, {"dataset"}),
    "observations": ({"dataset", "series", "entity", "start", "end", "as_known_at", "limit", "offset"}, {"dataset", "series"}),
    "tracked-institutions": ({"scope", "q", "limit", "offset"}, set()),
}


def query(command, arguments, *, verification=False, transport=exchange):
    if command not in COMMANDS or not isinstance(arguments, dict):
        raise ResearchError("unknown source-data command")
    allowed, required = COMMANDS[command]
    if set(arguments) - allowed or not required <= set(arguments):
        raise ResearchError("arguments do not match the selected source-data command")
    for name, value in arguments.items():
        if name in ("limit", "offset"):
            maximum = 500 if command == "tracked-institutions" and name == "limit" else 10000 if name == "limit" else 10000000
            if type(value) is not int or not (1 if name == "limit" else 0) <= value <= maximum:
                raise ResearchError("page bounds must be integers within the documented limits")
        elif not isinstance(value, str) or len(value) > 150 or (name in required and not value):
            raise ResearchError("query identifiers must be bounded strings")
    if "product" in arguments and arguments["product"] not in ("seiche", "liquilens", "undertow"):
        raise ResearchError("unknown product")
    if "scope" in arguments and arguments["scope"] not in ("dossiers", "rbi_registry"):
        raise ResearchError("unknown institution scope")
    client = Client(RESEARCH_DATA_ENDPOINT, verification=verification, transport=transport)
    client.initialize()
    evidence = client.call("research_" + command.replace("-", "_"), arguments)
    if evidence.get("schema") != "liquilens.research-data.v1":
        raise ResearchError("source-data response has an incompatible schema")
    if "dataset" in arguments:
        definition = evidence.get("series")
        returned_dataset = evidence.get("dataset") or (definition.get("dataset") if isinstance(definition, dict) else None)
        # Empty history can legitimately have no series definition. A populated
        # page must still prove its exact dataset/series/entity identity.
        unavailable = evidence.get("status") == "unavailable" and evidence.get("rows") == []
        if returned_dataset != arguments["dataset"] and not (unavailable and returned_dataset is None):
            raise ResearchError("source-data response does not match the requested dataset")
        if command == "observations":
            if isinstance(definition, dict) and definition.get("id") != arguments["series"]:
                raise ResearchError("source-data response does not match the requested series")
            for row in evidence.get("rows", []):
                if (row.get("dataset") != arguments["dataset"] or row.get("series") != arguments["series"]
                        or row.get("entity", "") != arguments.get("entity", "")):
                    raise ResearchError("source-data observation identity does not match the request")
    return evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=COMMANDS)
    for name in ("product", "dataset", "series", "entity", "start", "end", "as-known-at", "scope", "q"):
        parser.add_argument("--" + name)
    parser.add_argument("--limit", type=int, help="one page, 1..10000; tracked institutions allow at most 500")
    parser.add_argument("--offset", type=int, help="use the previous response's next_offset")
    parser.add_argument("--verification", action="store_true", help="mark operator testing separately from adoption")
    args = vars(parser.parse_args(argv))
    command, verification = args.pop("command"), args.pop("verification")
    arguments = {name: value for name, value in args.items() if value is not None}
    if "limit" in COMMANDS[command][0]:
        arguments.setdefault("limit", 100)
    try:
        evidence = query(command, arguments, verification=verification)
        print(json.dumps(evidence, indent=2, allow_nan=False))
        return 2 if evidence.get("status") == "unavailable" else 0
    except (ResearchError, ValueError, TypeError) as exc:
        print(json.dumps({"outcome": "error", "reason": str(exc)}, allow_nan=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
