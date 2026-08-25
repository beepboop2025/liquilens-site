"""The Evidence Desk is installable without making evidence appear offline-safe."""

import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def png_dimensions(path: str) -> tuple[int, int]:
    payload = (ROOT / path).read_bytes()
    assert payload[:8] == b"\x89PNG\r\n\x1a\n", path
    assert payload[12:16] == b"IHDR", path
    return struct.unpack(">II", payload[16:24])


def local_asset(url: str) -> str:
    assert url.startswith("/") and not url.startswith("//"), url
    return url.removeprefix("/")


def test_manifest_is_scoped_to_the_live_evidence_desk():
    manifest = json.loads(read("manifest.webmanifest"))
    assert manifest["id"] == "/evidence-desk/"
    assert manifest["start_url"] == "/evidence-desk/"
    assert manifest["scope"] == "/evidence-desk/"
    assert manifest["display"] == "standalone"
    assert manifest["categories"] == ["finance", "business", "productivity"]
    assert manifest["prefer_related_applications"] is False
    assert {shortcut["url"] for shortcut in manifest["shortcuts"]} == {
        "/evidence-desk/#query-heading",
        "/evidence-desk/#model-heading",
    }
    assert all(
        shortcut["url"].startswith(manifest["scope"])
        for shortcut in manifest["shortcuts"]
    )


def test_manifest_images_exist_and_match_declared_dimensions():
    manifest = json.loads(read("manifest.webmanifest"))
    images = manifest["icons"] + manifest["screenshots"]
    for image in images:
        path = local_asset(image["src"])
        declared = tuple(int(value) for value in image["sizes"].split("x"))
        assert (ROOT / path).is_file(), path
        assert png_dimensions(path) == declared, path
        assert image["type"] == "image/png"
    assert {image["form_factor"] for image in manifest["screenshots"]} == {
        "wide",
        "narrow",
    }


def test_page_links_manifest_and_explicitly_forbids_offline_evidence():
    page = read("evidence-desk/index.html")
    app = read("evidence-desk/app.mjs")
    assert '<link rel="manifest" href="/manifest.webmanifest">' in page
    assert '<meta name="theme-color" content="#f4f2e9">' in page
    assert "worker-src 'none'" in page
    assert "registers no service worker" in page
    assert "no offline evidence cache" in page
    assert "serviceWorker" not in app
    assert "caches.open" not in app
    assert not (ROOT / "service-worker.js").exists()
    assert not (ROOT / "sw.js").exists()
