"""Tests for the manifest module: round-trip, hash detection, prune."""

from __future__ import annotations

from pathlib import Path

from rf_agentskills import manifest as _m


def test_save_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "installed.json"
    m = _m.Manifest()
    m.upsert(
        _m.Installation(
            agent="claude-code",
            scope="user",
            installed_at="2026-05-07T00:00:00Z",
            bundle_version="0.3.0",
            files=[_m.FileEntry(path="/x/y", sha256="deadbeef", transform=None)],
            config_merges=[
                _m.ConfigMerge(
                    path="/x/.mcp.json",
                    added_keys=["rf-tools"],
                    kind="json_nested",
                    key_path=["mcpServers"],
                )
            ],
        )
    )
    m.save(path)
    loaded = _m.Manifest.load(path)

    assert len(loaded.installations) == 1
    ins = loaded.installations[0]
    assert ins.agent == "claude-code"
    assert ins.files[0].sha256 == "deadbeef"
    cm = ins.config_merges[0]
    assert cm.kind == "json_nested"
    assert cm.key_path == ["mcpServers"]


def test_load_handles_missing_file(tmp_path: Path) -> None:
    m = _m.Manifest.load(tmp_path / "does-not-exist.json")
    assert m.installations == []


def test_load_handles_corrupt_file(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.json"
    path.write_text("{not json")
    m = _m.Manifest.load(path)
    assert m.installations == []


def test_load_tolerates_old_schema_without_kind(tmp_path: Path) -> None:
    """Pre-existing manifests written before kind/key_path got added."""
    path = tmp_path / "old.json"
    path.write_text(
        '{"version": 1, "installations": [{'
        '"agent":"x", "scope":"user", "installed_at":"", "bundle_version":"0.0.1",'
        '"files":[], "config_merges":[{"path":"/x", "added_keys":["k"]}]}]}'
    )
    m = _m.Manifest.load(path)
    cm = m.installations[0].config_merges[0]
    # Defaults backfilled
    assert cm.kind == "json_top"
    assert cm.key_path == []


def test_upsert_replaces_same_agent_scope(tmp_path: Path) -> None:
    path = tmp_path / "m.json"
    m = _m.Manifest()
    m.upsert(_m.Installation(agent="a", scope="user", installed_at="t1",
                             bundle_version="v1"))
    m.upsert(_m.Installation(agent="a", scope="user", installed_at="t2",
                             bundle_version="v2"))
    # Different scope = separate entry
    m.upsert(_m.Installation(agent="a", scope="project", installed_at="t3",
                             bundle_version="v3"))
    m.save(path)

    loaded = _m.Manifest.load(path)
    assert len(loaded.installations) == 2
    user_entry = loaded.for_agent("a", "user")
    assert user_entry is not None
    assert user_entry.installed_at == "t2"


def test_remove_returns_dropped(tmp_path: Path) -> None:
    m = _m.Manifest()
    m.upsert(_m.Installation(agent="a", scope="user", installed_at="t",
                             bundle_version="v"))
    dropped = m.remove("a", "user")
    assert dropped is not None
    assert dropped.agent == "a"
    assert m.installations == []
    # second remove is a no-op
    assert m.remove("a", "user") is None


def test_is_user_modified_detects_edit(tmp_path: Path) -> None:
    f = tmp_path / "a.txt"
    f.write_text("hello")
    entry = _m.file_entry_for(f)
    assert not _m.is_user_modified(entry)

    f.write_text("hello!")
    assert _m.is_user_modified(entry)


def test_is_user_modified_treats_missing_as_unchanged(tmp_path: Path) -> None:
    """A deleted file shouldn't pretend to be 'user-modified'."""
    f = tmp_path / "gone.txt"
    f.write_text("x")
    entry = _m.file_entry_for(f)
    f.unlink()
    assert not _m.is_user_modified(entry)


def test_files_to_remove_skips_user_modified(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"; a.write_text("aaa")
    b = tmp_path / "b.txt"; b.write_text("bbb")
    ins = _m.Installation(agent="x", scope="user", installed_at="", bundle_version="")
    ins.files = [_m.file_entry_for(a), _m.file_entry_for(b)]
    # User modifies one of them
    a.write_text("aaaaaaaaa")

    removable = list(_m.files_to_remove(ins))
    assert removable == [b]


def test_prune_empty_parents_stops_at_home(tmp_path: Path) -> None:
    leaf = tmp_path / "a" / "b" / "c" / "skill.md"
    leaf.parent.mkdir(parents=True)
    leaf.write_text("x")
    leaf.unlink()
    _m.prune_empty_parents(leaf, stop_at=tmp_path)
    # Empty parents removed up to but not including tmp_path
    assert not (tmp_path / "a").exists()
    assert tmp_path.exists()
