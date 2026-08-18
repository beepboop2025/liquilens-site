"""Human and agent discovery surfaces stay crawlable and internally aligned."""

import json
import os
import re
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
    assert card["access"]["named_list"] == "https://liquilens.in/access/"
    assert card["access"]["named_list_sample"] == (
        "https://liquilens.in/access/sample/")
    assert card["access"]["pilot"] == "https://liquilens.in/pilot/"
    assert card["access"]["cli"] == (
        "https://github.com/beepboop2025/liquilens-cli")
    assert card["access"]["ai_catalog"] == (
        "https://liquilens.in/.well-known/ai-catalog.json")
    assert card["access"]["cli_evidence_command"] == "npx liquilens --record"
    assert card["updated"] == "2026-08-18"
    assert card["access"]["daily_articles"] == "https://liquilens.in/articles/"
    assert card["access"]["article_json_feed"] == (
        "https://liquilens.in/articles/feed.json")
    assert card["access"]["article_atom_feed"] == (
        "https://liquilens.in/articles/feed.xml")
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


def test_home_exposes_an_attributed_daily_brief_above_the_mobile_fold():
    home = read("index.html")
    hero = home[home.index('<div class="hero-actions">'):
                home.index('</div>', home.index('<div class="hero-actions">'))]
    telegram = "https://t.me/LiquiLens_bot?start=liquilens_home_hero"

    assert f'href="{telegram}"' in hero
    assert "Get 09:00 IST brief" in hero
    assert "daily failure radar · /stop any time" in hero
    assert 'target="_blank" rel="noopener noreferrer"' in hero
    assert hero.index(telegram) < hero.index('href="/replay/"')


def test_sitemap_excludes_cross_domain_undertow_mirrors():
    sitemap = read("sitemap.xml")
    assert "https://liquilens.in/undertow/" not in sitemap
    assert "https://liquilens.in/undertow/app/" not in sitemap


def test_contextual_product_network_is_visible_and_machine_readable():
    hub = "https://myquantdoesntspeakenglish.com/"
    home = read("index.html")
    card = json.loads(read("product-card.json"))
    assert hub in home
    assert hub in read("llms.txt")
    assert any(sibling["url"] == hub for sibling in card["siblings"])


def test_search_and_answer_crawlers_are_explicitly_welcome():
    robots = read("robots.txt")
    for agent in ("OAI-SearchBot", "ChatGPT-User", "Claude-SearchBot",
                  "Claude-User", "PerplexityBot", "Perplexity-User",
                  "Google-Extended", "Googlebot", "Bingbot"):
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
    app = read("developers/app.js")
    assert "https://api.liquilens.in/api/events" in app
    for token in (
        'MCP_PROTOCOL_VERSION = "2026-07-28"',
        '"Mcp-Method": "tools/call"',
        '"Mcp-Name": "failure_radar_board"',
        '"io.modelcontextprotocol/clientInfo"',
        '"io.modelcontextprotocol/clientCapabilities"',
        "MAX_MCP_RESPONSE_BYTES",
        "AbortController",
    ):
        assert token in app


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
    assert "https://liquilens.in/access/" in read("sitemap.xml")
    assert "https://liquilens.in/access/" in read("llms.txt")
    assert "INR 300,000 per year" in read("llms.txt")
    assert "INR 75,000" in read("llms.txt")

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
    assert mcp["version"] == "1.7.0"
    assert mcp["data"]["name"] == "io.github.beepboop2025/liquilens"
    assert mcp["data"]["version"] == mcp["version"]
    assert mcp["data"]["remotes"] == [
        {"type": "streamable-http", "url": "https://api.liquilens.in/mcp"}
    ]
    assert mcp["capabilities"] == [
        "corporate_transmission_board",
        "crypto_exposure_board",
        "crypto_regime_board",
        "evidence_europe",
        "evidence_india",
        "evidence_institution",
        "evidence_markets",
        "evidence_us",
        "failure_radar_board",
        "failure_radar_institution",
        "forward_odds",
        "household_credit_board",
        "institution_review_packet",
        "latest_article",
        "rbi_supervisory_tape",
        "stablecoin_rails_board",
        "universe_search",
        "verify_published_record",
    ]
    assert mcp["protocolVersions"] == [
        "2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26",
    ]
    assert mcp["prompts"] == [
        "crypto_liquidity_briefing",
        "failure_radar_briefing",
        "institution_health_check",
        "stress_evidence_pack",
    ]
    assert mcp["resourceTemplates"] == []
    assert mcp["metadata"]["publicToolCount"] == 18
    assert mcp["metadata"]["articleJsonFeed"] == (
        "https://liquilens.in/articles/feed.json")
    assert "latest_article" in mcp["capabilities"]
    for tool in ("crypto_regime_board", "stablecoin_rails_board",
                 "crypto_exposure_board"):
        assert tool in mcp["capabilities"]
    assert entries["urn:air:liquilens.in:catalog:seiche"]["version"] == "0.10.0"
    assert entries["urn:air:liquilens.in:catalog:undertow"]["version"] == "1.8.0"
    assert entries["urn:air:liquilens.in:openapi:failure-radar"]["version"] == (
        "1.0.0")
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
            "products": 10,
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
            "record_type": "prospective_forward_score",
        },
        "robustness": {"audit_records": 82556, "claim_blockers": 14},
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

    required_headline_copy = (
        "VALIDATED_NOT_COMPLETE",
        "ten-product replay pass",
        "421,620 evaluations",
        "5,273 canonical events",
        "413,828 exactly bound gap rows",
        "51,870 root causes",
        "82,556 robustness audit records",
        "4,146 genuine prospective forward",
        "0 of 7 requested products",
        "14 robustness claim blockers",
        "zero model changes",
    )
    for path in ("index.html", "status/index.html", "research/index.html",
                 "ship-log/index.html", "llms.txt"):
        surface = read(path)
        assert f"/{receipt_path}" in surface, path
        for token in required_headline_copy:
            assert token.lower() in surface.lower(), (path, token)

    required_provenance_copy = (
        "named-event coverage is 32 of 47 national jurisdictions",
        "15 have no named event rows",
        "4,191 verified event identities / 1,082 unresolved",
        "12 event-producing / 3 reviewed-no-event / 82 discovery-only",
        "1 supplemental event source",
    )
    for path in ("research/index.html", "llms.txt"):
        surface = read(path)
        visible_copy = re.sub(r"<[^>]+>", "", surface)
        for token in required_provenance_copy:
            assert token.lower() in visible_copy.lower(), (path, token)
    assert "https://liquilens.in/research/lab-reviewed-status-2026-08-09.json" \
        in read("sitemap.xml")


def test_ten_product_replay_atlas_reconciles_to_the_reviewed_receipt():
    atlas_path = "research/replay-atlas-2026-08-09.json"
    atlas = json.loads(read(atlas_path))
    receipt = json.loads(read("research/lab-reviewed-status-2026-08-09.json"))
    products = atlas["products"]

    assert atlas["schema"] == "liquilens.lab.replay-atlas.v1"
    assert atlas["status_id"] == receipt["status_id"]
    assert atlas["status"] == receipt["status"] == "VALIDATED_NOT_COMPLETE"
    assert atlas["definition_complete"] is False
    assert atlas["model_change_authorized"] is False
    assert len(products) == atlas["summary"]["products"] == 10
    assert [product["index"] for product in products] == list(range(1, 11))
    assert len({product["id"] for product in products}) == 10

    assert atlas["horizons_days"] == [30, 90, 180, 365]
    assert atlas["timing_conditions"] == ["baseline", "extra_lag"]
    assert atlas["extra_lag_days"] == 1
    assert atlas["event_checkpoints_per_product"] == 42162
    assert {product["evaluations"] for product in products} == {42162}
    assert atlas["summary"]["evaluations"] == 42162 * len(products)
    assert sum(product["evaluations"] for product in products) == 421620
    assert sum(product["gaps"] for product in products) == 413828
    assert sum(product["forward_records"] for product in products) == 4146
    assert sum(bool(product["forward_records"]) for product in products) == 3

    classification_names = {
        "captured_event": "captured",
        "correct_rejection": "correct_rejection",
        "false_positive": "false_positive",
        "missed_event": "missed",
        "not_applicable": "not_applicable",
        "unevaluable": "unevaluable",
    }
    for global_name, product_name in classification_names.items():
        assert sum(
            product["classifications"][product_name] for product in products
        ) == atlas["global_classifications"][global_name]
    for product in products:
        assert sum(product["classifications"].values()) == product["evaluations"]

    assert atlas["summary"]["events"] == receipt["replay"]["events"]
    assert atlas["summary"]["evaluations"] == receipt["replay"]["evaluations"]
    assert atlas["summary"]["gaps"] == receipt["replay"]["gaps"]
    assert atlas["summary"]["root_causes"] == receipt["replay"]["root_causes"]
    assert atlas["summary"]["robustness_records"] == receipt["robustness"]["audit_records"]
    assert atlas["summary"]["robustness_claim_blockers"] == receipt["robustness"]["claim_blockers"]
    assert atlas["summary"]["forward_records"] == receipt["forward_histories"]["forward_rows"]
    assert atlas["summary"]["retrospective_backtest_eligible_products"] == 0
    assert not any(atlas["claim_boundaries"].values())

    homepage = read("index.html")
    assert "42,162 checkpoints × 10 contracts" in homepage
    assert "not a count of unique product-event pairs, institutions, or backtests" \
        in homepage
    assert "8 passes" not in homepage

    for path in ("index.html", "research/index.html", "llms.txt",
                 "product-card.json", "sitemap.xml"):
        assert "replay-atlas-2026-08-09.json" in read(path), path


def test_every_discovery_pointer_uses_the_well_known_catalog():
    canonical = "https://liquilens.in/.well-known/ai-catalog.json"
    assert f"Agentmap: {canonical}" in read("robots.txt")
    assert 'rel="ai-catalog"' in read("index.html")
    assert canonical in read("llms.txt")
