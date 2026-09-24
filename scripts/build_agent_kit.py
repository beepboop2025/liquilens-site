#!/usr/bin/env python3
"""Build reproducible free-agent downloads from reviewed sources."""
import hashlib
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "agents"
SERVERS = {
    "seiche": {"url": "https://api.seiche.info/mcp", "tools": ["data_health", "funding_stress_now", "money_market_context"]},
    "liquilens": {"url": "https://api.liquilens.in/mcp", "tools": ["banking_specialisation_coverage", "bank_asset_quality_review", "institution_review_packet", "universe_search"]},
    "undertow": {"url": "https://api.seiche.info/undertow/mcp", "tools": ["exit_cost", "venue_concentration"]},
}


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def assets():
    servers = {name: {"url": spec["url"], "transport": "streamable-http",
                      "toolFilter": {"include": spec["tools"]}} for name, spec in SERVERS.items()}
    yaml = "mcp_servers:\n" + "".join(
        "  " + name + ":\n    url: " + spec["url"] + "\n    tools:\n      include: " + json.dumps(spec["tools"]) + "\n"
        for name, spec in SERVERS.items())
    result = {
        "openclaw.json": json_bytes({"mcp": {"servers": servers}}),
        "hermes.yaml": yaml.encode(),
        "cursor.json": json_bytes({"mcpServers": {n: {"url": s["url"]} for n, s in SERVERS.items()}}),
        "vscode.json": json_bytes({"servers": {n: {"type": "http", "url": s["url"]} for n, s in SERVERS.items()}}),
        "claude.txt": ("\n".join(f"claude mcp add --transport http {n} {s['url']}" for n, s in SERVERS.items()) + "\n").encode(),
        "codex.txt": ("\n".join(f"codex mcp add {n} --url {s['url']}" for n, s in SERVERS.items()) + "\n").encode(),
    }
    for name in ("financial_research.py", "trading_brief.py"):
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
    body = archive(files)
    (OUT / "trading-research-kit.zip").write_bytes(body)
    manifest = {
        "schema": "liquilens.agent-kit.v1", "version": "1.0.0",
        "updated_at": "2026-09-24", "homepage": "https://liquilens.in/agents/",
        "price": {"public_research": "free", "api_key_required": False,
                  "limits": "Fair-use limits apply. Model providers may charge separately."},
        "servers": SERVERS, "python": ">=3.11", "external_python_packages": [],
        "commands": ["python3 trading_brief.py doctor", "python3 trading_brief.py run"],
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
