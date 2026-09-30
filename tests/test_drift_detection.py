"""Verify root skill scripts stay in sync with plugin copies, and that the
drift check rejects orphaned distribution copies (skill-catalog spec) and
content/identity drift (skill-metadata-conformance spec)."""
import shutil
import subprocess
from pathlib import Path

import pytest
from _shell import BASH, requires_posix_bash

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_SCRIPTS = ROOT / "plugins" / "rf-agentskills" / "scripts"
PLUGIN_SKILLS = ROOT / "plugins" / "rf-agentskills" / "skills"


def _root_scripts() -> list[Path]:
    """Non-symlink skills/*/scripts/*.py — the same derivation as the scripts."""
    return sorted(
        p for p in ROOT.glob("skills/*/scripts/*.py") if p.is_file() and not p.is_symlink()
    )


def test_script_map_is_derived_from_root():
    names = {p.name for p in _root_scripts()}
    assert {"rf_libdoc.py", "rf_results.py"} <= names
    # The merged libdoc skill owns the single regular-file copy.
    assert ROOT / "skills" / "rf-libdoc" / "scripts" / "rf_libdoc.py" in _root_scripts()


def test_root_and_plugin_scripts_in_sync():
    """Root skill scripts must be identical to the plugin's per-skill copies."""
    for root_path in _root_scripts():
        skill = root_path.parent.parent.name
        plugin_path = PLUGIN_SKILLS / skill / "scripts" / root_path.name
        assert plugin_path.is_file(), f"Missing plugin script: {plugin_path.relative_to(ROOT)}"
        assert not plugin_path.is_symlink()
        assert root_path.read_text() == plugin_path.read_text(), (
            f"DRIFT DETECTED: {root_path.relative_to(ROOT)} differs from "
            f"{plugin_path.relative_to(ROOT)}. Run: bash scripts/sync-skills.sh"
        )


def test_no_flat_plugin_python_scripts():
    """Scripts ship per skill; the plugin scripts/ dir holds only hook .mjs files."""
    flat = sorted(p.name for p in PLUGIN_SCRIPTS.glob("*.py"))
    assert not flat, f"flat plugin scripts must not exist: {flat}"
    assert all(p.suffix == ".mjs" for p in PLUGIN_SCRIPTS.iterdir() if p.is_file())


@pytest.fixture
def scratch_repo(tmp_path: Path) -> Path:
    """A minimal copy of the repo tree the sync/drift scripts operate on."""
    dst = tmp_path / "repo"
    (dst / "vscode-extension").mkdir(parents=True)
    shutil.copytree(ROOT / "skills", dst / "skills", symlinks=True)
    shutil.copytree(ROOT / "scripts", dst / "scripts")
    shutil.copytree(
        ROOT / "plugins", dst / "plugins", ignore=shutil.ignore_patterns("__pycache__")
    )
    shutil.copytree(ROOT / "vscode-extension" / "skills", dst / "vscode-extension" / "skills")
    shutil.copy2(ROOT / "vscode-extension" / "package.json", dst / "vscode-extension" / "package.json")
    return dst


def _drift(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [BASH, str(repo / "scripts" / "check-drift.sh")],
        capture_output=True, text=True, env={"REPO_ROOT": str(repo), "PATH": "/usr/bin:/bin"},
    )


@requires_posix_bash
def test_drift_check_clean_tree_passes(scratch_repo: Path):
    res = _drift(scratch_repo)
    assert res.returncode == 0, res.stdout + res.stderr


@requires_posix_bash
@pytest.mark.parametrize(
    "orphan",
    [
        "plugins/rf-agentskills/skills/rf-orphan/SKILL.md",
        "plugins/rf-agentskills/scripts/retired_helper.py",
        "vscode-extension/skills/rf-orphan/SKILL.md",
    ],
)
def test_drift_check_names_orphan(scratch_repo: Path, orphan: str):
    target = scratch_repo / orphan
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("orphan\n")
    res = _drift(scratch_repo)
    assert res.returncode == 1, res.stdout
    expected = orphan.split("/SKILL.md")[0]
    assert f"ORPHAN: {expected}" in res.stdout


@requires_posix_bash
def test_sync_prunes_removed_root_skill(scratch_repo: Path):
    shutil.rmtree(scratch_repo / "skills" / "rf-results")
    subprocess.run(
        [BASH, str(scratch_repo / "scripts" / "sync-skills.sh")],
        check=True, capture_output=True, text=True,
    )
    assert not (scratch_repo / "plugins/rf-agentskills/skills/rf-results").exists()
    assert not (scratch_repo / "plugins/rf-agentskills/skills/rf-results/scripts/rf_results.py").exists()
    assert not (scratch_repo / "vscode-extension/skills/rf-results").exists()
    assert "rf-results" not in (scratch_repo / "vscode-extension/package.json").read_text()
    # Plugin-owned hook scripts are never pruned.
    assert (scratch_repo / "plugins/rf-agentskills/scripts/validate_robot.mjs").exists()
    assert _drift(scratch_repo).returncode == 0


@requires_posix_bash
@pytest.mark.parametrize(
    "tree",
    [
        "skills/rf-libdoc/scripts",
        "plugins/rf-agentskills/skills/rf-libdoc",
        "plugins/rf-agentskills/skills/rf-libdoc/scripts",
        "plugins/rf-agentskills/scripts",
        "vscode-extension/skills/rf-libdoc/scripts",
    ],
)
def test_drift_check_rejects_symlinks(scratch_repo: Path, tree: str):
    link = scratch_repo / tree / "linked.md"
    link.symlink_to(scratch_repo / "skills" / "rf-libdoc" / "SKILL.md")
    res = _drift(scratch_repo)
    assert res.returncode == 1, res.stdout
    assert f"SYMLINK: {tree}/linked.md" in res.stdout


@requires_posix_bash
def test_drift_check_compares_vscode_script_copy(scratch_repo: Path):
    copy = scratch_repo / "vscode-extension/skills/rf-libdoc/scripts/rf_libdoc.py"
    copy.write_text(copy.read_text() + "# drift\n")
    res = _drift(scratch_repo)
    assert res.returncode == 1, res.stdout
    assert "DRIFT: skills/rf-libdoc/scripts/rf_libdoc.py != vscode-extension/skills/rf-libdoc/scripts/rf_libdoc.py" in res.stdout


def _sync(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [BASH, str(repo / "scripts" / "sync-skills.sh")], capture_output=True, text=True,
    )


def test_channels_use_root_dir_names():
    """One identifier per skill: all three channels hold the same rf-* dir names."""
    root = {p.name for p in (ROOT / "skills").iterdir() if p.is_dir()}
    plugin = {p.name for p in (ROOT / "plugins/rf-agentskills/skills").iterdir() if p.is_dir()}
    vscode = {p.name for p in (ROOT / "vscode-extension/skills").iterdir() if p.is_dir()}
    assert root == plugin == vscode
    assert all(name.startswith("rf-") for name in root), root


@requires_posix_bash
def test_sync_renamed_root_skill_leaves_no_stale_copy(scratch_repo: Path):
    old, new = scratch_repo / "skills" / "rf-results", scratch_repo / "skills" / "rf-run-results"
    old.rename(new)
    md = new / "SKILL.md"
    md.write_text(md.read_text().replace("name: rf-results", "name: rf-run-results", 1))
    res = _sync(scratch_repo)
    assert res.returncode == 0, res.stdout + res.stderr
    for channel in ("plugins/rf-agentskills/skills", "vscode-extension/skills"):
        assert not (scratch_repo / channel / "rf-results").exists()
        assert "name: rf-run-results" in (scratch_repo / channel / "rf-run-results" / "SKILL.md").read_text()
    assert _drift(scratch_repo).returncode == 0


@requires_posix_bash
def test_sync_rejects_name_dir_mismatch(scratch_repo: Path):
    md = scratch_repo / "skills" / "rf-results" / "SKILL.md"
    md.write_text(md.read_text().replace("name: rf-results", "name: results", 1))
    res = _sync(scratch_repo)
    assert res.returncode == 1
    assert "skills/rf-results/SKILL.md has name: 'results'" in res.stderr
    drift = _drift(scratch_repo)
    assert drift.returncode == 1
    assert "NAME MISMATCH: skills/rf-results/SKILL.md" in drift.stdout


@requires_posix_bash
@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("plugins/rf-agentskills/skills/rf-results/SKILL.md",
         "DRIFT: skills/rf-results/SKILL.md != plugins/rf-agentskills/skills/rf-results/SKILL.md"),
        ("vscode-extension/skills/rf-setup/SKILL.md",
         "DRIFT: skills/rf-setup/SKILL.md != vscode-extension/skills/rf-setup/SKILL.md"),
        ("plugins/rf-agentskills/skills/rf-setup/references/new.md",
         "DRIFT: skills/rf-setup/references/ != plugins/rf-agentskills/skills/rf-setup/references/"),
    ],
)
def test_drift_check_compares_skill_content(scratch_repo: Path, path: str, expected: str):
    target = scratch_repo / path
    target.write_text((target.read_text() if target.exists() else "") + "drift\n")
    res = _drift(scratch_repo)
    assert res.returncode == 1, res.stdout
    assert expected in res.stdout


@requires_posix_bash
def test_drift_check_reports_missing_channel_copy(scratch_repo: Path):
    shutil.rmtree(scratch_repo / "plugins/rf-agentskills/skills/rf-browser")
    res = _drift(scratch_repo)
    assert res.returncode == 1
    assert "MISSING: plugins/rf-agentskills/skills/rf-browser/" in res.stdout


@requires_posix_bash
def test_drift_check_compares_plugin_script_copy(scratch_repo: Path):
    copy = scratch_repo / "plugins/rf-agentskills/skills/rf-results/scripts/rf_results.py"
    copy.write_text(copy.read_text() + "# drift\n")
    res = _drift(scratch_repo)
    assert res.returncode == 1, res.stdout
    assert ("DRIFT: skills/rf-results/scripts/rf_results.py != "
            "plugins/rf-agentskills/skills/rf-results/scripts/rf_results.py") in res.stdout


@requires_posix_bash
def test_sync_copies_scripts_per_skill_and_rewrites_commands(scratch_repo: Path):
    flat = scratch_repo / "plugins/rf-agentskills/scripts/rf_libdoc.py"
    flat.write_text("# stale flat copy\n")
    res = _sync(scratch_repo)
    assert res.returncode == 0, res.stdout + res.stderr
    assert not flat.exists()
    plugin_skill = scratch_repo / "plugins/rf-agentskills/skills/rf-libdoc"
    assert (plugin_skill / "scripts" / "rf_libdoc.py").is_file()
    text = (plugin_skill / "SKILL.md").read_text()
    assert 'uv run python "${CLAUDE_SKILL_DIR}/scripts/rf_libdoc.py"' in text
    assert "${CLAUDE_PLUGIN_ROOT}" not in text
    assert (scratch_repo / "vscode-extension/skills/rf-libdoc/scripts/rf_libdoc.py").is_file()
    assert _drift(scratch_repo).returncode == 0


def _append_line(repo: Path, rel: str, line: str) -> None:
    md = repo / rel
    md.write_text(md.read_text() + "\n" + line + "\n")


@requires_posix_bash
@pytest.mark.parametrize(
    ("rel", "line", "expected"),
    [
        ("skills/rf-results/SKILL.md", "python scripts/rf_results.py --output output.xml",
         "BARE PYTHON: skills/rf-results/SKILL.md"),
        ("vscode-extension/skills/rf-libdoc/SKILL.md", "`python3 scripts/rf_libdoc.py --library X`",
         "BARE PYTHON: vscode-extension/skills/rf-libdoc/SKILL.md"),
        ("plugins/rf-agentskills/skills/rf-libdoc/SKILL.md",
         'python "${CLAUDE_SKILL_DIR}/scripts/rf_libdoc.py" --library X',
         "BARE PYTHON: plugins/rf-agentskills/skills/rf-libdoc/SKILL.md"),
        ("plugins/rf-agentskills/skills/rf-results/SKILL.md",
         'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/rf_results.py" --output output.xml',
         "PLUGIN_ROOT IN SKILL.md: plugins/rf-agentskills/skills/rf-results/SKILL.md"),
        ("skills/rf-setup/SKILL.md", "See ${CLAUDE_PLUGIN_ROOT}/scripts.",
         "PLUGIN_ROOT IN SKILL.md: skills/rf-setup/SKILL.md"),
    ],
)
def test_drift_check_rejects_wrong_command_form(scratch_repo: Path, rel: str, line: str, expected: str):
    _append_line(scratch_repo, rel, line)
    res = _drift(scratch_repo)
    assert res.returncode == 1, res.stdout
    assert expected in res.stdout


@requires_posix_bash
def test_drift_check_accepts_project_env_command_forms(scratch_repo: Path):
    for line in (
        "uv run python scripts/rf_results.py --output output.xml",
        "`.venv/bin/python scripts/rf_results.py …` or `poetry run python scripts/rf_results.py …`",
    ):
        _append_line(scratch_repo, "skills/rf-results/SKILL.md", line)
    assert _sync(scratch_repo).returncode == 0
    res = _drift(scratch_repo)
    assert res.returncode == 0, res.stdout
