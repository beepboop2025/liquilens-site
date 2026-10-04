"""Transport-only receipt checks for the Financial Evidence release verifier."""

import re
from typing import Any


def require_fetch_semantics(
    result: dict[str, Any], *, expected_sources: list[dict[str, str]] | None = None,
) -> None:
    if expected_sources is None:
        expected_sources = [{
            "product": "Seiche",
            "source_url": "https://api.seiche.info/api/v2/money-markets",
            "adapter": "seiche_money_markets_v1",
        }]
    summary = result.get("structuredContent")
    if not isinstance(summary, dict):
        raise RuntimeError("MCP fetch omitted structuredContent")
    required = {
        "status": "complete",
        "transport_status": "complete",
        "status_semantics": "transport_only",
        "evidence_status": "not_evaluated",
        "carrier_verification": "not_performed",
        "output_status": "complete",
        "output_error": None,
    }
    actual = {name: summary.get(name) for name in required}
    if result.get("isError") is not False or actual != required:
        raise RuntimeError(f"remote MCP semantic boundary differs: {actual!r}")
    sources = summary.get("sources")
    if not isinstance(sources, list) or len(sources) != len(expected_sources):
        raise RuntimeError("remote MCP source count differs")
    shared = {}
    for source, expected in zip(sources, expected_sources):
        if not isinstance(source, dict):
            raise RuntimeError("remote MCP source receipt is not an object")
        digest = source.get("content_sha256", "")
        reported = source.get("source_reported")
        if (
            any(source.get(key) != value for key, value in expected.items() if key != "adapter")
            or source.get("ok") is not True
            or type(source.get("bytes")) is not int
            or source["bytes"] <= 0
            or not isinstance(digest, str)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None
            or not isinstance(reported, dict)
            or reported.get("adapter") != expected["adapter"]
            or not isinstance(reported.get("state"), list)
            or not reported["state"]
        ):
            raise RuntimeError(f"remote MCP provenance receipt differs: {source!r}")
        for group in ("state", "clocks"):
            fields = reported.get(group)
            if fields == "not_reported":
                continue
            if not isinstance(fields, list):
                raise RuntimeError(f"remote MCP source-reported {group} differs")
            for field in fields:
                provenance = field.get("provenance") if isinstance(field, dict) else None
                if provenance != {
                    "kind": "source_document",
                    "source_url": source.get("source_url"),
                    "content_sha256": digest,
                }:
                    raise RuntimeError(
                        f"remote MCP source-reported provenance differs: {reported!r}"
                    )
        receipt = {key: value for key, value in source.items() if key != "topic"}
        url = source["source_url"]
        if url in shared and shared[url] != receipt:
            raise RuntimeError("remote MCP shared-source receipts differ")
        shared[url] = receipt
