#!/usr/bin/env python3
"""Build reproducible free-agent downloads from reviewed sources."""
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "agents"
VERSION = "1.2.0"
SKILL_NAME = "liquilens-trading-research"
SERVERS = {
    "seiche": {"url": "https://api.seiche.info/mcp", "tools": ["data_health", "funding_stress_now", "money_market_context", "market_workbench", "gift_city_context", "gold_inventory_carry"]},
    "liquilens": {"url": "https://api.liquilens.in/mcp", "tools": ["banking_specialisation_coverage", "bank_asset_quality_review", "institution_review_packet", "universe_search"]},
    "undertow": {"url": "https://api.seiche.info/undertow/mcp", "tools": ["exit_cost", "venue_concentration", "gold_cash_realisation"]},
}
PROFILES = {
    "all-topics": {
        "label": "All research topics", "tools": {name: spec["tools"] for name, spec in SERVERS.items()},
        "description": "Funding, covered banks, BTC exits, GIFT City, reference FX and gold scenarios: thirteen selected public tools.",
        "prompt": "Choose the connected tools for my research question: Seiche for dated funding, reference FX and GIFT City context; LiquiLens for exact covered-bank evidence; Undertow for published BTC exit estimates. Use gold financing or cash scenarios only when I ask and supply all required assumptions. Keep sources, clocks, rights, partial coverage and unavailable values explicit. Do not infer execution prices or regulatory eligibility.",
    },
    "gift-city": {
        "label": "GIFT City / India–UAE",
        "tools": {"seiche": ["data_health", "money_market_context", "market_workbench", "gift_city_context", "gold_inventory_carry"], "liquilens": ["banking_specialisation_coverage", "bank_asset_quality_review"], "undertow": ["gold_cash_realisation"]},
        "description": "Research for gold importers and treasury desks, investors and fund managers, and banks or IFSC institutions.",
        "prompt": "Build a GIFT City research packet for my stated role: importer/treasury, investor/fund manager, or bank/IFSC institution. Read Seiche gift_city_context and preserve each funding, FX and gold-positioning source date and gap. Use market_workbench only for its supported reference providers and currency pairs; keep CBUAE context separate. Resolve exact LiquiLens bank coverage if a counterparty is named. Run gold scenarios only if I request them and provide the required assumptions. Do not invent fund NAVs, live bullion quotes, tax treatment or regulatory eligibility.",
    },
    "forex": {
        "label": "Forex reference rates",
        "tools": {"seiche": ["data_health", "market_workbench", "gift_city_context"]},
        "description": "Dated H.10/ECB reference histories and separate India–UAE FX context, with explicit pair conventions.",
        "prompt": "Use Seiche market_workbench for my currency pair and an explicitly selected h10 or ecb provider. Preserve quote direction, units, source dates, freshness and unavailable pairs. For CBUAE AED references use gift_city_context instead; do not invent an AED market_workbench pair or blend providers. Any conversion is a dated reference calculation with my stated amount and fees, not an executable quote.",
    },
    "gold": {
        "label": "Gold financing and cash",
        "tools": {"seiche": ["data_health", "gift_city_context", "gold_inventory_carry"], "undertow": ["gold_cash_realisation"]},
        "description": "Separate gold-positioning context, caller-assumption inventory carry and cash-at-cutoff scenarios.",
        "prompt": "Separate three questions: Seiche gift_city_context for dated funding, FX references and gold positioning; gold_inventory_carry for financing cost; Undertow gold_cash_realisation for hypothetical sale proceeds versus cash available at a cutoff. Before a requested scenario, ask for every required price, FX, quantity, fineness, fee and timing/access assumption. Preserve decimal strings and timezone-aware clocks. Do not turn positioning into a gold spot price, assume missing flags, or treat future settlement as current cash.",
    },
    "bank-risk": {
        "label": "Bank filing and risk research", "tools": {"liquilens": SERVERS["liquilens"]["tools"]},
        "description": "Resolve exact covered-bank filing evidence; keep Failure Radar and registry coverage separate.",
        "prompt": "Resolve my named bank with LiquiLens banking_specialisation_coverage before bank_asset_quality_review. Preserve filing periods, source units and unavailable fields. Use institution_review_packet only for a separately requested Failure Radar review; a registry match or filing record does not establish that coverage. No deposit-safety assurance or credit rating follows.",
    },
    "money-market": {
        "label": "Money markets and funding",
        "tools": {"seiche": ["data_health", "funding_stress_now", "money_market_context"]},
        "description": "Funding context, source freshness and native-cadence money-market evidence.",
        "prompt": "Read Seiche data_health and money_market_context(section=\"summary\"). Use funding_stress_now for the funding conclusion and counterevidence. Retain benchmark units, observation dates, stale sources and unavailable fields; do not treat missing evidence as calm or derive a trade recommendation.",
    },
    "market-liquidity": {
        "label": "BTC exit liquidity", "tools": {"undertow": ["exit_cost", "venue_concentration"]},
        "description": "Published BTC exit estimates at supported size rungs, source clocks and venue depth concentration.",
        "prompt": "For my requested BTC sell size, read Undertow exit_cost and venue_concentration. Preserve the requested size, supported size rung, source observation time, stale or unavailable venues and basis-point units. The estimate is not a current executable quote or a recommendation to use a venue.",
    },
    "funding-bank-exits": {
        "label": "Original funding / bank / BTC brief",
        "tools": {"seiche": ["data_health", "funding_stress_now", "money_market_context"], "liquilens": SERVERS["liquilens"]["tools"], "undertow": ["exit_cost", "venue_concentration"]},
        "description": "The original nine-tool selection used by the dated September 24 client checks and Python brief.",
        "prompt": "Prepare a funding, covered-bank and BTC-exit research brief. Read Seiche funding context and freshness. Use my explicit BTC sell size for Undertow exit estimates. If I name a bank, resolve exact LiquiLens coverage before reviewing it. Preserve source dates, units, counterevidence and failed sections. Do not issue a trade instruction.",
    },
}


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def discovery_assets(skill):
    """Publish both discovery formats from one reviewed, single-file skill."""
    text = skill.decode("utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError("Skill frontmatter is required for discovery")
    frontmatter = text[4:].split("\n---\n", 1)[0]
    names = re.findall(r"^name: ([a-z0-9-]+)$", frontmatter, re.MULTILINE)
    descriptions = re.findall(r"^description: (.+)$", frontmatter, re.MULTILINE)
    if names != [SKILL_NAME] or len(descriptions) != 1:
        raise ValueError("Discovery requires the expected name and one-line description")
    description = descriptions[0].strip()
    if not description or len(description) > 1024 or description[0] in "|>\"'":
        raise ValueError("Discovery description must be unquoted plain single-line text")
    skill_path = f"/.well-known/skills/{SKILL_NAME}/SKILL.md"
    legacy = {"skills": [{"name": SKILL_NAME, "description": description, "files": ["SKILL.md"]}]}
    current = {
        "$schema": "https://schemas.agentskills.io/discovery/0.2.0/schema.json",
        "skills": [{"name": SKILL_NAME, "type": "skill-md", "description": description,
                    "url": skill_path, "digest": "sha256:" + hashlib.sha256(skill).hexdigest()}],
    }
    return {
        ".well-known/skills/index.json": json_bytes(legacy),
        ".well-known/agent-skills/index.json": json_bytes(current),
        skill_path.lstrip("/"): skill,
    }


def configuration_assets(selected):
    """Apply tool filters only where the native client supports this format."""
    servers = {name: {"url": spec["url"], "transport": "streamable-http",
                      "toolFilter": {"include": spec["tools"]}} for name, spec in selected.items()}
    yaml = "mcp_servers:\n" + "".join(
        "  " + name + ":\n    url: " + spec["url"] + "\n    tools:\n      include: " + json.dumps(spec["tools"]) + "\n"
        for name, spec in selected.items())
    return {
        "openclaw.json": json_bytes({"mcp": {"servers": servers}}),
        "hermes.yaml": yaml.encode(),
        "cursor.json": json_bytes({"mcpServers": {n: {"url": s["url"]} for n, s in selected.items()}}),
        "vscode.json": json_bytes({"servers": {n: {"type": "http", "url": s["url"]} for n, s in selected.items()}}),
        "claude.txt": ("\n".join(f"claude mcp add --transport http {n} {s['url']}" for n, s in selected.items()) + "\n").encode(),
        "codex.txt": ("\n".join(f"codex mcp add {n} --url {s['url']}" for n, s in selected.items()) + "\n").encode(),
    }


def profile_assets():
    files, profiles = {}, {}
    for key, profile in PROFILES.items():
        selected = {}
        for name, tools in profile["tools"].items():
            if not tools or len(tools) != len(set(tools)) or not set(tools) <= set(SERVERS[name]["tools"]):
                raise ValueError(f"Invalid tool selection for {key}/{name}")
            selected[name] = {"url": SERVERS[name]["url"], "tools": tools}
        configs = configuration_assets(selected)
        profiles[key] = {**profile, "configurations": {}, "downloads": {}}
        for filename, body in configs.items():
            client = filename.split(".")[0]
            relative = f"profiles/{key}/{filename}"
            files[relative] = body
            profiles[key]["configurations"][client] = body.decode()
            profiles[key]["downloads"][client] = f"/agents/{relative}"
    payload = {"schema": "liquilens.agent-topic-profiles.v1", "version": VERSION,
               "default": "all-topics", "profiles": profiles,
               "filtering": {"hermes": "selected-tools", "openclaw": "selected-tools",
                             "claude": "selected-servers", "codex": "selected-servers",
                             "cursor": "selected-servers", "vscode": "selected-servers"}}
    files["profiles.json"] = json_bytes(payload)
    files["profiles.mjs"] = b"// Generated by scripts/build_agent_kit.py.\nexport default " + json_bytes(payload).rstrip() + b";\n"
    return files


def assets():
    result = configuration_assets(SERVERS)
    result.update(profile_assets())
    for name in ("financial_research.py", "trading_brief.py", "source_data.py"):
        result[name] = (ROOT / "developers/recipes" / name).read_bytes()
    for name in ("README.md", "trading-research/SKILL.md", "n8n-funding-research.json"):
        result[name] = (OUT / name).read_bytes()
    return result


def archive(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 24, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, data)
    return output.getvalue()


def build():
    files = assets()
    for name, body in files.items():
        (OUT / name).parent.mkdir(parents=True, exist_ok=True)
        (OUT / name).write_bytes(body)
    for name, data in discovery_assets(files["trading-research/SKILL.md"]).items():
        destination = ROOT / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    body = archive(files)
    (OUT / "trading-research-kit.zip").write_bytes(body)
    manifest = {
        "schema": "liquilens.agent-kit.v1", "version": VERSION,
        "updated_at": "2026-10-05", "homepage": "https://liquilens.in/agents/",
        "price": {"public_research": "free", "api_key_required": False,
                  "limits": "Fair-use limits apply. Model providers may charge separately."},
        "servers": SERVERS, "python": ">=3.11", "external_python_packages": [],
        "topic_profiles": {"url": "https://liquilens.in/agents/profiles.json", "default": "all-topics",
                           "ids": list(PROFILES), "scenario_inputs": "explicit caller assumptions required; never auto-run"},
        "commands": ["python3 trading_brief.py doctor", "python3 trading_brief.py run", "python3 source_data.py catalog"],
        "source_data": {"mcp": "https://api.seiche.info/api/v2/research-data/mcp",
                        "openapi": "https://api.seiche.info/api/v2/research-data/openapi.json",
                        "scope": "Funding series, bank filings and Bitcoin/Liquid settlement; units, capture clocks and receipts retained."},
        "archive": {"url": "https://liquilens.in/agents/trading-research-kit.zip",
                    "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)},
        "files": {name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                  for name, data in sorted(files.items())},
        "authority": {"execution": False, "credit_rating": False, "compliance_approval": False},
        "verification": {"flag": "--verification", "counts_as_adoption": False},
    }
    (OUT / "manifest.json").write_bytes(json_bytes(manifest))
    print(json.dumps({"files": len(files), "archive_bytes": len(body), "archive_sha256": manifest["archive"]["sha256"]}))


if __name__ == "__main__":
    build()
