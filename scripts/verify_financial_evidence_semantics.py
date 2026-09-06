"""Exact v0.1.5 semantic gate shared with the Financial Evidence release verifier."""

from typing import Any


def require_fetch_semantics(result: dict[str, Any]) -> None:
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
    if not isinstance(sources, list) or len(sources) != 1:
        raise RuntimeError("remote MCP money-market source count differs")
    source = sources[0]
    digest = source.get("content_sha256", "")
    reported = source.get("source_reported")
    if (
        source.get("product") != "Seiche"
        or source.get("ok") is not True
        or not isinstance(source.get("bytes"), int)
        or source["bytes"] <= 0
        or not isinstance(digest, str)
        or not digest.startswith("sha256:")
        or len(digest) != 71
        or not isinstance(reported, dict)
        or reported.get("adapter") != "seiche_money_markets_v1"
        or not isinstance(reported.get("state"), list)
        or not reported["state"]
    ):
        raise RuntimeError(f"remote MCP provenance receipt differs: {source!r}")
    for field in reported["state"]:
        provenance = field.get("provenance") if isinstance(field, dict) else None
        if provenance != {
            "kind": "source_document",
            "source_url": source.get("source_url"),
            "content_sha256": digest,
        }:
            raise RuntimeError(
                f"remote MCP source-reported provenance differs: {reported!r}"
            )
