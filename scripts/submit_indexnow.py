#!/usr/bin/env python3
"""Notify IndexNow about public HTML routes changed by one site commit."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


DEFAULT_ENDPOINT = "https://api.indexnow.org/indexnow"
KEY_RE = re.compile(r"[A-Za-z0-9-]{8,128}")
SHA_RE = re.compile(r"[0-9a-f]{40}")


def changed_paths(repo: pathlib.Path, before: str, after: str) -> list[str]:
    """Read changed paths from an exact two-commit range."""
    if not SHA_RE.fullmatch(after):
        raise ValueError("after must be a full lowercase Git SHA")
    if not SHA_RE.fullmatch(before) or before == "0" * 40:
        before = f"{after}^"
    completed = subprocess.run(
        ["git", "diff", "--name-only", before, after, "--"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in completed.stdout.splitlines() if line]


def public_urls(paths: list[str], base_url: str) -> list[str]:
    """Map changed static index files to their canonical public routes."""
    base = base_url.rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme != "https" or not parsed.hostname or parsed.path:
        raise ValueError("base URL must be an HTTPS origin with no path")
    routes = set()
    for raw in paths:
        path = pathlib.PurePosixPath(raw)
        if path == pathlib.PurePosixPath("index.html"):
            routes.add(f"{base}/")
        elif path.name == "index.html" and not any(part.startswith(".") for part in path.parts):
            routes.add(f"{base}/{'/'.join(path.parts[:-1])}/")
    return sorted(routes)


def read_key(path: pathlib.Path) -> str:
    key = path.read_text(encoding="utf-8").strip()
    if not KEY_RE.fullmatch(key):
        raise ValueError("IndexNow key file is malformed")
    if path.name != f"{key}.txt":
        raise ValueError("root IndexNow key filename must match its contents")
    return key


def submit(urls: list[str], *, base_url: str, key_file: pathlib.Path,
           endpoint: str = DEFAULT_ENDPOINT) -> int:
    if not urls:
        print("IndexNow: no changed public HTML routes")
        return 0
    key = read_key(key_file)
    base = base_url.rstrip("/")
    host = urlsplit(base).hostname
    payload = {
        "host": host,
        "key": key,
        "keyLocation": f"{base}/{key}.txt",
        "urlList": urls,
    }
    request = Request(
        endpoint,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        status = int(response.status)
    if status not in {200, 202}:
        raise RuntimeError(f"IndexNow returned HTTP {status}")
    print(f"IndexNow: submitted {len(urls)} changed route(s), HTTP {status}")
    return status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=pathlib.Path, default=pathlib.Path("."))
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--base-url", default="https://liquilens.in")
    parser.add_argument("--key-file", type=pathlib.Path, required=True)
    args = parser.parse_args()
    paths = changed_paths(args.repo.resolve(), args.before, args.after)
    urls = public_urls(paths, args.base_url)
    submit(urls, base_url=args.base_url, key_file=args.key_file.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
