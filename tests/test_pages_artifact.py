"""Exercise the real staging boundary and deployed discovery-byte verifier."""
import subprocess
import urllib.error
import urllib.parse

import pytest

from scripts import stage_pages_artifact as artifact


def repository(tmp_path, extra=None):
    root = tmp_path / "checkout"
    root.mkdir()
    files = {name: name.encode() for name in artifact.PUBLIC_HIDDEN}
    files.update({"index.html": b"public home", "agents/app.mjs": b"public code"})
    files.update(extra or {})
    for name, body in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    subprocess.run(["git", "init", "--quiet", root], check=True)
    subprocess.run(["git", "add", "--all"], cwd=root, check=True)
    return root


def test_artifact_contains_required_discovery_but_no_hidden_or_untracked_leaks(tmp_path):
    root = repository(tmp_path, {
        ".env": b"private", ".github/workflows/private.yml": b"internal",
        ".private/key": b"private", "assets/.private/key": b"private",
        ".well-known/.private/key": b"private", ".well-known/unreviewed.json": b"private",
        "scripts/private.py": b"internal", "tests/private.py": b"internal",
        "edge/private.mjs": b"internal", "package.json": b"internal",
    })
    (root / "untracked-secret.txt").write_text("must not publish")
    destination = tmp_path / "artifact"
    artifact.stage(root, destination)
    published = {p.relative_to(destination).as_posix() for p in destination.rglob("*") if p.is_file()}
    assert published == artifact.PUBLIC_HIDDEN | {"index.html", "agents/app.mjs"}
    for name in published:
        assert (destination / name).read_bytes() == (root / name).read_bytes()
    assert not (destination / ".git").exists()


def test_required_discovery_cannot_silently_disappear(tmp_path):
    root = repository(tmp_path)
    (root / ".well-known/skills/index.json").unlink()
    with pytest.raises(ValueError, match="Missing"):
        artifact.stage(root, tmp_path / "artifact")
    assert not (tmp_path / "artifact").exists()


def test_staging_refuses_symlinks_and_nonempty_or_internal_destinations(tmp_path):
    root = repository(tmp_path)
    outside = tmp_path / "private"
    outside.write_text("private")
    (root / "public-link.txt").symlink_to(outside)
    subprocess.run(["git", "add", "public-link.txt"], cwd=root, check=True)
    with pytest.raises(ValueError, match="Non-regular"):
        artifact.stage(root, tmp_path / "artifact")
    with pytest.raises(ValueError, match="outside"):
        artifact.stage(root, root / "output")
    with pytest.raises(ValueError, match="already exist"):
        artifact.stage(root, tmp_path)


def test_public_verification_checks_every_required_path_and_exact_bytes(tmp_path):
    root = repository(tmp_path)
    seen = []
    def fetch(url, *, max_bytes, timeout):
        parsed = urllib.parse.urlsplit(url)
        seen.append(parsed.path)
        body = (root / parsed.path.lstrip("/")).read_bytes()
        assert len(body) == max_bytes and 0 < timeout <= 15
        return body
    report = artifact.verify(root, "https://liquilens.in/", fetch=fetch)
    assert report["status"] == "PASS"
    assert set(seen) == {"/" + name for name in artifact.DISCOVERY_PROOF_PATHS}


@pytest.mark.parametrize("failure", ["404", "changed"])
def test_missing_or_changed_public_bytes_fail_the_release(tmp_path, failure):
    root = repository(tmp_path)
    def fetch(url, **kwargs):
        if failure == "404":
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        return b"wrong version"
    with pytest.raises(RuntimeError, match="Public discovery proof failed"):
        artifact.verify(root, "https://liquilens.in/", fetch=fetch, attempts=1)


def test_transient_propagation_retries_only_unverified_files(tmp_path):
    root = repository(tmp_path)
    attempts = {}
    delayed = "/.well-known/skills/index.json"
    def fetch(url, **kwargs):
        path = urllib.parse.urlsplit(url).path
        attempts[path] = attempts.get(path, 0) + 1
        if path == delayed and attempts[path] == 1:
            raise OSError("not propagated yet")
        return (root / path.lstrip("/")).read_bytes()
    assert artifact.verify(root, "https://liquilens.in/", fetch=fetch, delay=0)["status"] == "PASS"
    assert attempts.pop(delayed) == 2
    assert set(attempts.values()) == {1}


def test_workflow_uploads_only_the_staged_directory_and_keeps_postdeploy_proof():
    workflow = (artifact.Path(__file__).parents[1] / ".github/workflows/pages.yml").read_text()
    assert 'cp scripts/stage_pages_artifact.py "$RUNNER_TEMP/stage_pages_artifact.py"' in workflow
    assert 'path: \'${{ runner.temp }}/pages-artifact\'' in workflow
    assert "include-hidden-files: true" in workflow
    assert '--destination "$RUNNER_TEMP/pages-artifact"' in workflow
    assert '--artifact "$RUNNER_TEMP/pages-artifact" --base-url "$page_base_url"' in workflow
    assert workflow.index("Require exact public discovery bytes") > workflow.index("uses: actions/deploy-pages@")
