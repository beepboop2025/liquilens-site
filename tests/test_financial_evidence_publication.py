"""The policy publisher cannot expose catalog, runtime or untracked files."""
import importlib.util
import json
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "financial_evidence_publication", ROOT / "scripts/financial_evidence_publication.py"
)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


@pytest.fixture
def repository(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for name in publisher.PUBLIC_FILES:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(("committed:" + name).encode())
    (root / "private.txt").write_text("must never be published")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
         "-c", "commit.gpgsign=false", "commit", "-qm", "fixture"], check=True
    )
    commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    return root, commit


def test_stage_contains_only_committed_allowlist(repository, tmp_path):
    root, commit = repository
    (root / publisher.PUBLIC_FILES[0]).write_text("uncommitted change")
    (root / "financial-evidence" / "secret.txt").write_text("never publish")
    destination = tmp_path / "public"
    receipt = publisher.stage(root, destination, commit)
    actual = {str(p.relative_to(destination)) for p in destination.rglob("*") if p.is_file()}
    assert actual == set(publisher.PUBLIC_FILES) | {"_headers"}
    assert (destination / publisher.PUBLIC_FILES[0]).read_text().startswith("committed:")
    assert receipt["source_commit"] == commit
    assert set(receipt["files"]) == set(publisher.PUBLIC_FILES)


def test_existing_destination_is_rejected(repository, tmp_path):
    root, commit = repository
    destination = tmp_path / "public"
    destination.mkdir()
    (destination / "private.txt").write_text("must stay private")
    with pytest.raises(FileExistsError):
        publisher.stage(root, destination, commit)


@pytest.mark.parametrize("commit", ["main", "abc123", "../HEAD", "0" * 39, "0" * 41])
def test_non_exact_source_is_rejected(tmp_path, commit):
    with pytest.raises(ValueError):
        publisher.committed_files(tmp_path, commit)


def test_worker_has_only_app_page_routes_and_no_executable_runtime():
    config = json.loads((ROOT / "wrangler.financial-evidence.jsonc").read_text())
    assert config["name"] == "liquilens-financial-evidence-pages"
    assert config["workers_dev"] is False
    assert config["preview_urls"] is False
    assert "main" not in config
    assert config["routes"] == [
        {"pattern": "https://liquilens.in/financial-evidence", "zone_name": "liquilens.in"},
        {"pattern": "https://liquilens.in/financial-evidence/*", "zone_name": "liquilens.in"},
    ]
    assert config["assets"]["not_found_handling"] == "none"
