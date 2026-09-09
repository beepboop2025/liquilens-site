"""Bind Palimpsest's native host receipt to reviewed source and Registry bytes.

The signed receipt records a host deployment. Current public MCP inventory,
tool behavior and publication rights are separate checks in verify_catalog_edge.
Rights publication_sha is a data publication identity, never a runtime identity.
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
SIGNATURE_NAMESPACE = "palimpsest-mcp-release"
REPOSITORY = "beepboop2025/palimpsest"
MANIFEST_SHA256 = "be115e404655aaf00b2b935881296d59809093fb5aa526317ca3aa1c7a8a8820"
RECEIPT_FIELDS = {
    "deployed_at_utc", "previous_runtime_backup", "previous_runtime_sha256",
    "previous_runtime_source_sha", "previous_sha", "schema_version",
    "server_file_sha256", "server_version", "service", "target_sha", "verification",
}


def require(condition, message):
    if not condition:
        raise RuntimeError("Palimpsest native proof: " + message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def verify_signature(receipt, signature):
    """Trust the reviewed owner key, never a key supplied by receipt metadata."""
    with tempfile.TemporaryDirectory(prefix="palimpsest-release-") as directory:
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
             "-I", "fleet-owner", "-n", SIGNATURE_NAMESPACE,
             "-s", str(root / "receipt.sig")],
            input=receipt, capture_output=True, timeout=10,
        )
        require(result.returncode == 0, "owner signature is invalid")


def digest(value, label):
    require(isinstance(value, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", value),
            label + " digest is invalid")
    return value.removeprefix("sha256:")


def validate_receipt(receipt_bytes, metadata, version):
    receipt = json.loads(receipt_bytes)
    require(isinstance(receipt, dict) and set(receipt) == RECEIPT_FIELDS,
            "host receipt shape differs")
    require(canonical(receipt) == receipt_bytes, "host receipt is not canonical")
    require(type(receipt.get("schema_version")) is int and receipt["schema_version"] == 2,
            "host receipt schema differs")
    require(receipt.get("service") == "palimpsest-mcp.service", "host service differs")
    sha = metadata.get("nativeDeploymentCommit")
    require(isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{40}", sha),
            "native source SHA is invalid")
    require(receipt.get("target_sha") == sha, "native source differs")
    require(receipt.get("server_version") == version == "1.9.3", "native version differs")
    require(receipt.get("server_file_sha256") ==
            digest(metadata.get("nativeRuntimeSha256"), "native runtime"),
            "native runtime digest differs")
    require(receipt.get("verification") == {
        "github_signature": "valid", "local_initialize_list_call": "passed",
        "target_on_origin_main": True,
    }, "host acceptance checks differ")
    require(receipt["verification"]["target_on_origin_main"] is True,
            "host source acceptance is not a boolean")
    clock = receipt.get("deployed_at_utc", "")
    require(isinstance(clock, str) and re.fullmatch(r"[0-9]{8}T[0-9]{6}Z", clock),
            "host deployment clock is invalid")
    try:
        recorded = datetime.strptime(clock, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise RuntimeError("Palimpsest native proof: host deployment clock is invalid") from error
    require(recorded <= datetime.now(timezone.utc), "host deployment clock is in the future")
    previous_digest = receipt.get("previous_runtime_sha256", "")
    require(isinstance(previous_digest, str) and re.fullmatch(r"[0-9a-f]{64}", previous_digest),
            "rollback runtime digest is invalid")
    backup = receipt.get("previous_runtime_backup", "")
    require(isinstance(backup, str) and re.fullmatch(
        r"[0-9]{8}T[0-9]{6}Z-" + previous_digest + r"\.[A-Za-z0-9]{6}\.py", backup),
        "rollback backup does not bind the previous runtime")
    previous = receipt.get("previous_sha")
    previous_source = receipt.get("previous_runtime_source_sha")
    for value in (previous, previous_source):
        require(value is None or isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value),
                "rollback source identity is invalid")
    require((previous is None) == (previous_source is None), "rollback source presence differs")
    return receipt


def verify_release(card, registry_server, root, fetch_bytes):
    metadata = card.get("metadata", {})
    sha = metadata.get("nativeDeploymentCommit", "")
    require(isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{40}", sha),
            "seven-tool inventory requires an exact native deployment receipt")
    relative = "protocol/release-evidence/palimpsest/" + sha
    directory = root / relative
    values = []
    for name, field, limit in (
        ("host-receipt.json", "nativeDeploymentReceipt", 32768),
        ("host-receipt.json.sig", "nativeDeploymentSignature", 8192),
    ):
        require(metadata.get(field) == "https://liquilens.in/" + relative + "/" + name,
                "native evidence location differs")
        data = (directory / name).read_bytes()
        require(0 < len(data) <= limit, "native evidence size is invalid")
        require(hashlib.sha256(data).hexdigest() ==
                digest(metadata.get(field + "Sha256"), field), "native evidence digest differs")
        values.append(data)
    receipt_bytes, signature = values
    verify_signature(receipt_bytes, signature)
    receipt = validate_receipt(receipt_bytes, metadata, card.get("version"))
    require(digest(metadata.get("nativeManifestSha256"), "native manifest") == MANIFEST_SHA256,
            "reviewed Registry manifest changed")
    for path, expected, limit in (
        ("mcp/palimpsest_mcp.py", receipt["server_file_sha256"], 512000),
        ("server.json", MANIFEST_SHA256, 32768),
    ):
        body, _, _ = fetch_bytes(
            "https://api.github.com/repos/" + REPOSITORY + "/contents/" + path + "?ref=" + sha,
            accept="application/vnd.github.raw+json", timeout=5, max_bytes=limit,
        )
        require(hashlib.sha256(body).hexdigest() == expected, "public source bytes differ: " + path)
        if path == "server.json":
            require(json.loads(body) == registry_server, "Registry server differs from reviewed manifest")
    return "owner-signed native host receipt and public source bytes bind " + sha[:12]
