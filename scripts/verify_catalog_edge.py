#!/usr/bin/env python3
"""Require exact public catalogs, live MCP contracts, and release receipts."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import ipaddress
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from email.message import Message
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / ".well-known/ai-catalog.json"
API_CATALOG_PATH = ROOT / ".well-known/api-catalog.json"
PROTOCOL_CATALOG_PATH = ROOT / "protocol/catalog.json"
MCP_CONTRACT_PATH = ROOT / "protocol/financial-evidence-mcp-v0.1.4.json"
DEFAULT_URL = "https://liquilens.in/.well-known/ai-catalog.json"
DEFAULT_API_CATALOG_URL = "https://liquilens.in/.well-known/api-catalog"
DEFAULT_PROTOCOL_URL = "https://liquilens.in/protocol/catalog.json"
DEFAULT_MCP_URL = "https://liquilens.in/mcp/financial-evidence"
RFC_9727_PROFILE = "https://www.rfc-editor.org/info/rfc9727"
API_CATALOG_LINK = (
    '<https://liquilens.in/.well-known/api-catalog>; rel="api-catalog"; '
    'type="application/linkset+json"'
)
PALIMPSEST_CARD_ID = "urn:air:liquilens.in:catalog:palimpsest-china"
PALIMPSEST_RIGHTS_URI = "palimpsest://china-economic/publication-rights"
PALIMPSEST_RECEIPTS = (
    ("deployment", "deploymentReceipt", "deploymentReceiptSha256"),
    ("registry publication", "registryReceipt", "registryReceiptSha256"),
    ("Registry latest snapshot", "registrySnapshot", "registrySnapshotSha256"),
)
SIBLING_CARD_IDS = (
    ("Undertow", "urn:air:liquilens.in:catalog:undertow"),
    ("Riptide", "urn:air:liquilens.in:catalog:riptide"),
    ("NarcoScope", "urn:air:liquilens.in:catalog:narcoscope"),
)
SIBLING_REQUEST_TIMEOUT = 5.0
SIBLING_MAX_ATTEMPTS = 2
SIBLING_RETRY_DELAY = 2.0
MCP_2026_VERSION = "2026-07-28"
MAX_JSON_BODY_BYTES = 2 * 1024 * 1024
MAX_CATALOG_BODY_BYTES = 4 * 1024 * 1024
MIN_FETCH_TIMEOUT = 0.25
ALLOWED_FETCH_HOSTS = frozenset(
    {
        "api.github.com",
        "api.seiche.info",
        "beepboop2025.github.io",
        "liquilens.in",
        "liquilens-undertow.com",
        "narcoscope.com",
        "palimpsest.info",
        "www.palimpsest.info",
        "registry.modelcontextprotocol.io",
    }
)
ALLOWED_FETCH_SUFFIXES = (".vercel.app",)
SIBLING_ACTION_PROOFS: dict[str, tuple[dict[str, str], ...]] = {
    "Undertow": (
        {
            "kind": "Registry verification",
            "url": "https://github.com/beepboop2025/undertow-mcp/actions/runs/31910012605",
            "sha": "e9e1f1851ee6865584b250554c21fe2d4c19e42c",
            "workflow": ".github/workflows/verify.yml",
            "event": "push",
            "branch": "master",
        },
    ),
    "Riptide": (),
    "NarcoScope": (
        {
            "kind": "source CI",
            "url": "https://github.com/beepboop2025/narcoscope/actions/runs/33260623945",
            "sha_field": "sourceUpgradeCommit",
            "workflow": ".github/workflows/tests.yml",
            "event": "push",
        },
        {
            "kind": "Registry publication",
            "url_field": "registryPublicationWorkflow",
            "sha_field": "sourceUpgradeCommit",
            "workflow": ".github/workflows/registry-publish.yml",
            "event": "workflow_dispatch",
        },
    ),
}
SIBLING_PROBE_TOOL = {
    "Undertow": "agent_access_status",
    "Riptide": "riptide_overview",
    "NarcoScope": "list_capabilities",
}
SIBLING_REGISTRY_REPOSITORIES = {
    "Undertow": {
        "url": "https://github.com/beepboop2025/undertow-mcp",
        "source": "github",
    },
    "Riptide": {
        "url": "https://github.com/beepboop2025/riptide",
        "source": "github",
    },
    "NarcoScope": {
        "url": "https://github.com/beepboop2025/narcoscope",
        "source": "github",
    },
}
EXPECTED_MCP_CONTRACT = json.loads(MCP_CONTRACT_PATH.read_text(encoding="utf-8"))
EXPECTED_MCP_SERVER = EXPECTED_MCP_CONTRACT["serverInfo"]["name"]
EXPECTED_MCP_VERSION = EXPECTED_MCP_CONTRACT["serverInfo"]["version"]
EXPECTED_MCP_TOOLS = tuple(tool["name"] for tool in EXPECTED_MCP_CONTRACT["tools"])


@dataclass
class _NetworkBudget:
    deadline: float

    def timeout(self, requested: float, label: str) -> float:
        remaining = self.deadline - time.monotonic()
        if remaining < MIN_FETCH_TIMEOUT:
            raise RuntimeError(f"network deadline exhausted before {label}")
        return min(requested, remaining)

    def sleep(self, delay: float) -> None:
        remaining = self.deadline - time.monotonic()
        if delay > remaining:
            raise RuntimeError("network deadline exhausted before retry")
        time.sleep(delay)


_ACTIVE_BUDGET: _NetworkBudget | None = None


@contextlib.contextmanager
def _network_budget(seconds: float):
    global _ACTIVE_BUDGET
    previous = _ACTIVE_BUDGET
    _ACTIVE_BUDGET = _NetworkBudget(time.monotonic() + seconds)
    try:
        yield
    finally:
        _ACTIVE_BUDGET = previous


def _bounded_timeout(requested: float, label: str) -> float:
    if requested <= 0:
        raise RuntimeError(f"{label} timeout must be positive")
    if _ACTIVE_BUDGET is None:
        return requested
    return _ACTIVE_BUDGET.timeout(requested, label)


def _bounded_sleep(delay: float) -> None:
    if delay <= 0:
        return
    if _ACTIVE_BUDGET is None:
        time.sleep(delay)
    else:
        _ACTIVE_BUDGET.sleep(delay)


def _validate_public_https_url(url: str) -> str:
    """Reject credentialed, redirected, private, or undeclared network targets."""
    try:
        parsed = urllib.parse.urlsplit(url)
        port = parsed.port
    except ValueError as error:
        raise RuntimeError(f"invalid verification URL: {url!r}") from error
    hostname = (parsed.hostname or "").rstrip(".").lower()
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
    ):
        raise RuntimeError(f"verification URL must be credential-free HTTPS: {url!r}")
    if hostname not in ALLOWED_FETCH_HOSTS and not hostname.endswith(
        ALLOWED_FETCH_SUFFIXES
    ):
        raise RuntimeError(f"verification host is not allowlisted: {hostname!r}")
    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(
                hostname,
                443,
                type=socket.SOCK_STREAM,
            )
        }
    except OSError as error:
        raise RuntimeError(
            f"could not resolve verification host {hostname!r}: {error}"
        ) from error
    if not addresses:
        raise RuntimeError(f"verification host {hostname!r} resolved to no addresses")
    for address in addresses:
        parsed_address = ipaddress.ip_address(address)
        if not parsed_address.is_global:
            raise RuntimeError(
                f"verification host {hostname!r} resolved to non-public {address!r}"
            )
    return url


def _canonical_verification_url(url: str) -> str:
    """Resolve the one declared legacy hostname without accepting redirects."""
    parsed = urllib.parse.urlsplit(url)
    if (parsed.hostname or "").rstrip(".").lower() != "palimpsest.info":
        return url
    return urllib.parse.urlunsplit(
        (parsed.scheme, "www.palimpsest.info", parsed.path, parsed.query, parsed.fragment)
    )


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        _validate_public_https_url(newurl)
        raise RuntimeError(
            f"redirects are not accepted for verification: {req.full_url} -> {newurl}"
        )


_SAFE_OPENER = urllib.request.build_opener(_RejectRedirects)


def _read_bounded(response: Any, limit: int, label: str) -> bytes:
    body = response.read(limit + 1)
    if len(body) > limit:
        raise RuntimeError(f"{label} exceeds the {limit}-byte response limit")
    return body


def compact_json_bytes(value: Any) -> bytes:
    """Serialize JSON exactly as the edge Worker's JSON.stringify imports."""
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _content_type_parts(value: str) -> tuple[str, dict[str, str]]:
    if not value:
        return "", {}
    message = Message()
    message["Content-Type"] = value
    media_type = message.get_content_type().lower()
    parameters = {
        str(key).lower(): str(parameter)
        for key, parameter in message.get_params(header="content-type")[1:]
    }
    return media_type, parameters


def response_problem(
    expected: dict[str, Any],
    body: bytes,
    content_type: str,
    expected_content_type: str = "application/ai-catalog+json",
    *,
    expected_body: bytes | None = None,
    expected_profile: str | None = None,
) -> str | None:
    media_type, parameters = _content_type_parts(content_type)
    if media_type != expected_content_type.lower():
        return f"unexpected content type: {content_type or '<missing>'}"
    if expected_profile and parameters.get("profile") != expected_profile:
        return (
            f"unexpected content type profile: {parameters.get('profile', '<missing>')}"
        )
    try:
        actual = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        return f"response is not UTF-8 JSON: {error}"
    if actual == expected:
        if expected_body is not None and body != expected_body:
            expected_digest = hashlib.sha256(expected_body).hexdigest()
            actual_digest = hashlib.sha256(body).hexdigest()
            return (
                "catalog body differs byte-for-byte; "
                f"expected_sha256={expected_digest}; actual_sha256={actual_digest}"
            )
        return None
    identity_field = "anchor" if "linkset" in expected else "identifier"
    collection_field = "linkset" if identity_field == "anchor" else "entries"
    expected_ids = {
        row.get(identity_field)
        for row in expected.get(collection_field, [])
        if isinstance(row, dict)
    }
    actual_ids = (
        {
            row.get(identity_field)
            for row in actual.get(collection_field, [])
            if isinstance(row, dict)
        }
        if isinstance(actual, dict)
        else set()
    )
    missing = sorted(value for value in expected_ids - actual_ids if value)
    extra = sorted(value for value in actual_ids - expected_ids if value)
    return f"catalog body differs; missing={missing!r}; extra={extra!r}"


def response_headers_problem(
    headers: dict[str, str],
    *,
    expected_link: str | None = None,
    expected_cors_origin: str | None = None,
) -> str | None:
    """Check browser and RFC discovery headers after normalizing header names."""
    normalized = {key.lower(): value for key, value in headers.items()}
    if expected_link is not None and normalized.get("link") != expected_link:
        return f"unexpected Link header: {normalized.get('link', '<missing>')}"
    if (
        expected_cors_origin is not None
        and normalized.get("access-control-allow-origin") != expected_cors_origin
    ):
        return (
            "unexpected Access-Control-Allow-Origin header: "
            f"{normalized.get('access-control-allow-origin', '<missing>')}"
        )
    return None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--api-catalog-url", default=DEFAULT_API_CATALOG_URL)
    parser.add_argument("--protocol-url", default=DEFAULT_PROTOCOL_URL)
    parser.add_argument("--mcp-url", default=DEFAULT_MCP_URL)
    parser.add_argument(
        "--external-proof-only",
        action="store_true",
        help=(
            "verify declared Palimpsest and sibling release evidence before "
            "publishing the central catalogs"
        ),
    )
    parser.add_argument(
        "--pages-proof-only",
        action="store_true",
        help="verify exact bytes from a newly deployed GitHub Pages base URL",
    )
    parser.add_argument("--pages-base-url")
    parser.add_argument(
        "--worker-version-id",
        help="send Cloudflare's version-override header while probing a 0%% candidate",
    )
    parser.add_argument(
        "--palimpsest-proof",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="require live Palimpsest receipts, discovery, Registry, and MCP agreement",
    )
    parser.add_argument(
        "--sibling-proof",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="require live Undertow, Riptide, and NarcoScope release agreement",
    )
    parser.add_argument("--expected-version-tag")
    parser.add_argument("--attempts", type=int, default=12)
    parser.add_argument("--delay", type=float, default=10.0)
    parser.add_argument("--budget-seconds", type=float, default=240.0)
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
    timeout: float = 20,
    extra_headers: dict[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    _validate_public_https_url(url)
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
    if extra_headers:
        headers.update(extra_headers)
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with _SAFE_OPENER.open(
            request,
            timeout=_bounded_timeout(timeout, f"MCP {payload.get('method')!r}"),
        ) as response:
            body = _read_bounded(response, MAX_JSON_BODY_BYTES, "MCP response")
            decoded = decode_mcp_response(
                body,
                response.headers.get("Content-Type", ""),
            )
            response_headers = {
                key.lower(): value for key, value in response.headers.items()
            }
            if response.geturl() != url:
                raise RuntimeError(
                    f"MCP verification URL changed: {url!r} -> {response.geturl()!r}"
                )
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"{url}: HTTP {error.code} {error.reason}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"{url}: request failed: {error.reason}") from error
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
    if payload.get("jsonrpc") != "2.0":
        raise RuntimeError(
            f"MCP {request_id} response is not JSON-RPC 2.0: {payload!r}"
        )
    if payload.get("id") != request_id:
        raise RuntimeError(
            f"MCP response id differs: expected {request_id!r}, "
            f"received {payload.get('id')!r}"
        )
    if "error" in payload:
        raise RuntimeError(f"MCP {request_id} returned an error: {payload['error']!r}")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(
            f"MCP {request_id} response has no object result: {payload!r}"
        )
    return result


def _require_no_session_header(headers: dict[str, str], label: str) -> None:
    if "mcp-session-id" in {key.lower() for key in headers}:
        raise RuntimeError(f"{label} illegally returned Mcp-Session-Id for MCP 2026")


def _require_modern_result(
    payload: dict[str, Any],
    headers: dict[str, str],
    request_id: str,
    *,
    expected_name: str,
    expected_version: str,
) -> dict[str, Any]:
    _require_no_session_header(headers, request_id)
    result = _require_result(payload, request_id)
    _require_equal(result.get("resultType"), "complete", f"{request_id} resultType")
    server_info = result.get("_meta", {}).get("io.modelcontextprotocol/serverInfo")
    if not isinstance(server_info, dict):
        raise RuntimeError(f"{request_id} has no MCP 2026 serverInfo result metadata")
    _require_equal(server_info.get("name"), expected_name, f"{request_id} server name")
    _require_equal(
        server_info.get("version"), expected_version, f"{request_id} server version"
    )
    return result


def _validate_modern_cache_metadata(result: dict[str, Any], label: str) -> None:
    ttl_ms = result.get("ttlMs")
    if type(ttl_ms) is not int or ttl_ms < 0:
        raise RuntimeError(f"{label} has invalid ttlMs: {result!r}")
    cache_scope = result.get("cacheScope")
    if cache_scope not in {"private", "public"}:
        raise RuntimeError(f"{label} has invalid cacheScope: {result!r}")


def _normalized_tool_contract(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove non-semantic schema decoration emitted by the JS SDK."""

    normalized = json.loads(json.dumps(tools))
    for tool in normalized:
        schema = tool.get("inputSchema", {})
        schema.pop("$schema", None)
        if schema.get("properties") == {}:
            schema.pop("properties")
    return normalized


def _require_tool_contract(tools: Any, generation: str) -> None:
    if not isinstance(tools, list):
        raise RuntimeError(f"{generation} MCP tools are not a list: {tools!r}")
    if _normalized_tool_contract(tools) != EXPECTED_MCP_CONTRACT["tools"]:
        raise RuntimeError(f"{generation} MCP tool contract differs: {tools!r}")


def _verify_mcp(
    url: str,
    expected_version_tag: str | None,
    worker_version_id: str | None = None,
) -> str:
    extra_headers = (
        {
            "Cloudflare-Workers-Version-Overrides": (
                f'liquilens-ai-catalog="{worker_version_id}"'
            )
        }
        if worker_version_id
        else None
    )
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
        extra_headers=extra_headers,
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
        extra_headers=extra_headers,
    )
    _require_version_tag(headers, expected_version_tag)
    tools = _require_result(legacy_list, "legacy-list").get("tools")
    _require_tool_contract(tools, "legacy")

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
        extra_headers=extra_headers,
    )
    _require_version_tag(headers, expected_version_tag)
    discovered = _require_modern_result(
        modern_discover,
        headers,
        "modern-discover",
        expected_name=EXPECTED_MCP_SERVER,
        expected_version=EXPECTED_MCP_VERSION,
    )
    if MCP_2026_VERSION not in discovered.get("supportedVersions", []):
        raise RuntimeError(
            f"modern MCP discovery omits {MCP_2026_VERSION}: {discovered!r}"
        )
    if not isinstance(discovered.get("capabilities", {}).get("tools"), dict):
        raise RuntimeError(
            f"modern MCP discovery has no tools capability: {discovered!r}"
        )
    _validate_modern_cache_metadata(discovered, "modern MCP discovery")

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
        extra_headers=extra_headers,
    )
    _require_version_tag(headers, expected_version_tag)
    modern_list_result = _require_modern_result(
        modern_list,
        headers,
        "modern-list",
        expected_name=EXPECTED_MCP_SERVER,
        expected_version=EXPECTED_MCP_VERSION,
    )
    tools = modern_list_result.get("tools")
    _require_tool_contract(tools, "modern")

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
        extra_headers=extra_headers,
    )
    _require_version_tag(headers, expected_version_tag)
    routed = _require_modern_result(
        modern_route,
        headers,
        "modern-route",
        expected_name=EXPECTED_MCP_SERVER,
        expected_version=EXPECTED_MCP_VERSION,
    )
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
        extra_headers=extra_headers,
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
    worker_version_id: str | None = None,
) -> str:
    problem = "remote MCP was not checked"
    for attempt in range(1, attempts + 1):
        try:
            return _verify_mcp(url, expected_version_tag, worker_version_id)
        except (OSError, ValueError, RuntimeError, urllib.error.URLError) as error:
            problem = str(error)
        if attempt < attempts:
            _bounded_sleep(delay)
    raise RuntimeError(f"{url}: {problem}")


def _palimpsest_card(catalog: dict[str, Any]) -> dict[str, Any]:
    cards = [
        entry
        for entry in catalog.get("entries", [])
        if isinstance(entry, dict) and entry.get("identifier") == PALIMPSEST_CARD_ID
    ]
    if len(cards) != 1:
        raise RuntimeError(
            f"expected one {PALIMPSEST_CARD_ID} card, found {len(cards)}"
        )
    return cards[0]


def _github_run_identity(url: str) -> tuple[str, int]:
    parts = [part for part in urllib.parse.urlsplit(url).path.split("/") if part]
    if len(parts) != 5 or parts[2:4] != ["actions", "runs"]:
        raise RuntimeError(f"unexpected GitHub Actions run URL: {url!r}")
    try:
        run_id = int(parts[4])
    except ValueError as error:
        raise RuntimeError(f"unexpected GitHub Actions run id: {url!r}") from error
    return "/".join(parts[:2]), run_id


def _expected_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        raise RuntimeError(f"{label} has no sha256-prefixed digest")
    digest = value.removeprefix("sha256:")
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise RuntimeError(f"{label} has an invalid SHA-256 digest: {value!r}")
    return digest


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise RuntimeError(
            f"{label} differs: expected {expected!r}, received {actual!r}"
        )


def _json_object(body: bytes, content_type: str, label: str) -> dict[str, Any]:
    media_type, _ = _content_type_parts(content_type)
    if media_type != "application/json" and not media_type.endswith("+json"):
        raise RuntimeError(
            f"{label} has unexpected content type: {content_type or '<missing>'}"
        )
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise RuntimeError(f"{label} is not UTF-8 JSON: {error}") from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} must be one JSON object")
    return payload


def _mime_matches_declared(actual: str, declared: str) -> bool:
    actual_media_type, _ = _content_type_parts(actual)
    declared_media_type, _ = _content_type_parts(declared)
    return actual_media_type == declared_media_type or (
        actual_media_type == "application/json"
        and declared_media_type.startswith("application/")
        and declared_media_type.endswith("+json")
    )


def _fetch_bytes(
    url: str,
    *,
    accept: str,
    timeout: float = 20,
    extra_headers: dict[str, str] | None = None,
    max_bytes: int = MAX_CATALOG_BODY_BYTES,
) -> tuple[bytes, dict[str, str], str]:
    url = _canonical_verification_url(url)
    _validate_public_https_url(url)
    request_headers = {
        "Accept": accept,
        "Cache-Control": "no-cache",
        "User-Agent": "LiquiLens-edge-check/1",
    }
    if extra_headers:
        request_headers.update(extra_headers)
    request = urllib.request.Request(
        url,
        headers=request_headers,
    )
    try:
        with _SAFE_OPENER.open(
            request,
            timeout=_bounded_timeout(timeout, f"GET {url}"),
        ) as response:
            body = _read_bounded(response, max_bytes, f"GET {url}")
            headers = {key.lower(): value for key, value in response.headers.items()}
            final_url = response.geturl()
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"{url}: HTTP {error.code} {error.reason}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"{url}: request failed: {error.reason}") from error
    if final_url != url:
        raise RuntimeError(f"verification URL changed: {url!r} -> {final_url!r}")
    return body, headers, final_url


def _palimpsest_linkset_targets(
    api_catalog: dict[str, Any],
    endpoint: str,
) -> dict[str, str]:
    linksets = [
        item
        for item in api_catalog.get("linkset", [])
        if isinstance(item, dict) and item.get("anchor") == endpoint
    ]
    if len(linksets) != 1:
        raise RuntimeError(
            f"expected one RFC 9727 linkset for {endpoint}, found {len(linksets)}"
        )
    targets: dict[str, str] = {}
    for relation in ("service-desc", "service-doc", "service-meta"):
        for target in linksets[0].get(relation, []):
            if isinstance(target, dict) and isinstance(target.get("href"), str):
                targets[target["href"]] = str(target.get("type", ""))
    return targets


def _validate_palimpsest_receipts(
    card: dict[str, Any],
    receipts: dict[str, dict[str, Any]],
) -> None:
    metadata = card.get("metadata", {})
    version = card.get("version")
    endpoint = metadata.get("mcpEndpoint")
    server_name = metadata.get("mcpServerName")
    target_sha = metadata.get("deploymentCommit")
    repository, deploy_run_id = _github_run_identity(metadata.get("deploymentRun", ""))
    registry_repository, registry_run_id = _github_run_identity(
        metadata.get("registryRun", "")
    )
    _require_equal(registry_repository, repository, "Palimpsest Registry repository")

    deployment = receipts["deployment"]
    _require_equal(deployment.get("repository"), repository, "deployment repository")
    _require_equal(deployment.get("target_sha"), target_sha, "deployment target SHA")
    _require_equal(deployment.get("server_version"), version, "deployment version")
    _require_equal(
        deployment.get("workflow_run_id"),
        deploy_run_id,
        "deployment workflow run",
    )
    _require_equal(deployment.get("public_mcp_url"), endpoint, "deployment MCP URL")
    _require_equal(deployment.get("public_smoke"), "passed", "deployment public smoke")

    publication = receipts["registry publication"]
    _require_equal(publication.get("repository"), repository, "Registry repository")
    _require_equal(publication.get("target_sha"), target_sha, "Registry target SHA")
    _require_equal(publication.get("server_version"), version, "Registry version")
    _require_equal(publication.get("server_name"), server_name, "Registry server name")
    _require_equal(
        publication.get("workflow_run_id"),
        registry_run_id,
        "Registry workflow run",
    )
    _require_equal(
        publication.get("deploy_run_id"), deploy_run_id, "Registry deploy run"
    )
    _require_equal(publication.get("official_status"), "active", "Registry status")
    _require_equal(publication.get("official_is_latest"), True, "Registry latest flag")
    snapshot_digest = _expected_sha256(
        metadata.get("registrySnapshotSha256"),
        "Palimpsest Registry snapshot",
    )
    _require_equal(
        publication.get("registry_response_sha256"),
        snapshot_digest,
        "Registry response digest",
    )

    snapshot = receipts["Registry latest snapshot"]
    snapshot_server = snapshot.get("server", {})
    _require_equal(snapshot_server.get("name"), server_name, "snapshot server name")
    _require_equal(snapshot_server.get("version"), version, "snapshot version")
    remotes = snapshot_server.get("remotes", [])
    if not any(
        isinstance(remote, dict) and remote.get("url") == endpoint for remote in remotes
    ):
        raise RuntimeError(f"Registry snapshot does not expose {endpoint}")
    official = snapshot.get("_meta", {}).get(
        "io.modelcontextprotocol.registry/official", {}
    )
    _require_equal(official.get("status"), "active", "snapshot official status")
    _require_equal(official.get("isLatest"), True, "snapshot latest flag")


def _verify_palimpsest_action_runs(card: dict[str, Any]) -> None:
    metadata = card.get("metadata", {})
    target_sha = metadata.get("deploymentCommit")
    if not isinstance(target_sha, str) or len(target_sha) != 40:
        raise RuntimeError("Palimpsest has no exact deployment commit")
    for label, field, workflow in (
        ("deployment", "deploymentRun", ".github/workflows/deploy-mcp.yml"),
        ("Registry", "registryRun", ".github/workflows/registry-publish.yml"),
    ):
        run_url = metadata.get(field)
        if not isinstance(run_url, str):
            raise RuntimeError(f"Palimpsest has no {field}")
        api_url, run_id, repository = _github_workflow_api_url(run_url)
        body, headers, _ = _fetch_bytes(
            api_url,
            accept="application/vnd.github+json",
            timeout=SIBLING_REQUEST_TIMEOUT,
            max_bytes=MAX_JSON_BODY_BYTES,
        )
        payload = _json_object(
            body,
            headers.get("content-type", ""),
            f"Palimpsest {label} workflow",
        )
        _validate_sibling_source_workflow(
            f"Palimpsest {label}",
            card,
            payload,
            run_id,
            repository,
            expected_sha=target_sha,
            expected_workflow=workflow,
            expected_event="workflow_dispatch",
        )


def _validate_palimpsest_live_agreement(
    card: dict[str, Any],
    live_catalog: dict[str, Any],
    live_registry: dict[str, Any],
    initialize_result: dict[str, Any],
) -> None:
    metadata = card.get("metadata", {})
    version = card.get("version")
    endpoint = metadata.get("mcpEndpoint")
    server_name = metadata.get("mcpServerName")
    live_cards = [
        entry
        for entry in live_catalog.get("entries", [])
        if isinstance(entry, dict)
        and isinstance(entry.get("data"), dict)
        and entry["data"].get("name") == server_name
    ]
    if len(live_cards) != 1:
        raise RuntimeError(
            f"live Palimpsest catalog has {len(live_cards)} cards for {server_name}"
        )
    live_card = live_cards[0]
    _require_equal(live_card.get("version"), version, "live catalog version")
    _require_equal(
        live_card["data"].get("version"), version, "live server-card version"
    )
    if not any(
        isinstance(remote, dict) and remote.get("url") == endpoint
        for remote in live_card["data"].get("remotes", [])
    ):
        raise RuntimeError(f"live Palimpsest catalog does not expose {endpoint}")
    live_metadata = live_card.get("metadata", {})
    for declaration, count_field in (
        ("capabilities", "publicToolCount"),
        ("prompts", "publicPromptCount"),
        ("resources", "publicResourceCount"),
    ):
        expected_declaration = card.get(declaration)
        if not isinstance(expected_declaration, list) or not all(
            isinstance(value, str) and value for value in expected_declaration
        ):
            raise RuntimeError(
                f"central Palimpsest {declaration} declaration is not a string list"
            )
        live_declaration = live_card.get(declaration)
        if declaration != "resources" or live_declaration is not None:
            _require_equal(
                live_declaration,
                expected_declaration,
                f"live catalog {declaration}",
            )
        _require_equal(
            metadata.get(count_field),
            len(expected_declaration),
            f"central catalog {count_field}",
        )
        live_count = live_metadata.get(count_field)
        if declaration == "capabilities" or live_count is not None:
            _require_equal(
                live_count,
                len(expected_declaration),
                f"live catalog {count_field}",
            )
    for field in (
        "deploymentCommit",
        "deploymentReceipt",
        "deploymentReceiptSha256",
        "deploymentRun",
        "registryReceipt",
        "registryReceiptSha256",
        "registryRun",
        "registrySnapshot",
        "registrySnapshotSha256",
    ):
        _require_equal(
            live_metadata.get(field),
            metadata.get(field),
            f"live catalog {field}",
        )

    registry_server = live_registry.get("server", {})
    _require_equal(registry_server.get("name"), server_name, "live Registry name")
    _require_equal(registry_server.get("version"), version, "live Registry version")

    _require_equal(
        initialize_result.get("protocolVersion"),
        "2025-06-18",
        "Palimpsest MCP protocol",
    )
    runtime_server = initialize_result.get("serverInfo", {})
    _require_equal(runtime_server.get("version"), version, "Palimpsest MCP version")
    if not isinstance(runtime_server.get("name"), str) or not runtime_server["name"]:
        raise RuntimeError("Palimpsest MCP initialize has no server name")


def _palimpsest_surface_lists(endpoint: str) -> dict[str, dict[str, Any]]:
    surfaces: dict[str, dict[str, Any]] = {}
    for collection, method in (
        ("tools", "tools/list"),
        ("prompts", "prompts/list"),
        ("resources", "resources/list"),
    ):
        request_id = f"palimpsest-{collection}-list"
        payload, _ = _mcp_request(
            endpoint,
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": {},
            },
            protocol_version="2025-06-18",
        )
        surfaces[collection] = _require_result(payload, request_id)
    return surfaces


def _validate_palimpsest_surface_lists(
    card: dict[str, Any],
    surfaces: dict[str, dict[str, Any]],
) -> None:
    declarations = {
        "tools": (card.get("capabilities"), "name"),
        "prompts": (card.get("prompts"), "name"),
        "resources": (card.get("resources"), "uri"),
    }
    for collection, (expected, identity_field) in declarations.items():
        if not isinstance(expected, list) or not all(
            isinstance(value, str) and value for value in expected
        ):
            raise RuntimeError(
                f"Palimpsest card {collection} declaration is not a string list"
            )
        if len(expected) != len(set(expected)):
            raise RuntimeError(
                f"Palimpsest card {collection} declaration contains duplicates"
            )
        result = surfaces.get(collection)
        if not isinstance(result, dict):
            raise RuntimeError(f"Palimpsest {collection}/list has no object result")
        if result.get("nextCursor") is not None:
            raise RuntimeError(
                f"Palimpsest {collection}/list is paginated and therefore incomplete"
            )
        items = result.get(collection)
        if not isinstance(items, list):
            raise RuntimeError(f"Palimpsest {collection}/list has no {collection} list")
        actual = [
            item.get(identity_field) if isinstance(item, dict) else None
            for item in items
        ]
        if not all(isinstance(value, str) and value for value in actual):
            raise RuntimeError(
                f"Palimpsest {collection}/list contains an invalid {identity_field}"
            )
        _require_equal(
            len(actual),
            len(expected),
            f"Palimpsest live {collection} count",
        )
        _require_equal(
            sorted(actual),
            sorted(expected),
            f"Palimpsest live {collection} identities",
        )


def _palimpsest_rights_resource(endpoint: str, uri: str) -> dict[str, Any]:
    request_id = "palimpsest-publication-rights-read"
    payload, _ = _mcp_request(
        endpoint,
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "resources/read",
            "params": {"uri": uri},
        },
        protocol_version="2025-06-18",
    )
    return _require_result(payload, request_id)


def _validate_palimpsest_rights_resource(
    result: dict[str, Any],
    uri: str,
) -> None:
    contents = result.get("contents")
    if not isinstance(contents, list) or len(contents) != 1:
        raise RuntimeError(
            "Palimpsest publication-rights read must contain exactly one content"
        )
    content = contents[0]
    if not isinstance(content, dict):
        raise RuntimeError("Palimpsest publication-rights content is not an object")
    _require_equal(content.get("uri"), uri, "publication-rights content URI")
    media_type, _ = _content_type_parts(str(content.get("mimeType", "")))
    _require_equal(media_type, "application/json", "publication-rights MIME")
    text = content.get("text")
    if not isinstance(text, str):
        raise RuntimeError("Palimpsest publication-rights content has no JSON text")
    try:
        rights = json.loads(text)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Palimpsest publication-rights text is not JSON: {error}"
        ) from error
    if not isinstance(rights, dict):
        raise RuntimeError("Palimpsest publication-rights text is not an object")
    for field, expected in (
        ("status", "restricted"),
        ("availability", "unavailable"),
        ("evidence_class", "restricted"),
    ):
        _require_equal(rights.get(field), expected, f"publication-rights {field}")
    if rights.get("publication_allowed") is not False:
        raise RuntimeError(
            "publication-rights publication_allowed must be boolean false"
        )
    if rights.get("no_partial_rows") is not True:
        raise RuntimeError("publication-rights no_partial_rows must be boolean true")
    counts = rights.get("counts")
    if not isinstance(counts, dict):
        raise RuntimeError("Palimpsest publication-rights counts are missing")
    for field in ("allowed_records", "published_records"):
        value = counts.get(field)
        if type(value) is not int or value != 0:
            raise RuntimeError(f"rights {field.replace('_', ' ')} must be integer zero")
    restricted_records = counts.get("restricted_records")
    if type(restricted_records) is not int or restricted_records <= 0:
        raise RuntimeError(
            "Palimpsest publication-rights restricted records must be positive"
        )


def _verify_palimpsest_release(
    *,
    ai_catalog: dict[str, Any],
    api_catalog: dict[str, Any],
) -> str:
    card = _palimpsest_card(ai_catalog)
    metadata = card.get("metadata", {})
    receipts: dict[str, dict[str, Any]] = {}
    for label, url_field, digest_field in PALIMPSEST_RECEIPTS:
        url = metadata.get(url_field)
        if not isinstance(url, str):
            raise RuntimeError(f"Palimpsest card has no {url_field}")
        body, headers, _ = _fetch_bytes(url, accept="application/json")
        expected_digest = _expected_sha256(metadata.get(digest_field), label)
        actual_digest = hashlib.sha256(body).hexdigest()
        _require_equal(actual_digest, expected_digest, f"{label} SHA-256")
        receipts[label] = _json_object(
            body,
            headers.get("content-type", ""),
            label,
        )
    _validate_palimpsest_receipts(card, receipts)
    _verify_palimpsest_action_runs(card)

    endpoint = metadata.get("mcpEndpoint")
    if not isinstance(endpoint, str) or not endpoint:
        raise RuntimeError("Palimpsest card has no MCP endpoint")
    targets = _palimpsest_linkset_targets(api_catalog, endpoint)
    catalog_url = card.get("url")
    registry_url = receipts["registry publication"].get("registry_latest_url")
    for label, url in (
        ("Palimpsest AI catalog", catalog_url),
        ("Palimpsest Registry latest", registry_url),
    ):
        if not isinstance(url, str) or url not in targets:
            raise RuntimeError(f"RFC 9727 Palimpsest linkset omits {url!r}")
        declared_type = targets[url]
        body, headers, _ = _fetch_bytes(
            url,
            accept=f"{declared_type}, application/json",
        )
        actual_type = headers.get("content-type", "")
        if not _mime_matches_declared(actual_type, declared_type):
            raise RuntimeError(
                f"{label} MIME differs from Linkset: "
                f"declared {declared_type!r}, received {actual_type!r}"
            )
        payload = _json_object(body, actual_type, label)
        if label == "Palimpsest AI catalog":
            live_catalog = payload
        else:
            expected_digest = _expected_sha256(
                metadata.get("registrySnapshotSha256"),
                "Palimpsest live Registry latest",
            )
            _require_equal(
                hashlib.sha256(body).hexdigest(),
                expected_digest,
                "live Registry latest SHA-256",
            )
            live_registry = payload

    initialize, _ = _mcp_request(
        endpoint,
        {
            "jsonrpc": "2.0",
            "id": "palimpsest-initialize",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "liquilens-edge-check", "version": "1"},
            },
        },
    )
    initialized = _require_result(initialize, "palimpsest-initialize")
    _validate_palimpsest_live_agreement(
        card,
        live_catalog,
        live_registry,
        initialized,
    )
    surfaces = _palimpsest_surface_lists(endpoint)
    _validate_palimpsest_surface_lists(card, surfaces)
    _require_equal(
        card.get("resources"),
        [PALIMPSEST_RIGHTS_URI],
        "Palimpsest publication-rights resource declaration",
    )
    rights_result = _palimpsest_rights_resource(endpoint, PALIMPSEST_RIGHTS_URI)
    _validate_palimpsest_rights_resource(rights_result, PALIMPSEST_RIGHTS_URI)
    return (
        "Palimpsest receipts match exact bytes, source/version/run identity, "
        "RFC 9727 metadata targets, Registry latest, live MCP initialize, and "
        "the exact 6-tool/4-prompt/1-resource inventory with fail-closed "
        "publication-rights semantics"
    )


def _verify_palimpsest_release_with_retries(
    *,
    ai_catalog: dict[str, Any],
    api_catalog: dict[str, Any],
    attempts: int,
    delay: float,
) -> str:
    problem = "Palimpsest release proof was not checked"
    for attempt in range(1, attempts + 1):
        try:
            return _verify_palimpsest_release(
                ai_catalog=ai_catalog,
                api_catalog=api_catalog,
            )
        except (OSError, ValueError, RuntimeError, urllib.error.URLError) as error:
            problem = str(error)
        if attempt < attempts:
            _bounded_sleep(delay)
    raise RuntimeError(f"Palimpsest release proof: {problem}")


def _catalog_card(
    catalog: dict[str, Any],
    identifier: str,
    label: str,
) -> dict[str, Any]:
    cards = [
        entry
        for entry in catalog.get("entries", [])
        if isinstance(entry, dict) and entry.get("identifier") == identifier
    ]
    if len(cards) != 1:
        raise RuntimeError(f"expected one {label} card, found {len(cards)}")
    return cards[0]


def _sibling_expected_version(label: str, card: dict[str, Any]) -> str:
    version = card.get("version")
    if not isinstance(version, str) or not version:
        raise RuntimeError(f"{label} card has no version")
    server_card = card.get("data")
    if isinstance(server_card, dict):
        _require_equal(
            server_card.get("version"), version, f"{label} server-card version"
        )
    source_version = card.get("metadata", {}).get("sourceUpgradeVersion")
    if source_version is not None:
        _require_equal(source_version, version, f"{label} source upgrade version")
    return version


def _validate_sibling_api_catalog_response(
    label: str,
    card: dict[str, Any],
    body: bytes,
    headers: dict[str, str],
) -> dict[str, Any]:
    metadata = card.get("metadata", {})
    catalog_url = metadata.get("apiCatalog")
    endpoint = metadata.get("mcpEndpoint")
    if not isinstance(catalog_url, str) or not catalog_url:
        raise RuntimeError(f"{label} card has no RFC 9727 catalog URL")
    media_type, parameters = _content_type_parts(headers.get("content-type", ""))
    _require_equal(media_type, "application/linkset+json", f"{label} catalog MIME")
    _require_equal(
        parameters.get("profile"),
        RFC_9727_PROFILE,
        f"{label} catalog profile",
    )
    declared_digest = metadata.get("apiCatalogSha256")
    if declared_digest is not None:
        expected_digest = _expected_sha256(
            declared_digest,
            f"{label} API catalog",
        )
        _require_equal(
            hashlib.sha256(body).hexdigest(),
            expected_digest,
            f"{label} API catalog SHA-256",
        )
    link_header = headers.get("link", "")
    expected_link = f'<{catalog_url}>; rel="api-catalog"'
    if not link_header.startswith(expected_link):
        raise RuntimeError(
            f"{label} API catalog Link differs: expected prefix {expected_link!r}, "
            f"received {link_header!r}"
        )
    _require_equal(
        headers.get("access-control-allow-origin"),
        "*",
        f"{label} API catalog CORS",
    )
    payload = _json_object(
        body,
        headers.get("content-type", ""),
        f"{label} API catalog",
    )
    linksets = payload.get("linkset")
    if not isinstance(linksets, list):
        raise RuntimeError(f"{label} API catalog has no linkset list")
    endpoint_entries = [
        item
        for item in linksets
        if isinstance(item, dict) and item.get("anchor") == endpoint
    ]
    if len(endpoint_entries) != 1:
        raise RuntimeError(
            f"{label} API catalog has {len(endpoint_entries)} MCP anchors for {endpoint}"
        )
    return payload


def _registry_latest_target(
    label: str,
    api_catalog: dict[str, Any],
    endpoint: str,
) -> str:
    matching = [
        item
        for item in api_catalog.get("linkset", [])
        if isinstance(item, dict) and item.get("anchor") == endpoint
    ]
    if len(matching) != 1:
        raise RuntimeError(f"{label} API catalog has no unique MCP linkset")
    registry_targets = [
        target
        for target in matching[0].get("service-meta", [])
        if isinstance(target, dict)
        and isinstance(target.get("href"), str)
        and target["href"].startswith(
            "https://registry.modelcontextprotocol.io/v0.1/servers/"
        )
        and target["href"].endswith("/versions/latest")
    ]
    if len(registry_targets) != 1:
        raise RuntimeError(
            f"{label} API catalog has {len(registry_targets)} Registry latest targets"
        )
    _require_equal(
        registry_targets[0].get("type"),
        "application/json",
        f"{label} Registry target MIME",
    )
    return registry_targets[0]["href"]


def _validate_sibling_mcp(
    label: str,
    card: dict[str, Any],
    initialize_result: dict[str, Any],
    tools_result: dict[str, Any],
    *,
    protocol_version: str = "2025-06-18",
) -> None:
    metadata = card.get("metadata", {})
    expected_version = _sibling_expected_version(label, card)
    _require_equal(
        initialize_result.get("protocolVersion"),
        protocol_version,
        f"{label} MCP protocol",
    )
    server_info = initialize_result.get("serverInfo")
    if not isinstance(server_info, dict):
        raise RuntimeError(f"{label} MCP initialize has no serverInfo")
    _require_equal(
        server_info.get("version"),
        expected_version,
        f"{label} MCP version",
    )
    registry_name = metadata.get("mcpServerName")
    if not isinstance(registry_name, str):
        registry_name = card.get("data", {}).get("name")
    if not isinstance(registry_name, str) or not registry_name:
        raise RuntimeError(f"{label} card has no MCP server name")
    _require_equal(
        server_info.get("name"),
        registry_name.rsplit("/", 1)[-1],
        f"{label} MCP runtime name",
    )

    expected_tools = card.get("capabilities")
    if not isinstance(expected_tools, list) or not all(
        isinstance(name, str) and name for name in expected_tools
    ):
        raise RuntimeError(f"{label} capabilities are not a string list")
    if len(expected_tools) != len(set(expected_tools)):
        raise RuntimeError(f"{label} capabilities contain duplicates")
    _require_equal(
        metadata.get("publicToolCount"),
        len(expected_tools),
        f"{label} declared public tool count",
    )
    if tools_result.get("nextCursor") is not None:
        raise RuntimeError(f"{label} tools/list is paginated and incomplete")
    tools = tools_result.get("tools")
    if not isinstance(tools, list):
        raise RuntimeError(f"{label} tools/list has no tools list")
    actual_tools = [
        tool.get("name") if isinstance(tool, dict) else None for tool in tools
    ]
    if not all(isinstance(name, str) and name for name in actual_tools):
        raise RuntimeError(f"{label} tools/list contains an invalid name")
    _require_equal(
        len(actual_tools),
        len(expected_tools),
        f"{label} live public tool count",
    )
    _require_equal(
        sorted(actual_tools),
        sorted(expected_tools),
        f"{label} live public tool identities",
    )


def _sibling_runtime_name(card: dict[str, Any], label: str) -> str:
    metadata = card.get("metadata", {})
    registry_name = metadata.get("mcpServerName")
    if not isinstance(registry_name, str):
        registry_name = card.get("data", {}).get("name")
    if not isinstance(registry_name, str) or not registry_name:
        raise RuntimeError(f"{label} card has no MCP server name")
    return registry_name.rsplit("/", 1)[-1]


def _validate_modern_sibling_discovery(
    label: str,
    card: dict[str, Any],
    result: dict[str, Any],
) -> None:
    advertised = card.get("protocolVersions")
    if not isinstance(advertised, list) or MCP_2026_VERSION not in advertised:
        raise RuntimeError(f"{label} does not advertise MCP {MCP_2026_VERSION}")
    supported = result.get("supportedVersions")
    if (
        not isinstance(supported, list)
        or not supported
        or len(supported) != len(set(supported))
        or MCP_2026_VERSION not in supported
        or any(version not in advertised for version in supported)
    ):
        raise RuntimeError(
            f"{label} modern supported versions are invalid: "
            f"advertised {advertised!r}, received {supported!r}"
        )
    if not isinstance(result.get("capabilities", {}).get("tools"), dict):
        raise RuntimeError(f"{label} modern discovery has no tools capability")
    _validate_modern_cache_metadata(result, f"{label} modern discovery")


def _validate_modern_tool_call(label: str, result: dict[str, Any]) -> None:
    if result.get("isError") is not False:
        raise RuntimeError(f"{label} modern tool probe returned an error")
    if not isinstance(result.get("content"), list) or not result["content"]:
        raise RuntimeError(f"{label} modern tool probe has no content")
    if not isinstance(result.get("structuredContent"), dict):
        raise RuntimeError(f"{label} modern tool probe has no structuredContent")


def _verify_sibling_mcp_protocols(
    label: str,
    card: dict[str, Any],
    endpoint: str,
) -> None:
    versions = card.get("protocolVersions")
    if (
        not isinstance(versions, list)
        or not versions
        or len(versions) != len(set(versions))
    ):
        raise RuntimeError(f"{label} protocolVersions are missing or duplicated")
    expected_version = _sibling_expected_version(label, card)
    expected_name = _sibling_runtime_name(card, label)
    tool_name = SIBLING_PROBE_TOOL[label]
    if tool_name not in card.get("capabilities", []):
        raise RuntimeError(f"{label} safe probe tool is not advertised: {tool_name}")

    modern_meta = {
        "io.modelcontextprotocol/clientInfo": {
            "name": "liquilens-edge-check",
            "version": "1",
        },
        "io.modelcontextprotocol/protocolVersion": MCP_2026_VERSION,
        "io.modelcontextprotocol/clientCapabilities": {},
    }
    for version in versions:
        if version == MCP_2026_VERSION:
            requests = (
                ("discover", "server/discover", {"_meta": modern_meta}, None),
                ("list", "tools/list", {"_meta": modern_meta}, None),
                (
                    "call",
                    "tools/call",
                    {
                        "name": tool_name,
                        "arguments": {},
                        "_meta": modern_meta,
                    },
                    tool_name,
                ),
            )
            modern_results: dict[str, dict[str, Any]] = {}
            for suffix, method, params, name in requests:
                request_id = f"{label.lower()}-modern-{suffix}"
                payload, headers = _mcp_request(
                    endpoint,
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "method": method,
                        "params": params,
                    },
                    protocol_version=version,
                    method_header=method,
                    name_header=name,
                    timeout=SIBLING_REQUEST_TIMEOUT,
                )
                modern_results[suffix] = _require_modern_result(
                    payload,
                    headers,
                    request_id,
                    expected_name=expected_name,
                    expected_version=expected_version,
                )
            _validate_modern_sibling_discovery(label, card, modern_results["discover"])
            _validate_sibling_mcp(
                label,
                card,
                {
                    "protocolVersion": version,
                    "serverInfo": {"name": expected_name, "version": expected_version},
                },
                modern_results["list"],
                protocol_version=version,
            )
            _validate_modern_tool_call(label, modern_results["call"])
            continue

        initialize_id = f"{label.lower()}-{version}-initialize"
        initialize, _ = _mcp_request(
            endpoint,
            {
                "jsonrpc": "2.0",
                "id": initialize_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": version,
                    "capabilities": {},
                    "clientInfo": {"name": "liquilens-edge-check", "version": "1"},
                },
            },
            protocol_version=version,
            timeout=SIBLING_REQUEST_TIMEOUT,
        )
        list_id = f"{label.lower()}-{version}-tools-list"
        tools, _ = _mcp_request(
            endpoint,
            {"jsonrpc": "2.0", "id": list_id, "method": "tools/list", "params": {}},
            protocol_version=version,
            timeout=SIBLING_REQUEST_TIMEOUT,
        )
        _validate_sibling_mcp(
            label,
            card,
            _require_result(initialize, initialize_id),
            _require_result(tools, list_id),
            protocol_version=version,
        )
        call_id = f"{label.lower()}-{version}-tool-call"
        called, _ = _mcp_request(
            endpoint,
            {
                "jsonrpc": "2.0",
                "id": call_id,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": {}},
            },
            protocol_version=version,
            timeout=SIBLING_REQUEST_TIMEOUT,
        )
        called_result = _require_result(called, call_id)
        if called_result.get("isError") is not False:
            raise RuntimeError(f"{label} MCP {version} tool probe returned an error")


def _validate_sibling_origin_catalog(
    label: str,
    card: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    metadata = card.get("metadata", {})
    server_name = metadata.get("mcpServerName")
    live_cards = [
        entry
        for entry in payload.get("entries", [])
        if isinstance(entry, dict)
        and isinstance(entry.get("data"), dict)
        and entry["data"].get("name") == server_name
    ]
    if len(live_cards) != 1:
        raise RuntimeError(
            f"{label} origin catalog has {len(live_cards)} cards for {server_name}"
        )
    live_card = live_cards[0]
    version = _sibling_expected_version(label, card)
    _require_equal(live_card.get("version"), version, f"{label} origin version")
    _require_equal(
        live_card["data"].get("version"),
        version,
        f"{label} origin server-card version",
    )
    _require_equal(
        live_card.get("capabilities"),
        card.get("capabilities"),
        f"{label} origin tool declaration",
    )
    if card.get("prompts") is not None:
        _require_equal(
            live_card.get("prompts"),
            card.get("prompts"),
            f"{label} origin prompt declaration",
        )
    _require_equal(
        live_card.get("metadata", {}).get("publicToolCount"),
        metadata.get("publicToolCount"),
        f"{label} origin public tool count",
    )
    endpoint = metadata.get("mcpEndpoint")
    if not any(
        isinstance(remote, dict) and remote.get("url") == endpoint
        for remote in live_card["data"].get("remotes", [])
    ):
        raise RuntimeError(f"{label} origin catalog does not expose {endpoint}")
    repository = live_card["data"].get("repository")
    if not isinstance(repository, dict):
        raise RuntimeError(f"{label} origin catalog has no source repository")
    return repository


def _sibling_registry_version(label: str, card: dict[str, Any]) -> str:
    metadata = card.get("metadata", {})
    live_version = _sibling_expected_version(label, card)
    exact_url = metadata.get("registryVersion")
    if exact_url is None:
        registry_version = live_version
    elif isinstance(exact_url, str):
        registry_version = urllib.parse.unquote(
            urllib.parse.urlsplit(exact_url).path.rsplit("/", 1)[-1]
        )
    else:
        raise RuntimeError(f"{label} Registry version URL is invalid")
    advertised = metadata.get("registryAdvertisedVersion")
    if advertised is not None:
        _require_equal(advertised, registry_version, f"{label} Registry declaration")
    if registry_version != live_version:
        if label != "Riptide":
            raise RuntimeError(
                f"{label} live {live_version} / Registry {registry_version} split "
                "is not permitted"
            )
        for field, expected in (
            ("sourceUpgradeState", "live-registry-publication-gated"),
            ("registryUpgradeState", "held-until-origin-catalog-live"),
        ):
            _require_equal(
                metadata.get(field),
                expected,
                f"Riptide explicit Registry split {field}",
            )
        release_gate = metadata.get("originCatalogReleaseGate")
        if not isinstance(release_gate, str) or not release_gate.startswith("https://"):
            raise RuntimeError(
                "Riptide Registry split has no HTTPS origin release gate"
            )
    return registry_version


def _validate_sibling_registry(
    label: str,
    card: dict[str, Any],
    payload: dict[str, Any],
    *,
    expected_version: str,
    require_latest: bool,
    expected_repository: dict[str, Any] | None = None,
) -> None:
    metadata = card.get("metadata", {})
    server = payload.get("server")
    if not isinstance(server, dict):
        raise RuntimeError(f"{label} Registry response has no server card")
    expected_name = metadata.get("mcpServerName")
    central_server = card.get("data")
    if not isinstance(expected_name, str) and isinstance(central_server, dict):
        expected_name = central_server.get("name")
    _require_equal(server.get("name"), expected_name, f"{label} Registry name")
    _require_equal(
        server.get("version"),
        expected_version,
        f"{label} Registry version",
    )
    endpoint = metadata.get("mcpEndpoint")
    if not any(
        isinstance(remote, dict) and remote.get("url") == endpoint
        for remote in server.get("remotes", [])
    ):
        raise RuntimeError(f"{label} Registry card does not expose {endpoint}")
    if isinstance(central_server, dict) and isinstance(
        central_server.get("repository"), dict
    ):
        expected_repository = central_server.get("repository")
    if expected_repository is None:
        expected_repository = SIBLING_REGISTRY_REPOSITORIES.get(label)
    if not isinstance(expected_repository, dict):
        raise RuntimeError(f"{label} has no independent Registry repository contract")
    _require_equal(
        server.get("repository"),
        expected_repository,
        f"{label} Registry source repository",
    )
    official = payload.get("_meta", {}).get(
        "io.modelcontextprotocol.registry/official", {}
    )
    _require_equal(official.get("status"), "active", f"{label} Registry status")
    if require_latest:
        _require_equal(
            official.get("isLatest"),
            True,
            f"{label} Registry latest flag",
        )
    declared_status = metadata.get("registryStatus")
    if declared_status is not None:
        _require_equal(
            declared_status,
            "active-latest",
            f"{label} central Registry status",
        )


def _github_workflow_api_url(url: str) -> tuple[str, int, str]:
    repository, run_id = _github_run_identity(url)
    owner, name = repository.split("/", 1)
    return (
        f"https://api.github.com/repos/{owner}/{name}/actions/runs/{run_id}",
        run_id,
        repository,
    )


def _validate_sibling_source_workflow(
    label: str,
    card: dict[str, Any],
    payload: dict[str, Any],
    run_id: int,
    repository: str,
    *,
    expected_sha: str | None = None,
    expected_workflow: str | None = None,
    expected_event: str | None = None,
    expected_branch: str = "main",
) -> None:
    metadata = card.get("metadata", {})
    _require_equal(payload.get("id"), run_id, f"{label} source workflow run id")
    _require_equal(
        payload.get("repository", {}).get("full_name"),
        repository,
        f"{label} source workflow repository",
    )
    _require_equal(payload.get("status"), "completed", f"{label} workflow status")
    _require_equal(payload.get("conclusion"), "success", f"{label} workflow result")
    if expected_workflow is not None:
        actual_path = payload.get("path")
        if isinstance(actual_path, str):
            actual_path = actual_path.split("@", 1)[0]
        _require_equal(actual_path, expected_workflow, f"{label} workflow path")
    if expected_event is not None:
        _require_equal(payload.get("event"), expected_event, f"{label} workflow event")
    _require_equal(
        payload.get("head_branch"),
        expected_branch,
        f"{label} workflow branch",
    )
    _require_equal(
        payload.get("head_sha"),
        expected_sha or metadata.get("sourceUpgradeCommit"),
        f"{label} workflow source SHA",
    )


def _verify_sibling_action_proofs(label: str, card: dict[str, Any]) -> str:
    metadata = card.get("metadata", {})
    proofs = SIBLING_ACTION_PROOFS.get(label, ())
    if label == "Riptide":
        private_proofs = (
            (
                "sourceUpgrade",
                "https://github.com/beepboop2025/riptide/actions/runs/33259877818",
                metadata.get("sourceUpgradeCommit"),
            ),
            (
                "registryPublication",
                "https://github.com/beepboop2025/riptide/actions/runs/32929046333",
                "350169e471d10085c2381c459486b9c263de7985",
            ),
        )
        for prefix, expected_run, expected_sha in private_proofs:
            for suffix, expected in (
                ("ProofRun", expected_run),
                ("ProofCommit", expected_sha),
                ("ProofVisibility", "owner-private"),
                ("ProofState", "owner-verified-success"),
                ("ProofPubliclyFetchable", False),
            ):
                _require_equal(
                    metadata.get(f"{prefix}{suffix}"),
                    expected,
                    f"Riptide private proof boundary {prefix}{suffix}",
                )
        return (
            "two explicitly owner-private successful GitHub Actions proofs; "
            "public runtime and Registry state independently verified"
        )
    if not proofs:
        raise RuntimeError(f"{label} has no immutable GitHub Actions proof contract")
    for proof in proofs:
        url = proof.get("url") or metadata.get(proof.get("url_field", ""))
        if not isinstance(url, str):
            raise RuntimeError(f"{label} {proof['kind']} has no workflow URL")
        api_url, run_id, repository = _github_workflow_api_url(url)
        expected_sha = proof.get("sha") or metadata.get(proof.get("sha_field", ""))
        if not isinstance(expected_sha, str) or len(expected_sha) != 40:
            raise RuntimeError(f"{label} {proof['kind']} has no exact source SHA")
        body, headers, _ = _fetch_bytes(
            api_url,
            accept="application/vnd.github+json",
            timeout=SIBLING_REQUEST_TIMEOUT,
            max_bytes=MAX_JSON_BODY_BYTES,
        )
        payload = _json_object(
            body,
            headers.get("content-type", ""),
            f"{label} {proof['kind']}",
        )
        _validate_sibling_source_workflow(
            f"{label} {proof['kind']}",
            card,
            payload,
            run_id,
            repository,
            expected_sha=expected_sha,
            expected_workflow=proof["workflow"],
            expected_event=proof["event"],
            expected_branch=proof.get("branch", "main"),
        )
    return f"{len(proofs)} immutable successful GitHub Actions proofs"


def _validate_github_deployment(
    label: str,
    deployment: dict[str, Any],
    statuses: list[Any],
    *,
    expected_id: int,
    expected_sha: str,
) -> None:
    _require_equal(deployment.get("id"), expected_id, f"{label} deployment id")
    _require_equal(deployment.get("sha"), expected_sha, f"{label} deployment SHA")
    _require_equal(deployment.get("ref"), expected_sha, f"{label} deployment ref")
    _require_equal(deployment.get("task"), "deploy", f"{label} deployment task")
    _require_equal(
        str(deployment.get("environment", "")).lower(),
        "production",
        f"{label} deployment environment",
    )
    if not statuses or not isinstance(statuses[0], dict):
        raise RuntimeError(f"{label} deployment has no status")
    _require_equal(statuses[0].get("state"), "success", f"{label} deployment status")
    environment_url = statuses[0].get("environment_url")
    if not isinstance(environment_url, str):
        raise RuntimeError(f"{label} deployment has no environment URL")
    _validate_public_https_url(environment_url)


def _verify_sibling_deployment_proof(label: str, card: dict[str, Any]) -> str:
    metadata = card.get("metadata", {})
    deployment_id = metadata.get("productionDeploymentId")
    if deployment_id is None:
        return ""
    try:
        expected_id = int(deployment_id)
    except (TypeError, ValueError) as error:
        raise RuntimeError(f"{label} deployment ID is invalid") from error
    source_sha = metadata.get("sourceUpgradeCommit")
    if not isinstance(source_sha, str):
        raise RuntimeError(f"{label} deployment proof has no source SHA")
    repository = urllib.parse.urlsplit(
        card.get("data", {}).get("repository", {}).get("url", "")
    ).path.strip("/")
    if not repository:
        raise RuntimeError(f"{label} deployment proof has no source repository")
    base_url = f"https://api.github.com/repos/{repository}/deployments/{expected_id}"
    body, headers, _ = _fetch_bytes(
        base_url,
        accept="application/vnd.github+json",
        timeout=SIBLING_REQUEST_TIMEOUT,
        max_bytes=MAX_JSON_BODY_BYTES,
    )
    deployment = _json_object(
        body,
        headers.get("content-type", ""),
        f"{label} GitHub deployment",
    )
    status_body, status_headers, _ = _fetch_bytes(
        f"{base_url}/statuses",
        accept="application/vnd.github+json",
        timeout=SIBLING_REQUEST_TIMEOUT,
        max_bytes=MAX_JSON_BODY_BYTES,
    )
    try:
        statuses = json.loads(status_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise RuntimeError(f"{label} deployment statuses are not JSON") from error
    if not isinstance(statuses, list):
        raise RuntimeError(f"{label} deployment statuses are not a list")
    _validate_github_deployment(
        label,
        deployment,
        statuses,
        expected_id=expected_id,
        expected_sha=source_sha,
    )
    return ", and one successful production deployment proof"


def _verify_sibling_product(label: str, card: dict[str, Any]) -> str:
    metadata = card.get("metadata", {})
    endpoint = metadata.get("mcpEndpoint")
    catalog_url = metadata.get("apiCatalog")
    if not isinstance(endpoint, str) or not endpoint:
        raise RuntimeError(f"{label} card has no MCP endpoint")
    if not isinstance(catalog_url, str) or not catalog_url:
        raise RuntimeError(f"{label} card has no API catalog")

    body, headers, _ = _fetch_bytes(
        catalog_url,
        accept="application/linkset+json",
        timeout=SIBLING_REQUEST_TIMEOUT,
    )
    api_catalog = _validate_sibling_api_catalog_response(
        label,
        card,
        body,
        headers,
    )
    expected_repository = None
    if card.get("type") == "application/ai-catalog+json":
        origin_url = card.get("url")
        if not isinstance(origin_url, str):
            raise RuntimeError(f"{label} card has no origin AI catalog URL")
        origin_body, origin_headers, _ = _fetch_bytes(
            origin_url,
            accept="application/ai-catalog+json, application/json",
            timeout=SIBLING_REQUEST_TIMEOUT,
        )
        if not _mime_matches_declared(
            origin_headers.get("content-type", ""),
            "application/ai-catalog+json",
        ):
            raise RuntimeError(
                f"{label} origin AI catalog has unexpected MIME: "
                f"{origin_headers.get('content-type', '<missing>')}"
            )
        origin_catalog = _json_object(
            origin_body,
            origin_headers.get("content-type", ""),
            f"{label} origin AI catalog",
        )
        expected_repository = _validate_sibling_origin_catalog(
            label,
            card,
            origin_catalog,
        )

    _verify_sibling_mcp_protocols(label, card, endpoint)

    expected_registry_version = _sibling_registry_version(label, card)
    latest_url = _registry_latest_target(label, api_catalog, endpoint)
    registry_body, registry_headers, _ = _fetch_bytes(
        latest_url,
        accept="application/json",
        timeout=SIBLING_REQUEST_TIMEOUT,
    )
    latest_registry = _json_object(
        registry_body,
        registry_headers.get("content-type", ""),
        f"{label} Registry latest",
    )
    _validate_sibling_registry(
        label,
        card,
        latest_registry,
        expected_version=expected_registry_version,
        require_latest=True,
        expected_repository=expected_repository,
    )
    exact_registry_url = metadata.get("registryVersion")
    if isinstance(exact_registry_url, str) and exact_registry_url != latest_url:
        exact_body, exact_headers, _ = _fetch_bytes(
            exact_registry_url,
            accept="application/json",
            timeout=SIBLING_REQUEST_TIMEOUT,
        )
        exact_registry = _json_object(
            exact_body,
            exact_headers.get("content-type", ""),
            f"{label} exact Registry version",
        )
        _validate_sibling_registry(
            label,
            card,
            exact_registry,
            expected_version=expected_registry_version,
            require_latest=False,
            expected_repository=expected_repository,
        )

    action_proofs = _verify_sibling_action_proofs(label, card)
    deployment_proof = _verify_sibling_deployment_proof(label, card)
    return (
        f"{label} RFC 9727 catalog, MCP {_sibling_expected_version(label, card)} "
        f"across {len(card['protocolVersions'])} protocols with "
        f"{len(card['capabilities'])} exact tools, active Registry "
        f"{expected_registry_version}, {action_proofs}{deployment_proof} agree"
    )


def _verify_sibling_products_with_retries(
    *,
    ai_catalog: dict[str, Any],
    attempts: int,
    delay: float,
) -> str:
    bounded_attempts = min(attempts, SIBLING_MAX_ATTEMPTS)
    bounded_delay = min(delay, SIBLING_RETRY_DELAY)
    results = []
    failures = []
    for label, identifier in SIBLING_CARD_IDS:
        card = _catalog_card(ai_catalog, identifier, label)
        problem = f"{label} was not checked"
        for attempt in range(1, bounded_attempts + 1):
            try:
                results.append(_verify_sibling_product(label, card))
                break
            except (OSError, ValueError, RuntimeError, urllib.error.URLError) as error:
                problem = str(error)
            if attempt < bounded_attempts:
                _bounded_sleep(bounded_delay)
        else:
            failures.append(f"{label}: {problem}")
    if failures:
        summary = "; ".join(failures)
        if results:
            summary += f"; passed={'; '.join(results)}"
        raise RuntimeError(f"sibling external proof failed: {summary}")
    return "; ".join(results)


def _verify_external_release_proofs(
    *,
    ai_catalog: dict[str, Any],
    api_catalog: dict[str, Any],
    palimpsest_proof: bool,
    sibling_proof: bool,
    attempts: int,
    delay: float,
) -> tuple[str, ...]:
    results = []
    failures = []
    if palimpsest_proof:
        try:
            results.append(
                _verify_palimpsest_release_with_retries(
                    ai_catalog=ai_catalog,
                    api_catalog=api_catalog,
                    attempts=attempts,
                    delay=delay,
                )
            )
        except RuntimeError as error:
            failures.append(str(error))
    if sibling_proof:
        try:
            results.append(
                _verify_sibling_products_with_retries(
                    ai_catalog=ai_catalog,
                    attempts=attempts,
                    delay=delay,
                )
            )
        except RuntimeError as error:
            failures.append(str(error))
    if failures:
        summary = "; ".join(failures)
        if results:
            summary += f"; passed={'; '.join(results)}"
        raise RuntimeError(f"external release proof failed: {summary}")
    return tuple(results)


def _verify_url(
    *,
    expected: dict[str, Any],
    expected_path: Path,
    expected_content_type: str,
    expected_body: bytes | None = None,
    expected_profile: str | None = None,
    expected_link: str | None = None,
    expected_cors_origin: str | None = None,
    url: str,
    attempts: int,
    delay: float,
    worker_version_id: str | None = None,
) -> str:
    problem = "edge catalog was not checked"
    for attempt in range(1, attempts + 1):
        separator = "&" if urllib.parse.urlsplit(url).query else "?"
        request_url = f"{url}{separator}catalog_check={attempt}-{time.time_ns()}"
        extra_headers = (
            {
                "Cloudflare-Workers-Version-Overrides": (
                    f'liquilens-ai-catalog="{worker_version_id}"'
                )
            }
            if worker_version_id
            else None
        )
        try:
            body, headers, _ = _fetch_bytes(
                request_url,
                accept=expected_content_type,
                timeout=20,
                extra_headers=extra_headers,
                max_bytes=MAX_CATALOG_BODY_BYTES,
            )
            problem = (
                response_problem(
                    expected,
                    body,
                    headers.get("content-type", ""),
                    expected_content_type,
                    expected_body=expected_body,
                    expected_profile=expected_profile,
                )
                or ""
            )
            if not problem:
                problem = (
                    response_headers_problem(
                        headers,
                        expected_link=expected_link,
                        expected_cors_origin=expected_cors_origin,
                    )
                    or ""
                )
        except (OSError, RuntimeError, urllib.error.URLError) as error:
            problem = f"edge request failed: {error}"
        if not problem:
            return f"edge catalog matches {expected_path}"
        if attempt < attempts:
            _bounded_sleep(delay)
    raise RuntimeError(f"{expected_path}: {problem}")


def _verify_pages_bytes(
    *,
    base_url: str,
    attempts: int,
    delay: float,
) -> tuple[str, ...]:
    if not base_url.endswith("/"):
        base_url += "/"
    _validate_public_https_url(base_url)
    results = []
    for path in (CATALOG_PATH, API_CATALOG_PATH, PROTOCOL_CATALOG_PATH):
        relative = path.relative_to(ROOT).as_posix()
        url = urllib.parse.urljoin(base_url, relative)
        expected = path.read_bytes()
        problem = "Pages bytes were not checked"
        for attempt in range(1, attempts + 1):
            separator = "&" if urllib.parse.urlsplit(url).query else "?"
            request_url = f"{url}{separator}pages_check={attempt}-{time.time_ns()}"
            try:
                body, _, _ = _fetch_bytes(
                    request_url,
                    accept="application/json, application/*+json",
                    timeout=20,
                    max_bytes=MAX_CATALOG_BODY_BYTES,
                )
                if body == expected:
                    results.append(f"Pages exact bytes match {relative}")
                    break
                problem = (
                    f"byte mismatch expected_sha256={hashlib.sha256(expected).hexdigest()} "
                    f"actual_sha256={hashlib.sha256(body).hexdigest()}"
                )
            except (OSError, RuntimeError, urllib.error.URLError) as error:
                problem = str(error)
            if attempt < attempts:
                _bounded_sleep(delay)
        else:
            raise RuntimeError(f"Pages {relative}: {problem}")
    return tuple(results)


def _run(args: argparse.Namespace) -> int:
    ai_catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    api_catalog = json.loads(API_CATALOG_PATH.read_text(encoding="utf-8"))
    if args.pages_proof_only:
        try:
            for result in _verify_pages_bytes(
                base_url=args.pages_base_url,
                attempts=args.attempts,
                delay=args.delay,
            ):
                print(result)
        except RuntimeError as error:
            print(error)
            return 1
        return 0
    if args.external_proof_only:
        try:
            for result in _verify_external_release_proofs(
                ai_catalog=ai_catalog,
                api_catalog=api_catalog,
                palimpsest_proof=True,
                sibling_proof=True,
                attempts=args.attempts,
                delay=args.delay,
            ):
                print(result)
        except RuntimeError as error:
            print(error)
            return 1
        return 0
    protocol_catalog = json.loads(PROTOCOL_CATALOG_PATH.read_text(encoding="utf-8"))
    checks = (
        {
            "expected": api_catalog,
            "expected_path": API_CATALOG_PATH,
            "expected_content_type": "application/linkset+json",
            "expected_body": compact_json_bytes(api_catalog),
            "expected_profile": RFC_9727_PROFILE,
            "expected_link": API_CATALOG_LINK,
            "expected_cors_origin": "*",
            "url": args.api_catalog_url,
        },
        {
            "expected": ai_catalog,
            "expected_path": CATALOG_PATH,
            "expected_content_type": "application/ai-catalog+json",
            "url": args.url,
        },
        {
            "expected": protocol_catalog,
            "expected_path": PROTOCOL_CATALOG_PATH,
            "expected_content_type": "application/json",
            "url": args.protocol_url,
        },
    )
    try:
        for check in checks:
            print(
                _verify_url(
                    attempts=args.attempts,
                    delay=args.delay,
                    worker_version_id=args.worker_version_id,
                    **check,
                )
            )
        print(
            _verify_mcp_with_retries(
                url=args.mcp_url,
                expected_version_tag=args.expected_version_tag,
                attempts=args.attempts,
                delay=args.delay,
                worker_version_id=args.worker_version_id,
            )
        )
        for result in _verify_external_release_proofs(
            ai_catalog=ai_catalog,
            api_catalog=api_catalog,
            palimpsest_proof=args.palimpsest_proof,
            sibling_proof=args.sibling_proof,
            attempts=args.attempts,
            delay=args.delay,
        ):
            print(result)
    except RuntimeError as error:
        print(error)
        return 1
    return 0


def main() -> int:
    args = _parser().parse_args()
    if args.attempts < 1 or args.delay < 0 or args.budget_seconds <= 0:
        raise SystemExit(
            "attempts and budget must be positive and delay must be non-negative"
        )
    if args.external_proof_only and args.pages_proof_only:
        raise SystemExit("proof-only modes cannot be combined")
    if args.pages_proof_only and not args.pages_base_url:
        raise SystemExit("--pages-proof-only requires --pages-base-url")
    if args.pages_base_url and not args.pages_proof_only:
        raise SystemExit("--pages-base-url requires --pages-proof-only")
    if args.worker_version_id and (
        len(args.worker_version_id) != 36
        or any(
            character not in "0123456789abcdef-"
            for character in args.worker_version_id.lower()
        )
    ):
        raise SystemExit("--worker-version-id must be one UUID-shaped version ID")
    if args.external_proof_only and (
        not args.palimpsest_proof or not args.sibling_proof
    ):
        raise SystemExit(
            "--external-proof-only cannot be combined with an external proof opt-out"
        )
    with _network_budget(args.budget_seconds):
        return _run(args)


if __name__ == "__main__":
    raise SystemExit(main())
