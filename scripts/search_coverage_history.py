#!/usr/bin/env python3
"""Retrieve the latest successful main-branch inventory without trusting PR artifacts."""

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import zipfile

from check_search_coverage import MAX_BYTES, validate_baseline


REPOSITORY = "beepboop2025/liquilens-site"
WORKFLOW = ".github/workflows/search-coverage.yml"
MAX_ARCHIVE_BYTES = 8 * 1024 * 1024


def api(path, binary=False):
    # gh handles GitHub's signed artifact redirect without exposing its URL or token.
    process = subprocess.run(["gh", "api", "--hostname", "github.com", path],
                             capture_output=True, timeout=45,
                             env={**os.environ, "GH_PROMPT_DISABLED": "1"})
    if process.returncode:
        raise ValueError(f"GitHub API request failed (exit {process.returncode}); inventory unavailable")
    if len(process.stdout) > MAX_ARCHIVE_BYTES:
        raise ValueError("GitHub response exceeds the reviewed byte limit")
    return process.stdout if binary else json.loads(process.stdout)


def select_run(runs, current_run_id):
    eligible = [run for run in runs
                if isinstance(run, dict) and str(run.get("id")) != str(current_run_id)
                and run.get("status") == "completed" and run.get("conclusion") == "success"
                and run.get("head_branch") == "main" and run.get("path") == WORKFLOW
                and run.get("event") in {"schedule", "workflow_dispatch", "workflow_run"}
                and run.get("repository", {}).get("full_name") == REPOSITORY
                and run.get("head_repository", {}).get("full_name") == REPOSITORY]
    # A rerun of older code must not displace a newer successful inventory.
    return max(eligible, key=lambda run: (run["created_at"], run["id"]), default=None)


def read_report(archive):
    if len(archive) > MAX_ARCHIVE_BYTES:
        raise ValueError("baseline archive exceeds the reviewed byte limit")
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        candidates = [info for info in bundle.infolist() if info.filename == "report.json"]
        if len(candidates) != 1 or candidates[0].file_size > MAX_BYTES:
            raise ValueError("baseline archive needs one bounded root report.json")
        # Read a named member; never extract paths supplied by the archive.
        with bundle.open(candidates[0]) as source:
            payload = source.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise ValueError("baseline report exceeds the reviewed byte limit")
    report = json.loads(payload)
    validate_baseline(report)
    return payload, report


def download_baseline(output, current_run_id, request=api):
    run = None
    for page in (1, 2):
        result = request(f"repos/{REPOSITORY}/actions/workflows/search-coverage.yml/runs?status=success&branch=main&per_page=100&page={page}")
        runs = result.get("workflow_runs")
        if not isinstance(runs, list):
            raise ValueError("invalid workflow history response")
        run = select_run(runs, current_run_id)
        if run or len(runs) < 100:
            break
    if not run:
        raise ValueError("no previous successful trusted inventory in the bounded history")
    run_id, attempt = run["id"], run.get("run_attempt")
    if type(run_id) is not int or type(attempt) is not int or run_id <= 0 or attempt <= 0:
        raise ValueError("invalid baseline run identity")
    if not re.fullmatch(r"[0-9a-f]{40}", run.get("head_sha", "")):
        raise ValueError("invalid baseline source commit")
    name = f"search-coverage-{run_id}-{attempt}"
    result = request(f"repos/{REPOSITORY}/actions/runs/{run_id}/artifacts?per_page=100")
    artifacts = [a for a in result.get("artifacts", []) if a.get("name") == name]
    if len(artifacts) != 1 or artifacts[0].get("expired") is not False:
        raise ValueError("latest successful inventory artifact is missing or expired; refusing an older fallback")
    artifact = artifacts[0]
    if (type(artifact.get("id")) is not int or artifact["id"] <= 0
            or type(artifact.get("size_in_bytes")) is not int
            or not 0 < artifact["size_in_bytes"] <= MAX_ARCHIVE_BYTES):
        raise ValueError("invalid or oversized baseline artifact")
    archive = request(f"repos/{REPOSITORY}/actions/artifacts/{artifact['id']}/zip", binary=True)
    payload, report = read_report(archive)
    receipt = {"schema": "liquilens.search-coverage-baseline.v1",
               "retrieved_at": datetime.now(timezone.utc).isoformat(),
               "run_id": run_id, "run_attempt": attempt, "event": run["event"],
               "run_url": f"https://github.com/{REPOSITORY}/actions/runs/{run_id}",
               "head_sha": run["head_sha"], "artifact_id": artifact["id"],
               "artifact_name": name, "report_observed_at": report["observed_at"],
               "archive_sha256": hashlib.sha256(archive).hexdigest(),
               "report_sha256": hashlib.sha256(payload).hexdigest()}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    output.with_suffix(".source.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        # Never let a previous local download masquerade as this invocation's success.
        args.output.unlink(missing_ok=True)
        args.output.with_suffix(".source.json").unlink(missing_ok=True)
        receipt = download_baseline(args.output, os.environ.get("GITHUB_RUN_ID", ""))
    except (OSError, ValueError, zipfile.BadZipFile, subprocess.TimeoutExpired) as error:
        print(f"Inventory baseline unavailable: {error}")
        return 1
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
