"""The robotcode CLI is a documented prerequisite (robotcode-prerequisite spec)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "rf-agentskills"
READMES = [ROOT / "README.md", PLUGIN / "README.md"]
ISOLATED = re.compile(r"uvx robotcode|pipx (install|run) robotcode|uv tool install robotcode")


@pytest.mark.parametrize("readme", READMES, ids=lambda p: str(p.relative_to(ROOT)))
def test_readme_states_requirement_and_extras(readme: Path) -> None:
    text = readme.read_text(encoding="utf-8")
    for cmd in ('uv add --dev "robotcode[all]>=2.8"', 'poetry add --group dev "robotcode[all]>=2.8"',
                'pip install "robotcode[all]>=2.8"'):
        assert cmd in text, cmd
    for extra in ("`runner`", "`analyze`", "`repl`", "Robocop", "robotcode[runner]"):
        assert extra in text, extra


@pytest.mark.parametrize("readme", READMES, ids=lambda p: str(p.relative_to(ROOT)))
def test_readme_recommends_robotcode_plugin(readme: Path) -> None:
    text = readme.read_text(encoding="utf-8")
    assert "robotcode@robotframework-agent-plugins" in text
    assert "robotcodedev/robotframework-agent-plugins" in text
    assert "RobotCode" in text and "extension" in text


def test_readme_per_agent_companion_commands() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for agent in ("claude", "copilot", "codex"):
        ours = text.index(f"{agent} plugin marketplace add manykarim/robotframework-agentskills")
        theirs = text.index(f"{agent} plugin marketplace add robotcodedev/robotframework-agent-plugins")
        assert ours < theirs, agent


def test_readme_states_ownership_split() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    prereq = text.split("## Prerequisites", 1)[1].split("\n## ", 1)[0]
    for area in ("running", "discovery", "keyword documentation", "result analysis", "the debugger"):
        assert area in prereq, area
    for owned in ("Robot Framework syntax", "Python keyword libraries", "test-library skills",
                  "environment setup", "validation hooks"):
        assert owned in prereq, owned


def _shipped_texts() -> list[Path]:
    paths = [*READMES, *(ROOT / "skills").rglob("*.md"), *(PLUGIN / "agents").glob("*.md"),
             PLUGIN / "hooks" / "README.md", *(PLUGIN / "scripts").glob("*.mjs")]
    return [p for p in paths if p.is_file()]


def test_no_isolated_robotcode_install_advice() -> None:
    for path in _shipped_texts():
        for line in path.read_text(encoding="utf-8").splitlines():
            if ISOLATED.search(line):
                assert re.search(r"(?i)\b(never|don't|do not|not)\b", line), f"{path}: {line}"


def _manifests() -> list[Path]:
    found = [*ROOT.glob(".claude-plugin/*.json"), *ROOT.glob(".agents/plugins/*.json"),
             *ROOT.glob(".plugin/*.json"), *PLUGIN.glob(".*-plugin/*.json"), *PLUGIN.glob(".plugin/*.json")]
    return sorted(p for p in found if p.is_file())


def _keys(node: object) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {k for v in node.values() for k in _keys(v)}
    if isinstance(node, list):
        return {k for v in node for k in _keys(v)}
    return set()


def test_manifests_declare_no_plugin_dependency() -> None:
    manifests = _manifests()
    assert any(p.name == "marketplace.json" for p in manifests)
    assert any(p.name == "plugin.json" for p in manifests)
    for path in manifests:
        keys = _keys(json.loads(path.read_text(encoding="utf-8")))
        assert not {"dependencies", "allowCrossMarketplaceDependenciesOn"} & keys, path
