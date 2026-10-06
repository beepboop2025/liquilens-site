#!/usr/bin/env python3
"""Run the read-only audit from an independent scheduler, retaining good history."""
import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from check_search_coverage import validate_baseline


def atomic_write(path, content):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content)
    temporary.replace(path)


def full_due(state, now):
    try:
        observed = datetime.fromisoformat(json.loads(state.read_text())["observed_at"])
        return observed.tzinfo is None or not timedelta(0) <= now - observed < timedelta(hours=24)
    except (OSError, KeyError, TypeError, ValueError):
        return True


def accept_result(state, report, returncode):
    """Failures never reset the successful inventory or daily-full clock."""
    if returncode:
        return False
    try:
        validate_baseline(report)
        if report.get("inventory_history", {}).get("status") != "PASS":
            return False
    except ValueError:
        return False
    payload = json.dumps(report, indent=2) + "\n"
    atomic_write(state / "baseline.json", payload)
    if report["full_page_audit"]:
        atomic_write(state / "last-full.json", payload)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    args = parser.parse_args()
    state = args.state_dir
    state.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    scripts = Path(__file__).resolve().parent
    with (state / "watch.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Another search audit is running; no duplicate started.")
            return 75
        with tempfile.TemporaryDirectory(prefix="audit-", dir=state) as directory:
            output = Path(directory) / "report.json"
            command = [sys.executable, "-B", str(scripts / "check_search_coverage.py"),
                       "--full-on-change", "--baseline", str(state / "baseline.json"),
                       "--retirements", str(scripts / "search-coverage-retirements.json"),
                       "--output", str(output)]
            if full_due(state / "last-full.json", now):
                command.append("--full")
            try:
                completed = subprocess.run(command, timeout=1200, check=False)
                report = json.loads(output.read_text())
                accepted = accept_result(state, report, completed.returncode)
            except (OSError, ValueError, subprocess.TimeoutExpired) as error:
                report = {"observed_at": now.isoformat(), "operator_probe": True,
                          "status": "UNKNOWN", "monitoring_errors": [str(error)]}
                accepted = False
            atomic_write(state / "latest.json", json.dumps(report, indent=2) + "\n")
            if output.with_suffix(".md").exists():
                atomic_write(state / "latest.md", output.with_suffix(".md").read_text())
            else:
                atomic_write(state / "latest.md", "Audit did not complete. Coverage is unknown.\n")
            with (state / "runs.jsonl").open("a") as receipts:
                receipts.write(json.dumps({"started_at": now.isoformat(),
                    "completed_at": datetime.now(timezone.utc).isoformat(), "accepted": accepted,
                    "full_page_audit": report.get("full_page_audit", False),
                    "errors": sum(len(p.get("errors", [])) for p in report.get("products", [])),
                    "monitoring_errors": report.get("monitoring_errors", [])}) + "\n")
            return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
