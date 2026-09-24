#!/usr/bin/env python3
"""Stage tracked public files, then prove discovery bytes after Pages deploys."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import time
import urllib.parse
import urllib.request


# Adding a hidden public route requires explicit review here. Other dot paths,
# including nested ones, never enter the artifact even with include-hidden-files.
PUBLIC_HIDDEN = frozenset({
    ".nojekyll",
    ".well-known/ai-catalog.json",
    ".well-known/api-catalog.json",
    ".well-known/security.txt",
    ".well-known/skills/index.json",
    ".well-known/skills/liquilens-trading-research/SKILL.md",
    ".well-known/agent-skills/index.json",
})
EXCLUDED_ROOTS = frozenset({
    "scripts", "tests", "edge", "node_modules", "wrangler.catalog.jsonc",
    "requirements-ci.txt", "package.json", "package-lock.json",
})
# The existing edge verifier covers the independently served AI/API catalogs.
DISCOVERY_PROOF_PATHS = tuple(sorted(PUBLIC_HIDDEN - {
    ".nojekyll", ".well-known/ai-catalog.json", ".well-known/api-catalog.json",
}))


def public_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError("Invalid tracked artifact path")
    if path.parts[0] in EXCLUDED_ROOTS:
        return False
    return not any(part.startswith(".") for part in path.parts) or name in PUBLIC_HIDDEN


def stage(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination == source or destination.is_relative_to(source):
        raise ValueError("Artifact directory must be outside the checkout")
    if destination.exists():
        raise ValueError("Artifact directory must not already exist")
    repository = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], cwd=source, text=True,
    ).strip()
    if Path(repository).resolve() != source:
        raise ValueError("Source must be the checkout root")
    tracked = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=source)
    selected = []
    for entry in tracked.decode("utf-8").split("\0"):
        if not entry:
            continue
        metadata, name = entry.split("\t", 1)
        mode, _, index_stage = metadata.split()
        if not public_path(name):
            continue
        if index_stage != "0" or mode not in {"100644", "100755"}:
            raise ValueError(f"Non-regular or conflicted public file: {name}")
        path = source / name
        if any(parent.is_symlink() for parent in (path, *path.parents)) or not path.is_file():
            raise ValueError(f"Missing or symlinked public file: {name}")
        selected.append(name)
    missing = PUBLIC_HIDDEN - set(selected)
    if missing:
        raise ValueError(f"Required public discovery files are missing: {sorted(missing)}")
    destination.mkdir(parents=True)
    for name in selected:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
    return {"files": len(selected), "public_hidden": sorted(PUBLIC_HIDDEN)}


def fetch_bytes(url, *, max_bytes, timeout):
    request = urllib.request.Request(url, headers={
        "User-Agent": "LiquiLens-Operator-Pages-Verification/1.0",
        "Accept-Encoding": "identity",
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        body = response.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise RuntimeError("Response exceeds the expected artifact size")
    return body


def verify(artifact, base_url, *, attempts=12, delay=5, budget_seconds=150,
           fetch=fetch_bytes, clock=time.monotonic, sleep=time.sleep):
    parsed = urllib.parse.urlsplit(base_url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment):
        raise ValueError("Pages proof requires a public HTTPS base URL without query or credentials")
    if attempts < 1 or delay < 0 or budget_seconds <= 0:
        raise ValueError("Invalid verification retry budget")
    expected = {name: (Path(artifact) / name).read_bytes() for name in DISCOVERY_PROOF_PATHS}
    pending, matched, problems = dict(expected), {}, {}
    deadline = clock() + budget_seconds
    for attempt in range(1, attempts + 1):
        for name, body in list(pending.items()):
            remaining = deadline - clock()
            if remaining <= 0:
                break
            url = urllib.parse.urljoin(base_url.rstrip("/") + "/", name)
            url += f"?pages_discovery_check={attempt}-{time.time_ns()}"
            try:
                actual = fetch(url, max_bytes=len(body), timeout=min(15, remaining))
                if actual != body:
                    raise RuntimeError("Returned bytes differ from the staged artifact")
                matched[name] = hashlib.sha256(body).hexdigest()
                del pending[name]
            except (OSError, RuntimeError) as error:
                problems[name] = str(error)
        if not pending:
            return {"status": "PASS", "sha256": matched}
        remaining = deadline - clock()
        if attempt < attempts and remaining > 0:
            sleep(min(delay, remaining))
    raise RuntimeError("Public discovery proof failed: " + json.dumps({
        name: problems.get(name, "Verification budget exhausted") for name in pending
    }, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    staging = commands.add_parser("stage")
    staging.add_argument("--source", type=Path, required=True)
    staging.add_argument("--destination", type=Path, required=True)
    proof = commands.add_parser("verify")
    proof.add_argument("--artifact", type=Path, required=True)
    proof.add_argument("--base-url", required=True)
    args = parser.parse_args()
    result = (stage(args.source, args.destination) if args.command == "stage"
              else verify(args.artifact, args.base_url))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
