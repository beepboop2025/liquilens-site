"""Historical losses and untrusted/missing baselines must never become a pass."""

import copy
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_search_coverage as monitor
import search_coverage_history as history


def report():
    rows = []
    for product in monitor.PRODUCTS:
        urls = {product["origin"] + path for path in product["pages"]}
        urls.update(product["origin"] + f"/reference/{i}/" for i in range(product["minimum_urls"]))
        rows.append({"product": product["name"], "origin": product["origin"], "status": "PASS",
                     "errors": [], "warnings": [], "sitemap_urls": sorted(urls), "pages_checked": len(urls)})
    return {"schema": "liquilens.search-coverage.v1", "operator_probe": True,
            "observed_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "full_page_audit": True, "products": rows}


def run(run_id=41, **changes):
    return {"id": run_id, "status": "completed", "conclusion": "success", "head_branch": "main",
            "event": "schedule", "path": history.WORKFLOW, "run_attempt": 1,
            "repository": {"full_name": history.REPOSITORY},
            "head_repository": {"full_name": history.REPOSITORY}, "head_sha": "a" * 40,
            "created_at": "2026-10-05T16:00:00Z", **changes}


def archive(document=None, name="report.json"):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as bundle:
        bundle.writestr(name, json.dumps(report() if document is None else document))
    return stream.getvalue()


class InventoryTests(unittest.TestCase):
    def test_url_replacement_fails_even_above_minimum_with_unchanged_total(self):
        baseline = report()
        current = copy.deepcopy(baseline)
        row = current["products"][0]
        old = row["origin"] + "/reference/0/"
        row["sitemap_urls"].remove(old)
        row["sitemap_urls"].append(row["origin"] + "/new-reference/")
        monitor.compare_inventory(current, baseline)
        self.assertEqual(len(row["sitemap_urls"]), len(baseline["products"][0]["sitemap_urls"]))
        self.assertEqual(row["status"], "FAIL")
        self.assertEqual(row["errors"][0]["url"], old)
        self.assertEqual(row["inventory_changes"]["removed"], [old])

    def test_growth_is_preserved_and_subsequent_loss_detected(self):
        baseline = report()
        grown = copy.deepcopy(baseline)
        url = "https://seiche.info/new-guide/"
        grown["products"][1]["sitemap_urls"].append(url)
        monitor.compare_inventory(grown, baseline)
        self.assertEqual(grown["inventory_history"]["status"], "PASS")
        later = report()
        monitor.compare_inventory(later, grown)
        self.assertEqual(later["products"][1]["errors"][0]["url"], url)

    def test_failed_partial_duplicate_and_offsite_baselines_are_rejected(self):
        bad = []
        for change in (
            lambda r: r["products"].pop(),
            lambda r: r["products"].__setitem__(1, copy.deepcopy(r["products"][0])),
            lambda r: r["products"][0]["errors"].append({"problem": "failure"}),
            lambda r: r["products"][0]["sitemap_urls"].append("https://other.example/"),
            lambda r: r["products"][0]["sitemap_urls"].append(r["products"][0]["sitemap_urls"][0]),
            lambda r: r["products"][0]["sitemap_urls"].remove("https://liquilens.in/"),
            lambda r: r.update(monitoring_errors=["baseline missing"]),
            lambda r: r.update(observed_at="2099-01-01T00:00:00+00:00"),
            lambda r: r.update(observed_at="2026-10-05T16:00:00"),
        ):
            document = report()
            change(document)
            bad.append(document)
        for document in bad:
            with self.subTest(document=document), self.assertRaises(ValueError):
                monitor.validate_baseline(document)

    def test_exact_reviewed_retirement_does_not_mask_another_loss(self):
        baseline = report()
        current = copy.deepcopy(baseline)
        row = current["products"][0]
        approved, unexpected = row["origin"] + "/reference/0/", row["origin"] + "/reference/1/"
        row["sitemap_urls"].remove(approved)
        row["sitemap_urls"].remove(unexpected)
        reasons = monitor.validate_retirements({"schema": "liquilens.search-retirements.v1", "retirements": [
            {"product": "LiquiLens", "url": approved, "reason": "Reviewed canonical consolidation into the replacement guide."}]})
        monitor.compare_inventory(current, baseline, reasons)
        self.assertEqual([e["url"] for e in row["errors"]], [unexpected])
        self.assertEqual(row["inventory_changes"]["reviewed_retirements"][0]["url"], approved)

    def test_required_entry_and_unexplained_retirement_are_rejected(self):
        for url, reason in [("https://seiche.info/", "Required pages cannot be retired."),
                            ("https://seiche.info/old/", ""), ("https://other.example/", "Wrong product origin.")]:
            with self.subTest(url=url, reason=reason), self.assertRaises(ValueError):
                monitor.validate_retirements({"schema": "liquilens.search-retirements.v1", "retirements": [
                    {"product": "Seiche", "url": url, "reason": reason}]})

    def test_missing_baseline_still_emits_current_report_and_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            args = ["check_search_coverage.py", "--baseline", str(Path(directory) / "missing.json"), "--output", str(output)]
            with patch.object(sys, "argv", args), patch.object(monitor, "audit_product", side_effect=report()["products"]), patch("sys.stdout", new=io.StringIO()):
                self.assertEqual(monitor.main(), 1)
            document = json.loads(output.read_text())
            self.assertEqual(document["inventory_history"]["status"], "UNAVAILABLE")
            self.assertEqual(len(document["products"]), 3)
            self.assertIn("Monitoring error", output.with_suffix(".md").read_text())


class BaselineSourceTests(unittest.TestCase):
    def test_only_successful_main_own_repository_live_runs_are_trusted(self):
        changes = [dict(event="pull_request"), dict(head_branch="feature"), dict(status="in_progress"),
                   dict(conclusion="failure"), dict(path=".github/workflows/other.yml"),
                   dict(head_repository={"full_name": "other/fork"}), dict(repository={"full_name": "other/repo"})]
        for change in changes:
            with self.subTest(change=change):
                self.assertIsNone(history.select_run([run(**change)], "99"))
        self.assertIsNone(history.select_run([run()], "41"))
        self.assertEqual(history.select_run([run()], "99")["id"], 41)

    def test_old_rerun_cannot_replace_a_newer_successful_inventory(self):
        old_rerun = run(40, run_started_at="2026-10-05T18:00:00Z", run_attempt=2)
        self.assertEqual(history.select_run([old_rerun, run()], "99")["id"], 41)

    def test_report_reader_never_extracts_paths_or_accepts_duplicate_reports(self):
        for name in ("../report.json", "nested/report.json"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                history.read_report(archive(name=name))
        stream = io.BytesIO(archive())
        with zipfile.ZipFile(stream, "a") as bundle:
            bundle.writestr("unrelated/path.txt", "not extracted")
        payload, document = history.read_report(stream.getvalue())
        self.assertEqual(json.loads(payload), document)
        self.assertEqual(document["schema"], "liquilens.search-coverage.v1")
        with self.assertRaises(ValueError):
            history.read_report(archive({"schema": "other"}))

    def test_oversized_report_is_rejected_before_decompression(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr("report.json", "x" * (monitor.MAX_BYTES + 1))
        with self.assertRaises(ValueError):
            history.read_report(stream.getvalue())

    def test_download_records_exact_source_and_report_digest(self):
        content = archive()
        def request(path, binary=False):
            if "/workflows/" in path:
                return {"workflow_runs": [run()]}
            if "/runs/41/artifacts" in path:
                return {"artifacts": [{"id": 7, "name": "search-coverage-41-1", "expired": False, "size_in_bytes": len(content)}]}
            self.assertTrue(binary)
            self.assertTrue(path.endswith("/artifacts/7/zip"))
            return content
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "baseline.json"
            receipt = history.download_baseline(output, "99", request)
            self.assertEqual(receipt["run_id"], 41)
            self.assertEqual(receipt["head_sha"], "a" * 40)
            self.assertEqual(receipt["report_sha256"], history.hashlib.sha256(output.read_bytes()).hexdigest())
            self.assertTrue(output.with_suffix(".source.json").is_file())

    def test_expired_or_missing_latest_artifact_cannot_fall_back(self):
        for artifacts in ([], [{"id": 7, "name": "search-coverage-41-1", "expired": True}]):
            calls = []
            def request(path, binary=False):
                calls.append(path)
                if "/workflows/" in path:
                    return {"workflow_runs": [run(), run(40, created_at="2026-10-05T15:00:00Z")]}
                return {"artifacts": artifacts}
            with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
                history.download_baseline(Path(directory) / "report.json", "99", request)
            self.assertEqual(len(calls), 2)

    def test_absent_trusted_history_cannot_bootstrap_silently(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            history.download_baseline(Path(directory) / "report.json", "99", lambda path: {"workflow_runs": [run(event="pull_request")]})


if __name__ == "__main__":
    unittest.main()
