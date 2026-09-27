"""Tests for the rf-setup skill.

Two layers:

1. **Structural** (always run) — directory, frontmatter, references, the
   tool-detection table, Python floors, the no-global-install rule and the
   companion-skill links are present.

2. **Example validity** — the TOML examples parse, the smoke test passes
   ``robot --dryrun`` (skipped if Robot Framework is absent) and the GitHub
   Actions example is valid YAML (skipped if PyYAML is absent). The install
   recipes themselves were run manually against uv 0.9.26 / Poetry 2.4.1 /
   pip 26 on 2026-09-26; they need network access and minutes, so CI doesn't
   repeat them.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

try:  # Python 3.11+; the CI matrix still includes 3.10
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]

needs_tomllib = pytest.mark.skipif(tomllib is None, reason="tomllib needs Python 3.11+")

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "robotframework-setup-skill"
SKILL_MD = SKILL_DIR / "SKILL.md"
REFERENCES = SKILL_DIR / "references"
EXAMPLES = SKILL_DIR / "assets" / "examples"

EXPECTED_REFERENCES = {
    "uv.md",
    "venv-pip.md",
    "poetry.md",
    "cli-tools.md",
    "libraries.md",
    "project-layout.md",
    "ci.md",
    "troubleshooting.md",
}

COMPANION_SKILLS = {
    "rf-browser",
    "rf-selenium",
    "rf-appium",
    "rf-requests",
    "rf-restinstance",
    "rf-platynui",
    "rf-robotcode",
}


def _skill_text() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


# --- Structural (always) --------------------------------------------------


def test_skill_structure_exists() -> None:
    assert SKILL_MD.is_file(), "SKILL.md missing"
    assert REFERENCES.is_dir(), "references/ missing"
    assert EXAMPLES.is_dir(), "assets/examples/ missing"
    assert any(EXAMPLES.iterdir()), "assets/examples/ is empty"


def test_skill_frontmatter() -> None:
    content = _skill_text()
    assert content.startswith("---"), "missing frontmatter"
    end = content.find("---", 3)
    assert end != -1, "unclosed frontmatter"
    fm = content[3:end]
    assert "name: rf-setup" in fm, "frontmatter name must be rf-setup"
    desc = fm.split("description:", 1)[1].lower()
    for word in ("install", "uv", "venv", "poetry"):
        assert word in desc, f"description should mention {word!r}"


def test_all_references_present() -> None:
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


def test_detection_table_maps_lockfiles_to_tools() -> None:
    content = _skill_text()
    rows = [ln for ln in content.splitlines() if ln.startswith("|")]
    def row_with(marker: str) -> str:
        return next((r for r in rows if marker in r), "")
    assert "uv" in row_with("uv.lock")
    assert "Poetry" in row_with("poetry.lock")
    assert "pip" in row_with("requirements")
    assert "uv" in row_with("New project") or "uv" in row_with("Nothing")


def test_python_floors_and_recommendation() -> None:
    content = _skill_text()
    assert "Python 3.12" in content
    assert "2026-09-26" in content, "floors must carry the date they were checked"
    for floor in ("3.10", "3.11", "3.12"):
        assert floor in content


def test_no_global_install_rule() -> None:
    content = _skill_text()
    assert "sudo pip" in content
    assert "pipx" in content and "uv tool" in content
    # Every documented install command in SKILL.md targets a project env.
    for line in content.splitlines():
        stripped = line.strip()
        assert not stripped.startswith("pip install"), f"bare pip install: {line}"
        assert not stripped.startswith("sudo "), f"sudo command: {line}"


def test_companion_skills_linked() -> None:
    content = _skill_text()
    missing = {s for s in COMPANION_SKILLS if s not in content}
    assert not missing, f"missing companion skills: {sorted(missing)}"


def test_troubleshooting_covers_required_problems() -> None:
    text = (REFERENCES / "troubleshooting.md").read_text(encoding="utf-8").lower()
    for topic in ("wrong interpreter", "externally-managed-environment", "rfbrowser",
                  "python too old", "powershell"):
        assert topic in text, f"troubleshooting lacks {topic!r}"


def test_venv_activation_for_all_shells() -> None:
    text = (REFERENCES / "venv-pip.md").read_text(encoding="utf-8")
    for cmd in ("source .venv/bin/activate", "Activate.ps1", "activate.bat", ".venv/bin/python -m"):
        assert cmd in text, f"venv-pip.md lacks {cmd!r}"


def test_browser_documents_both_install_paths() -> None:
    text = (REFERENCES / "libraries.md").read_text(encoding="utf-8")
    assert "robotframework-browser[bb]" in text and "rfbrowser install" in text
    assert "rfbrowser init" in text and "Browser.entry" in text


def test_robotcode_skill_links_back() -> None:
    content = (ROOT / "skills" / "robotframework-robotcode-skill" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "rf-setup" in content


# --- Example validity -----------------------------------------------------


@needs_tomllib
@pytest.mark.parametrize("name", ["pyproject.uv.toml", "pyproject.poetry.toml", "robot.toml"])
def test_toml_examples_parse(name: str) -> None:
    with (EXAMPLES / name).open("rb") as fh:
        data = tomllib.load(fh)
    assert data, f"{name} is empty"


@needs_tomllib
def test_poetry_example_uses_non_package_mode() -> None:
    with (EXAMPLES / "pyproject.poetry.toml").open("rb") as fh:
        data = tomllib.load(fh)
    assert data["tool"]["poetry"]["package-mode"] is False


@needs_tomllib
def test_uv_example_pins_python_floor() -> None:
    with (EXAMPLES / "pyproject.uv.toml").open("rb") as fh:
        data = tomllib.load(fh)
    assert data["project"]["requires-python"] == ">=3.12"
    assert "dev" in data["dependency-groups"]


@pytest.mark.skipif(importlib.util.find_spec("robot") is None, reason="robotframework not installed")
def test_smoke_example_passes_dryrun(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "robot", "--dryrun", "--outputdir", str(tmp_path),
         str(EXAMPLES / "smoke.robot")],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_github_actions_example_is_valid_yaml() -> None:
    yaml = pytest.importorskip("yaml")
    data = yaml.safe_load((EXAMPLES / "github-actions-robot.yml").read_text(encoding="utf-8"))
    steps = data["jobs"]["robot"]["steps"]
    runs = " ".join(step.get("run", "") for step in steps)
    assert "uv sync --locked" in runs and "uv run robot" in runs
