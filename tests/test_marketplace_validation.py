"""Tests for marketplace structural integrity."""
import importlib.util
import json
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
    """Delegates to scripts/validate-skills.py so there is one rule set."""
    spec = importlib.util.spec_from_file_location("validate_skills", ROOT / "scripts" / "validate-skills.py")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    violations = validator.validate(ROOT, ["root", "plugin"])
    assert not violations, "\n".join(violations)


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_plugin_sets_no_default_main_agent():
    """Enabling the plugin must not replace the user's main agent."""
    assert not (PLUGIN_ROOT / "settings.json").exists()
    manifest = _json(PLUGIN_ROOT / ".claude-plugin" / "plugin.json")
    assert "agent" not in (manifest.get("settings") or {})


def test_one_claude_format_marketplace_for_every_agent():
    """Copilot, Codex and Cursor read .claude-plugin/; a root plugin.json or
    .cursor-plugin/ manifest would take precedence there and drop hooks/agents."""
    assert not (ROOT / "plugin.json").exists()
    assert not (PLUGIN_ROOT / "plugin.json").exists()
    assert not (ROOT / ".cursor-plugin").exists()
    assert not (PLUGIN_ROOT / ".cursor-plugin").exists()


def test_marketplace_and_plugin_manifests_agree():
    marketplace = _json(ROOT / ".claude-plugin" / "marketplace.json")
    manifest = _json(PLUGIN_ROOT / ".claude-plugin" / "plugin.json")
    [entry] = [p for p in marketplace["plugins"] if p["name"] == manifest["name"]]
    assert entry["source"] == "./plugins/rf-agentskills"
    assert entry["version"] == manifest["version"]
    assert marketplace.get("metadata", {}).get("version") == manifest["version"]
    # A v<VERSION> tag is the pinnable marketplace ref (RELEASING.md).
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == manifest["version"]
