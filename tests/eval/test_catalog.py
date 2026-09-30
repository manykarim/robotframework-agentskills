"""Task validity and coverage (strengthen-skill-eval-harness 2.2, 4.2, 4.3, 4.7, 4.8)."""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml
from typer.testing import CliRunner

from rf_skill_eval.application.catalog import coverage, shipped_skills, validate_tasks
from rf_skill_eval.cli import app

_REPO = Path(__file__).resolve().parents[2]
_RETIRED = {
    "keyword-builder",
    "testcase-builder",
    "resource-architect",
    "libdoc-search",
    "libdoc-explain",
    "rf-keyword-builder",
    "rf-testcase-builder",
    "rf-resource-architect",
    "rf-libdoc-search",
    "rf-libdoc-explain",
}
runner = CliRunner()


def _task(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "id": "narrow-x-01",
        "skill": "rf-results",
        "tier": "narrow",
        "prompt": "x",
        "model": "claude-haiku-4-5-20251001",
        "primary_metric": "file_exists",
        "grader_checks": [{"type": "file_exists", "path": "a"}],
    }
    data.update(overrides)
    return data


def _write(dir_: Path, name: str, data: dict[str, object]) -> Path:
    dir_.mkdir(parents=True, exist_ok=True)
    path = dir_ / f"{name}.yaml"
    path.write_text(yaml.safe_dump(data))
    return path


def test_repo_tasks_are_valid() -> None:
    report = validate_tasks(
        _REPO / "eval" / "tasks",
        skills=shipped_skills(_REPO),
        fixtures_root=_REPO / "eval" / "fixtures",
    )
    assert report.ok, report.problems
    assert not {t.skill for _p, t in report.tasks.values()} & _RETIRED


def test_validate_tasks_cli_on_repo_exits_zero() -> None:
    result = runner.invoke(app, ["validate-tasks", str(_REPO / "eval" / "tasks")])
    assert result.exit_code == 0, result.stdout
    assert "task(s) valid" in result.stdout


def test_retired_skill_task_rejected(tmp_path: Path) -> None:
    _write(tmp_path / "narrow", "t", _task(skill="keyword-builder"))
    report = validate_tasks(tmp_path, skills=shipped_skills(_REPO))
    assert not report.ok
    assert any("unknown skill 'keyword-builder'" in p for p in report.problems)


def test_plugin_pseudo_skill_accepted(tmp_path: Path) -> None:
    _write(tmp_path / "narrow", "t", _task(skill="plugin"))
    assert validate_tasks(tmp_path, skills=shipped_skills(_REPO)).ok


def test_old_model_id_rejected_with_permitted_list(tmp_path: Path) -> None:
    _write(tmp_path / "narrow", "t", _task(model="claude-sonnet-4-6"))
    report = validate_tasks(tmp_path, skills=shipped_skills(_REPO))
    assert any("claude-sonnet-5" in p and "Permitted" in p for p in report.problems)


def test_opus_in_yaml_rejected(tmp_path: Path) -> None:
    _write(tmp_path / "narrow", "t", _task(model="claude-opus-5-5"))
    report = validate_tasks(tmp_path, skills=shipped_skills(_REPO))
    assert any("--allow-opus" in p for p in report.problems)


def test_task_without_gating_check_rejected(tmp_path: Path) -> None:
    _write(tmp_path / "narrow", "t", _task(primary_metric=None))
    report = validate_tasks(tmp_path, skills=shipped_skills(_REPO))
    assert any("no gating check" in p for p in report.problems)


def test_rf_mcp_tools_require_declaration(tmp_path: Path) -> None:
    _write(tmp_path / "narrow", "t", _task(allowed_tools=["Read", "mcp__rf-mcp__*"]))
    report = validate_tasks(tmp_path, skills=shipped_skills(_REPO))
    assert any("mcp_servers: [rf-mcp]" in p for p in report.problems)
    _write(tmp_path / "narrow", "t", _task(allowed_tools=["mcp__rf-mcp__*"], mcp_servers=["rf-mcp"]))
    assert validate_tasks(tmp_path, skills=shipped_skills(_REPO)).ok


def test_tier_must_match_directory_and_fixture_must_exist(tmp_path: Path) -> None:
    _write(tmp_path / "realistic", "t", _task(fixture="sut-nowhere"))
    report = validate_tasks(
        tmp_path, skills=shipped_skills(_REPO), fixtures_root=_REPO / "eval" / "fixtures"
    )
    assert any("does not match directory" in p for p in report.problems)
    assert any("sut-nowhere" in p for p in report.problems)


def test_duplicate_ids_rejected(tmp_path: Path) -> None:
    _write(tmp_path / "narrow", "a", _task())
    _write(tmp_path / "narrow", "b", _task())
    assert any("duplicate task id" in p for p in validate_tasks(tmp_path, skills=shipped_skills(_REPO)).problems)


def test_canary_tasks_are_plugin_and_libdoc_tasks_use_merged_name() -> None:
    report = validate_tasks(_REPO / "eval" / "tasks", skills=shipped_skills(_REPO))
    skills = {tid: t.skill for tid, (_p, t) in report.tasks.items()}
    assert skills["narrow-non-rf-control-01"] == "plugin"
    assert skills["narrow-rf-injection-positive-01"] == "plugin"
    assert skills["narrow-libdoc-search-01"] == "rf-libdoc"
    assert skills["narrow-libdoc-search-02-no-mcp"] == "rf-libdoc"


def test_coverage_passes_on_repo() -> None:
    rep = coverage(_REPO, _REPO / "eval" / "tasks", _REPO / "eval" / "triggers")
    assert rep.ok, rep.problems
    assert set(rep.skills) == set(shipped_skills(_REPO))


def test_coverage_cli_passes_on_repo() -> None:
    result = runner.invoke(app, ["coverage", "--repo-root", str(_REPO),
                                 "--tasks-dir", str(_REPO / "eval" / "tasks"),
                                 "--triggers-dir", str(_REPO / "eval" / "triggers")])
    assert result.exit_code == 0, result.stdout


def _mini_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(_REPO / "skills", root / "skills", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(_REPO / "eval" / "tasks", root / "eval" / "tasks")
    shutil.copytree(_REPO / "eval" / "triggers", root / "eval" / "triggers")
    shutil.copytree(_REPO / "eval" / "fixtures", root / "eval" / "fixtures")
    return root


def test_coverage_fails_when_new_skill_lacks_task_and_trigger_set(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    new = root / "skills" / "rf-newskill"
    new.mkdir()
    (new / "SKILL.md").write_text("---\nname: rf-newskill\ndescription: x\n---\n# body\n")
    result = runner.invoke(
        app,
        ["coverage", "--repo-root", str(root), "--tasks-dir", str(root / "eval" / "tasks"),
         "--triggers-dir", str(root / "eval" / "triggers")],
    )
    assert result.exit_code == 1
    assert "skill 'rf-newskill' has no narrow task" in result.stdout
    assert "skill 'rf-newskill' has no trigger set" in result.stdout


def test_coverage_accepts_new_skill_once_covered(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    new = root / "skills" / "rf-newskill"
    new.mkdir()
    (new / "SKILL.md").write_text("---\nname: rf-newskill\ndescription: x\n---\n")
    _write(root / "eval" / "tasks" / "narrow", "narrow-newskill-01", _task(id="narrow-newskill-01", skill="rf-newskill"))
    browser = yaml.safe_load((root / "eval" / "triggers" / "rf-browser.yaml").read_text())
    browser["skill"] = "rf-newskill"
    (root / "eval" / "triggers" / "rf-newskill.yaml").write_text(yaml.safe_dump(browser))
    rep = coverage(root, root / "eval" / "tasks", root / "eval" / "triggers")
    assert rep.ok, rep.problems
