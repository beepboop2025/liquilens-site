"""Current discovery must not inherit acceptance from an older application."""

import hashlib
import json
import subprocess
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SIGNER = "fleet-owner ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBuJV6o8YL2XXR9q4vcwpHuc2z1GEBawSmrJWGrgwzFV\n"


def local_public_file(url):
    parsed = urlparse(url)
    assert parsed.scheme == "https" and parsed.netloc == "liquilens.in"
    path = ROOT / parsed.path.lstrip("/")
    assert path.resolve().is_relative_to(ROOT)
    return path


def test_current_application_acceptance_cannot_inherit_historical_recovery(tmp_path):
    catalog = json.loads((ROOT / ".well-known/ai-catalog.json").read_text())
    current = next(e for e in catalog["entries"] if e["identifier"].endswith(":seiche"))
    meta = current["metadata"]
    receipt_path = local_public_file(meta["releaseAcceptanceReceipt"])
    signature_path = local_public_file(meta["releaseAcceptanceSignature"])
    for field, path in (("releaseAcceptanceReceipt", receipt_path), ("releaseAcceptanceSignature", signature_path)):
        assert meta[field + "Sha256"] == "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    receipt = json.loads(receipt_path.read_bytes())
    assert receipt["schema"] == "seiche.application-and-distribution-discovery-acceptance.v1"
    assert receipt["version"] == current["version"] == "0.13.2"
    assert receipt["source"] == meta["releaseCommit"] == "1deccedc16dc832f6c0bdef61a0426e4b9b2d9eb"
    assert receipt["signed_tag_object"] == meta["signedTagObject"]
    assert receipt["status"] == "PASS"
    assert receipt["distribution_state"] == meta["distributionState"] == "verified"
    assert receipt["recovery_accepted"] is meta["recoveryAccepted"] is False
    assert receipt["full_release_accepted"] is meta["fullReleaseAccepted"] is False
    assert meta["recoveryState"] == "user_deferred"
    assert receipt["recovery_status"] == "USER_DEFERRED_RECOVERY_AND_VOLUME_RESIZE"
    assert meta["scheduledRecoveryAttestation"] == "held_for_current_application"
    assert not {"recoveryRun", "recoveryReceiptSha256", "offsiteReceiptSha256"}.intersection(meta)
    prior = receipt["historical_release_acceptance"]
    assert prior["version"] == meta["historicalReleaseVersion"] == "0.13.1"
    assert prior["source"] == meta["historicalReleaseCommit"] != receipt["source"]
    assert prior["receipt"] == meta["historicalReleaseAcceptanceReceipt"]
    assert prior["sha256"] == meta["historicalReleaseAcceptanceReceiptSha256"]
    assert prior["sha256"] == "sha256:" + hashlib.sha256(local_public_file(prior["receipt"]).read_bytes()).hexdigest()
    assert receipt["archive"]["source"] == receipt["source"]
    assert receipt["archive"]["doi"] == meta["archiveDoi"] == "10.5281/zenodo.22732023"
    assert receipt["archive"]["source_file_count"] == meta["archiveSourceFileCount"] == 1126
    assert receipt["registry"]["version"] == current["version"]
    for kind, suffix in (("Wheel", ".whl"), ("Sdist", ".tar.gz")):
        artifact = next(f for f in receipt["pypi_files"] if f["filename"].endswith(suffix))
        assert meta["pypi" + kind + "Sha256"] == "sha256:" + artifact["sha256"]
        assert meta["pypi" + kind + "Bytes"] == artifact["bytes"]
    signers = tmp_path / "allowed_signers"
    signers.write_text(SIGNER)
    subprocess.run(["ssh-keygen", "-Y", "verify", "-f", str(signers), "-I", "fleet-owner", "-n", "seiche-connected-release-acceptance", "-s", str(signature_path)], input=receipt_path.read_bytes(), check=True, capture_output=True)
    card = json.loads((ROOT / "product-card.json").read_text())
    sibling = next(s for s in card["siblings"] if s["name"] == "Seiche")
    assert sibling["version"] == current["version"]
    assert sibling["release_commit"] == receipt["source"]
    assert sibling["recovery_accepted"] is False
    assert sibling["full_release_accepted"] is False
    assert sibling["release_acceptance_receipt"] == meta["releaseAcceptanceReceipt"]


def test_palimpsest_download_discovery_retains_per_dataset_rights_boundary():
    catalog = json.loads((ROOT / ".well-known/ai-catalog.json").read_text())
    pal = next(e for e in catalog["entries"] if e["identifier"].endswith(":palimpsest-china"))
    assert pal["metadata"]["publicDataCatalog"] == "https://www.palimpsest.info/readings/public-data-catalog-latest.json"
    assert "restricted data has no public download" in pal["metadata"]["publicDataCatalogBoundary"]
    assert pal["metadata"]["publicResourceCount"] == 1
