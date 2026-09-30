"""CI preflight path mapping (task 7.1) and workflow structure (7.2-7.4)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from rf_skill_eval import cli
from rf_skill_eval.application.preflight import frontmatter_description, map_changed_paths

_REPO = Path(__file__).resolve().parents[2]
_DIRS = {"rf-browser": "rf-browser", "rf-selenium": "rf-selenium", "rf-requests": "rf-requests"}
_TASKS = {"eval/tasks/narrow/narrow-browser-login-01.yaml": "rf-browser"}
_FIXTURES = {"sut-api": {"rf-requests", "rf-restinstance"}}
runner = CliRunner()


def _map(paths: list[str], changed: set[str] | None = None):  # type: ignore[no-untyped-def]
    return map_changed_paths(
        paths,
        dir_to_skill=_DIRS,
        task_skill=_TASKS.get,
        fixture_skills=_FIXTURES,
        description_changed=lambda p: p in (changed or set()),
    )


@pytest.mark.parametrize(
    ("paths", "skills"),
    [
        (["skills/rf-selenium/references/locators.md"], {"rf-selenium"}),
        (["plugins/rf-agentskills/skills/rf-selenium/SKILL.md"], {"rf-selenium"}),
        (["vscode-extension/skills/rf-browser/SKILL.md"], {"rf-browser"}),
        (["eval/tasks/narrow/narrow-browser-login-01.yaml"], {"rf-browser"}),
        (["eval/fixtures/sut-api/libraries/ApiServer.py"], {"rf-requests", "rf-restinstance"}),
        (["plugins/rf-agentskills/hooks/hooks.json"], {"plugin"}),
        (["README.md", "docs/ci/usage.md"], set()),
    ],
)
def test_changed_paths_map_to_skills(paths: list[str], skills: set[str]) -> None:
    result = _map(paths)
    assert result.skills == skills
    assert result.full_tier is False


def test_harness_change_selects_full_narrow_tier() -> None:
    result = _map(["src/rf_skill_eval/cli.py", "skills/rf-browser/SKILL.md"])
    assert result.full_tier is True
    assert result.skills_arg() == ""
    assert result.github_outputs()["full_tier"] == "true"


def test_scoped_run_always_includes_canaries() -> None:
    assert _map(["skills/rf-selenium/SKILL.md"]).skills_arg() == "plugin,rf-selenium"


def test_description_change_triggers_trigger_eval() -> None:
    result = _map(["skills/rf-browser/SKILL.md"], changed={"skills/rf-browser/SKILL.md"})
    assert result.trigger_skills == {"rf-browser"}
    assert result.github_outputs()["run_triggers"] == "true"
    body_only = _map(["skills/rf-browser/SKILL.md"])
    assert body_only.trigger_skills == set()
    assert body_only.github_outputs()["run_triggers"] == "false"


def test_trigger_set_change_runs_that_set() -> None:
    assert _map(["eval/triggers/rf-requests.yaml"]).trigger_skills == {"rf-requests"}


def test_nothing_relevant_means_no_evals() -> None:
    assert _map(["README.md"]).github_outputs()["run_evals"] == "false"


def test_frontmatter_description() -> None:
    text = '---\nname: x\ndescription: "Writes, fixes: tests"\nlicense: Apache-2.0\n---\nbody\n'
    assert frontmatter_description(text) == "Writes, fixes: tests"
    assert frontmatter_description("no frontmatter") is None
    assert frontmatter_description(None) is None


def test_preflight_cli_with_paths_file(tmp_path: Path) -> None:
    paths = tmp_path / "paths.txt"
    paths.write_text("skills/rf-selenium/SKILL.md\neval/tasks/narrow/narrow-requests-users-01.yaml\n")
    out = tmp_path / "gh_output"
    res = runner.invoke(cli.app, ["preflight", "--paths-file", str(paths),
                                  "--tasks-dir", str(_REPO / "eval" / "tasks"),
                                  "--github-output", str(out)])
    assert res.exit_code == 0, res.stdout
    outputs = dict(line.split("=", 1) for line in out.read_text().splitlines())
    assert outputs["skills"] == "plugin,rf-requests,rf-selenium"
    assert outputs["run_evals"] == "true"
    # without git history a changed SKILL.md is assumed to carry a new description
    assert outputs["trigger_skills"] == "rf-selenium"


# --- workflow structure ----------------------------------------------------------------

_WORKFLOW = _REPO / ".github" / "workflows" / "skill-evaluation.yml"


def _wf() -> dict:  # type: ignore[type-arg]
    return yaml.safe_load(_WORKFLOW.read_text())


def _job_text(job: dict) -> str:  # type: ignore[type-arg]
    parts = [str(v) for v in (job.get("env") or {}).values()]
    parts += [str(step.get("run", "")) for step in job["steps"]]
    parts += [str(step.get("with", "")) for step in job["steps"]]
    return "\n".join(parts)


def test_workflow_is_valid_yaml_with_expected_jobs() -> None:
    wf = _wf()
    assert {"preflight", "pr-eval", "full-eval"} <= set(wf["jobs"])


def test_every_harness_invocation_has_a_cost_cap() -> None:
    text = _WORKFLOW.read_text()
    for cmd in ("run-batch", "trigger"):
        for line in [ln for ln in text.splitlines() if f"rf-skill-eval {cmd}" in ln]:
            block = text[text.index(line):text.index(line) + 800]
            assert "--max-cost-usd" in block, line


def test_pr_job_is_treatment_only_haiku_runs_3_and_gated() -> None:
    wf = _wf()
    text = _job_text(wf["jobs"]["pr-eval"])
    assert "--arms treatment" in text
    assert "--runs 3" in text
    assert '--model "${HAIKU_MODEL}"' in text
    assert wf["env"]["HAIKU_MODEL"] == "claude-haiku-4-5-20251001"
    assert "rf-skill-eval gate" in text
    assert "--split validation" in text


def test_full_job_runs_both_arms_and_uploads_candidate_baseline() -> None:
    text = _job_text(_wf()["jobs"]["full-eval"])
    assert '--arms "${ARMS}"' in text
    assert "'treatment,baseline'" in text
    assert "candidate-baseline" in text
    assert "baseline update" in text


def test_missing_credentials_reported_not_run() -> None:
    text = _WORKFLOW.read_text()
    assert "not run: no credentials" in text


def test_manual_dispatch_inputs() -> None:
    wf = _wf()
    on = wf.get("on") or wf.get(True)  # PyYAML parses bare `on` as True
    inputs = on["workflow_dispatch"]["inputs"]
    assert {"model", "runs", "allow_opus"} <= set(inputs)
    assert "claude-opus-5-5" in inputs["model"]["options"]
    assert "schedule" in on
