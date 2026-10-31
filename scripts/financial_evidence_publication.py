#!/usr/bin/env python3
"""Publish only the owned-domain app information pages from an exact Git commit."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = (
    "financial-evidence/index.html",
    "financial-evidence/privacy/index.html",
    "financial-evidence/terms/index.html",
    "financial-evidence/site.css",
    "financial-evidence/share.png",
    "financial-evidence/privacy/share.png",
    "financial-evidence/terms/share.png",
)
CONTENT_TYPES = {".html": "text/html", ".css": "text/css", ".png": "image/png"}


def committed_files(root: Path, commit: str) -> dict[str, bytes]:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("an exact 40-character Git commit is required")
    return {
        name: subprocess.check_output(["git", "-C", str(root), "show", f"{commit}:{name}"])
        for name in PUBLIC_FILES
    }


def stage(root: Path, destination: Path, commit: str) -> dict:
    files = committed_files(root, commit)
    # A fresh directory excludes unrelated files left by an earlier build.
    destination.mkdir(parents=True, exist_ok=False)
    for name, content in files.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    (destination / "_headers").write_text(
        "/financial-evidence/*\n"
        f"  X-Financial-Evidence-Source: {commit}\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n", encoding="utf-8",
    )
    return {
        "source_commit": commit,
        "files": {name: hashlib.sha256(content).hexdigest() for name, content in files.items()},
    }


def verify(root: Path, commit: str, base_url: str, attempts: int, delay: float) -> dict:
    files = committed_files(root, commit)
    results = []
    for name, expected in files.items():
        path = name.removesuffix("index.html") if name.endswith("index.html") else name
        url = base_url.rstrip("/") + "/" + path
        problem = "not fetched"
        for attempt in range(attempts):
            try:
                request = urllib.request.Request(
                    url, headers={"Cache-Control": "no-cache", "User-Agent": "FinancialEvidence-PublicationCheck/1"}
                )
                with urllib.request.urlopen(request, timeout=15) as response:
                    actual = response.read(len(expected) + 1)
                    if response.status != 200 or response.geturl() != url:
                        raise RuntimeError("public response status or canonical URL differs")
                    if response.headers.get_content_type() != CONTENT_TYPES[Path(name).suffix]:
                        raise RuntimeError("public content type differs")
                    if response.headers.get("X-Financial-Evidence-Source") != commit:
                        raise RuntimeError("public source commit differs")
                if actual != expected:
                    raise RuntimeError("public bytes differ from the committed file")
                results.append({"url": url, "sha256": hashlib.sha256(actual).hexdigest()})
                break
            except (OSError, RuntimeError, urllib.error.URLError) as error:
                problem = str(error)
                if attempt + 1 < attempts:
                    time.sleep(delay)
        else:
            raise RuntimeError(f"{url}: {problem}")
    return {"status": "PASS", "source_commit": commit, "files": results}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("stage", "verify"))
    parser.add_argument("--commit", required=True)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--base-url", default="https://liquilens.in")
    parser.add_argument("--attempts", type=int, default=6)
    parser.add_argument("--delay", type=float, default=5)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    if not 1 <= args.attempts <= 12 or not 0 <= args.delay <= 10:
        parser.error("attempts must be 1..12 and delay 0..10 seconds")
    if args.command == "stage":
        if args.destination is None:
            parser.error("stage requires a fresh --destination")
        result = stage(ROOT, args.destination, args.commit)
    else:
        result = verify(ROOT, args.commit, args.base_url, args.attempts, args.delay)
    text = json.dumps(result, indent=2) + "\n"
    if args.receipt:
        args.receipt.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
