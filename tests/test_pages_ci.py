"""Pages may consume only a current, authenticated native CI result."""

import copy
import json
import subprocess

import pytest

from scripts import verify_pages_ci as gate

GATE = vars(gate)
SOURCE = "a" * 40
URL = (
    f"https://railway.com/project/{GATE['PROJECT']}/service/{GATE['SERVICE']}"
    f"?id=0311d2f9-2adf-4466-b8e7-2e9d037f4f9c&environmentId={GATE['ENVIRONMENT']}"
)


def result():
    return {
        "id": 123,
        "context": GATE["CONTEXT"],
        "state": "success",
        "creator": dict(GATE["BOT"]),
        "target_url": URL,
    }


def verify(statuses, current=SOURCE):
    return GATE["verify_result"](statuses, source=SOURCE, current_main=current)


def test_current_native_main_pass_is_accepted():
    assert verify([result()])["source"] == SOURCE


def test_main_advancing_revokes_admission():
    with pytest.raises(ValueError, match="current main"):
        verify([result()], "b" * 40)


@pytest.mark.parametrize("state", ["pending", "failure", "error"])
def test_newer_nonpassing_result_cannot_reuse_old_success(state):
    with pytest.raises(ValueError, match="has not passed"):
        verify([{**result(), "state": state}, result()])


@pytest.mark.parametrize(
    "field,value", [("id", 1), ("login", "someone"), ("type", "User")]
)
def test_lookalike_status_provider_is_rejected(field, value):
    status = result()
    status["creator"][field] = value
    with pytest.raises(ValueError):
        verify([status])


@pytest.mark.parametrize(
    "state,url",
    [
        ("pending", None),
        (
            "success",
            URL.replace(GATE["ENVIRONMENT"], "5f41a5a7-2960-452e-b8fa-c4def50b1137"),
        ),
    ],
)
def test_newer_authenticated_invalid_result_cannot_reuse_old_pass(state, url):
    with pytest.raises(ValueError):
        verify([{**result(), "state": state, "target_url": url}, result()])


@pytest.mark.parametrize(
    "url",
    [
        URL.replace(GATE["ENVIRONMENT"], "5f41a5a7-2960-452e-b8fa-c4def50b1137"),
        URL.replace(GATE["SERVICE"], "477a4dbe-47c2-4d61-b0ef-cfa398a20b53"),
        URL.replace("railway.com", "railway.com.evil.example"),
        URL.replace("https://", "http://"),
        URL + "&environmentId=other",
        URL + "#fragment",
        URL + "&unexpected=true",
    ],
)
def test_preview_other_service_and_malformed_targets_are_rejected(url):
    status = copy.deepcopy(result())
    status["target_url"] = url
    with pytest.raises(ValueError, match="configured Railway main CI service"):
        verify([status])


def context():
    return {
        "GITHUB_REPOSITORY": gate.REPOSITORY,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_SHA": SOURCE,
        "GITHUB_EVENT_NAME": "status",
    }


def event():
    return {
        "sha": SOURCE,
        "context": gate.CONTEXT,
        "state": "success",
        "target_url": URL,
    }


def test_status_event_admits_only_exact_main_context():
    assert gate.verify_context(context(), event()) == SOURCE


@pytest.mark.parametrize(
    "key,value",
    [
        ("sha", "b" * 40),
        ("context", "another-ci"),
        ("state", "pending"),
        (
            "target_url",
            URL.replace(gate.ENVIRONMENT, "5f41a5a7-2960-452e-b8fa-c4def50b1137"),
        ),
    ],
)
def test_irrelevant_or_preview_event_cannot_authorize_main(key, value):
    with pytest.raises(ValueError):
        gate.verify_context(context(), {**event(), key: value})


@pytest.mark.parametrize(
    "key,value",
    [
        ("GITHUB_REPOSITORY", "someone/liquilens-site"),
        ("GITHUB_REF", "refs/heads/feature"),
        ("GITHUB_EVENT_NAME", "pull_request"),
        ("GITHUB_SHA", "HEAD"),
    ],
)
def test_fork_branch_or_other_event_is_rejected(key, value):
    with pytest.raises(ValueError):
        gate.verify_context({**context(), key: value}, event())


def test_manual_dispatch_still_requires_main_context():
    assert (
        gate.verify_context({**context(), "GITHUB_EVENT_NAME": "workflow_dispatch"}, {})
        == SOURCE
    )


def test_unprotected_main_revokes_otherwise_valid_native_result(tmp_path, monkeypatch):
    path = tmp_path / "event.json"
    path.write_text(json.dumps(event()))
    for key, value in {**context(), "GITHUB_EVENT_PATH": str(path)}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr("sys.argv", ["verify_pages_ci.py"])
    monkeypatch.setattr(
        gate,
        "api",
        lambda path: (
            [result()]
            if path.startswith("/commits/")
            else {"protected": False, "commit": {"sha": SOURCE}}
        ),
    )
    with pytest.raises(ValueError, match="remain protected"):
        gate.main()


def publication(identifier, source=SOURCE, event="status"):
    return {
        "id": identifier,
        "head_sha": source,
        "head_branch": "main",
        "workflow_id": 307232463,
        "path": ".github/workflows/pages.yml",
        "repository": {"full_name": gate.REPOSITORY},
        "head_repository": {"full_name": gate.REPOSITORY},
        "status": "completed",
        "conclusion": "success",
        "event": event,
    }


def history(rows, total=None):
    def request(path):
        assert (
            path
            == "/actions/workflows/307232463/runs?branch=main&status=success&per_page=100"
        )
        return {
            "workflow_runs": rows,
            "total_count": len(rows) if total is None else total,
        }

    return request


@pytest.mark.parametrize("event", ["status", "push", "workflow_dispatch"])
def test_indexnow_accepts_real_pages_event_shapes_without_deployment_app_assumption(
    event,
):
    assert gate.previous_pages_source(history([publication(1, event=event)])) == SOURCE


@pytest.mark.parametrize(
    "key,value",
    [
        ("workflow_id", 123),
        ("path", ".github/workflows/other.yml"),
        ("head_branch", "feature"),
        ("repository", {"full_name": "someone/site"}),
        ("head_repository", {"full_name": "someone/site"}),
        ("event", "pull_request"),
        ("status", "in_progress"),
        ("conclusion", "failure"),
        ("head_sha", "main"),
        ("id", "123"),
    ],
)
def test_indexnow_rejects_unexpected_run_even_before_an_older_good_run(key, value):
    with pytest.raises(ValueError):
        gate.previous_pages_source(
            history([{**publication(2), key: value}, publication(1)])
        )


def test_incomplete_history_does_not_claim_first_publication():
    with pytest.raises(ValueError, match="incomplete"):
        gate.previous_pages_source(history([], total=1))


def git(repo, *args, input=None):
    return (
        subprocess.check_output(["git", "-C", str(repo), *args], input=input)
        .decode()
        .strip()
    )


def commit_route(repo, route):
    path = repo / route
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(route)
    git(repo, "add", route)
    git(repo, "-c", "commit.gpgsign=false", "commit", "-qm", route)
    return git(repo, "rev-parse", "HEAD")


def repository(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "Fixture")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    return commit_route(tmp_path, "index.html")


def test_indexnow_keeps_all_routes_in_a_batch_since_last_publication(
    tmp_path, monkeypatch
):
    from scripts.submit_indexnow import changed_paths

    first = repository(tmp_path)
    commit_route(tmp_path, "articles/first/index.html")
    final = commit_route(tmp_path, "articles/second/index.html")
    monkeypatch.chdir(tmp_path)
    before = gate.indexnow_before(history([publication(1, first)]), source=final)
    assert changed_paths(tmp_path, before, final) == [
        "articles/first/index.html",
        "articles/second/index.html",
    ]


def test_first_publication_includes_all_routes_and_repeat_includes_none(
    tmp_path, monkeypatch
):
    from scripts.submit_indexnow import changed_paths

    repository(tmp_path)
    final = commit_route(tmp_path, "articles/first/index.html")
    monkeypatch.chdir(tmp_path)
    before = gate.indexnow_before(history([]), source=final)
    assert changed_paths(tmp_path, before, final) == [
        "articles/first/index.html",
        "index.html",
    ]
    repeat = gate.indexnow_before(history([publication(1, final)]), source=final)
    assert changed_paths(tmp_path, repeat, final) == []


def test_diverged_previous_publication_is_not_silently_narrowed(tmp_path, monkeypatch):
    repository(tmp_path)
    git(tmp_path, "checkout", "-qb", "other")
    previous = commit_route(tmp_path, "other/index.html")
    git(tmp_path, "checkout", "-q", "-")
    final = commit_route(tmp_path, "current/index.html")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(subprocess.CalledProcessError):
        gate.indexnow_before(
            history([publication(1, previous)]),
            source=final,
        )
