from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import watch_search_coverage as watch
from test_search_coverage_history import report


class WatchTests(unittest.TestCase):
    def test_daily_full_due_handles_missing_stale_and_future_clocks(self):
        now = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "last-full.json"
            self.assertTrue(watch.full_due(path, now))
            for hours, expected in [(2, False), (25, True), (-1, True)]:
                path.write_text(json.dumps({"observed_at": (now - timedelta(hours=hours)).isoformat()}))
                self.assertEqual(watch.full_due(path, now), expected)

    def test_failed_and_partial_results_cannot_replace_good_history(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            baseline = state / "baseline.json"
            baseline.write_text("held")
            current = report()
            current["inventory_history"] = {"status": "PASS"}
            self.assertFalse(watch.accept_result(state, current, 1))
            self.assertEqual(baseline.read_text(), "held")
            current["products"][0]["errors"].append({"url": "https://liquilens.in/", "problem": "not available"})
            self.assertFalse(watch.accept_result(state, current, 0))
            self.assertEqual(baseline.read_text(), "held")

    def test_success_advances_inventory_but_only_full_success_advances_daily_clock(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            current = report()
            current["inventory_history"] = {"status": "PASS"}
            current["full_page_audit"] = False
            self.assertTrue(watch.accept_result(state, current, 0))
            self.assertFalse((state / "last-full.json").exists())
            current["full_page_audit"] = True
            self.assertTrue(watch.accept_result(state, current, 0))
            self.assertEqual(json.loads((state / "last-full.json").read_text()), current)
