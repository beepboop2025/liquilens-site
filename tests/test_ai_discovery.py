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
    assert card["access"]["early_warning_coverage_check"] == (
        "https://liquilens.in/tools/ews-coverage-check/")
    assert card["access"]["rbi_nbfc_ews_guide"] == (
        "https://liquilens.in/guides/rbi-nbfc-early-warning-system/")
    assert card["access"]["named_list_sample"] == (
        "https://liquilens.in/access/sample/")
    assert card["access"]["pilot"] == "https://liquilens.in/pilot/"
    assert card["access"]["cli"] == (
        "https://github.com/beepboop2025/liquilens-cli")
    assert card["access"]["ai_catalog"] == (
        "https://liquilens.in/.well-known/ai-catalog.json")
    assert card["access"]["world_economy_evidence_map"] == (
        "https://liquilens.in/world-economy/")
    assert card["access"]["world_economy_dataset_catalog"] == (
        "https://liquilens.in/world-economy/evidence-catalog.json")
    assert card["access"]["evidence_carrier"] == (
        "https://liquilens.in/protocol/")
    assert card["access"]["evidence_carrier_catalog"] == (
        "https://liquilens.in/protocol/catalog.json")
    assert card["access"]["evidence_carrier_browser_verifier"] == (
        "https://beepboop2025.github.io/liquilens-evidence-carrier/")
    assert card["access"]["cli_evidence_command"] == "npx liquilens --record"
    assert card["updated"] == "2026-09-05"
    assert card["access"]["api_catalog_discovery"] == (
        "https://liquilens.in/.well-known/api-catalog")
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
    assert '<a class="btn btn-ghost" href="/banking/">Research a bank for free</a>' in home
    assert 'https://liquilens.in/banking/' in read("sitemap.xml")
    assert 'https://liquilens.in/banking/' in read("llms.txt")


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
    assert "Content-Signal: search=yes, ai-input=yes, ai-train=no" in robots
    for agent in ("OAI-SearchBot", "ChatGPT-User", "Claude-SearchBot",
                  "Claude-User", "PerplexityBot", "Perplexity-User",
                  "Google-Extended", "Googlebot", "Bingbot"):
        assert f"User-agent: {agent}\nAllow: /" in robots
    for training_agent in ("GPTBot", "ClaudeBot", "anthropic-ai", "CCBot",
                           "Applebot-Extended"):
        assert f"User-agent: {training_agent}\nAllow: /" not in robots


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
    for required in ("Ask the founder", "Write the founder", "six weeks",
                     "credited toward", "Runs in your environment",
                     "Alerts per catch"):
        assert required.lower() in pilot.lower()
    assert "₹2.5 lakh" not in pilot
    assert "₹12 lakh" not in pilot
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
    assert "no list price" in read("llms.txt")
    assert "mrinal@liquilens.in" in read("llms.txt")
    assert "INR 300,000 per year" not in read("llms.txt")
    assert "INR 75,000" not in read("llms.txt")

    for surface in ("index.html", "about/index.html", "pilot/index.html"):
        copy = read(surface)
        assert "₹2.5 lakh" not in copy
        assert "₹12 lakh" not in copy

    machine_copy = read("llms.txt")
    assert "INR 250,000" not in machine_copy
    assert "INR 1,200,000 per year" not in machine_copy


def test_aggregate_funnel_events_are_documented_as_property_free():
    privacy = read("privacy/index.html")
    assert "short allow-listed event name" in privacy
    assert "no email address, free text, device ID or user property" in privacy
    assert "cli_install_copied" in privacy
    assert "homepage, use-case, developer, named-list, pilot and free-tool" in privacy


def test_homepage_schema_matches_the_institutional_product_boundary():
    home = read("index.html")
    blocks = re.findall(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>', home,
        flags=re.S,
    )
    graph = json.loads(blocks[0])["@graph"]
    software = next(row for row in graph if row.get("@type") == "SoftwareApplication")

    assert "offers" not in software
    audience = software["audience"]["audienceType"]
    for segment in (
        "Regulated financial institutions",
        "asset managers",
        "accounting and advisory firms",
        "market-data platforms",
    ):
        assert segment in audience
    assert "MSMEs sitting on idle cash" not in home
    assert "Indian businesses managing idle cash" not in home


def test_catalog_obeys_the_ard_envelope():
    catalog = _catalog()
    assert catalog["specVersion"] == "1.0"
    assert catalog["host"]["displayName"] == "LiquiLens"
    assert len(catalog["entries"]) == 18

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
    assert mcp["version"] == "1.8.0"
    assert mcp["data"]["name"] == "io.github.beepboop2025/liquilens"
    assert mcp["data"]["version"] == mcp["version"]
    assert mcp["data"]["remotes"] == [
        {"type": "streamable-http", "url": "https://api.liquilens.in/mcp"}
    ]
    assert mcp["capabilities"] == [
        "bank_asset_quality_review",
        "bank_npa_reconciliation",
        "banking_specialisation_coverage",
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
        "bank_asset_quality_brief",
        "crypto_liquidity_briefing",
        "failure_radar_briefing",
        "institution_health_check",
        "stress_evidence_pack",
    ]
    assert mcp["resourceTemplates"] == []
    assert mcp["metadata"]["publicToolCount"] == 21
    assert mcp["metadata"]["articleJsonFeed"] == (
        "https://liquilens.in/articles/feed.json")
    assert "latest_article" in mcp["capabilities"]
    for tool in ("crypto_regime_board", "stablecoin_rails_board",
                 "crypto_exposure_board"):
        assert tool in mcp["capabilities"]
    assert entries["urn:air:liquilens.in:catalog:seiche"]["version"] == "0.11.1"
    assert entries["urn:air:liquilens.in:catalog:undertow"]["version"] == "1.10.0"
    assert entries["urn:air:liquilens.in:openapi:failure-radar"]["version"] == (
        "1.0.0")
    assert entries["urn:air:liquilens.in:catalog:seiche"]["url"] == (
        "https://seiche.info/.well-known/ai-catalog.json")
    assert entries["urn:air:liquilens.in:catalog:seiche"]["metadata"][
        "publicToolCount"] == 11
    assert entries["urn:air:liquilens.in:catalog:seiche"]["metadata"][
        "globalMoneyMarketAtlas"] == (
            "https://api.seiche.info/api/v2/money-markets")
    assert entries["urn:air:liquilens.in:catalog:seiche"]["metadata"][
        "worldMarketsApi"] == "https://api.seiche.info/api/v2/world-markets"
    assert entries["urn:air:liquilens.in:catalog:seiche"]["metadata"][
        "worldMarketsPage"] == "https://seiche.info/markets/"
    assert entries[
        "urn:air:liquilens.in:catalog:world-economy-evidence"
    ]["url"] == "https://liquilens.in/world-economy/evidence-catalog.json"
    assert entries["urn:air:liquilens.in:catalog:undertow"]["url"] == (
        "https://liquilens-undertow.com/.well-known/ai-catalog.json")


def test_seiche_discovery_contract_and_distribution_receipts_are_exact():
    entries = {entry["identifier"]: entry for entry in _catalog()["entries"]}
    seiche = entries["urn:air:liquilens.in:catalog:seiche"]

    assert seiche["version"] == "0.11.1"
    assert seiche["updatedAt"] == "2026-08-24T14:52:00Z"
    assert seiche["capabilities"] == [
        "latest_article",
        "funding_stress_now",
        "historical_analogs",
        "proof_backtest",
        "data_health",
        "crypto_stress_record",
        "institutional_flows",
        "oil_funding_context",
        "fx_materials_passage",
        "money_market_context",
        "world_markets_context",
    ]
    assert seiche["prompts"] == [
        "is_now_dangerous",
        "money_market_deep_dive",
        "world_markets_briefing",
        "cross_market_cash_pressure",
    ]
    assert seiche["resourceTemplates"] == []
    assert {
        key: seiche["metadata"][key]
        for key in (
            "publicToolCount",
            "publicPromptCount",
            "publicResourceCount",
            "mcpServerName",
            "mcpEndpoint",
            "mcpDiscovery",
            "apiCatalog",
            "openapi",
            "productCard",
            "pypiProject",
            "pypiSpec",
            "releaseCommit",
            "signedTag",
            "signedTagObject",
            "pypiRun",
            "pypiWheelSha256",
            "pypiWheelBytes",
            "pypiSdistSha256",
            "pypiSdistBytes",
            "staticRun",
            "staticDeployment",
            "catalogSha256",
            "productCardSha256",
            "mcpDiscoverySha256",
            "registryRun",
            "registryVersion",
            "registryPublishedAt",
            "registryServerSha256",
            "liveVersionAuthority",
        )
    } == {
        "publicToolCount": 11,
        "publicPromptCount": 4,
        "publicResourceCount": 0,
        "mcpServerName": "io.github.beepboop2025/seiche",
        "mcpEndpoint": "https://api.seiche.info/mcp",
        "mcpDiscovery": "https://api.seiche.info/.well-known/mcp.json",
        "apiCatalog": "https://api.seiche.info/api",
        "openapi": "https://api.seiche.info/api/openapi.json",
        "productCard": "https://seiche.info/product-card.json",
        "pypiProject": "https://pypi.org/project/seiche/0.11.1/",
        "pypiSpec": "seiche==0.11.1",
        "releaseCommit": "0cd20bfd0a4d274c8bb8173f6fe59e2d2f5259db",
        "signedTag": "v0.11.1",
        "signedTagObject": "fc1742880be1be06837c5fc703b4ba5312ff4b2b",
        "pypiRun": (
            "https://github.com/beepboop2025/seiche/actions/runs/"
            "32758138386/attempts/2"
        ),
        "pypiWheelSha256": (
            "sha256:01b5b770d88391d31ba406ca651ab5d6054b2e4c6f6c3cf6138f713f4374e4a1"
        ),
        "pypiWheelBytes": 1101154,
        "pypiSdistSha256": (
            "sha256:0fa965b00f0c81a5f9ad8a5d66a4140523a90f962f3bdcf196fd884d89057a15"
        ),
        "pypiSdistBytes": 980967,
        "staticRun": (
            "https://github.com/beepboop2025/seiche/actions/runs/32758837757"
        ),
        "staticDeployment": "https://699fdc4e.seiche.pages.dev",
        "catalogSha256": (
            "sha256:735516115752afebd3b8a3637a22f806ff8f592826381ce1bbe32ab5b7b5cc74"
        ),
        "productCardSha256": (
            "sha256:1d382ad21d4fa8c35433f9270946d74dca592fb833c454c02cc3613a6c2edf08"
        ),
        "mcpDiscoverySha256": (
            "sha256:1db329dbc3155a0a695a3ddf7e7dcd37d7edaea22d4898b97002cbf172c931fe"
        ),
        "registryRun": (
            "https://github.com/beepboop2025/seiche/actions/runs/32758834990"
        ),
        "registryVersion": (
            "https://registry.modelcontextprotocol.io/v0.1/servers/"
            "io.github.beepboop2025%2Fseiche/versions/0.11.1"
        ),
        "registryPublishedAt": "2026-08-24T17:50:12.865984Z",
        "registryServerSha256": (
            "sha256:2a7a82905c2466684fdf61de0862a5dbfb9b1d2703918c88a594d0017dd8b6f1"
        ),
        "liveVersionAuthority": (
            "Initialize the linked MCP remote and compare serverInfo.version "
            "before treating a release as deployed."
        ),
    }


def test_undertow_and_palimpsest_discovery_contracts_are_exact():
    entries = {entry["identifier"]: entry for entry in _catalog()["entries"]}

    undertow = entries["urn:air:liquilens.in:catalog:undertow"]
    assert undertow["version"] == "1.10.0"
    assert undertow["updatedAt"] == "2026-09-02T00:00:00Z"
    assert undertow["capabilities"] == [
        "agent_access_status",
        "depth_episodes",
        "exit_cost",
        "latest_article",
        "liquidity_tiers",
        "sealed_record",
        "trade_safety_exit_context",
        "unwind_watch",
        "venue_concentration",
        "venue_price_reconciliation",
    ]
    assert undertow["protocolVersions"] == [
        "2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26",
    ]
    assert undertow["prompts"] == [
        "can_this_book_exit",
        "exit_cost_check",
        "market_liquidity_briefing",
    ]
    assert undertow["resourceTemplates"] == []
    assert {
        key: undertow["metadata"][key]
        for key in (
            "publicToolCount",
            "subscriberToolCount",
            "publicPromptCount",
            "publicResourceCount",
            "mcpServerName",
            "mcpEndpoint",
            "openapi",
            "productCard",
        )
    } == {
        "publicToolCount": 10,
        "subscriberToolCount": 8,
        "publicPromptCount": 3,
        "publicResourceCount": 0,
        "mcpServerName": "io.github.beepboop2025/undertow",
        "mcpEndpoint": "https://api.seiche.info/undertow/mcp",
        "openapi": "https://api.seiche.info/undertow/x402/openapi.json",
        "productCard": "https://liquilens-undertow.com/product-card.json",
    }

    palimpsest = entries["urn:air:liquilens.in:catalog:palimpsest-china"]
    assert palimpsest["version"] == "1.9.3"
    assert palimpsest["updatedAt"] == "2026-08-29T14:47:02.39659Z"
    assert palimpsest["capabilities"] == [
        "list_signals",
        "get_signal",
        "get_newsroom",
        "query_economic_observations",
        "whats_happening",
        "gfw_reading",
    ]
    assert palimpsest["protocolVersions"] == ["2025-06-18", "2025-03-26"]
    assert palimpsest["prompts"] == [
        "evidence_desk_briefing",
        "censorship_briefing",
        "gfw_status_check",
        "signal_deep_dive",
    ]
    assert palimpsest["resourceTemplates"] == []
    assert palimpsest["resources"] == [
        "palimpsest://china-economic/publication-rights"
    ]
    assert {
        key: palimpsest["metadata"][key]
        for key in (
            "publicToolCount",
            "publicPromptCount",
            "publicResourceCount",
            "mcpServerName",
            "mcpEndpoint",
            "deploymentBoundary",
            "deploymentCommit",
            "deploymentReceipt",
            "deploymentReceiptSha256",
            "deploymentRun",
            "registryReceipt",
            "registryReceiptSha256",
            "registryRun",
            "registrySnapshot",
            "registrySnapshotSha256",
            "registryVersion",
            "registryPublishedAt",
            "liveVersionAuthority",
            "quickstart",
            "productCard",
        )
    } == {
        "publicToolCount": 6,
        "publicPromptCount": 4,
        "publicResourceCount": 1,
        "mcpServerName": "io.github.beepboop2025/palimpsest",
        "mcpEndpoint": "https://api.seiche.info/palimpsest/mcp",
        "deploymentBoundary": "production-verified",
        "deploymentCommit": "1b71dd2bb2dcdec0b99691f7d4caaa13c4857574",
        "deploymentReceipt": (
                "https://palimpsest.info/.well-known/receipts/"
            "mcp-deployment-1.9.3.json"
        ),
        "deploymentReceiptSha256": (
            "sha256:db370a46897b58d32e31561f1e664d68ea053ac38454caa58b52dd4c9ba5e834"
        ),
        "deploymentRun": (
            "https://github.com/beepboop2025/palimpsest/actions/runs/33258332928"
        ),
        "registryReceipt": (
                "https://palimpsest.info/.well-known/receipts/"
            "mcp-registry-publication-1.9.3.json"
        ),
        "registryReceiptSha256": (
            "sha256:d9f153a99b52b686995e22e378fcd1383335d0f74c175932d4dfd6d70147b4f5"
        ),
        "registryRun": (
            "https://github.com/beepboop2025/palimpsest/actions/runs/33258465637"
        ),
        "registrySnapshot": (
                "https://palimpsest.info/.well-known/receipts/"
            "mcp-registry-latest-1.9.3.json"
        ),
        "registrySnapshotSha256": (
            "sha256:b242bf50ef87441222ac2b3b9103b99d4fad44d52dd5b119a500ee13d4508287"
        ),
        "registryVersion": (
            "https://registry.modelcontextprotocol.io/v0.1/servers/"
            "io.github.beepboop2025%2Fpalimpsest/versions/1.9.3"
        ),
        "registryPublishedAt": "2026-08-29T14:47:02.39659Z",
        "liveVersionAuthority": (
            "Initialize the linked MCP remote and compare serverInfo.version "
            "before treating a release as deployed."
        ),
        "quickstart": "https://palimpsest.info/developers.html",
        "productCard": "https://palimpsest.info/product-card.json",
    }


def test_sibling_product_cards_match_the_catalog_contracts():
    siblings = {
        sibling["name"]: sibling
        for sibling in json.loads(read("product-card.json"))["siblings"]
    }
    seiche = siblings["Seiche"]
    assert {
        key: seiche[key]
        for key in (
            "version",
            "ai_catalog",
            "ai_catalog_sha256",
            "product_card",
            "product_card_sha256",
            "mcp",
            "mcp_discovery",
            "mcp_discovery_sha256",
            "mcp_server_name",
            "api_catalog",
            "openapi",
            "public_tools",
            "public_prompts",
            "public_resources",
            "pypi",
            "pypi_spec",
            "pypi_wheel_sha256",
            "pypi_wheel_bytes",
            "pypi_sdist_sha256",
            "pypi_sdist_bytes",
            "signed_tag",
            "signed_tag_object",
            "release_commit",
            "static_deployment",
            "registry_version",
            "registry_server_sha256",
            "live_version_authority",
        )
    } == {
        "version": "0.11.1",
        "ai_catalog": "https://seiche.info/.well-known/ai-catalog.json",
        "ai_catalog_sha256": (
            "sha256:735516115752afebd3b8a3637a22f806ff8f592826381ce1bbe32ab5b7b5cc74"
        ),
        "product_card": "https://seiche.info/product-card.json",
        "product_card_sha256": (
            "sha256:1d382ad21d4fa8c35433f9270946d74dca592fb833c454c02cc3613a6c2edf08"
        ),
        "mcp": "https://api.seiche.info/mcp",
        "mcp_discovery": "https://api.seiche.info/.well-known/mcp.json",
        "mcp_discovery_sha256": (
            "sha256:1db329dbc3155a0a695a3ddf7e7dcd37d7edaea22d4898b97002cbf172c931fe"
        ),
        "mcp_server_name": "io.github.beepboop2025/seiche",
        "api_catalog": "https://api.seiche.info/api",
        "openapi": "https://api.seiche.info/api/openapi.json",
        "public_tools": 11,
        "public_prompts": 4,
        "public_resources": 0,
        "pypi": "https://pypi.org/project/seiche/0.11.1/",
        "pypi_spec": "seiche==0.11.1",
        "pypi_wheel_sha256": (
            "sha256:01b5b770d88391d31ba406ca651ab5d6054b2e4c6f6c3cf6138f713f4374e4a1"
        ),
        "pypi_wheel_bytes": 1101154,
        "pypi_sdist_sha256": (
            "sha256:0fa965b00f0c81a5f9ad8a5d66a4140523a90f962f3bdcf196fd884d89057a15"
        ),
        "pypi_sdist_bytes": 980967,
        "signed_tag": "v0.11.1",
        "signed_tag_object": "fc1742880be1be06837c5fc703b4ba5312ff4b2b",
        "release_commit": "0cd20bfd0a4d274c8bb8173f6fe59e2d2f5259db",
        "static_deployment": "https://699fdc4e.seiche.pages.dev",
        "registry_version": (
            "https://registry.modelcontextprotocol.io/v0.1/servers/"
            "io.github.beepboop2025%2Fseiche/versions/0.11.1"
        ),
        "registry_server_sha256": (
            "sha256:2a7a82905c2466684fdf61de0862a5dbfb9b1d2703918c88a594d0017dd8b6f1"
        ),
        "live_version_authority": (
            "Initialize the linked MCP remote and compare serverInfo.version "
            "before treating a release as deployed."
        ),
    }

    undertow = siblings["Undertow"]
    assert {
        "version": undertow["version"],
        "catalog": undertow["ai_catalog"],
        "mcp": undertow["mcp"],
        "server": undertow["mcp_server_name"],
        "protocols": undertow["protocol_versions"],
        "counts": (
            undertow["public_tools"],
            undertow["public_prompts"],
            undertow["public_resources"],
        ),
    } == {
        "version": "1.10.0",
        "catalog": "https://liquilens-undertow.com/.well-known/ai-catalog.json",
        "mcp": "https://api.seiche.info/undertow/mcp",
        "server": "io.github.beepboop2025/undertow",
        "protocols": [
            "2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26",
        ],
        "counts": (10, 3, 0),
    }
    assert undertow["trade_safety_tool"] == "trade_safety_exit_context"

    palimpsest = siblings["Palimpsest"]
    assert palimpsest["version"] == "1.9.3"
    assert palimpsest["mcp"] == "https://api.seiche.info/palimpsest/mcp"
    assert palimpsest["protocol_versions"] == ["2025-06-18", "2025-03-26"]
    assert (
        palimpsest["public_tools"],
        palimpsest["public_prompts"],
        palimpsest["public_resources"],
    ) == (6, 4, 1)
    assert palimpsest["deployment_receipt_sha256"] == (
        "sha256:db370a46897b58d32e31561f1e664d68ea053ac38454caa58b52dd4c9ba5e834"
    )
    assert palimpsest["registry_receipt_sha256"] == (
        "sha256:d9f153a99b52b686995e22e378fcd1383335d0f74c175932d4dfd6d70147b4f5"
    )
    assert palimpsest["registry_snapshot_sha256"] == (
        "sha256:b242bf50ef87441222ac2b3b9103b99d4fad44d52dd5b119a500ee13d4508287"
    )


def test_sibling_release_status_ship_log_and_sitemap_are_converged():
    status = read("status/index.html")
    assert "Release contract · 2 September 2026" in status
    assert "Seiche 0.11.1" in status
    assert "11 public read-only MCP tools, 4 prompts and 0 resources" in status
    assert "runtime, signed tag, exact PyPI artifacts, static catalog" in status
    assert "Undertow 1.9.0" in status
    assert "9 public + 8 subscriber MCP tools, 3 public prompts and 0 resources" in status
    assert "Palimpsest 1.9.3" in status
    assert "6 public read-only MCP tools, 4 prompts and 1 metadata-only" in status
    assert "LIVE / RECEIPTED" in status
    assert "Evidence Carrier 0.18.0 + Trade Safety Receipt v1" in status

    ship_log = read("ship-log/index.html")
    assert "Seiche 0.11.1 closes its public distribution contract" in ship_log
    assert "https://pypi.org/project/seiche/0.11.1/" in ship_log
    assert "io.github.beepboop2025%2Fseiche/versions/0.11.1" in ship_log
    assert "Palimpsest 1.9.3 makes publication rights native" in ship_log
    assert "mcp-deployment-1.9.3.json" in ship_log
    assert "mcp-registry-publication-1.9.3.json" in ship_log
    assert "Palimpsest 1.9.1 refreshes its exact agent boundary" in ship_log
    assert "Trade Safety Receipt v1 ships as open, order-bound infrastructure" in ship_log
    assert "Evidence Carrier 0.18.0 puts Trade Safety Receipt v1 on the paper-order path" in ship_log
    assert "906ca033a96ea862ab813c64db2a6b01c5ce8c4f" in ship_log
    for historical_release in ("Seiche 0.10.0", "Seiche 0.10.1"):
        assert historical_release in ship_log

    sitemap = read("sitemap.xml")
    assert (
        "<loc>https://liquilens.in/ship-log/</loc>\n"
        "    <lastmod>2026-09-02</lastmod>"
    ) in sitemap
    assert (
        "<loc>https://liquilens.in/status/</loc>\n"
        "    <lastmod>2026-09-02</lastmod>"
    ) in sitemap
    generator = read("scripts/build_replay_pages.py")
    assert '("/protocol/", "2026-09-02", "monthly", "0.9")' in generator
    assert '("/protocol/trade-safety/", "2026-09-02", "monthly", "0.95")' in generator
    assert '("/ship-log/", "2026-09-02", "weekly", "0.7")' in generator
    assert '("/status/", "2026-09-02", None, None)' in generator


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
    api_catalog = "https://liquilens.in/.well-known/api-catalog"
    assert 'rel="api-catalog"' in read("index.html")
    assert api_catalog in read("llms.txt")
