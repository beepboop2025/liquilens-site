"""DPIIT startup recognition stays one verifiable fact across company surfaces.

The record lives in company-profile.json. Every other surface that repeats it
must carry the same certificate number and public verification page, and copy
must state it as a registration status rather than an approval of the products.
"""
from __future__ import annotations

import datetime
import importlib.util
import json
import pathlib
import re
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
CERTIFICATE = "DIPP290644"
VERIFY_URL = (
    "https://www.startupindia.gov.in/content/sih/en/startupgov/"
    "validate-startup-recognition.html"
)
CIN = "U62011RJ2026PTC116792"


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def profile_recognition() -> dict:
    company = json.loads(read("company-profile.json"))["company"]
    records = [row for row in company["recognitions"]
               if row["certificate_number"] == CERTIFICATE]
    assert len(records) == 1
    return records[0]


def organization_identifiers(relative: str) -> dict[str, dict]:
    source = read(relative)
    found: dict[str, dict] = {}
    for block in re.findall(
            r'<script type="application/ld\+json"[^>]*>(.*?)</script>',
            source, re.S):
        payload = json.loads(block)
        nodes = payload.get("@graph", [payload])
        for node in nodes:
            if node.get("@type") != "Organization":
                continue
            identifiers = node.get("identifier", [])
            if isinstance(identifiers, dict):
                identifiers = [identifiers]
            for row in identifiers:
                found[row["propertyID"]] = row
    return found


def test_profile_record_is_complete_and_bounded():
    record = profile_recognition()
    assert record["issuer"] == "DPIIT, Government of India (Startup India)"
    assert record["certificate_type"] == "Certificate of Recognition"
    datetime.date.fromisoformat(record["approved_on"])
    assert record["verification_url"] == VERIFY_URL
    assert CERTIFICATE in record["verification_method"]
    assert "not an endorsement, a licence or a regulatory approval" in record["scope"]
    assert record["tax_exemption"].startswith("Not claimed.")
    profile = json.loads(read("company-profile.json"))
    assert profile["updated"] >= record["approved_on"]
    assert profile["company"]["registration_number"] == CIN


def test_product_card_mirrors_the_profile_record():
    card = json.loads(read("product-card.json"))
    assert card["company"]["recognitions"] == (
        json.loads(read("company-profile.json"))["company"]["recognitions"])
    summary = card["product"]["startup_recognition"]
    assert CERTIFICATE in summary
    assert profile_recognition()["approved_on"] in summary
    assert "not a regulatory approval" in summary
    assert card["updated"] >= profile_recognition()["approved_on"]


def test_structured_identifiers_match_on_home_and_investor_pages():
    for page in ("index.html", "investors/index.html"):
        identifiers = organization_identifiers(page)
        assert identifiers["CIN"]["value"] == CIN, page
        dpiit = identifiers["DPIIT"]
        assert dpiit["value"] == CERTIFICATE, page
        assert dpiit["url"] == VERIFY_URL, page
        assert dpiit["@type"] == "PropertyValue", page


def test_investor_claim_register_cites_the_public_check():
    claims = json.loads(read("investors/claims.json"))
    rows = [row for row in claims["claims"] if CERTIFICATE in row.get("record", "")]
    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == "VERIFIED_COMPANY_RECORD"
    assert row["verification_url"] == VERIFY_URL
    assert "not an endorsement, a licence or a regulatory approval" in row["limit"]
    assert claims["updated"] >= profile_recognition()["approved_on"]


def test_reader_surfaces_name_the_certificate_and_its_limit():
    about = read("about/index.html")
    assert CERTIFICATE in about and VERIFY_URL in about
    assert "not an endorsement, a licence or a regulatory approval" in about
    llms = read("llms.txt")
    company_section = llms.split("## Company and connected products", 1)[1]
    company_section = company_section.split("\n## ", 1)[0]
    assert CERTIFICATE in company_section and VERIFY_URL in company_section
    assert "not a regulatory approval" in company_section
    for page in ("index.html", "investors/index.html"):
        assert "DPIIT recognised startup" in read(page), page


def test_no_surface_turns_recognition_into_an_approval():
    surfaces = ("index.html", "about/index.html", "investors/index.html",
                "llms.txt", "company-profile.json", "product-card.json",
                "investors/claims.json")
    for relative in surfaces:
        text = re.sub(r"<[^>]+>", " ", read(relative))
        for sentence in re.split(r"(?<=[.;])\s+", text):
            if "DPIIT" not in sentence and "Startup India" not in sentence:
                continue
            lowered = sentence.lower()
            assert not re.search(r"\b(endorsed|accredited|certified)\b", lowered), (
                relative, sentence)
            assert not re.search(r"\b(rbi|sebi)\b", lowered), (relative, sentence)
            if "approval" in lowered:
                assert re.search(r"\bnot\b", lowered), (relative, sentence)


def test_about_page_date_matches_its_sitemap_entry():
    about = read("about/index.html")
    shown = re.search(r"Updated (\d{1,2} [A-Z][a-z]+ \d{4})</div>", about)
    assert shown
    updated = datetime.datetime.strptime(shown.group(1), "%d %B %Y").date().isoformat()
    assert updated >= profile_recognition()["approved_on"]
    spec = importlib.util.spec_from_file_location(
        "build_replay_pages", ROOT / "scripts" / "build_replay_pages.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    configured = {row[0]: row[1] for row in module.BASE_SITEMAP}
    assert configured["/about/"] == updated
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    sitemap = ET.fromstring(read("sitemap.xml"))
    lastmods = {
        node.findtext("sm:loc", namespaces=namespace):
        node.findtext("sm:lastmod", namespaces=namespace)
        for node in sitemap.findall("sm:url", namespace)
    }
    assert lastmods["https://liquilens.in/about/"] == updated
    assert lastmods["https://liquilens.in/"] == configured["/"]
