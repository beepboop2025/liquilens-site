"""The historical production proof cannot become an unsigned health shortcut."""

import copy
import json
from pathlib import Path

import pytest

from scripts import verify_narcoscope_release as release
from scripts.verify_catalog_edge import _verify_sibling_deployment_proof
from scripts.verify_catalog_edge import _require_modern_result


SOURCE = "0f3887d456fbb985a1dd3532ec689cda259e1aa4"
DIRECTORY = Path(__file__).resolve().parents[1] / "protocol/release-evidence/narcoscope" / SOURCE
RECEIPT_BYTES = (DIRECTORY / "receipt.json").read_bytes()
RECEIPT = json.loads(RECEIPT_BYTES)
MANIFEST = (DIRECTORY / "release-manifest.json").read_bytes()
SIGNATURE = (DIRECTORY / "receipt.json.sig").read_bytes()


def test_reviewed_actual_receipt_signature_and_manifest_verify():
    release.verify_signature(RECEIPT_BYTES, SIGNATURE)
    release.validate_receipt(RECEIPT, MANIFEST, SOURCE, RECEIPT["deployment_id"])


def test_receipt_bytes_cannot_be_changed_after_owner_review():
    with pytest.raises(RuntimeError, match="signature"):
        release.verify_signature(RECEIPT_BYTES.replace(b"succeeded", b"untrusted"), SIGNATURE)


def test_catalog_cannot_drop_the_narcoscope_deployment_proof():
    with pytest.raises(RuntimeError, match="requires"):
        _verify_sibling_deployment_proof("NarcoScope", {"metadata": {}})


def test_signer_cannot_come_from_untrusted_evidence(monkeypatch):
    monkeypatch.setattr(release, "OWNER_FINGERPRINT", "SHA256:unreviewed-key")
    with pytest.raises(RuntimeError, match="fingerprint"):
        release.verify_signature(RECEIPT_BYTES, SIGNATURE)


@pytest.mark.parametrize("mutation", ["source", "project", "service", "host", "status", "deployment"])
def test_signed_claims_still_require_the_exact_production_boundary(mutation):
    receipt = copy.deepcopy(RECEIPT)
    if mutation == "source":
        receipt["bundle"]["source_commit"] = "a" * 40
    elif mutation in ("project", "service"):
        receipt["railway"][mutation + "_id"] = "wrong-identity"
    elif mutation == "host":
        receipt["health"][0]["url"] = "https://attacker.example/healthz"
    elif mutation == "status":
        receipt["outcome"] = "failed"
    else:
        receipt["deployment_id"] = "00000000-0000-0000-0000-000000000000"
    with pytest.raises(RuntimeError):
        release.validate_receipt(receipt, MANIFEST, SOURCE, RECEIPT["deployment_id"])


def test_manifest_bytes_cannot_be_substituted():
    with pytest.raises(RuntimeError, match="manifest digest"):
        release.validate_receipt(RECEIPT, MANIFEST + b" ", SOURCE, RECEIPT["deployment_id"])


def current_health(source="b" * 40):
    return {"status": "ready", "service": "narcoscope", "releaseIdentity": "fleet-manifest",
            "source_commit": source, "revision": source, "release_id": "c" * 64,
            "tree_sha256": "d" * 64}


def test_later_data_releases_do_not_invalidate_a_historical_deployment_receipt():
    # Current version and contract bytes are checked separately by the caller.
    identity = release.validate_current_origins([current_health(), current_health()])
    assert identity[0] != SOURCE


def test_agreed_later_data_identity_cannot_bypass_the_existing_live_version_gate():
    release.validate_current_origins([current_health(), current_health()])
    payload = {"jsonrpc": "2.0", "id": "probe", "result": {
        "resultType": "complete", "_meta": {"io.modelcontextprotocol/serverInfo": {
            "name": "narcoscope", "version": "1.4.0"}}}}
    with pytest.raises(RuntimeError, match="version"):
        _require_modern_result(payload, {}, "probe", expected_name="narcoscope",
                               expected_version="1.5.0")


@pytest.mark.parametrize("mutation", ["origin", "missing_identity", "revision", "unready"])
def test_current_origins_must_agree_on_a_complete_ready_identity(mutation):
    first, second = current_health(), current_health()
    if mutation == "origin":
        second["source_commit"] = second["revision"] = "a" * 40
    elif mutation == "missing_identity":
        second.pop("tree_sha256")
    elif mutation == "revision":
        second["revision"] = "a" * 40
    else:
        second["status"] = "unready"
    with pytest.raises(RuntimeError):
        release.validate_current_origins([first, second])
