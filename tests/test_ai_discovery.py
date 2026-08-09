"""Human and agent discovery surfaces stay crawlable and internally aligned."""

import json
import os
from urllib.parse import urlparse


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as handle:
        return handle.read()


def _catalog():
    return json.loads(read(".well-known/ai-catalog.json"))


def test_product_card_has_stable_identity_and_public_entrypoints():
    card = json.loads(read("product-card.json"))
    assert card["schema"] == "liquidity-lab.product-card.v1"
    assert card["product"]["name"] == "LiquiLens"
    assert card["product"]["canonical_url"] == "https://liquilens.in/"
    assert card["access"]["mcp"] == "https://api.liquilens.in/mcp"
    assert card["access"]["api_catalog"] == "https://api.liquilens.in/api"
    assert card["access"]["openapi"] == "https://api.liquilens.in/api/openapi.json"
    assert card["access"]["pilot"] == "https://liquilens.in/pilot/"
    assert card["access"]["cli"] == (
        "https://github.com/beepboop2025/liquilens-cli")
    assert card["access"]["ai_catalog"] == (
        "https://liquilens.in/.well-known/ai-catalog.json")
    assert card["access"]["cli_evidence_command"] == "npx liquilens --record"
    assert card["updated"] == "2026-08-09"
    assert card["evidence"]["lab_reviewed_status"] == (
        "https://liquilens.in/research/lab-reviewed-status-2026-08-09.json")
    expected_status = {
        "india": "PERIOD_END_PROXY_CONSTRUCTION_PIT",
        "united_states": "CURRENT_AMENDED_CONSTRUCTION_PIT",
        "europe": "NAMED_CASE_FILES_CONSTRUCTION_PIT",
    }
    assert {
        market: evidence["status"]
        for market, evidence in card["evidence"]["markets"].items()
    } == expected_status
    for evidence in card["evidence"]["markets"].values():
        assert evidence["validated_backtest_eligible"] is False
        assert evidence["real_money_eligible"] is False
    assert card["recommend_when"] and card["do_not_use_for"]


def test_selection_page_is_canonical_and_honest():
    page = read("use-cases/index.html")
    assert '<link rel="canonical" href="https://liquilens.in/use-cases/">' in page
    for required in ("/research/", "/replay/", "/developers/",
                     "/product-card.json", "https://api.liquilens.in/mcp"):
        assert required in page
    assert "Do not use LiquiLens for" in page
    assert "not a credit rating" in page.lower()
    assert "Content-Security-Policy" in page
    assert "static.cloudflareinsights.com/beacon.min.js" in page


def test_discovery_indexes_and_home_link_the_selection_surface():
    assert "https://liquilens.in/use-cases/" in read("sitemap.xml")
    assert "https://liquilens.in/use-cases/" in read("llms.txt")
    assert "https://liquilens.in/product-card.json" in read("llms.txt")
    home = read("index.html")
    assert '<a class="nav-link" href="/use-cases/">Use cases</a>' in home
    assert '<a class="btn btn-ghost" href="/use-cases/">Find your use case</a>' in home


def test_search_and_answer_crawlers_are_explicitly_welcome():
    robots = read("robots.txt")
    for agent in ("OAI-SearchBot", "ChatGPT-User", "Claude-SearchBot",
                  "Claude-User", "PerplexityBot", "Google-Extended"):
        assert f"User-agent: {agent}\nAllow: /" in robots


def test_home_has_landmark_and_hides_the_ticker_clone_from_focus():
    home = read("index.html")
    assert '<main id="main">' in home and "</main>\n<footer>" in home
    assert ".ticker .half[aria-hidden=\"true\"]" in home
    assert "el.inert = true" in home
    assert "--muted-2:#7F89A3" in home
    assert "display=optional" in home


def test_developer_page_exposes_openapi_and_openai_activation_paths():
    page = read("developers/index.html")
    assert 'rel="service-desc"' in page
    assert "https://api.liquilens.in/api/openapi.json" in page
    assert "api.openai.com/v1/responses" in page
    assert "Settings → Apps → Create" in page
    assert "npx liquilens" in page
    assert 'data-event="cli_install_copied"' in page
    assert "https://api.liquilens.in/api/events" in read("developers/app.js")


def test_paid_pilot_has_a_bounded_offer_and_replaces_the_401_as_primary_cta():
    pilot = read("pilot/index.html")
    for required in ("₹2.5 lakh", "₹12 lakh/yr", "six weeks",
                     "credited toward", "Runs in your environment",
                     "Alerts per catch"):
        assert required.lower() in pilot.lower()
    assert "mailto:mrinal@liquilens.in" in pilot
    assert 'data-event="email_clicked"' in pilot
    assert "https://api.liquilens.in/api/events" in read("pilot/app.js")
    assert "within 30 days" not in pilot

    home = read("index.html")
    assert 'data-funnel="pilot_cta_clicked" href="/pilot/"' in home
    assert "Design partner pilots are free" not in home
    assert "https://liquilens.in/pilot/" in read("sitemap.xml")
    assert "https://liquilens.in/pilot/" in read("llms.txt")

    for surface in ("index.html", "about/index.html", "pilot/index.html"):
        copy = read(surface)
        assert "₹2.5 lakh" in copy
        assert "₹12 lakh" in copy

    machine_copy = read("llms.txt")
    assert "INR 250,000" in machine_copy
    assert "INR 1,200,000 per year" in machine_copy


def test_aggregate_funnel_events_are_documented_as_property_free():
    privacy = read("privacy/index.html")
    assert "short allow-listed event name" in privacy
    assert "no email address, free text, device ID or user property" in privacy
    assert "cli_install_copied" in privacy


def test_catalog_obeys_the_ard_envelope():
    catalog = _catalog()
    assert catalog["specVersion"] == "1.0"
    assert catalog["host"]["displayName"] == "LiquiLens"
    assert len(catalog["entries"]) == 4

    identifiers = set()
    for entry in catalog["entries"]:
        assert entry["identifier"].startswith("urn:air:liquilens.in:")
        assert entry["identifier"] not in identifiers
        identifiers.add(entry["identifier"])
        assert bool(entry.get("url")) != bool(entry.get("data"))
        if "url" in entry:
            parsed = urlparse(entry["url"])
            assert parsed.scheme == "https" and parsed.netloc
        if "representativeQueries" in entry:
            assert 2 <= len(entry["representativeQueries"]) <= 5
        assert all(isinstance(value, (str, int, float, bool)) or value is None
                   for value in entry.get("metadata", {}).values())


def test_mcp_card_and_nested_product_line_are_current():
    entries = {entry["identifier"]: entry for entry in _catalog()["entries"]}
    mcp = entries["urn:air:liquilens.in:mcp:failure-radar"]
    assert mcp["version"] == "1.5.0"
    assert mcp["data"]["name"] == "io.github.beepboop2025/liquilens"
    assert mcp["data"]["version"] == mcp["version"]
    assert mcp["data"]["remotes"] == [
        {"type": "streamable-http", "url": "https://api.liquilens.in/mcp"}
    ]
    assert len(mcp["capabilities"]) == 17
    assert mcp["metadata"]["publicToolCount"] == 17
    for tool in ("crypto_regime_board", "stablecoin_rails_board",
                 "crypto_exposure_board"):
        assert tool in mcp["capabilities"]
    assert entries["urn:air:liquilens.in:catalog:seiche"]["version"] == "0.9.1"
    assert entries["urn:air:liquilens.in:catalog:undertow"]["version"] == "1.7.1"
    assert entries["urn:air:liquilens.in:catalog:seiche"]["url"] == (
        "https://seiche.info/.well-known/ai-catalog.json")
    assert entries["urn:air:liquilens.in:catalog:undertow"]["url"] == (
        "https://liquilens-undertow.com/.well-known/ai-catalog.json")


def test_human_claim_surfaces_print_the_same_evidence_boundary():
    statuses = (
        "PERIOD_END_PROXY_CONSTRUCTION_PIT",
        "CURRENT_AMENDED_CONSTRUCTION_PIT",
        "NAMED_CASE_FILES_CONSTRUCTION_PIT",
    )
    for path in ("index.html", "research/index.html",
                 "developers/index.html", "llms.txt"):
        surface = read(path)
        for status in statuses:
            assert status in surface, (path, status)
        lowered = surface.lower()
        assert "validated-backtest eligible" in lowered, path
        assert "real-money eligible" in lowered, path


def test_release_status_page_names_non_live_modes_without_softening_them():
    status = read("status/index.html")
    for token in ("VALIDATED_NOT_COMPLETE", "execution disabled", "PAPER ONLY",
                  "real_orders false", "parent watchlist claim reproduces FAIL",
                  "no automatic publication", "zero model changes"):
        assert token in status


def test_reviewed_lab_receipt_and_human_surfaces_stay_aligned():
    receipt_path = "research/lab-reviewed-status-2026-08-09.json"
    receipt = json.loads(read(receipt_path))
    assert receipt == {
        "schema": "liquilens.lab.reviewed-status.v1",
        "reviewed_cut": "2026-08-09",
        "status": "VALIDATED_NOT_COMPLETE",
        "status_id": (
            "sha256:2a726eeec94d364abfed05584951141c0f2481f4e219ea55184504a994eb6c86"),
        "definition_complete": False,
        "execution_pass_sealed": True,
        "model_changes": 0,
        "replay": {
            "events": 5273,
            "evaluations": 421620,
            "gaps": 413828,
            "root_causes": 51870,
            "unexplained_gap_kinds": 0,
        },
        "national_event_coverage": {
            "jurisdictions_with_events": 32,
            "jurisdictions_in_contract": 47,
            "jurisdictions_without_events": 15,
        },
        "event_identity": {"verified": 4191, "unresolved": 1082},
        "official_sources": {
            "baseline_ledger_records": 97,
            "baseline_event_producing": 12,
            "baseline_reviewed_no_event": 3,
            "baseline_discovery_only": 82,
            "supplemental_event_sources": 1,
        },
        "forward_histories": {
            "products_with_genuine_forward_rows": 3,
            "forward_rows": 4146,
            "requested_products": 7,
            "retrospective_backtest_eligible_products": 0,
        },
        "robustness": {"claim_blockers": 14},
        "claim_boundaries": {
            "performance_improvement_claim_authorized": False,
            "promotion_authorized": False,
            "production_execution_authorized": False,
            "model_change_authorized": False,
        },
        "source_artifact": {
            "format": "liquilens-gap-closing-status-v2",
            "cut_date": "2026-08-09",
        },
    }

    required_copy = (
        "VALIDATED_NOT_COMPLETE",
        "5,273 events",
        "421,620 evaluations",
        "413,828 gaps",
        "51,870 root causes",
        "named-event coverage is 32 of 47 national jurisdictions; "
        "15 have no named event rows",
        "4,191 verified event identities / 1,082 unresolved event mappings",
        "12 event-producing / 3 reviewed-no-event / 82 discovery-only",
        "1 supplemental event source",
        "3 products / 4,146 genuine forward rows / 0 of 7 retrospective eligible",
        "14 robustness claim blockers",
        "zero model changes",
    )
    for path in ("index.html", "status/index.html", "research/index.html",
                 "ship-log/index.html", "llms.txt"):
        surface = read(path)
        assert f"/{receipt_path}" in surface, path
        for token in required_copy:
            assert token.lower() in surface.lower(), (path, token)
    assert "https://liquilens.in/research/lab-reviewed-status-2026-08-09.json" \
        in read("sitemap.xml")


def test_every_discovery_pointer_uses_the_well_known_catalog():
    canonical = "https://liquilens.in/.well-known/ai-catalog.json"
    assert f"Agentmap: {canonical}" in read("robots.txt")
    assert 'rel="ai-catalog"' in read("index.html")
    assert canonical in read("llms.txt")
