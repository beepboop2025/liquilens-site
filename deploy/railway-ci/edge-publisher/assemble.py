"""Assemble only signed controller blobs and their pinned verifier inputs."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
GATES = ("scripts/verify_catalog_edge.py", "scripts/verify_financial_evidence_semantics.py",
         "scripts/verify_narcoscope_release.py", "scripts/verify_palimpsest_release.py")
PINS = GATES + (".github/workflows/deploy-catalog-edge.yml", "wrangler.catalog.jsonc",
                "deploy/railway-ci/run.sh")
OWNER_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBuJV6o8YL2XXR9q4vcwpHuc2z1GEBawSmrJWGrgwzFV"

parser = argparse.ArgumentParser()
parser.add_argument("output", type=Path)
args = parser.parse_args()
source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
with tempfile.TemporaryDirectory(prefix="catalog-controller-signature-") as directory:
    signers = Path(directory) / "allowed_signers"
    signers.write_text("* " + OWNER_KEY + "\n")
    subprocess.run(["git", "-c", "gpg.ssh.allowedSignersFile=" + str(signers),
                    "verify-commit", source], cwd=ROOT, check=True)


def blob(name):
    return subprocess.check_output(["git", "show", source + ":" + name], cwd=ROOT)


args.output.mkdir(parents=True, exist_ok=False)
for name in ("Dockerfile", "entry.py", "publish.py", "isolation.py", "verify.py", "test_publish.py"):
    (args.output / name).write_bytes(blob("deploy/railway-ci/edge-publisher/" + name))
(args.output / "gates").mkdir()
for name in GATES:
    (args.output / "gates" / Path(name).name).write_bytes(blob(name))
(args.output / "pins.json").write_text(json.dumps(
    {name: hashlib.sha256(blob(name)).hexdigest() for name in PINS}, indent=2) + "\n")
(args.output / "controller-source.json").write_text(json.dumps({
    "sha": source, "signer": "SHA256:yhoa/PIDMM6M/ZennILp8jtRJy5pArncJRARbQssTMI",
}, indent=2) + "\n")
print(args.output)
