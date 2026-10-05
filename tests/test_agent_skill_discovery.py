"""Verify native legacy layout and draft discovery integrity from shared bytes."""
import hashlib
import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("discovery_kit", ROOT / "scripts/build_agent_kit.py")
kit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kit)


def test_both_indexes_resolve_to_the_exact_same_reviewed_skill():
    skill = (ROOT / "agents/trading-research/SKILL.md").read_bytes()
    files = kit.discovery_assets(skill)
    legacy = json.loads(files[".well-known/skills/index.json"])["skills"]
    current = json.loads(files[".well-known/agent-skills/index.json"])
    assert len(legacy) == len(current["skills"]) == 1
    old, new = legacy[0], current["skills"][0]
    assert old["files"] == ["SKILL.md"]
    legacy_path = f'.well-known/skills/{old["name"]}/{old["files"][0]}'
    assert new["type"] == "skill-md"
    assert new["url"].lstrip("/") == legacy_path
    assert new["description"] == old["description"]
    assert files[legacy_path] == skill
    assert new["digest"] == "sha256:" + hashlib.sha256(skill).hexdigest()
    assert current["$schema"] == "https://schemas.agentskills.io/discovery/0.2.0/schema.json"


def test_generated_discovery_files_are_current_and_reproducible():
    skill = (ROOT / "agents/trading-research/SKILL.md").read_bytes()
    expected = kit.discovery_assets(skill)
    assert expected == kit.discovery_assets(skill)
    for name, data in expected.items():
        assert (ROOT / name).read_bytes() == data


@pytest.mark.parametrize("frontmatter", [
    "name: ../wrong\ndescription: Research tools",
    "name: liquilens-trading-research\ndescription: |\n  Hidden multiline value",
    "name: liquilens-trading-research\ndescription: First\ndescription: Second",
    "name: liquilens-trading-research",
])
def test_ambiguous_or_incompatible_metadata_cannot_publish_stale_discovery(frontmatter):
    with pytest.raises(ValueError):
        kit.discovery_assets(("---\n" + frontmatter + "\n---\nBody\n").encode())


def test_integrity_digest_changes_when_instructions_change():
    before = b"---\nname: liquilens-trading-research\ndescription: Research tools\n---\nFirst\n"
    after = before.replace(b"First", b"Second")
    def digest(body):
        return json.loads(kit.discovery_assets(body)[".well-known/agent-skills/index.json"])["skills"][0]["digest"]
    assert digest(before) != digest(after)


def test_topic_profiles_reach_live_gift_fx_and_gold_tools_without_private_tools():
    profiles = kit.PROFILES
    assert {"gift_city_context", "market_workbench", "gold_inventory_carry"} <= set(
        profiles["gift-city"]["tools"]["seiche"]
    )
    assert profiles["gold"]["tools"]["undertow"] == ["gold_cash_realisation"]
    assert "market_workbench" in profiles["forex"]["tools"]["seiche"]
    assert "gift_city_context" in profiles["forex"]["tools"]["seiche"]
    assert sum(map(len, profiles["all-topics"]["tools"].values())) == 13
    assert sum(map(len, profiles["funding-bank-exits"]["tools"].values())) == 9
    assert set(profiles["bank-risk"]["tools"]) == {"liquilens"}
    assert set(profiles["market-liquidity"]["tools"]) == {"undertow"}
    selected = {tool for profile in profiles.values() for tools in profile["tools"].values() for tool in tools}
    assert not selected.intersection({"board_full", "exit_desk_full", "exit_schedule", "unwind_stress"})


def test_topic_downloads_browser_payload_and_default_filters_cannot_diverge():
    files = kit.assets()
    manifest = json.loads(files["profiles.json"])
    assert manifest["default"] == "all-topics"
    assert set(manifest["profiles"]) == set(kit.PROFILES)
    for key, profile in manifest["profiles"].items():
        for client, text in profile["configurations"].items():
            relative = profile["downloads"][client].removeprefix("/agents/")
            assert files[relative].decode() == text
            if key == "all-topics":
                assert files[relative] == files[relative.rsplit("/", 1)[1]]
        claw = json.loads(profile["configurations"]["openclaw"])["mcp"]["servers"]
        gemini = json.loads(profile["configurations"]["gemini"])["mcpServers"]
        assert set(claw) == set(profile["tools"])
        assert set(gemini) == set(profile["tools"])
        for name, tools in profile["tools"].items():
            assert gemini[name] == {"httpUrl": kit.SERVERS[name]["url"], "timeout": 30000, "includeTools": tools}
            assert claw[name]["toolFilter"]["include"] == tools
            assert claw[name]["url"] == kit.SERVERS[name]["url"]
            assert f'      include: {json.dumps(tools)}\n' in profile["configurations"]["hermes"]
    assert manifest["filtering"]["hermes"] == manifest["filtering"]["openclaw"] == "selected-tools"
    assert manifest["filtering"]["codex"] == "selected-servers"
    assert manifest["filtering"]["gemini"] == "selected-tools"


@pytest.mark.parametrize("tools", [["invented_gold_quote"], ["gold_inventory_carry"] * 2, []])
def test_invalid_profile_tool_filters_fail_generation(monkeypatch, tools):
    profiles = copy.deepcopy(kit.PROFILES)
    profiles["gold"]["tools"]["seiche"] = tools
    monkeypatch.setattr(kit, "PROFILES", profiles)
    with pytest.raises(ValueError, match="Invalid tool selection"):
        kit.profile_assets()
