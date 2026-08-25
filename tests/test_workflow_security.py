"""Supply-chain and credential boundaries for the public-site workflows."""

from pathlib import Path
import json
import re


ROOT = Path(__file__).resolve().parents[1]
PAGES = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
ARTICLES = (ROOT / ".github/workflows/articles-daily.yml").read_text(encoding="utf-8")
EDGE_DEPLOY = (ROOT / ".github/workflows/deploy-catalog-edge.yml").read_text(
    encoding="utf-8"
)
EDGE_PR = (ROOT / ".github/workflows/edge-pr.yml").read_text(encoding="utf-8")

ACTION_PINS = {
    "actions/checkout": "3d3c42e5aac5ba805825da76410c181273ba90b1",
    "actions/setup-python": "5fda3b95a4ea91299a34e894583c3862153e4b97",
    "actions/setup-node": "249970729cb0ef3589644e2896645e5dc5ba9c38",
    "actions/configure-pages": "45bfe0192ca1faeb007ade9deae92b16b8254a0d",
    "actions/upload-pages-artifact": "fc324d3547104276b827a68afc52ff2a11cc49c9",
    "actions/deploy-pages": "cd2ce8fcbc39b97be8ca5fce6e763baed58fa128",
    "cloudflare/wrangler-action": "ebbaa1584979971c8614a24965b4405ff95890e0",
}


def test_every_external_action_is_pinned_to_the_reviewed_commit():
    combined = PAGES + ARTICLES + EDGE_DEPLOY + EDGE_PR
    uses = re.findall(r"uses:\s+([^\s@]+)@([0-9a-f]{40})", combined)
    assert uses
    assert "@v" not in combined
    for action, commit in uses:
        assert ACTION_PINS[action] == commit
    assert sum(action == "actions/checkout" for action, _ in uses) == 4
    assert sum(action == "actions/setup-python" for action, _ in uses) == 4
    assert sum(action == "actions/setup-node" for action, _ in uses) == 3
    assert sum(action == "cloudflare/wrangler-action" for action, _ in uses) == 1


def test_workflows_pin_the_runner_and_scope_checkout_credentials():
    assert "ubuntu-latest" not in PAGES + ARTICLES + EDGE_DEPLOY + EDGE_PR
    assert "runs-on: ubuntu-24.04" in PAGES
    assert "runs-on: ubuntu-24.04" in ARTICLES
    assert "runs-on: ubuntu-24.04" in EDGE_DEPLOY
    assert "runs-on: ubuntu-24.04" in EDGE_PR
    assert "persist-credentials: false" in PAGES
    assert "persist-credentials: true" in ARTICLES
    assert "persist-credentials: false" in EDGE_DEPLOY
    assert "persist-credentials: false" in EDGE_PR
    assert "wrangler.catalog.jsonc requirements-ci.txt" in PAGES
    assert 'python3 scripts/daily_article.py "${args[@]}"' in ARTICLES


def test_ci_dependencies_are_binary_only_and_hash_locked():
    requirements = (ROOT / "requirements-ci.txt").read_text(encoding="utf-8")
    assert requirements.count("--hash=sha256:") == 5
    assert re.search(r"^[^#\n]*[<>=]=?[^\n]*$", requirements, re.MULTILINE) is not None
    for workflow in (PAGES, ARTICLES, EDGE_DEPLOY, EDGE_PR):
        assert "--only-binary=:all:" in workflow
        assert "--require-hashes" in workflow
        assert "pytest>=" not in workflow


def test_workflow_permissions_match_their_jobs():
    for permission in ("contents: read", "pages: write", "id-token: write"):
        assert permission in PAGES
    for permission in ("contents: write", "actions: write"):
        assert permission in ARTICLES
    for workflow in (EDGE_DEPLOY, EDGE_PR):
        assert "contents: read" in workflow
        assert "contents: write" not in workflow
        assert "pull-requests: write" not in workflow


def test_public_edge_has_non_deploying_pr_gate_and_exact_release_receipt():
    assert "pull_request:" in EDGE_PR
    assert "paths:" not in EDGE_PR
    assert "CLOUDFLARE_API_TOKEN" not in EDGE_PR
    assert (
        "npx --no-install wrangler deploy --config wrangler.catalog.jsonc --dry-run"
        in EDGE_PR
    )
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert package["devDependencies"]["wrangler"] == "4.125.0"
    lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
    assert lock["packages"][""]["devDependencies"]["wrangler"] == "4.125.0"
    assert "--tag ${{ github.sha }}" in EDGE_DEPLOY
    assert '--expected-version-tag "$GITHUB_SHA"' in EDGE_DEPLOY


def test_daily_publisher_deploys_exact_sha_edge_before_pages():
    pushed_sha = 'echo "PUSHED_SHA=$(git rev-parse HEAD)" >> "$GITHUB_ENV"'
    edge_dispatch = "gh workflow run deploy-catalog-edge.yml --ref main"
    edge_wait = 'gh run watch "$run_id" --exit-status --interval 5'
    pages_dispatch = "gh workflow run pages.yml --ref main"
    assert pushed_sha in ARTICLES
    assert ARTICLES.index(pushed_sha) < ARTICLES.index(edge_dispatch)
    assert ARTICLES.index(edge_dispatch) < ARTICLES.index(edge_wait)
    assert ARTICLES.index(edge_wait) < ARTICLES.index(pages_dispatch)
    assert ARTICLES.count('--commit "$PUSHED_SHA"') == 4
    assert ARTICLES.count(
        'test "$(git ls-remote origin refs/heads/main | awk '
    ) == 1
