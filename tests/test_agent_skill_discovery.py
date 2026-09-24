"""Verify native legacy layout and draft discovery integrity from shared bytes."""
import hashlib
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
