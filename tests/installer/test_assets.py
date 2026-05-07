"""Verify the bundled asset tree is reachable at runtime."""

from __future__ import annotations

from rf_agentskills import _assets


def test_asset_root_exists() -> None:
    with _assets.asset_root_path() as root:
        assert root.is_dir()
        assert (root / "skills").is_dir()
        assert (root / "agents").is_dir()
        assert (root / "hooks" / "hooks.json").is_file()


def test_asset_files_walks_all_categories() -> None:
    files = list(_assets.asset_files())
    assert len(files) > 50, f"expected the full bundle ({len(files)} found)"


def test_asset_files_filtered_by_category() -> None:
    skills = list(_assets.asset_files("skills"))
    agents = list(_assets.asset_files("agents"))
    assert len(skills) > 10
    assert 1 <= len(agents) <= 20
    assert all(f.suffix == ".md" for f in agents)


def test_skill_md_exists_for_known_skill() -> None:
    files = list(_assets.asset_files("skills", "libdoc-search"))
    assert any(f.name == "SKILL.md" for f in files)
