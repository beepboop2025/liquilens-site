"""Manual, exact-main Railway executor for the single catalog Worker."""

from contextlib import contextmanager, nullcontext
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import tempfile
import time
import urllib.error
import urllib.request
import uuid

from isolation import clean_env, copy_tree, quiesce_builder, read_regular, run

CONTROLLER = Path(__file__).resolve().parent
REPOSITORY = "https://github.com/beepboop2025/liquilens-site.git"
ACCOUNT = "6b33e9ac81f0df1e9b52650676ddb0f1"
SCRIPT = "liquilens-ai-catalog"
UUID = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
BINDINGS = [
    {"name": "FINANCIAL_EVIDENCE_RATE_LIMITER", "type": "ratelimit",
     "namespace_id": "24082401", "simple": {"limit": 60, "period": 60}},
    {"name": "CF_VERSION_METADATA", "type": "version_metadata"},
]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError("Refusing an API redirect")


def require(value, message):
    if not value:
        raise RuntimeError(message)


def current_main(expected):
    request = urllib.request.Request(
        "https://api.github.com/repos/beepboop2025/liquilens-site/branches/main",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "railway-catalog-publisher"},
    )
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=25) as response:
        body = response.read(65537)
    require(len(body) <= 65536, "Oversized GitHub branch response")
    branch = json.loads(body)
    require(branch.get("protected") is True and branch.get("commit", {}).get("sha") == expected,
            "Requested source is not current protected main")


def version_metadata(source):
    return {"main_module": "catalog-worker.mjs", "compatibility_date": "2026-08-06",
            "bindings": BINDINGS, "keep_bindings": ["secret_text", "secret_key"],
            "annotations": {"workers/tag": source, "workers/message": "Railway-" + source,
                            "workers/commit_sha": source,
                            "workers/repository_url": "https://github.com/beepboop2025/liquilens-site"}}


def multipart(module, source):
    boundary = "railway-catalog-" + uuid.uuid4().hex
    require(boundary.encode() not in module, "Multipart boundary collision")
    fields = [
        ("metadata", None, "application/json", json.dumps(version_metadata(source)).encode()),
        ("catalog-worker.mjs", "catalog-worker.mjs", "application/javascript+module", module),
    ]
    body = b""
    for name, filename, content_type, content in fields:
        disposition = f'Content-Disposition: form-data; name="{name}"'
        if filename:
            disposition += f'; filename="{filename}"'
        body += (f"--{boundary}\r\n{disposition}\r\nContent-Type: {content_type}\r\n\r\n".encode()
                 + content + b"\r\n")
    body += f"--{boundary}--\r\n".encode()
    return body, "multipart/form-data; boundary=" + boundary


class Cloudflare:
    def __init__(self, token):
        require(bool(token), "CLOUDFLARE_API_TOKEN is required for apply")
        self.token = token

    def request(self, path, method="GET", body=None, content_type="application/json"):
        require(re.fullmatch(r"/(?:versions(?:/" + UUID + r"|\?bindings_inherit=strict)?|deployments)", path),
                "Unsupported Cloudflare operation")
        request = urllib.request.Request(
            f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT}/workers/scripts/{SCRIPT}" + path,
            data=body, method=method,
            headers={"Authorization": "Bearer " + self.token, "Content-Type": content_type,
                     "User-Agent": "railway-liquilens-catalog-publisher/1"},
        )
        try:
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=90) as response:
                data = response.read(4 * 1024 * 1024 + 1)
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"Cloudflare {method} {path}: HTTP {error.code}") from None
        require(len(data) <= 4 * 1024 * 1024, "Cloudflare response exceeds bound")
        result = json.loads(data)
        require(result.get("success") is True, "Cloudflare operation did not succeed")
        return result["result"]

    def latest(self):
        deployments = self.request("/deployments")["deployments"]
        require(bool(deployments), "No active Worker deployment")
        return deployments[0]

    def deploy(self, versions, message):
        require(all(re.fullmatch(UUID, version) for version, _ in versions), "Invalid version ID")
        require(sum(percentage for _, percentage in versions) == 100 and
                all(0 <= percentage <= 100 for _, percentage in versions), "Invalid traffic allocation")
        return self.request("/deployments", "POST", json.dumps({
            "strategy": "percentage", "versions": [
                {"version_id": version, "percentage": percentage} for version, percentage in versions],
            "annotations": {"workers/message": message},
        }).encode())


def stable_version(deployment):
    versions = deployment.get("versions", [])
    require(len(versions) == 1 and versions[0].get("percentage") == 100,
            "Refusing a split or unstable existing deployment")
    version = versions[0].get("version_id", "")
    require(re.fullmatch(UUID, version), "Invalid stable Worker version")
    return version


def durable_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def verify(*arguments):
    run(["python", "-I", "-S", str(CONTROLLER / "verify.py"), *arguments],
        Path("/verification"), timeout=190)


def prepare(source, work):
    trusted = work / "trusted"
    run(["git", "clone", "--quiet", "--no-checkout", REPOSITORY, str(trusted)], work)
    run(["git", "checkout", "--quiet", "--detach", source], trusted)
    actual = run(["git", "rev-parse", "HEAD"], trusted, capture=True)
    require(actual == source, "Checkout source differs")
    pins = json.loads((CONTROLLER / "pins.json").read_text())
    for name, digest in pins.items():
        require(hashlib.sha256(read_regular(trusted / name, 4 * 1024 * 1024)).hexdigest() == digest,
                "Reviewed verification policy changed: " + name)
    proof = Path("/verification")
    proof.mkdir(mode=0o755)
    for name in (".well-known", "protocol"):
        copy_tree(trusted / name, proof / name)
    for name in ("llms.txt", "sitemap.xml"):
        (proof / name).write_bytes(read_regular(trusted / name, 4 * 1024 * 1024))
    (proof / "scripts").mkdir()
    for name in (CONTROLLER / "gates").iterdir():
        shutil.copyfile(name, proof / "scripts" / name.name)
    app = Path("/app")
    app.mkdir(mode=0o755)
    copy_tree(trusted, app)
    for path in [app, *app.rglob("*")]:
        os.chown(path, 10001, 10001)
    env = {"HOME": "/home/builder", "LIQUILENS_OFFLINE": "1",
           "RAILWAY_GIT_COMMIT_SHA": source,
           "PATH": "/home/builder/venv/bin:/usr/local/bin:/usr/bin:/bin"}
    run(["python", "-m", "venv", "/home/builder/venv"], app, builder=True, extra=env)
    run(["/home/builder/venv/bin/python", "-m", "pip", "install", "--only-binary=:all:",
         "--require-hashes", "-r", "requirements-ci.txt"], app, builder=True, extra=env)
    run(["npm", "ci", "--ignore-scripts"], app, builder=True, extra=env)
    run(["sh", "deploy/railway-ci/run.sh"], app, builder=True, extra=env)
    run(["npx", "--no-install", "wrangler", "deploy", "--dry-run", "--outdir", "/app/worker-output",
         "--config", "wrangler.catalog.jsonc"], app, builder=True, extra=env)
    quiesce_builder()
    module = read_regular(app / "worker-output/catalog-worker.js", 5 * 1024 * 1024)
    verify("--external-proof-only", "--attempts", "2", "--delay", "2", "--budget-seconds", "150")
    current_main(source)
    return module


@contextmanager
def publication_lock(evidence):
    descriptor = os.open(evidence / "publisher.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another manual publication is already running") from None
        yield
    finally:
        os.close(descriptor)


def assert_active(api, deployment_id, versions):
    current = api.latest()
    actual = sorted((row["version_id"], row["percentage"]) for row in current.get("versions", []))
    require(current.get("id") == deployment_id and actual == sorted(versions),
            "Active Worker deployment changed; refusing to overwrite a concurrent release")


def rollback(api, previous, candidate, transaction=None):
    current = api.latest()
    held = {item.get("version_id") for item in current.get("versions", [])}
    require(held and held <= {previous, candidate}, "Refusing to overwrite a concurrent Worker release")
    if transaction is not None:
        if current.get("id") == transaction["previous_deployment_id"]:
            require(stable_version(current) == previous, "Previous traffic identity changed")
            return  # No stage occurred, or the exact original deployment is still active.
        owned = {transaction.get("staged_deployment_id"), transaction.get("promoted_deployment_id")}
        messages = {"Railway stage " + transaction["operation_id"],
                    "Railway promote " + transaction["operation_id"]}
        require(current.get("id") in (owned - {None}) or
                current.get("annotations", {}).get("workers/message") in messages,
                "Active deployment is not owned by this publication transaction")
    api.deploy([(previous, 100)], "Railway rollback after failed exact-main publication")
    require(stable_version(api.latest()) == previous, "Rollback did not restore the exact prior version")


def main():
    source = os.environ.get("EXPECTED_MAIN_SHA", "")
    require(re.fullmatch(r"[0-9a-f]{40}", source), "An explicit EXPECTED_MAIN_SHA is required")
    apply = os.environ.get("PUBLISH_APPLY", "0")
    require(apply in ("0", "1"), "PUBLISH_APPLY must be 0 or 1")
    evidence = Path("/evidence")
    if apply == "1":
        require(os.path.ismount(evidence), "Apply requires the dedicated evidence volume")
    if os.path.ismount(evidence):
        evidence.chmod(0o700)
    with publication_lock(evidence) if apply == "1" else nullcontext():
        execute(source, apply, evidence)


def execute(source, apply, evidence):
    current_main(source)
    with tempfile.TemporaryDirectory(prefix="catalog-publisher-") as directory:
        module = prepare(source, Path(directory))
        digest = hashlib.sha256(module).hexdigest()
        if apply == "0":
            print(f"RAILWAY_CATALOG_PREPARED source={source} sha256={digest}", flush=True)
            return
        api = Cloudflare(os.environ.get("CLOUDFLARE_API_TOKEN", ""))
        pending = evidence / "pending.json"
        if pending.exists():
            prior = json.loads(read_regular(pending, 65536))
            require(prior.get("account") == ACCOUNT and prior.get("script") == SCRIPT,
                    "Pending transaction belongs to another publisher")
            rollback(api, prior["previous"], prior["candidate"], prior)
            pending.unlink()
        prior_deployment = api.latest()
        previous = stable_version(prior_deployment)
        previous_deployment_id = prior_deployment["id"]
        require(re.fullmatch(UUID, previous_deployment_id), "Invalid previous deployment identity")
        current_main(source)
        body, content_type = multipart(module, source)
        candidate = api.request("/versions?bindings_inherit=strict", "POST", body, content_type)["id"]
        require(re.fullmatch(UUID, candidate), "Invalid uploaded version ID")
        version = api.request("/versions/" + candidate)
        annotations = version.get("annotations", {})
        require(version.get("id") == candidate and annotations.get("workers/tag") == source
                and annotations.get("workers/message") == "Railway-" + source,
                "Uploaded candidate is not bound to the requested source")
        transaction = {"account": ACCOUNT, "script": SCRIPT, "source": source,
                       "operation_id": uuid.uuid4().hex,
                       "previous": previous, "previous_deployment_id": previous_deployment_id,
                       "candidate": candidate, "module_sha256": digest,
                       "controller": json.loads((CONTROLLER / "controller-source.json").read_text()),
                       "version": version}
        durable_json(pending, transaction)
        signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
        try:
            current_main(source)
            assert_active(api, previous_deployment_id, [(previous, 100)])
            staged = api.deploy([(previous, 100), (candidate, 0)], "Railway stage " + transaction["operation_id"])
            require(re.fullmatch(UUID, staged.get("id", "")), "Invalid staged deployment identity")
            transaction["staged_deployment_id"] = staged["id"]
            durable_json(pending, transaction)
            assert_active(api, staged["id"], [(previous, 100), (candidate, 0)])
            verify("--worker-version-id", candidate, "--expected-version-tag", source,
                   "--attempts", "24", "--delay", "5", "--budget-seconds", "150",
                   "--no-palimpsest-proof", "--no-sibling-proof")
            current_main(source)
            assert_active(api, staged["id"], [(previous, 100), (candidate, 0)])
            promoted = api.deploy([(candidate, 100)], "Railway promote " + transaction["operation_id"])
            transaction["promoted_deployment_id"] = promoted["id"]
            verify("--expected-version-tag", source, "--expected-worker-version-id", candidate,
                   "--attempts", "24", "--delay", "5",
                   "--budget-seconds", "150")
            current_main(source)
            assert_active(api, promoted["id"], [(candidate, 100)])
            transaction.update({"outcome": "succeeded", "completed_at": time.time(),
                                "deployment": os.environ.get("RAILWAY_DEPLOYMENT_ID", "unknown")})
            durable_json(evidence / (source + "-" + candidate + ".json"), transaction)
            pending.unlink()
        except BaseException:
            rollback(api, previous, candidate, transaction)
            pending.unlink()
            raise
        print(f"RAILWAY_CATALOG_PUBLISH_PASS source={source} version={candidate} previous={previous}", flush=True)
