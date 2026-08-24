#!/usr/bin/env python3
"""Require exact public catalogs and a live Financial Evidence MCP contract."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / ".well-known/ai-catalog.json"
PROTOCOL_CATALOG_PATH = ROOT / "protocol/catalog.json"
DEFAULT_URL = "https://liquilens.in/.well-known/ai-catalog.json"
DEFAULT_PROTOCOL_URL = "https://liquilens.in/protocol/catalog.json"
DEFAULT_MCP_URL = "https://liquilens.in/mcp/financial-evidence"
EXPECTED_MCP_SERVER = "financial-evidence"
EXPECTED_MCP_VERSION = "0.1.3"
EXPECTED_MCP_TOOLS = (
    "financial_evidence_topics",
    "financial_evidence_route",
    "financial_evidence_fetch",
)


def response_problem(
    expected: dict[str, Any],
    body: bytes,
    content_type: str,
    expected_content_type: str = "application/ai-catalog+json",
) -> str | None:
    if not content_type.lower().startswith(expected_content_type):
        return f"unexpected content type: {content_type or '<missing>'}"
    try:
        actual = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        return f"response is not UTF-8 JSON: {error}"
    if actual == expected:
        return None
    expected_ids = {
        row.get("identifier") for row in expected.get("entries", [])
        if isinstance(row, dict)
    }
    actual_ids = {
        row.get("identifier") for row in actual.get("entries", [])
        if isinstance(row, dict)
    } if isinstance(actual, dict) else set()
    missing = sorted(value for value in expected_ids - actual_ids if value)
    extra = sorted(value for value in actual_ids - expected_ids if value)
    return f"catalog body differs; missing={missing!r}; extra={extra!r}"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--protocol-url", default=DEFAULT_PROTOCOL_URL)
    parser.add_argument("--mcp-url", default=DEFAULT_MCP_URL)
    parser.add_argument("--expected-version-tag")
    parser.add_argument("--attempts", type=int, default=12)
    parser.add_argument("--delay", type=float, default=10.0)
    return parser


def decode_mcp_response(body: bytes, content_type: str) -> dict[str, Any]:
    """Decode one JSON or SSE-wrapped JSON-RPC response."""
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"MCP response is not UTF-8: {error}") from error
    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type == "application/json":
        candidate = text
    elif media_type == "text/event-stream":
        candidates = [
            line.removeprefix("data: ")
            for line in text.splitlines()
            if line.startswith("data: ") and line != "data: [DONE]"
        ]
        if len(candidates) != 1:
            raise ValueError(
                f"expected one MCP SSE data event, received {len(candidates)}"
            )
        candidate = candidates[0]
    else:
        raise ValueError(f"unexpected MCP content type: {content_type or '<missing>'}")
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as error:
        raise ValueError(f"MCP response is not JSON: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("MCP response must be one JSON-RPC object")
    return payload


def _mcp_request(
    url: str,
    payload: dict[str, Any],
    *,
    protocol_version: str | None = None,
    method_header: str | None = None,
    name_header: str | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "User-Agent": "LiquiLens-edge-check/1",
    }
    if protocol_version:
        headers["MCP-Protocol-Version"] = protocol_version
    if method_header:
        headers["Mcp-Method"] = method_header
    if name_header:
        headers["Mcp-Name"] = name_header
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        decoded = decode_mcp_response(
            response.read(),
            response.headers.get("Content-Type", ""),
        )
        response_headers = {key.lower(): value for key, value in response.headers.items()}
    return decoded, response_headers


def _require_version_tag(headers: dict[str, str], expected: str | None) -> None:
    if not expected:
        return
    actual = headers.get("x-liquilens-worker-tag")
    if actual != expected:
        raise RuntimeError(
            f"Worker version tag differs: expected {expected!r}, received {actual!r}"
        )


def _require_result(payload: dict[str, Any], request_id: str) -> dict[str, Any]:
    if payload.get("id") != request_id:
        raise RuntimeError(
            f"MCP response id differs: expected {request_id!r}, "
            f"received {payload.get('id')!r}"
        )
    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(f"MCP {request_id} response has no object result: {payload!r}")
    return result


def _verify_mcp(url: str, expected_version_tag: str | None) -> str:
    legacy_initialize, headers = _mcp_request(
        url,
        {
            "jsonrpc": "2.0",
            "id": "legacy-initialize",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "liquilens-edge-check", "version": "1"},
            },
        },
    )
    _require_version_tag(headers, expected_version_tag)
    initialized = _require_result(legacy_initialize, "legacy-initialize")
    if initialized.get("protocolVersion") != "2025-11-25":
        raise RuntimeError(f"legacy MCP protocol differs: {initialized!r}")
    if initialized.get("serverInfo") != {
        "name": EXPECTED_MCP_SERVER,
        "version": EXPECTED_MCP_VERSION,
    }:
        raise RuntimeError(f"legacy MCP server identity differs: {initialized!r}")

    legacy_list, headers = _mcp_request(
        url,
        {"jsonrpc": "2.0", "id": "legacy-list", "method": "tools/list", "params": {}},
    )
    _require_version_tag(headers, expected_version_tag)
    tools = _require_result(legacy_list, "legacy-list").get("tools")
    if not isinstance(tools, list) or tuple(tool.get("name") for tool in tools) != EXPECTED_MCP_TOOLS:
        raise RuntimeError(f"legacy MCP tools differ: {tools!r}")

    modern_meta = {
        "io.modelcontextprotocol/clientInfo": {
            "name": "liquilens-edge-check",
            "version": "1",
        },
        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientCapabilities": {},
    }
    modern_discover, headers = _mcp_request(
        url,
        {
            "jsonrpc": "2.0",
            "id": "modern-discover",
            "method": "server/discover",
            "params": {"_meta": modern_meta},
        },
        protocol_version="2026-07-28",
        method_header="server/discover",
    )
    _require_version_tag(headers, expected_version_tag)
    discovered = _require_result(modern_discover, "modern-discover")
    server_info = discovered.get("_meta", {}).get(
        "io.modelcontextprotocol/serverInfo", {}
    )
    if server_info.get("name") != EXPECTED_MCP_SERVER:
        raise RuntimeError(f"modern MCP server identity differs: {discovered!r}")

    modern_list, headers = _mcp_request(
        url,
        {
            "jsonrpc": "2.0",
            "id": "modern-list",
            "method": "tools/list",
            "params": {"_meta": modern_meta},
        },
        protocol_version="2026-07-28",
        method_header="tools/list",
    )
    _require_version_tag(headers, expected_version_tag)
    tools = _require_result(modern_list, "modern-list").get("tools")
    if not isinstance(tools, list) or tuple(tool.get("name") for tool in tools) != EXPECTED_MCP_TOOLS:
        raise RuntimeError(f"modern MCP tools differ: {tools!r}")

    modern_route, headers = _mcp_request(
        url,
        {
            "jsonrpc": "2.0",
            "id": "modern-route",
            "method": "tools/call",
            "params": {
                "name": "financial_evidence_route",
                "arguments": {"topics": ["china-economy"]},
                "_meta": modern_meta,
            },
        },
        protocol_version="2026-07-28",
        method_header="tools/call",
        name_header="financial_evidence_route",
    )
    _require_version_tag(headers, expected_version_tag)
    routed = _require_result(modern_route, "modern-route")
    products = [
        source.get("product")
        for source in routed.get("structuredContent", {})
        .get("topics", {})
        .get("china-economy", [])
    ]
    if products != ["Palimpsest", "Seiche"]:
        raise RuntimeError(f"modern MCP route differs: {routed!r}")

    limiter_probe, headers = _mcp_request(
        url,
        {
            "jsonrpc": "2.0",
            "id": "limiter-probe",
            "method": "tools/call",
            "params": {
                "name": "financial_evidence_fetch",
                "arguments": {"topics": ["money-market"]},
            },
        },
    )
    _require_version_tag(headers, expected_version_tag)
    probed = _require_result(limiter_probe, "limiter-probe")
    probe_summary = probed.get("structuredContent", {})
    if probe_summary.get("status") != "complete" or probed.get("isError") is not False:
        raise RuntimeError(f"MCP money-market fetch is not complete: {probed!r}")
    probe_sources = probe_summary.get("sources", [])
    if len(probe_sources) != 1:
        raise RuntimeError(f"MCP money-market source count differs: {probed!r}")
    source = probe_sources[0]
    digest = source.get("content_sha256", "")
    if (
        source.get("product") != "Seiche"
        or source.get("ok") is not True
        or not isinstance(source.get("bytes"), int)
        or source["bytes"] <= 0
        or not digest.startswith("sha256:")
        or len(digest) != 71
    ):
        raise RuntimeError(f"MCP money-market receipt is incomplete: {source!r}")
    return (
        f"remote MCP exposes {len(EXPECTED_MCP_TOOLS)} exact tools, both protocol "
        "generations, the China route, and a successful limiter-backed money-market fetch"
    )


def _verify_mcp_with_retries(
    *,
    url: str,
    expected_version_tag: str | None,
    attempts: int,
    delay: float,
) -> str:
    problem = "remote MCP was not checked"
    for attempt in range(1, attempts + 1):
        try:
            return _verify_mcp(url, expected_version_tag)
        except (OSError, ValueError, RuntimeError, urllib.error.URLError) as error:
            problem = str(error)
        if attempt < attempts:
            time.sleep(delay)
    raise RuntimeError(f"{url}: {problem}")


def _verify_url(
    *,
    expected: dict[str, Any],
    expected_path: Path,
    expected_content_type: str,
    url: str,
    attempts: int,
    delay: float,
) -> str:
    problem = "edge catalog was not checked"
    for attempt in range(1, attempts + 1):
        separator = "&" if urllib.parse.urlsplit(url).query else "?"
        request = urllib.request.Request(
            f"{url}{separator}catalog_check={attempt}-{time.time_ns()}",
            headers={"Cache-Control": "no-cache", "User-Agent": "LiquiLens-edge-check/1"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                problem = response_problem(
                    expected,
                    response.read(),
                    response.headers.get("Content-Type", ""),
                    expected_content_type,
                ) or ""
        except (OSError, urllib.error.URLError) as error:
            problem = f"edge request failed: {error}"
        if not problem:
            return f"edge catalog matches {expected_path}"
        if attempt < attempts:
            time.sleep(delay)
    raise RuntimeError(f"{expected_path}: {problem}")


def main() -> int:
    args = _parser().parse_args()
    if args.attempts < 1 or args.delay < 0:
        raise SystemExit("attempts must be positive and delay must be non-negative")
    checks = (
        (
            CATALOG_PATH,
            args.url,
            "application/ai-catalog+json",
        ),
        (
            PROTOCOL_CATALOG_PATH,
            args.protocol_url,
            "application/json",
        ),
    )
    try:
        for expected_path, url, expected_content_type in checks:
            expected = json.loads(expected_path.read_text(encoding="utf-8"))
            print(_verify_url(
                expected=expected,
                expected_path=expected_path,
                expected_content_type=expected_content_type,
                url=url,
                attempts=args.attempts,
                delay=args.delay,
            ))
        print(_verify_mcp_with_retries(
            url=args.mcp_url,
            expected_version_tag=args.expected_version_tag,
            attempts=args.attempts,
            delay=args.delay,
        ))
    except RuntimeError as error:
        print(error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
