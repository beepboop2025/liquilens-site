#!/usr/bin/env python3
"""Run a public bank review or funding brief with Python 3.11+, without an LLM.

One run performs one bounded research task. No account, key, package, scheduler,
automatic retry or filesystem write is required. JSON goes to stdout.
"""
import argparse
from datetime import datetime, timezone
import json
from queue import Empty, Queue
import re
import sys
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

VERSION = "1.0.0"
PROTOCOL = "2025-11-25"
CLIENT_INFO = {"name": "liquilens-research-recipes", "version": VERSION}
ENDPOINTS = {
    "bank-review": "https://api.liquilens.in/mcp",
    "funding-brief": "https://api.seiche.info/mcp",
}
TIMEOUT = 20
MAX_BYTES = 2 * 1024 * 1024


class ResearchError(Exception):
    """A transport, protocol or tool error; never a research conclusion."""


def parse_json(raw):
    def invalid_constant(value):
        raise ValueError("non-finite JSON value: " + value)

    try:
        return json.loads(raw, parse_constant=invalid_constant)
    except (ValueError, UnicodeError) as exc:
        raise ResearchError("response is not valid finite JSON") from exc


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        raise ResearchError("redirect refused; only the documented endpoints are allowed")


def _exchange(url, payload, headers):
    """A bounded HTTP exchange; called inside a deadline-limited daemon thread."""
    if url not in ENDPOINTS.values():
        raise ResearchError("endpoint is not allowed")
    request = Request(url, data=json.dumps(payload).encode(), headers=headers)
    try:
        with build_opener(ProxyHandler({}), NoRedirects()).open(request, timeout=TIMEOUT) as response:
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ResearchError("response exceeds the 2 MiB limit")
            if response.status not in (200, 202, 204):
                raise ResearchError("unexpected HTTP status " + str(response.status))
            return response.status, dict(response.headers.items()), raw
    except HTTPError as exc:
        raise ResearchError("HTTP " + str(exc.code) + "; no automatic retry") from exc
    except (URLError, OSError) as exc:
        raise ResearchError("network request failed or timed out") from exc


def exchange(url, payload, headers):
    # Socket timeouts alone can be extended by a slowly trickling response.
    # A daemon worker enforces the wall-clock deadline on macOS/Linux/Windows;
    # the CLI exits on failure and never retries the outstanding read.
    result = Queue(maxsize=1)

    def run():
        try:
            result.put((True, _exchange(url, payload, headers)))
        except Exception as exc:
            result.put((False, exc))

    Thread(target=run, daemon=True).start()
    try:
        succeeded, value = result.get(timeout=TIMEOUT)
    except Empty as exc:
        raise ResearchError("20-second request deadline exceeded; no automatic retry") from exc
    if not succeeded:
        raise value
    return value


class Client:
    def __init__(self, endpoint, *, verification=False, transport=exchange):
        if endpoint not in ENDPOINTS.values():
            raise ResearchError("endpoint is not allowed")
        self.endpoint = endpoint
        self.transport = transport
        self.sequence = 0
        self.session = None
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": "LiquiLens-Operator-Growth-Audit/1.0" if verification
            else "liquilens-research-recipes/" + VERSION,
        }
        if verification:
            self.headers["X-Liquilens-Traffic-Class"] = "synthetic"

    def request(self, method, params=None, *, notification=False):
        self.sequence += 1
        payload = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        if not notification:
            payload["id"] = self.sequence
        headers = dict(self.headers)
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        status, received_headers, raw = self.transport(self.endpoint, payload, headers)
        received_headers = {key.lower(): value for key, value in received_headers.items()}
        if notification:
            if status not in (200, 202, 204) or raw.strip():
                raise ResearchError("initialization notification was not accepted")
            return None
        if status != 200:
            raise ResearchError("MCP request did not return HTTP 200")
        message = parse_json(raw)
        if (not isinstance(message, dict) or message.get("jsonrpc") != "2.0"
                or type(message.get("id")) is not int or message["id"] != self.sequence):
            raise ResearchError("invalid or mismatched JSON-RPC response")
        if "error" in message:
            raise ResearchError("MCP rejected " + method + ": " + json.dumps(message["error"])[:500])
        result = message.get("result")
        if not isinstance(result, dict):
            raise ResearchError("MCP response has no result object")
        if method == "initialize":
            if result.get("protocolVersion") != PROTOCOL:
                raise ResearchError("server did not negotiate the supported MCP version")
            self.session = received_headers.get("mcp-session-id")
        return result

    def initialize(self):
        self.request("initialize", {"protocolVersion": PROTOCOL,
                                    "capabilities": {}, "clientInfo": CLIENT_INFO})
        self.headers["MCP-Protocol-Version"] = PROTOCOL
        self.request("notifications/initialized", notification=True)

    def call(self, name, arguments):
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError", False) is not False:
            raise ResearchError("MCP tool " + name + " returned an error")
        evidence = result.get("structuredContent")
        if evidence is None:
            content = result.get("content", [])
            texts = [row.get("text") for row in content if isinstance(row, dict) and row.get("type") == "text"]
            if len(texts) != 1 or not isinstance(texts[0], str):
                raise ResearchError("MCP tool returned no structured JSON evidence")
            evidence = parse_json(texts[0])
        if not isinstance(evidence, dict):
            raise ResearchError("MCP tool evidence must be an object")
        if evidence.get("status") in ("FAILED", "error"):
            raise ResearchError("MCP tool reported failure: " + str(evidence.get("reason", name))[:500])
        return evidence


def research(recipe, slug=None, *, verification=False, transport=exchange):
    if recipe not in ENDPOINTS:
        raise ResearchError("unknown recipe")
    if recipe == "bank-review" and slug is not None and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ResearchError("use an exact slug from bank-review coverage")
    client = Client(ENDPOINTS[recipe], verification=verification, transport=transport)
    client.initialize()
    out = {"schema": "liquilens.research-recipe.v1", "recipe": recipe,
           "client": CLIENT_INFO, "verification": verification,
           "endpoint": client.endpoint, "outcome": "evidence_returned",
           "execution_authority": False, "evidence": {}}
    if recipe == "bank-review":
        coverage = client.call("banking_specialisation_coverage", {})
        if not isinstance(coverage.get("rows"), list):
            raise ResearchError("bank coverage has no rows; no slug can be established")
        out["evidence"]["coverage"] = coverage
        if slug is not None:
            if not any(isinstance(row, dict) and row.get("slug") == slug for row in coverage["rows"]):
                out.update(outcome="not_covered", requested_slug=slug,
                           reason="No exact coverage match; no bank review was requested.")
                out["retrieved_at"] = datetime.now(timezone.utc).isoformat()
                return out
            review = client.call("bank_asset_quality_review", {"slug": slug, "include_history": True})
            if review.get("slug") != slug:
                raise ResearchError("bank review identity does not match the requested slug")
            out["evidence"]["review"] = review
            if review.get("status") in ("unavailable", "not_covered"):
                out["outcome"] = review["status"]
    else:
        desk = client.call("money_market_context", {"section": "all"})
        if desk.get("schema") != "seiche.money-market-desk.v1" or type(desk.get("ok")) is not bool:
            raise ResearchError("funding response does not match the money-market desk contract")
        out["evidence"]["money_market"] = desk
        if desk["ok"] is False:
            out["outcome"] = "unavailable"
    out["retrieved_at"] = datetime.now(timezone.utc).isoformat()
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", choices=ENDPOINTS)
    parser.add_argument("--slug", help="exact bank slug; omit to discover coverage")
    parser.add_argument("--verification", action="store_true",
                        help="mark operator/testing calls so they are not counted as adoption")
    args = parser.parse_args(argv)
    if args.slug and args.recipe != "bank-review":
        parser.error("--slug applies only to bank-review")
    try:
        result = research(args.recipe, args.slug, verification=args.verification)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if result["outcome"] == "evidence_returned" else 2
    except (ResearchError, ValueError, TypeError) as exc:
        print(json.dumps({"outcome": "error", "reason": str(exc)}, allow_nan=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
