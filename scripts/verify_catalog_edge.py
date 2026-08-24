#!/usr/bin/env python3
"""Require the public edge catalog to equal the committed canonical catalog."""

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
    parser.add_argument("--attempts", type=int, default=12)
    parser.add_argument("--delay", type=float, default=10.0)
    return parser


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
    except RuntimeError as error:
        print(error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
