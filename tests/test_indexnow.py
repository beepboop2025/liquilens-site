import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import submit_indexnow  # noqa: E402


def test_changed_html_paths_map_only_to_canonical_routes():
    assert submit_indexnow.public_urls([
        "index.html",
        "guides/rbi-nbfc-early-warning-system/index.html",
        "articles/example/index.html",
        ".hidden/index.html",
        "articles/feed.xml",
        "scripts/tool.py",
    ], "https://liquilens.in") == [
        "https://liquilens.in/",
        "https://liquilens.in/articles/example/",
        "https://liquilens.in/guides/rbi-nbfc-early-warning-system/",
    ]


def test_key_requires_matching_root_filename(tmp_path):
    key = "12345678abcdef90"
    valid = tmp_path / f"{key}.txt"
    valid.write_text(key + "\n", encoding="utf-8")
    assert submit_indexnow.read_key(valid) == key

    wrong_name = tmp_path / "indexnow.txt"
    wrong_name.write_text(key, encoding="utf-8")
    try:
        submit_indexnow.read_key(wrong_name)
    except ValueError as exc:
        assert "filename must match" in str(exc)
    else:
        raise AssertionError("mismatched IndexNow key filename was accepted")


def test_submit_sends_bounded_indexnow_payload(tmp_path, monkeypatch):
    key = "12345678abcdef90"
    key_file = tmp_path / f"{key}.txt"
    key_file.write_text(key, encoding="utf-8")
    captured = {}

    class Response:
        status = 202

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_open(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data)
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(submit_indexnow, "urlopen", fake_open)
    urls = ["https://liquilens.in/tools/ews-coverage-check/"]
    assert submit_indexnow.submit(
        urls,
        base_url="https://liquilens.in",
        key_file=key_file,
    ) == 202
    assert captured == {
        "url": "https://api.indexnow.org/indexnow",
        "body": {
            "host": "liquilens.in",
            "key": key,
            "keyLocation": f"https://liquilens.in/{key}.txt",
            "urlList": urls,
        },
        "timeout": 20,
    }


def test_pages_workflow_notifies_only_after_deployment():
    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(
        encoding="utf-8"
    )
    assert "fetch-depth: 2" in workflow
    assert "submit_indexnow.py" in workflow
    assert "continue-on-error: true" in workflow
    assert workflow.index("id: deployment") < workflow.index("Notify IndexNow")
    assert re.search(r'--before "\$BEFORE_SHA"', workflow)
