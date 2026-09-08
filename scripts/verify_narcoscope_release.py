"""Verify NarcoScope's signed historical Fleet deployment and current origins.

The receipt proves the recorded release, not every later data refresh. Current
origin agreement and version/contract checks remain separate live requirements.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile


OWNER_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBuJV6o8YL2XXR9q4vcwpHuc2z1GEBawSmrJWGrgwzFV"
OWNER_FINGERPRINT = "SHA256:yhoa/PIDMM6M/ZennILp8jtRJy5pArncJRARbQssTMI"
RAILWAY = {
    "project_id": "d4da4135-1f9f-44f2-b66c-89c76f54b15d",
    "environment_id": "e18d163f-7bac-48bf-a266-6c3d48f7b24f",
    "service_id": "21d80a60-b268-46f0-a581-4cfc48598268",
}
HEALTH_URLS = (
    "https://narcoscope-web-production.up.railway.app/healthz",
    "https://www.narcoscope.com/healthz",
)


def require(condition, message):
    if not condition:
        raise RuntimeError("NarcoScope Fleet proof: " + message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False) + "\n").encode()


def verify_signature(receipt, signature):
    """The signer comes from reviewed code, never the catalog or receipt."""
    with tempfile.TemporaryDirectory(prefix="narcoscope-release-") as directory:
        root = Path(directory)
        key = root / "owner.pub"
        key.write_text(OWNER_KEY + "\n")
        fingerprint = subprocess.run(
            ["ssh-keygen", "-lf", str(key)], capture_output=True, text=True,
            timeout=10, check=True,
        ).stdout.split()[1]
        require(fingerprint == OWNER_FINGERPRINT, "owner key fingerprint differs")
        (root / "allowed_signers").write_text("fleet-owner " + OWNER_KEY + "\n")
        (root / "receipt.sig").write_bytes(signature)
        result = subprocess.run(
            ["ssh-keygen", "-Y", "verify", "-f", str(root / "allowed_signers"),
             "-I", "fleet-owner", "-n", "fleet-release", "-s", str(root / "receipt.sig")],
            input=receipt, capture_output=True, timeout=10,
        )
        require(result.returncode == 0, "owner signature is invalid")


def validate_receipt(receipt, manifest_bytes, expected_sha, deployment_id):
    require(receipt.get("format") == "fleet-publisher-receipt/v1", "receipt format")
    require(receipt.get("product_id") == "narcoscope", "receipt product")
    require(receipt.get("outcome") == "succeeded" and receipt.get("rollback") is None,
            "release did not succeed")
    require(receipt.get("railway") == RAILWAY, "Railway project/environment/service")
    require(receipt.get("deployment_id") == deployment_id and
            re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", deployment_id),
            "deployment identity")
    finished = datetime.fromisoformat(receipt["finished_at"].replace("Z", "+00:00"))
    require(finished.tzinfo is not None and finished <= datetime.now(timezone.utc),
            "release timestamp")
    bundle = receipt["bundle"]
    require(bundle.get("product_id") == "narcoscope" and
            bundle.get("source_commit") == expected_sha, "receipt source")
    release = hashlib.sha256(manifest_bytes).hexdigest()
    require(bundle.get("release_id") == release and
            bundle.get("manifest_sha256") == release, "manifest digest")
    manifest = json.loads(manifest_bytes)
    require(canonical(manifest) == manifest_bytes, "noncanonical manifest")
    require(manifest.get("format") == "fleet-release-manifest/v1" and
            manifest.get("product_id") == "narcoscope", "manifest format/product")
    require(manifest.get("source") == {
        "branch": "main", "commit": expected_sha,
        "repository": "git@github-narcoscope:beepboop2025/narcoscope.git",
    }, "manifest source")
    files = manifest.get("files")
    require(isinstance(files, list) and bool(files), "empty manifest")
    tree = hashlib.sha256(canonical(files)).hexdigest()
    require(manifest.get("tree_sha256") == tree and bundle.get("tree_sha256") == tree,
            "tree digest")
    regular = [entry for entry in files if entry.get("type") == "file"]
    require(len(regular) == bundle.get("file_count") and
            sum(entry["size"] for entry in regular) == bundle.get("byte_count"),
            "manifest file totals")
    health = receipt.get("health", [])
    require(len(health) == 2 and {item.get("url") for item in health} == set(HEALTH_URLS),
            "historical health origins")
    require(all(item.get("status") == 200 and item.get("identity_verified") is True and
                re.fullmatch(r"[0-9a-f]{64}", item.get("body_sha256", ""))
                for item in health), "historical health proof")


def validate_current_origins(health):
    identities = []
    for body in health:
        require(body.get("status") == "ready" and body.get("service") == "narcoscope"
                and body.get("releaseIdentity") == "fleet-manifest", "current health state")
        identity = tuple(body.get(key, "") for key in ("source_commit", "release_id", "tree_sha256"))
        require(all(re.fullmatch(r"[0-9a-f]{" + str(size) + "}", value)
                    for size, value in zip((40, 64, 64), identity)), "current identity format")
        require(body.get("revision") == identity[0], "current revision differs")
        identities.append(identity)
    require(len(identities) == 2 and identities[0] == identities[1], "current origins disagree")
    return identities[0]


def verify_release(card, root, fetch_bytes):
    metadata = card.get("metadata", {})
    require(card.get("data", {}).get("repository", {}).get("url") ==
            "https://github.com/beepboop2025/narcoscope", "catalog repository")
    sha = metadata.get("sourceUpgradeCommit", "")
    require(isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{40}", sha), "catalog source")
    relative = "protocol/release-evidence/narcoscope/" + sha
    require(metadata.get("productionReleaseReceipt") ==
            "https://liquilens.in/" + relative + "/receipt.json", "catalog receipt location")
    directory = root / relative
    values = []
    for name, limit in (("receipt.json", 32768), ("receipt.json.sig", 8192),
                        ("release-manifest.json", 512000)):
        data = (directory / name).read_bytes()
        require(0 < len(data) <= limit, "evidence size")
        values.append(data)
    receipt_bytes, signature, manifest = values
    verify_signature(receipt_bytes, signature)
    validate_receipt(json.loads(receipt_bytes), manifest, sha,
                     metadata.get("productionDeploymentId", ""))
    health = []
    for url in HEALTH_URLS:
        body, _, _ = fetch_bytes(url, accept="application/json", timeout=5, max_bytes=32768)
        health.append(json.loads(body))
    current = validate_current_origins(health)
    return ("; signed historical Fleet deployment " + sha[:12] +
            ", current origins agree at " + current[0][:12])
