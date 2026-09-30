"""Re-install removes files the bundle no longer ships (installer-uninstall-safety).

A previous install is simulated by planting files on disk and recording
them in the manifest exactly like an older installer would have (with or
without the ``category`` field). Everything runs sandboxed via
``fake_home``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from rf_agentskills import manifest as _m
from rf_agentskills import transforms as _x
from rf_agentskills.cli import main


@pytest.fixture(autouse=True)
def _force_node(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_x, "node_available", lambda: True)


def _manifest_path(home: Path) -> Path:
    return home / "share" / "rf-agentskills" / "installed.json"


def _install(*extra: str) -> int:
    return main(["install", "--agent", "claude-code", "--scope", "user", *extra])


def _record(home: Path) -> _m.Installation:
    rec = _m.Manifest.load(_manifest_path(home)).for_agent("claude-code", "user")
    assert rec is not None
    return rec


def _plant(home: Path, rel: str, text: str = "retired\n", *, category: bool = True) -> Path:
    """Write a file under ~/.claude and add it to the existing manifest record."""
    path = home / ".claude" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    mpath = _manifest_path(home)
    data = json.loads(mpath.read_text(encoding="utf-8"))
    entry = {"path": str(path), "sha256": _m.sha256_file(path), "transform": None}
    if category:
        entry["category"] = _m.category_for_path(path)
    data["installations"][0]["files"].append(entry)
    mpath.write_text(json.dumps(data), encoding="utf-8")
    return path


def _tracked(home: Path) -> set[str]:
    return {f.path for f in _record(home).files}


def test_upgrade_removes_retired_skill(fake_home: Path, capsys) -> None:
    assert _install() == 0
    retired = _plant(fake_home, "skills/retired-generator/SKILL.md")
    retired_script = _plant(fake_home, "rf-agentskills-files/scripts/retired_generator.py")
    capsys.readouterr()

    assert _install() == 0

    assert not retired.exists()
    assert not retired.parent.exists(), "empty skill dir must be pruned"
    assert (fake_home / ".claude" / "skills").is_dir(), "pruning stops below the install root"
    assert not retired_script.exists()
    tracked = _tracked(fake_home)
    assert str(retired) not in tracked and str(retired_script) not in tracked
    assert "2 removed" in capsys.readouterr().out


def test_user_modified_stale_file_is_kept_and_untracked(fake_home: Path, capsys) -> None:
    assert _install() == 0
    retired = _plant(fake_home, "skills/retired-builder/SKILL.md")
    retired.write_text("my own notes\n", encoding="utf-8")  # user edit after install

    assert _install() == 0

    assert retired.read_text(encoding="utf-8") == "my own notes\n"
    assert str(retired) not in _tracked(fake_home)
    assert str(retired) in capsys.readouterr().err.replace("\n", "")

    # A later uninstall must not touch it.
    assert main(["uninstall", "--agent", "claude-code", "--scope", "user"]) == 0
    assert retired.exists()


def test_partial_reinstall_keeps_other_categories(fake_home: Path) -> None:
    assert _install() == 0
    before = _record(fake_home)
    agent_files = [f.path for f in before.files if _m.entry_category(f) == "agents"]
    support_files = [f.path for f in before.files if _m.entry_category(f) == "support"]
    assert agent_files and support_files
    merges_before = {(m.path, m.kind) for m in before.config_merges}
    assert merges_before

    assert _install("--what", "skills") == 0

    after = _record(fake_home)
    tracked = {f.path for f in after.files}
    for path in agent_files + support_files:
        assert Path(path).is_file(), path
        assert path in tracked, path
    assert {(m.path, m.kind) for m in after.config_merges} >= merges_before


def test_partial_reinstall_does_not_prune_unselected_stale(fake_home: Path) -> None:
    assert _install() == 0
    old_agent = _plant(fake_home, "agents/rf-retired-agent.md")

    assert _install("--what", "skills") == 0
    assert old_agent.exists()
    assert str(old_agent) in _tracked(fake_home)

    assert _install() == 0
    assert not old_agent.exists()


def test_dry_run_lists_removals_without_deleting(fake_home: Path, capsys) -> None:
    assert _install() == 0
    retired = _plant(fake_home, "skills/retired-architect/SKILL.md")
    manifest_before = _manifest_path(fake_home).read_text(encoding="utf-8")
    capsys.readouterr()

    assert _install("--dry-run") == 0

    out = capsys.readouterr().out
    assert "remove" in out
    assert out.count("no longer shipped by this bundle") == 1
    assert retired.exists()
    assert _manifest_path(fake_home).read_text(encoding="utf-8") == manifest_before


def test_old_manifest_without_category_is_pruned(fake_home: Path) -> None:
    assert _install() == 0
    # Strip `category` from every entry, as written by installer <= 0.6.0.
    mpath = _manifest_path(fake_home)
    data = json.loads(mpath.read_text(encoding="utf-8"))
    for f in data["installations"][0]["files"]:
        f.pop("category", None)
    mpath.write_text(json.dumps(data), encoding="utf-8")
    retired = _plant(fake_home, "skills/retired-generator/SKILL.md", category=False)
    old_agent = _plant(fake_home, "agents/rf-retired-agent.md", category=False)

    # Old records load fine and derive their category from the path.
    rec = _record(fake_home)
    assert all(f.category is None for f in rec.files)

    assert _install("--what", "skills") == 0
    assert not retired.exists()
    assert old_agent.exists(), "agents are not in scope for a skills-only re-install"


@pytest.mark.parametrize(
    ("path", "category"),
    [
        ("/h/.claude/skills/rf-results/SKILL.md", "skills"),
        ("/h/.claude/skills/rf-results/references/agents.md", "skills"),
        ("/h/.agents/skills/rf-results/SKILL.md", "skills"),
        ("/h/.claude/agents/rf-test-architect.md", "agents"),
        ("/h/.codex/agents/rf-test-architect.toml", "agents"),
        ("/h/.claude/rf-agentskills-files/scripts/rf_libdoc.py", "support"),
        ("/h/.claude/rf-agentskills-files/hooks/hooks.json", "support"),
        ("/h/.codex/hooks.json", "hooks"),
        ("/h/.goosehints", "hints"),
        ("/h/.config/something.json", "other"),
    ],
)
def test_category_for_path(path: str, category: str) -> None:
    assert _m.category_for_path(path) == category


def test_upgrade_from_split_libdoc_skills_installs_merged_skill(fake_home: Path) -> None:
    """A 1.2.0-style install with libdoc-search/ + libdoc-explain/ is upgraded
    to the single merged rf-libdoc skill (libdoc-skill spec)."""
    assert _install() == 0
    old = [
        _plant(fake_home, "skills/libdoc-search/SKILL.md", "---\nname: libdoc-search\n---\n"),
        _plant(fake_home, "skills/libdoc-explain/SKILL.md", "---\nname: libdoc-explain\n---\n"),
    ]

    assert _install() == 0

    for path in old:
        assert not path.exists()
        assert not path.parent.exists(), "old skill dir must be pruned"
    merged = fake_home / ".claude" / "skills" / "rf-libdoc" / "SKILL.md"
    assert merged.is_file()
    assert "name: rf-libdoc" in merged.read_text(encoding="utf-8")
    tracked = _tracked(fake_home)
    assert str(merged) in tracked
    assert not {str(p) for p in old} & tracked


def _downgrade_to_short_names(home: Path) -> dict[str, Path]:
    """Turn the fresh install into what a pre-2.0 bundle left behind: skill
    dirs named by the old plugin short names (``browser/``, ``setup/``, …),
    recorded in the manifest under those paths."""
    skills = home / ".claude" / "skills"
    mapping = {}
    for d in sorted(skills.iterdir()):
        if d.is_dir() and d.name.startswith("rf-"):
            old = skills / d.name.removeprefix("rf-")
            d.rename(old)
            mapping[d.name] = old
    mpath = _manifest_path(home)
    data = json.loads(mpath.read_text(encoding="utf-8"))
    for f in data["installations"][0]["files"]:
        for new_name, old in mapping.items():
            prefix = str(skills / new_name) + os.sep
            if f["path"].startswith(prefix):
                f["path"] = str(old) + os.sep + f["path"][len(prefix):]
    mpath.write_text(json.dumps(data), encoding="utf-8")
    return mapping


def test_upgrade_renames_short_skill_dirs_to_rf_ids(fake_home: Path, capsys) -> None:
    """skill-metadata-conformance: an install from a bundle with short plugin
    dir names (browser/, setup/, …) is migrated to the rf-* dirs."""
    assert _install() == 0
    mapping = _downgrade_to_short_names(fake_home)
    assert {"rf-browser", "rf-setup", "rf-results", "rf-libdoc"} <= set(mapping)
    assert (fake_home / ".claude" / "skills" / "browser" / "SKILL.md").is_file()
    capsys.readouterr()

    assert _install() == 0

    skills = fake_home / ".claude" / "skills"
    for new_name, old in mapping.items():
        assert not old.exists(), f"{old} must be pruned"
        assert (skills / new_name / "SKILL.md").is_file()
    assert sorted(p.name for p in skills.iterdir()) == sorted(mapping)
    tracked = _tracked(fake_home)
    skill_paths = [p for p in tracked if p.startswith(str(skills) + os.sep)]
    assert skill_paths and all(Path(p).relative_to(skills).parts[0].startswith("rf-") for p in skill_paths)
    assert "removed (no longer shipped)" in capsys.readouterr().out


def test_upgrade_keeps_user_edited_legacy_skill_file(fake_home: Path, capsys) -> None:
    assert _install() == 0
    _downgrade_to_short_names(fake_home)
    edited = fake_home / ".claude" / "skills" / "browser" / "SKILL.md"
    edited.write_text(edited.read_text(encoding="utf-8") + "\nmy team notes\n", encoding="utf-8")
    capsys.readouterr()

    assert _install() == 0

    assert edited.is_file() and "my team notes" in edited.read_text(encoding="utf-8")
    assert str(edited) in capsys.readouterr().err.replace("\n", "")
    assert str(edited) not in _tracked(fake_home)
    assert (fake_home / ".claude" / "skills" / "rf-browser" / "SKILL.md").is_file()
    # Unedited files of the same legacy dir are still pruned.
    assert not (fake_home / ".claude" / "skills" / "browser" / "references").exists()
