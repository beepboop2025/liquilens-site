"""The historical production proof cannot become an unsigned health shortcut."""

import copy
import json
from pathlib import Path

import pytest

from scripts import verify_narcoscope_release as release
from scripts.verify_catalog_edge import _verify_sibling_deployment_proof
from scripts.verify_catalog_edge import _require_modern_result
from scripts.verify_catalog_edge import _validate_narcoscope_native_ci


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


def native_card_and_status():
    catalog = json.loads((DIRECTORY.parents[3] / ".well-known/ai-catalog.json").read_text())
    card = next(row for row in catalog["entries"]
                if row["identifier"] == "urn:air:liquilens.in:catalog:narcoscope")
    metadata = card["metadata"]
    return card, {"sha": metadata["sourceUpgradeCommit"], "statuses": [{
        "context": "railway-automation - narcoscope-pr-ci", "state": "success",
        "target_url": metadata["sourceValidationUrl"],
    }]}


def test_current_native_release_retains_a_valid_owner_signed_receipt():
    card, payload = native_card_and_status()
    _validate_narcoscope_native_ci(card, payload)
    sha = card["metadata"]["sourceUpgradeCommit"]
    directory = DIRECTORY.parent / sha
    receipt = (directory / "receipt.json").read_bytes()
    release.verify_signature(receipt, (directory / "receipt.json.sig").read_bytes())
    release.validate_receipt(json.loads(receipt), (directory / "release-manifest.json").read_bytes(),
                             sha, card["metadata"]["productionDeploymentId"])


@pytest.mark.parametrize("mutation", ["source", "failure", "missing", "duplicate",
                                    "context", "deployment", "lane", "publication"])
def test_native_ci_cannot_be_replaced_by_an_unrelated_success(mutation):
    card, payload = native_card_and_status()
    if mutation == "source":
        payload["sha"] = "a" * 40
    elif mutation == "failure":
        payload["statuses"][0]["state"] = "failure"
    elif mutation == "missing":
        payload["statuses"] = []
    elif mutation == "duplicate":
        payload["statuses"] *= 2
    elif mutation == "context":
        payload["statuses"][0]["context"] = "unrelated-check"
    elif mutation == "deployment":
        payload["statuses"][0]["target_url"] += "&extra=1"
    elif mutation == "lane":
        wrong = card["metadata"]["sourceValidationUrl"].replace("96649d78", "aaaaaaaa")
        card["metadata"]["sourceValidationUrl"] = wrong
        payload["statuses"][0]["target_url"] = wrong
    else:
        card["metadata"]["registryPublicationMethod"] = "unverified"
    with pytest.raises(RuntimeError):
        _validate_narcoscope_native_ci(card, payload)


NATIVE_DIRECTORY = DIRECTORY.parents[3] / release.NATIVE_EVIDENCE
NATIVE_BYTES = (NATIVE_DIRECTORY / "receipt.json").read_bytes()
NATIVE = json.loads(NATIVE_BYTES)
NATIVE_MANIFEST = (NATIVE_DIRECTORY / "release-manifest.json").read_bytes()
HISTORICAL_NATIVE_ANCHOR = (DIRECTORY.parent / "e818c33feaf5f8081cbfc5807aced0cd50d8952f" / "receipt.json").read_bytes()


def test_reviewed_actual_native_transition_signature_and_manifest_verify():
    release.verify_signature(NATIVE_BYTES, (NATIVE_DIRECTORY / "receipt.json.sig").read_bytes(),
                             namespace="hetzner-hosting")
    release.validate_native_receipt(NATIVE, NATIVE_MANIFEST, HISTORICAL_NATIVE_ANCHOR)


def test_native_transition_signature_is_scoped_and_cannot_be_reused_as_fleet_authority():
    with pytest.raises(RuntimeError, match="signature"):
        release.verify_signature(NATIVE_BYTES, (NATIVE_DIRECTORY / "receipt.json.sig").read_bytes())


@pytest.mark.parametrize("mutation", ["provider", "history", "image", "source", "release", "tree", "host", "origin", "identity", "railway"])
def test_native_transition_rejects_changed_claims(mutation):
    receipt = copy.deepcopy(NATIVE)
    if mutation == "provider":
        receipt["provider"] = "railway"
    elif mutation == "history":
        receipt["historical_receipt_sha256"] = "0" * 64
    elif mutation == "image":
        receipt["image_id"] = "mutable-tag"
    elif mutation in ("source", "release", "tree"):
        receipt[{"source": "source_commit", "release": "release_id", "tree": "tree_sha256"}[mutation]] = "a" * 64
    elif mutation == "host":
        receipt["public_health"]["url"] = release.HEALTH_URLS[0]
    elif mutation == "origin":
        receipt["public_health"]["hosting_origin"] = "railway"
    elif mutation == "identity":
        receipt["public_health"]["body"] = current_health()
    else:
        receipt["railway_called"] = True
    with pytest.raises(RuntimeError):
        release.validate_native_receipt(receipt, NATIVE_MANIFEST, HISTORICAL_NATIVE_ANCHOR)


def test_native_current_origin_keeps_later_data_refresh_and_never_contacts_railway():
    card, _ = native_card_and_status()
    calls = []
    def fetch(url, **kwargs):
        calls.append(url)
        return json.dumps(current_health()).encode(), {"x-hosting-origin": "hetzner-sin1"}, url
    result = release.verify_release(card, DIRECTORY.parents[3], fetch)
    assert "current native public origin" in result
    assert calls == [release.NATIVE_HEALTH_URL]


@pytest.mark.parametrize("mutation", ["redirect", "origin", "digest", "location"])
def test_native_live_check_rejects_wrong_route_or_substituted_evidence(mutation):
    card, _ = native_card_and_status()
    if mutation == "digest":
        card["metadata"]["nativeHostingReceiptSha256"] = "sha256:" + "0" * 64
    elif mutation == "location":
        card["metadata"]["nativeHostingReceipt"] = "https://attacker.example/receipt.json"
    def fetch(url, **kwargs):
        return (json.dumps(current_health()).encode(),
                {"x-hosting-origin": "railway" if mutation == "origin" else "hetzner-sin1"},
                release.HEALTH_URLS[0] if mutation == "redirect" else url)
    with pytest.raises(RuntimeError):
        release.verify_release(card, DIRECTORY.parents[3], fetch)
