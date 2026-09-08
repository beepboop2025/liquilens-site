"""Generate the daily edition with a separate, constrained Git publisher."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import sys
import tempfile

from isolation import (
    COLLECTOR_UID, CONTROLLER, digest, drop_privileges, event, git,
    publisher_environment, read_regular, stop_collectors,
)

REPOSITORY = "git@github.com:beepboop2025/liquilens-site.git"
FILES = ("Dockerfile", "editorial.py", "isolation.py", "test_editorial.py",
         "requirements-ci.txt", "github-known-hosts")
EDITORIAL_ENV = (
    "EDITORIAL_LLM_API_KEY", "EDITORIAL_LLM_BASE_URL", "EDITORIAL_LLM_MODEL",
    "EDITORIAL_REVIEW_MODEL", "EDITORIAL_REASONING_EFFORT",
)
MAX_TREE_BYTES = 512 * 1024 * 1024
SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"


def controller_digest():
    return digest(b"".join(name.encode() + b"\0" + (CONTROLLER / name).read_bytes()
                           for name in FILES))


def allowed_output(name):
    return name in {
        "sitemap.xml", "llms.txt", "articles/index.json", "articles/index.html",
        "articles/feed.json", "articles/feed.xml", "articles/learning.json",
        "articles/share.png",
    } or re.fullmatch(rf"articles/{SLUG}(?:\.(?:json|md)|/(?:index\.html|share\.png))", name) is not None


def checkout(mirror, env, source, work):
    baseline = {}
    total = 0
    for entry in git(mirror, env, "ls-tree", "-rz", "--full-tree", source).split(b"\0"):
        if not entry:
            continue
        header, raw_name = entry.split(b"\t", 1)
        mode, kind, blob = header.decode().split()
        name = raw_name.decode("utf-8")
        relative = Path(name)
        if relative.is_absolute() or any(p in {"..", ".git"} for p in relative.parts):
            raise ValueError("unsafe source path")
        if mode not in {"100644", "100755"} or kind != "blob":
            raise ValueError(f"unsupported source object: {name}")
        content = git(mirror, env, "cat-file", "blob", blob)
        total += len(content)
        if total > MAX_TREE_BYTES:
            raise ValueError("source tree exceeds byte limit")
        path = work / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        path.chmod(0o555 if mode == "100755" else 0o444)
        baseline[name] = digest(content)
    if (work / "requirements-ci.txt").read_bytes() != (CONTROLLER / "requirements-ci.txt").read_bytes():
        raise ValueError("verification lock changed; reviewed image rebuild required")
    # New editions create files and directories, but the writer cannot replace
    # the root-owned articles directory or any code outside it.
    articles = work / "articles"
    for path in [articles, *articles.rglob("*")]:
        os.chown(path, COLLECTOR_UID, COLLECTOR_UID)
        path.chmod(0o755 if path.is_dir() else 0o644)
    for name in ("sitemap.xml", "llms.txt"):
        path = work / name
        os.chown(path, COLLECTOR_UID, COLLECTOR_UID)
        path.chmod(0o644)
    return baseline


def run_writer(work, scratch, args, writer_env, timeout):
    scratch.mkdir(mode=0o700)
    os.chown(scratch, COLLECTOR_UID, COLLECTOR_UID)
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(scratch),
           "TMPDIR": str(scratch), "PYTHONDONTWRITEBYTECODE": "1",
           "PYTHONUNBUFFERED": "1", **writer_env}
    process = subprocess.Popen(
        [sys.executable, *args], cwd=work, env=env, stdin=subprocess.DEVNULL,
        close_fds=True, preexec_fn=drop_privileges, start_new_session=True,
    )
    try:
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise RuntimeError("editorial step exceeded its deadline") from None
        if code:
            raise RuntimeError(f"editorial step failed with exit {code}")
    finally:
        stop_collectors()


def validate_outputs(work, baseline, day):
    # All children, including detached ones, are dead before output traversal.
    seen, changed = set(), {}
    total = 0
    for path in work.rglob("*"):
        if path.is_symlink():
            raise ValueError("symbolic output link")
        if path.is_dir():
            continue
        name = path.relative_to(work).as_posix()
        content = read_regular(path)
        total += len(content)
        if total > MAX_TREE_BYTES:
            raise ValueError("output tree exceeds byte limit")
        seen.add(name)
        if digest(content) != baseline.get(name):
            if not allowed_output(name):
                raise ValueError(f"unapproved changed output: {name}")
            changed[name] = content
    if not set(baseline).issubset(seen):
        raise ValueError("source files were removed")
    index = json.loads(read_regular(work / "articles/index.json"))
    if not isinstance(index, list):
        raise ValueError("invalid article index")
    today = [row for row in index if isinstance(row, dict) and row.get("date") == day]
    if len(today) != 1 or re.fullmatch(SLUG, str(today[0].get("slug", ""))) is None:
        raise ValueError("today's edition is absent or ambiguous")
    slug = today[0]["slug"]
    sidecar = json.loads(read_regular(work / f"articles/{slug}.json"))
    if (sidecar.get("slug") != slug or sidecar.get("date") != day
            or sidecar.get("quality_gate", {}).get("status") != "PASS"
            or sidecar.get("canonical_url") != f"https://liquilens.in/articles/{slug}/"):
        raise ValueError("today's edition failed identity or quality gate")
    for suffix in (".md", "/index.html", "/share.png"):
        if not read_regular(work / f"articles/{slug}{suffix}"):
            raise ValueError("empty edition output")
    return changed, slug


def publish(mirror, env, source, changed, day, deployment, apply):
    current = git(mirror, env, "ls-remote", "origin", "refs/heads/main").decode().split()[0]
    if current != source:
        event("superseded", source=source, current=current)
        return None
    if not changed:
        return source
    index_env = {**env, "GIT_INDEX_FILE": str(mirror.parent / "publication-index")}
    git(mirror, index_env, "read-tree", source)
    for name, content in sorted(changed.items()):
        if not allowed_output(name):
            raise ValueError("unapproved publication path")
        blob = git(mirror, env, "hash-object", "-w", "--stdin", data=content).decode().strip()
        git(mirror, index_env, "update-index", "--add", "--cacheinfo", f"100644,{blob},{name}")
    tree = git(mirror, index_env, "write-tree").decode().strip()
    message = (f"articles: publish {day} edition from Railway\n\n"
               f"Editorial-Source: {source}\nRailway-Deployment: {deployment}\n"
               f"Editorial-Controller: {controller_digest()}\n")
    commit = git(mirror, env, "commit-tree", tree, "-p", source, data=message.encode()).decode().strip()
    paths = git(mirror, env, "diff-tree", "--no-commit-id", "--name-only", "-r", commit).decode().splitlines()
    if set(paths) != set(changed):
        raise ValueError("publication diff differs from validated output")
    event("publication", source=source, commit=commit, paths=paths, apply=apply)
    if apply:
        git(mirror, env, "push", "origin", f"{commit}:refs/heads/main")
    return commit


def main():
    if os.geteuid() != 0:
        raise RuntimeError("controller must be root; writer drops privileges")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    key = os.environ.pop("GITHUB_DEPLOY_KEY")
    writer_env = {name: os.environ.pop(name) for name in EDITORIAL_ENV if os.environ.get(name)}
    apply = os.getenv("EDITORIAL_APPLY") == "1"
    deployment = os.getenv("RAILWAY_DEPLOYMENT_ID", "local")
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with tempfile.TemporaryDirectory(prefix="editorial-publisher-") as private, \
            tempfile.TemporaryDirectory(prefix="editorial-writer-") as public:
        private_root, public_root = Path(private), Path(public)
        public_root.chmod(0o755)
        env = publisher_environment(private_root, key)
        env.update(GIT_AUTHOR_NAME="liquilens-desk", GIT_COMMITTER_NAME="liquilens-desk",
                   GIT_AUTHOR_EMAIL="desk@liquilens.in", GIT_COMMITTER_EMAIL="desk@liquilens.in")
        del key
        mirror = private_root / "repository.git"
        git(None, env, "clone", "--bare", "--single-branch", "--branch", "main", REPOSITORY, str(mirror))
        source = git(mirror, env, "rev-parse", "refs/heads/main").decode().strip()
        if re.fullmatch(r"[0-9a-f]{40}", source) is None:
            raise ValueError("invalid source identity")
        work = public_root / "repo"
        work.mkdir(mode=0o755)
        baseline = checkout(mirror, env, source, work)
        event("editorial_start", source=source, deployment=deployment, day=day,
              controller=controller_digest(), editorial_model_configured=bool(writer_env.get("EDITORIAL_LLM_API_KEY")))
        run_writer(work, public_root / "writer", ["scripts/daily_article.py", "--date", day], writer_env, 900)
        # Tests receive neither publishing credentials nor the editorial model key.
        run_writer(work, public_root / "tests", ["-m", "pytest", "-p", "no:cacheprovider",
                   "tests/test_daily_articles.py", "tests/test_social_cards.py",
                   "tests/test_investigations.py", "tests/test_ai_discovery.py", "-q"], {}, 300)
        changed, slug = validate_outputs(work, baseline, day)
        commit = publish(mirror, env, source, changed, day, deployment, apply)
        if commit is None:
            return 3
        event("RAILWAY_EDITORIAL_PASS" if apply else "RAILWAY_EDITORIAL_DRY_RUN_PASS",
              source=source, commit=commit, deployment=deployment, day=day,
              slug=slug, changed_files=len(changed), controller=controller_digest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
