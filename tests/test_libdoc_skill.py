"""The merged rf-libdoc skill (libdoc-skill spec)."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "rf-libdoc"
SKILL_MD = SKILL_DIR / "SKILL.md"
SCRIPT = SKILL_DIR / "scripts" / "rf_libdoc.py"

SKILL_TREES = (
    ROOT / "skills",
    ROOT / "plugins" / "rf-agentskills" / "skills",
    ROOT / "plugins" / "rf-agentskills" / "scripts",
    ROOT / "vscode-extension" / "skills",
)
OLD_NAMES = (
    "libdoc-search",
    "libdoc-explain",
    "rf-libdoc-search",
    "rf-libdoc-explain",
    "robotframework-libdoc-search",
    "robotframework-libdoc-explain",
)


def _text() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


def _frontmatter() -> dict[str, str]:
    m = re.match(r"^---\n(.*?)\n---\n", _text(), re.S)
    assert m, "SKILL.md has no frontmatter"
    return dict(
        line.split(": ", 1) for line in m.group(1).splitlines() if ": " in line
    )


def _code_blocks() -> str:
    return "\n".join(re.findall(r"```(?:bash|sh)?\n(.*?)```", _text(), re.S))


def test_name_matches_directory() -> None:
    assert _frontmatter()["name"] == SKILL_DIR.name == "rf-libdoc"


def test_description_covers_both_jobs() -> None:
    # Compact description (tune-skill-descriptions D11) plus the "## When to use"
    # body block (D12), which carries the trigger terms that no longer fit.
    desc = _frontmatter()["description"]
    assert len(desc) <= 160
    low = desc.lower()
    assert "keyword" in low and "argument" in low and "libdoc" in low
    assert low.strip("\"").startswith("use")
    m = re.search(r"^## When to use[ \t]*\n(.*?)(?=^## )", _text(), re.M | re.S)
    assert m, "no '## When to use' block"
    block = m.group(1).lower()
    assert "which keyword" in block, "search job missing"
    assert "arguments" in block and "signature" in block, "explain job missing"


def test_robotcode_boundary_at_start() -> None:
    body = _text().split("\n---\n", 1)[1]
    head = body.split("## Which command", 1)[0]
    assert "robotcode libdoc" in head
    assert "rf-robotcode" in head


def test_all_modes_shown() -> None:
    code = _code_blocks()
    lines = [ln for ln in code.splitlines() if "rf_libdoc.py" in ln]
    assert any("--search" in ln and "--keyword" not in ln for ln in lines)
    assert any("--keyword" in ln and "--search" not in ln for ln in lines)
    assert any("--keyword" in ln and "--search" in ln for ln in lines)
    assert any("--keyword" not in ln and "--search" not in ln for ln in lines), "list mode"
    text = _text()
    for mode in ("search", "explain", "fallback", "list"):
        assert f'"{mode}"' in text or f"`{mode}`" in text, mode


def test_contract_documented_once() -> None:
    text = _text()
    for token in ("mode", "results", "usage.params", "--include-library-doc"):
        assert token in text
    for flag in (
        "--library", "--resource", "--suite", "--spec", "--tag",
        "--include-private", "--exclude-deprecated", "--limit",
    ):
        assert flag in text, flag


def test_documented_flags_exist() -> None:
    help_text = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True, text=True, check=True,
    ).stdout
    accepted = set(re.findall(r"--[a-z][a-z-]+", help_text))
    documented = set(re.findall(r"--[a-z][a-z-]+", _code_blocks()))
    assert documented, "no options found in code blocks"
    assert documented <= accepted, documented - accepted


def test_script_is_regular_file() -> None:
    assert SCRIPT.is_file() and not SCRIPT.is_symlink()


@pytest.mark.parametrize("tree", SKILL_TREES, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_symlinks_in_skill_trees(tree: Path) -> None:
    links = [str(p.relative_to(ROOT)) for p in tree.rglob("*") if p.is_symlink()]
    assert not links, links


def test_old_skill_dirs_absent_in_all_channels() -> None:
    for tree in (SKILL_TREES[0], SKILL_TREES[1], SKILL_TREES[3]):
        present = [n for n in OLD_NAMES if (tree / n).exists()]
        assert not present, (tree, present)


def test_single_libdoc_skill_per_channel() -> None:
    assert (ROOT / "plugins/rf-agentskills/skills/rf-libdoc/SKILL.md").is_file()
    assert (ROOT / "vscode-extension/skills/rf-libdoc/SKILL.md").is_file()
    pkg = (ROOT / "vscode-extension/package.json").read_text(encoding="utf-8")
    assert pkg.count("./skills/rf-libdoc/SKILL.md") == 1
    for tree in (SKILL_TREES[0], SKILL_TREES[1], SKILL_TREES[3]):
        libdoc = [p.name for p in tree.iterdir() if p.is_dir() and "libdoc" in p.name]
        assert len(libdoc) == 1, (tree, libdoc)
