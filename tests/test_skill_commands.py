"""How skill scripts are invoked, per channel (skill-script-execution spec).

Scans every SKILL.md (root, plugin, VS Code), the plugin subagents and the
script-related hook message for the canonical command form, and checks the
scripts' PEP 723 metadata and the skills' `compatibility` declaration.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "rf-agentskills"
CHANNELS = {
    "root": ROOT / "skills",
    "plugin": PLUGIN / "skills",
    "vscode": ROOT / "vscode-extension" / "skills",
}
SCRIPT_SKILLS = {"rf-libdoc": "rf_libdoc.py", "rf-results": "rf_results.py", "rf-language": "rf_conventions.py",
                 "rf-python-library": "check_library.py"}
#: Skills whose content is Robot Framework code, so `${var}` is expected; only
#: agent-specific variables such as ${CLAUDE_SKILL_DIR} are forbidden there.
RF_CODE_SKILLS = {"rf-language", "rf-python-library"}

#: Any fenced block (so ```python / ```toml blocks pair correctly); only shell
#: blocks (bash/sh/shell/console or no language) count as commands.
FENCE = re.compile(r"^[ \t]*```([\w-]*)\n(.*?)^[ \t]*```", re.S | re.M)
SHELL_LANGS = {"", "bash", "sh", "shell", "console"}
BARE_PYTHON = re.compile(r"(?<![\w/.\\-])python3? +\S*scripts/")


def _skill_mds() -> list[Path]:
    return sorted(md for tree in CHANNELS.values() for md in tree.glob("*/SKILL.md"))


def _shell_lines(text: str) -> list[str]:
    return [ln.strip() for lang, block in FENCE.findall(text) if lang in SHELL_LANGS
            for ln in block.splitlines() if ln.strip() and not ln.strip().startswith("#")]


def _is_bare(line: str) -> bool:
    for m in BARE_PYTHON.finditer(line):
        before = line[: m.start()].rstrip()
        if not before.endswith("run"):
            return True
    return False


SKILL_IDS = [str(p.relative_to(ROOT)) for p in _skill_mds()]


@pytest.mark.parametrize("md", _skill_mds(), ids=SKILL_IDS)
def test_no_bare_python_or_plugin_root(md: Path) -> None:
    text = md.read_text(encoding="utf-8")
    assert "${CLAUDE_PLUGIN_ROOT}" not in text
    bad = [ln for ln in text.splitlines() if _is_bare(ln)]
    assert not bad, bad


@pytest.mark.parametrize("channel", list(CHANNELS))
@pytest.mark.parametrize("skill", list(SCRIPT_SKILLS))
def test_script_commands_use_channel_form(channel: str, skill: str) -> None:
    script = SCRIPT_SKILLS[skill]
    skill_dir = CHANNELS[channel] / skill
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    path = f'"${{CLAUDE_SKILL_DIR}}/scripts/{script}"' if channel == "plugin" else f"scripts/{script}"
    commands = [ln for ln in _shell_lines(text) if script in ln]
    assert len(commands) >= 3, commands
    for cmd in commands:
        assert cmd.startswith(f"uv run python {path} "), cmd
    # Exactly one non-uv fallback line naming the project interpreter + rf-setup.
    fallback = [ln for ln in text.splitlines() if ".venv/bin/python" in ln]
    assert len(fallback) == 1, fallback
    assert "poetry run python" in fallback[0] and "rf-setup" in fallback[0]
    if channel == "plugin":
        assert f"scripts/{script}" not in text.replace(path, "")
    else:
        assert "${CLAUDE_SKILL_DIR}" not in text
        assert "relative to this skill's directory" in text
    assert "pip install" not in text
    # The script the commands point at ships in this channel's skill dir.
    shipped = skill_dir / "scripts" / script
    assert shipped.is_file() and not shipped.is_symlink()


@pytest.mark.parametrize("skill", list(SCRIPT_SKILLS))
def test_root_skill_has_no_agent_specific_variables(skill: str) -> None:
    text = (CHANNELS["root"] / skill / "SKILL.md").read_text(encoding="utf-8")
    if skill in RF_CODE_SKILLS:
        assert not re.search(r"\$\{(CLAUDE|COPILOT|CURSOR)_", text), skill
    else:
        assert "${" not in text


def test_subagents_do_not_run_script_paths() -> None:
    for md in sorted((PLUGIN / "agents").glob("*.md")):
        text = md.read_text(encoding="utf-8")
        assert "scripts/rf_" not in text, md.name
        assert "${CLAUDE_PLUGIN_ROOT}/scripts" not in text, md.name
        assert not any(_is_bare(ln) for ln in text.splitlines()), md.name
    consultant = (PLUGIN / "agents" / "rf-keyword-consultant.md").read_text(encoding="utf-8")
    assert "rf_libdoc_search" in consultant and "rf_libdoc_explain" in consultant
    assert "rf_results_analyze" in (PLUGIN / "agents" / "rf-debug-expert.md").read_text(encoding="utf-8")


def test_hook_reminder_uses_project_environment() -> None:
    text = (PLUGIN / "scripts" / "maybe_remind_robot_tests.mjs").read_text(encoding="utf-8")
    assert "${CLAUDE_PLUGIN_ROOT}" not in text
    assert "import.meta.url" in text
    assert "uv run python" in text
    assert "pip install" not in text
    assert not any(_is_bare(ln) for ln in text.splitlines())


@pytest.mark.parametrize("skill", list(SCRIPT_SKILLS))
def test_script_declares_pep723_metadata(skill: str) -> None:
    for tree in CHANNELS.values():
        src = (tree / skill / "scripts" / SCRIPT_SKILLS[skill]).read_text(encoding="utf-8")
        block = re.search(r"^# /// script\n((?:#.*\n)+?)# ///$", src, re.M)
        assert block, "missing PEP 723 block"
        meta = block.group(1)
        assert re.search(r'^# requires-python = ">=3\.\d+"$', meta, re.M), meta
        assert re.search(r'^# dependencies = \[.*"robotframework>=7".*\]$', meta, re.M), meta
        assert "pip install" not in src


def _compatibility(md: Path) -> str:
    front = md.read_text(encoding="utf-8").split("---", 2)[1]
    m = re.search(r"^compatibility:\s*(.+)$", front, re.M)
    assert m, f"{md}: no compatibility"
    return m.group(1)


@pytest.mark.parametrize("channel", list(CHANNELS))
def test_script_bearing_skills_declare_requirements(channel: str) -> None:
    skills = [d for d in CHANNELS[channel].iterdir() if (d / "scripts").is_dir()]
    assert {d.name for d in skills} == set(SCRIPT_SKILLS)
    for d in skills:
        compat = _compatibility(d / "SKILL.md")
        assert "Python" in compat and "robotframework>=7" in compat, compat
        # The declared Python floor matches the scripts' requires-python.
        floor = re.search(r"Python (\d+\.\d+)\+", compat)
        script = (d / "scripts" / SCRIPT_SKILLS[d.name]).read_text(encoding="utf-8")
        if floor:
            assert f'requires-python = ">={floor.group(1)}"' in script
