"""Run browser-panel behavior tests inside the existing native Python CI suite."""
from pathlib import Path
import subprocess


def test_live_coverage_panel_behavior():
    root = Path(__file__).resolve().parents[1]
    subprocess.run(
        ["node", "--test", "tests/test_world_economy_live_coverage.mjs"],
        cwd=root, check=True, timeout=30, capture_output=True, text=True,
    )
