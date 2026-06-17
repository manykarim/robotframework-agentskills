"""Tests for marketplace structural integrity."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
PLUGIN_ROOT = ROOT / "plugins" / "rf-agentskills"


def test_marketplace_json_exists():
    assert (ROOT / ".claude-plugin" / "marketplace.json").exists()


def test_marketplace_json_valid():
    with open(ROOT / ".claude-plugin" / "marketplace.json", encoding="utf-8") as f:
        data = json.load(f)
    assert "name" in data
    assert "owner" in data
    assert "plugins" in data
    assert isinstance(data["plugins"], list)
    assert len(data["plugins"]) > 0


def test_plugin_json_exists():
    assert (PLUGIN_ROOT / ".claude-plugin" / "plugin.json").exists()


def test_plugin_json_valid():
    with open(PLUGIN_ROOT / ".claude-plugin" / "plugin.json", encoding="utf-8") as f:
        data = json.load(f)
    assert "name" in data
    assert "version" in data


def test_all_plugin_sources_exist():
    with open(ROOT / ".claude-plugin" / "marketplace.json", encoding="utf-8") as f:
        data = json.load(f)
    for plugin in data["plugins"]:
        source = plugin["source"]
        plugin_dir = ROOT / source
        assert plugin_dir.is_dir(), f"Plugin source missing: {source}"


def test_all_skills_have_skill_md():
    skills_dir = PLUGIN_ROOT / "skills"
    for entry in sorted(skills_dir.iterdir()):
        if entry.is_dir():
            skill_md = entry / "SKILL.md"
            assert skill_md.exists(), f"Missing SKILL.md: {entry.name}"


def test_plugin_names_unique():
    with open(ROOT / ".claude-plugin" / "marketplace.json", encoding="utf-8") as f:
        data = json.load(f)
    names = [p["name"] for p in data["plugins"]]
    assert len(names) == len(set(names)), "Duplicate plugin names found"


def test_skill_md_frontmatter():
    skills_dir = PLUGIN_ROOT / "skills"
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.exists():
            continue
        content = skill_md.read_text(encoding="utf-8")
        assert content.startswith("---"), f"{entry.name}/SKILL.md missing frontmatter"
        end = content.find("---", 3)
        assert end != -1, f"{entry.name}/SKILL.md unclosed frontmatter"
        fm = content[3:end]
        assert "name:" in fm, f"{entry.name}/SKILL.md frontmatter missing name"
        assert "description:" in fm, f"{entry.name}/SKILL.md frontmatter missing description"
