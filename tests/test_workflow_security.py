"""Supply-chain and credential boundaries for the public-site workflows."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PAGES = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
ARTICLES = (ROOT / ".github/workflows/articles-daily.yml").read_text(encoding="utf-8")

ACTION_PINS = {
    "actions/checkout": "3d3c42e5aac5ba805825da76410c181273ba90b1",
    "actions/setup-python": "5fda3b95a4ea91299a34e894583c3862153e4b97",
    "actions/configure-pages": "45bfe0192ca1faeb007ade9deae92b16b8254a0d",
    "actions/upload-pages-artifact": "fc324d3547104276b827a68afc52ff2a11cc49c9",
    "actions/deploy-pages": "cd2ce8fcbc39b97be8ca5fce6e763baed58fa128",
}


def test_every_external_action_is_pinned_to_the_reviewed_commit():
    combined = PAGES + ARTICLES
    uses = re.findall(r"uses:\s+([^\s@]+)@([0-9a-f]{40})", combined)
    assert uses
    assert "@v" not in combined
    for action, commit in uses:
        assert ACTION_PINS[action] == commit
    assert sum(action == "actions/checkout" for action, _ in uses) == 2
    assert sum(action == "actions/setup-python" for action, _ in uses) == 2


def test_workflows_pin_the_runner_and_scope_checkout_credentials():
    assert "ubuntu-latest" not in PAGES + ARTICLES
    assert "runs-on: ubuntu-24.04" in PAGES
    assert "runs-on: ubuntu-24.04" in ARTICLES
    assert "persist-credentials: false" in PAGES
    assert "persist-credentials: true" in ARTICLES
    assert "wrangler.catalog.jsonc requirements-ci.txt" in PAGES
    assert 'python3 scripts/daily_article.py "${args[@]}"' in ARTICLES


def test_ci_dependencies_are_binary_only_and_hash_locked():
    requirements = (ROOT / "requirements-ci.txt").read_text(encoding="utf-8")
    assert requirements.count("--hash=sha256:") == 5
    assert re.search(r"^[^#\n]*[<>=]=?[^\n]*$", requirements, re.MULTILINE) is not None
    for workflow in (PAGES, ARTICLES):
        assert "--only-binary=:all:" in workflow
        assert "--require-hashes" in workflow
        assert "pytest>=" not in workflow


def test_workflow_permissions_match_their_jobs():
    for permission in ("contents: read", "pages: write", "id-token: write"):
        assert permission in PAGES
    for permission in ("contents: write", "actions: write"):
        assert permission in ARTICLES
