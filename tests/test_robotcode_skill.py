"""Tests for the rf-robotcode skill.

Two layers:

1. **Structural** (always run) — the skill directory, frontmatter, the
   per-use-case references and examples exist; SKILL.md links resolve; the
   version-stamped gotchas, the inline traps and the complementary
   fallbacks/cross-links to the script-based skills are present.

2. **CLI fidelity** (run when ``robotcode`` is on PATH, else skipped) — every
   subcommand and long option the skill documents must appear in the
   corresponding ``robotcode ... --help`` output. Verified against 2.7.0.
   REPL / ``(rdb)`` dot-commands are not visible in ``--help`` and are
   covered by manual smoke runs instead.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "robotframework-robotcode-skill"
SKILL_MD = SKILL_DIR / "SKILL.md"
REFERENCES = SKILL_DIR / "references"

EXPECTED_REFERENCES = {
    "setup-and-config.md",
    "discover.md",
    "run-and-wrapper.md",
    "libdoc.md",
    "repl.md",
    "debug.md",
    "results.md",
    "analyze.md",
    "agent-mode.md",
    "gotchas.md",
}

# The robotcode CLI surface the skill documents. This dict IS the skill's
# claim; the fidelity test checks it against `robotcode ... --help`.
# Key: command path (() = root). Value: long options that must be listed.
DOCUMENTED_CLI: dict[tuple[str, ...], set[str]] = {
    (): {
        "--config", "--profile", "--root", "--format", "--dry", "--no-color",
        "--no-pager", "--wrapper", "--no-wrapper", "--version",
    },
    ("discover", "all"): {"--tags", "--search", "--search-regex", "--by-longname"},
    ("discover", "tests"): {
        "--tags", "--full-paths", "--by-longname", "--exclude-by-longname",
        "--search", "--search-regex",
    },
    ("discover", "tasks"): set(),
    ("discover", "suites"): set(),
    ("discover", "tags"): {"--tests"},
    ("discover", "files"): set(),
    ("discover", "info"): set(),
    ("libdoc",): set(),
    ("rebot",): set(),
    ("testdoc",): set(),
    ("robot",): {"--by-longname", "--exclude-by-longname"},
    ("repl",): {
        "--no-history", "--backend", "--plain", "--variable", "--variablefile",
        "--pythonpath", "--show-keywords", "--inspect", "--outputdir", "--output",
        "--report", "--log", "--xunit", "--source",
    },
    ("robot-debug",): {
        "--no-history", "--plain", "--by-longname", "--break", "--break-on-exception",
        "--no-break-on-exception", "--break-on-all-exceptions",
        "--break-on-failed-test", "--break-on-failed-suite", "--stop-on-entry",
    },
    ("results", "summary"): {
        "--status", "--include", "--exclude", "--suite", "--test", "--by-longname",
        "--search", "--output", "--failed",
    },
    ("results", "show"): {
        "--failed", "--passed", "--skipped", "--search", "--output", "--top",
        "--message-chars", "--tags", "--timing", "--sort", "--reverse",
    },
    ("results", "log"): {
        "--failed", "--output", "--level", "--max-depth", "--extract", "--keyword-info",
    },
    ("results", "stats"): {"--by", "--sort", "--top"},
    ("results", "diff"): {"--only", "--message-chars"},
    ("analyze", "code"): {
        "--filter", "--variable", "--variablefile", "--pythonpath",
        "--modifiers-ignore", "--modifiers-error", "--modifiers-warning",
        "--modifiers-information", "--modifiers-hint", "--exit-code-mask",
        "--extend-exit-code-mask", "--severity", "--code", "--load-library-timeout",
        "--collect-unused", "--show-tracebacks", "--full-paths", "--output-format",
        "--output-file",
    },
    ("analyze", "cache", "path"): set(),
    ("analyze", "cache", "info"): set(),
    ("analyze", "cache", "list"): set(),
    ("analyze", "cache", "clear"): set(),
    ("analyze", "cache", "prune"): set(),
    ("config", "show"): set(),
    ("config", "files"): set(),
    ("config", "root"): set(),
    ("config", "info"): set(),
    ("profiles", "list"): set(),
    ("profiles", "show"): set(),
}

# Aliases the skill mentions; they are listed in the root help's Aliases section.
DOCUMENTED_ALIASES = {"run", "run-debug", "shell"}

_ROBOTCODE = shutil.which("robotcode")


def _skill_text() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


def _all_text() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in SKILL_DIR.rglob("*.md"))


# --- Structural (always) --------------------------------------------------


def test_skill_structure_exists() -> None:
    assert SKILL_MD.is_file(), "SKILL.md missing"
    assert REFERENCES.is_dir(), "references/ missing"
    examples = SKILL_DIR / "assets" / "examples"
    assert examples.is_dir(), "assets/examples/ missing"
    assert any(examples.iterdir()), "assets/examples/ is empty"


def test_skill_frontmatter() -> None:
    content = _skill_text()
    assert content.startswith("---"), "missing frontmatter"
    end = content.find("---", 3)
    assert end != -1, "unclosed frontmatter"
    fm = content[3:end]
    assert "name: rf-robotcode" in fm, "frontmatter name must be rf-robotcode"
    desc = fm.split("description:", 1)[1].lower()
    for word in ("robotcode", "discover", "debug", "result"):
        assert word in desc, f"description should mention {word!r}"


def test_all_use_case_references_present() -> None:
    present = {p.name for p in REFERENCES.glob("*.md")}
    missing = EXPECTED_REFERENCES - present
    assert not missing, f"missing references: {sorted(missing)}"


def test_skill_md_links_resolve() -> None:
    links = set(re.findall(r"(?:references|assets/examples)/[\w.-]+", _skill_text()))
    assert links, "SKILL.md should link to references"
    broken = sorted(link for link in links if not (SKILL_DIR / link).exists())
    assert not broken, f"broken links in SKILL.md: {broken}"


def test_skill_md_stays_a_router() -> None:
    assert len(_skill_text().splitlines()) <= 200, "SKILL.md should stay <= 200 lines"


def test_agent_safety_rule_before_examples() -> None:
    content = _skill_text()
    rule = content.find("## ⚠️ Agent safety rule")
    assert rule != -1, "agent safety section missing"
    section = content[rule : content.find("\n## ", rule + 1)]
    assert "--plain" in section and "Pipe" in section and ".exit" in section
    for later in ("## Which command", "## Recommended agent workflow", "## Cheat sheet"):
        assert rule < content.find(later), f"safety rule must come before {later!r}"
    assert "ROBOTCODE_FORCE_AI_AGENT" in _all_text()


def test_gotchas_are_version_stamped() -> None:
    gotchas = (REFERENCES / "gotchas.md").read_text(encoding="utf-8")
    assert "2.7.0" in gotchas
    rows = [ln for ln in gotchas.splitlines() if re.match(r"^\| \d+ \|", ln)]
    assert len(rows) == 14, f"expected 14 limitations, found {len(rows)}"


def test_critical_traps_inline_in_skill_md() -> None:
    content = _skill_text().lower()
    assert "output directory" in content
    assert ".save" in content and "failed" in content
    assert ".break" in content and "quotes" in content
    assert "exit code is always 0" in content


def test_secrets_warning_present() -> None:
    blob = (REFERENCES / "repl.md").read_text(encoding="utf-8") + (
        REFERENCES / "agent-mode.md"
    ).read_text(encoding="utf-8")
    assert "plain text" in blob and "password" in blob


def test_fallback_to_script_skills() -> None:
    content = _skill_text()
    for skill in ("rf-results", "rf-libdoc-search", "rf-libdoc-explain"):
        assert skill in content, f"companion fallback {skill} missing"


@pytest.mark.parametrize(
    "skill_dir",
    [
        "robotframework-results",
        "robotframework-libdoc-search",
        "robotframework-libdoc-explain",
    ],
)
def test_script_skills_link_back(skill_dir: str) -> None:
    content = (ROOT / "skills" / skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "rf-robotcode" in content, f"{skill_dir} must point to rf-robotcode"
    assert "scripts/" in content, f"{skill_dir} must keep its script usage"


# --- CLI fidelity (skip if robotcode absent) ------------------------------


def _help(*cmd: str) -> str:
    result = subprocess.run(
        [_ROBOTCODE, *cmd, "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        # Some help texts contain non-ASCII (e.g. "→"); on Windows a piped
        # stdout defaults to cp1252 and robotcode crashes while printing.
        env={**os.environ, "NO_COLOR": "1", "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )
    assert result.returncode == 0, f"`robotcode {' '.join(cmd)} --help` failed: {result.stderr}"
    return result.stdout


def _listed_commands(help_text: str) -> set[str]:
    names: set[str] = set()
    in_section = False
    for line in help_text.splitlines():
        if line.strip() in ("Commands:", "Aliases:"):
            in_section = True
            continue
        if in_section:
            m = re.match(r"^  (\S+)\s", line + " ")
            if m:
                names.add(m.group(1))
            elif line and not line.startswith(" "):
                in_section = False
    return names


@pytest.mark.skipif(_ROBOTCODE is None, reason="robotcode not installed")
@pytest.mark.parametrize(
    "cmd", sorted(DOCUMENTED_CLI), ids=lambda c: " ".join(c) or "<root>"
)
def test_documented_command_and_options_exist(cmd: tuple[str, ...]) -> None:
    if cmd:
        parent = _help(*cmd[:-1])
        assert cmd[-1] in _listed_commands(parent), (
            f"`robotcode {' '.join(cmd)}` is not a subcommand"
        )
    options = set(re.findall(r"--[a-z][\w-]*", _help(*cmd)))
    missing = DOCUMENTED_CLI[cmd] - options
    assert not missing, f"`robotcode {' '.join(cmd)}` lacks options: {sorted(missing)}"


@pytest.mark.skipif(_ROBOTCODE is None, reason="robotcode not installed")
def test_documented_aliases_exist() -> None:
    missing = DOCUMENTED_ALIASES - _listed_commands(_help())
    assert not missing, f"missing aliases: {sorted(missing)}"
