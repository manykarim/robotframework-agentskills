"""Tests for the rf-platynui skill.

Two layers:

1. **Structural** (always run) — the skill directory, frontmatter, references,
   and examples exist and the skill documents the correct library
   (``PlatynUI.BareMetal``, not the placeholder ``PlatynUI``).

2. **Keyword fidelity** (run when ``PlatynUI`` is installed, else skipped) —
   every keyword name the skill claims must be a real keyword in
   ``PlatynUI.BareMetal`` per ``robot.libdoc``. libdoc is display-free (the
   native runtime is lazy), so installing ``robotframework-PlatynUI`` in CI is
   enough — no desktop/AT-SPI needed. Verified against 0.12.0.dev330.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "robotframework-platynui-skill"
SKILL_MD = SKILL_DIR / "SKILL.md"

# The PlatynUI.BareMetal keyword names the skill documents (keywords-reference.md).
# This list IS the skill's claim; the fidelity test checks it against the library.
DOCUMENTED_KEYWORDS = {
    "Activate Window",
    "Bring To Front",
    "Close Window",
    "Focus",
    "Get Attribute",
    "Get Pointer Position",
    "Highlight",
    "Keyboard Press",
    "Keyboard Release",
    "Keyboard Type",
    "Maximize Window",
    "Minimize Window",
    "Move And Resize Window",
    "Move Window",
    "Pointer Click",
    "Pointer Move To",
    "Pointer Multi Click",
    "Pointer Press",
    "Pointer Release",
    "Query",
    "Resize Window",
    "Restore Window",
    "Set Root",
    "Take Screenshot",
}

_PLATYNUI_INSTALLED = importlib.util.find_spec("PlatynUI") is not None


# --- Structural (always) --------------------------------------------------


def test_skill_structure_exists() -> None:
    assert SKILL_MD.is_file(), "SKILL.md missing"
    assert (SKILL_DIR / "references").is_dir(), "references/ missing"
    assert (SKILL_DIR / "assets" / "examples").is_dir(), "assets/examples/ missing"
    # At least one reference and one example.
    assert any((SKILL_DIR / "references").glob("*.md"))
    assert any((SKILL_DIR / "assets" / "examples").glob("*.robot"))


def test_skill_frontmatter() -> None:
    content = SKILL_MD.read_text(encoding="utf-8")
    assert content.startswith("---"), "missing frontmatter"
    end = content.find("---", 3)
    assert end != -1, "unclosed frontmatter"
    fm = content[3:end]
    assert "name: rf-platynui" in fm, "frontmatter name must be rf-platynui"
    assert "description:" in fm and "PlatynUI" in fm


def test_skill_documents_baremetal_not_placeholder() -> None:
    content = SKILL_MD.read_text(encoding="utf-8")
    assert "PlatynUI.BareMetal" in content, "skill must document PlatynUI.BareMetal"
    # The footgun + placeholder status must be disclosed somewhere in the skill.
    refs = " ".join(p.read_text(encoding="utf-8") for p in SKILL_DIR.rglob("*.md"))
    blob = content + refs
    assert "placeholder" in blob.lower(), "must note the high-level PlatynUI is a placeholder"
    assert "--pre" in blob or "0.12.0.dev" in blob, "must disclose the pre-release install"


# --- Keyword fidelity (skip if PlatynUI absent) ---------------------------


@pytest.mark.skipif(not _PLATYNUI_INSTALLED, reason="PlatynUI not installed")
def test_documented_keywords_exist_in_library() -> None:
    from robot import libdoc

    ld = libdoc.LibraryDocumentation("PlatynUI.BareMetal")
    actual = {k.name for k in ld.keywords}
    missing = DOCUMENTED_KEYWORDS - actual
    assert not missing, (
        f"skill documents keywords absent from PlatynUI.BareMetal "
        f"{ld.version}: {sorted(missing)}"
    )


@pytest.mark.skipif(not _PLATYNUI_INSTALLED, reason="PlatynUI not installed")
def test_high_level_platynui_is_placeholder() -> None:
    """Guards that we are pinned to new_core: the high-level PlatynUI library is
    a single-keyword placeholder there (sanity that the docs match reality)."""
    from robot import libdoc

    ld = libdoc.LibraryDocumentation("PlatynUI")
    names = {k.name for k in ld.keywords}
    assert names == {"Dummy Keyword"}, (
        f"expected the placeholder PlatynUI library, got keywords: {sorted(names)}"
    )
