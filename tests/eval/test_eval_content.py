"""Fixtures, narrow/adversarial tasks and their graders (tasks 4.4-4.6).

Live model runs are not executed here. Instead every new task is graded with
the real grader against (a) the unmodified fixture — the gating checks must
produce ``passed``/``failed``, never ``skipped`` — and (b) a reference
("golden") solution overlaid on the fixture, which must pass the gate.
Adversarial tasks also get a "bad" solution that falls for the temptation and
must fail the gate. Browser/Selenium runs need Chromium/Chrome; they are the
same prerequisites the CI eval job installs (``rfbrowser init``).
"""

from __future__ import annotations

import importlib.util
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rf_skill_eval.application.catalog import load_task_file
from rf_skill_eval.domain.run import Run
from rf_skill_eval.domain.scorecard import Scorecard
from rf_skill_eval.domain.task import Task
from rf_skill_eval.scoring.rubric import RubricGrader

_REPO = Path(__file__).resolve().parents[2]
_FIXTURES = _REPO / "eval" / "fixtures"
_TASKS = _REPO / "eval" / "tasks"
_GOLDEN = Path(__file__).parent / "golden"

pytestmark = pytest.mark.integration


def _task(task_id: str) -> Task:
    matches = list(_TASKS.rglob(f"{task_id}.yaml"))
    assert len(matches) == 1, task_id
    return load_task_file(matches[0])


def _workspace(tmp_path: Path, task: Task, overlay: Path | None) -> Run:
    ws = tmp_path / "workspace"
    assert task.fixture
    shutil.copytree(_FIXTURES / task.fixture, ws)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    if overlay is not None:
        for src in overlay.rglob("*"):
            if src.is_file():
                if src.name == "stdout.stream.jsonl":
                    shutil.copy(src, artifacts / src.name)
                    continue
                dst = ws / src.relative_to(overlay)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, dst)
    now = datetime.now(UTC)
    return Run(
        id="golden",
        task_id=task.id,
        profile_name="treatment",
        started_at=now,
        finished_at=now,
        exit_code=0,
        artifacts_dir=artifacts,
        workspace_dir=ws,
    )


def _grade(tmp_path: Path, task_id: str, overlay: Path | None) -> Scorecard:
    task = _task(task_id)
    run = _workspace(tmp_path, task, overlay)
    return Scorecard(run_id=run.id, task_id=task.id, verdicts=tuple(RubricGrader().grade(run, task)))


def _require(*modules: str) -> None:
    for mod in modules:
        if importlib.util.find_spec(mod) is None:
            pytest.fail(f"grader dependency {mod} is not installed (uv sync --all-packages)")


NARROW = [
    "narrow-browser-login-01",
    "narrow-selenium-login-01",
    "narrow-appium-login-01",
    "narrow-requests-users-01",
    "narrow-restinstance-schema-01",
    "narrow-platynui-calculator-01",
    "narrow-robotcode-discover-01",
    "narrow-setup-requests-01",
]


@pytest.mark.parametrize("task_id", NARROW)
def test_gating_checks_decide_on_unmodified_fixture(tmp_path: Path, task_id: str) -> None:
    sc = _grade(tmp_path, task_id, None)
    gating = sc.gating_verdicts
    assert gating, task_id
    assert all(v.status in ("passed", "failed") for v in gating), [
        (v.check_name, v.status, v.reason) for v in gating
    ]
    assert sc.gate_result == "fail"


@pytest.mark.parametrize("task_id", NARROW)
def test_reference_solution_passes_gate(tmp_path: Path, task_id: str) -> None:
    _require("Browser", "SeleniumLibrary", "RequestsLibrary", "REST")
    sc = _grade(tmp_path, task_id, _GOLDEN / task_id)
    problems = [(v.check_name, v.status, v.details) for v in sc.gating_verdicts if not v.passed]
    assert sc.gate_result == "pass", problems


ADVERSARIAL = [
    "adv-browser-deprecated-wait",
    "adv-selenium-nonexistent-kw",
    "adv-web-wrong-library",
    "adv-make-it-pass",
    "adv-setup-system-pip",
    "adv-restinstance-expectation-leak",
    "adv-appium-deprecated-visibility",
    "adv-legacy-syntax-01",
]


@pytest.mark.parametrize("task_id", ADVERSARIAL)
def test_adversarial_good_solution_passes(tmp_path: Path, task_id: str) -> None:
    sc = _grade(tmp_path, task_id, _GOLDEN / task_id / "good")
    problems = [(v.check_name, v.status, v.details) for v in sc.verdicts if not v.passed]
    assert sc.gate_result == "pass", problems


@pytest.mark.parametrize("task_id", ADVERSARIAL)
def test_adversarial_temptation_fails(tmp_path: Path, task_id: str) -> None:
    sc = _grade(tmp_path, task_id, _GOLDEN / task_id / "bad")
    assert sc.gate_result == "fail", [(v.check_name, v.status, v.details) for v in sc.verdicts]


def test_adversarial_tasks_are_tier_adversarial() -> None:
    for task_id in ADVERSARIAL:
        assert _task(task_id).tier == "adversarial"


# --- fixtures (4.4) ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("fixture", "target"),
    [
        ("sut-minimal", "tests/example.robot"),
        ("sut-selenium", "tests/example.robot"),
        ("sut-api", "tests"),
        ("sut-browser", "tests/example.robot"),
    ],
)
def test_fixture_smoke_suite_passes(tmp_path: Path, fixture: str, target: str) -> None:
    from rf_skill_eval.scoring.deterministic import check_robot_pass

    ws = tmp_path / fixture
    shutil.copytree(_FIXTURES / fixture, ws)
    now = datetime.now(UTC)
    run = Run(
        id="fx",
        task_id="fx",
        profile_name="treatment",
        started_at=now,
        artifacts_dir=tmp_path,
        workspace_dir=ws,
    )
    v = check_robot_pass(run, "smoke", {"path": target})
    assert v.status == "passed", v.details


@pytest.mark.parametrize(
    ("fixture", "spec", "library"),
    [
        ("sut-appium", "specs/AppiumLibrary.json", "AppiumLibrary"),
        ("sut-platynui", "specs/PlatynUI.BareMetal.json", "PlatynUI.BareMetal"),
    ],
)
def test_spec_only_fixture_stub_resolves(fixture: str, spec: str, library: str) -> None:
    from rf_skill_eval.scoring.keyword_resolution import resolve_suite_keywords

    root = _FIXTURES / fixture
    result = resolve_suite_keywords(
        root / "tests" / "example.robot", [root / spec], required_libraries=(library,)
    )
    assert result.ok, result.summary()


def test_failing_fixture_really_fails(tmp_path: Path) -> None:
    sc = _grade(tmp_path, "adv-make-it-pass", None)
    robot = next(v for v in sc.verdicts if v.check_type == "robot_pass")
    assert robot.status == "failed"


@pytest.mark.parametrize(
    "fixture", ["sut-selenium", "sut-api", "sut-appium", "sut-platynui", "sut-failing", "sut-legacy-style"]
)
def test_new_fixtures_follow_the_readme_layout(fixture: str) -> None:
    root = _FIXTURES / fixture
    for name in ("pyproject.toml", "README.md", ".gitignore"):
        assert (root / name).is_file(), f"{fixture}/{name}"
    assert any((root / "tests").glob("*.robot"))


@pytest.mark.parametrize(
    ("command", "violation"),
    [
        ("pip install robotframework-browser", True),
        ("sudo pip3 install robotframework-browser", True),
        ("python -m pip install robotframework-browser", True),
        ("cd /tmp && pip install x", True),
        ("uv add robotframework-browser", False),
        ("uv pip install robotframework-browser", False),
        ("uv run pip install robotframework-browser", False),
        (".venv/bin/pip install robotframework-browser", False),
        (".venv/bin/python -m pip install robotframework-browser", False),
        ("pip --version", False),
    ],
)
def test_system_pip_pattern(command: str, violation: bool) -> None:
    import json
    import re

    check = next(c for c in _task("adv-setup-system-pip").grader_checks if c.type == "tool_call_count")
    pattern = re.compile(str(check.params["input_pattern"]))
    serialised = json.dumps({"command": command, "description": "x"}, sort_keys=True)
    assert bool(pattern.search(serialised)) is violation


# --- rf-language tasks (add-rf-language-skill, tasks 5.2-5.4) -----------------------

LANGUAGE_NARROW = [
    "narrow-language-data-driven-01",
    "narrow-language-bdd-01",
    "narrow-language-suite-setup-tags-01",
    "narrow-language-embedded-01",
    "narrow-language-env-varfiles-01",
]
LANGUAGE_ADVERSARIAL = ["adv-language-force-tags-01", "adv-language-rf71-typed-01"]
LANGUAGE_TASKS = LANGUAGE_NARROW + LANGUAGE_ADVERSARIAL


def _rf71_available() -> bool:
    from rf_skill_eval.scoring.custom.language import PINNED_RF71, _pinned_robot_available

    return _pinned_robot_available(PINNED_RF71) is None


def _require_language_tools(task_id: str) -> None:
    _require("yaml")
    if task_id == "adv-language-rf71-typed-01" and not _rf71_available():
        pytest.skip("uvx --from robotframework==7.1.1 robot is unavailable (no uv or no network)")


@pytest.mark.parametrize("task_id", LANGUAGE_TASKS)
def test_language_task_is_graded_for_rf_language(task_id: str) -> None:
    task = _task(task_id)
    assert task.skill == "rf-language"
    assert task.tier == ("adversarial" if task_id.startswith("adv-") else "narrow")
    assert task.gating_checks


@pytest.mark.parametrize("task_id", LANGUAGE_TASKS)
def test_language_gate_fails_on_unmodified_fixture(tmp_path: Path, task_id: str) -> None:
    _require_language_tools(task_id)
    sc = _grade(tmp_path, task_id, None)
    assert all(v.status in ("passed", "failed") for v in sc.gating_verdicts), [
        (v.check_name, v.status, v.reason) for v in sc.gating_verdicts
    ]
    assert sc.gate_result == "fail"


@pytest.mark.parametrize("task_id", LANGUAGE_TASKS)
def test_language_reference_solution_passes(tmp_path: Path, task_id: str) -> None:
    _require_language_tools(task_id)
    sc = _grade(tmp_path, task_id, _GOLDEN / task_id / "good")
    problems = [(v.check_name, v.status, v.details) for v in sc.gating_verdicts if not v.passed]
    assert sc.gate_result == "pass", problems


@pytest.mark.parametrize("task_id", LANGUAGE_TASKS)
def test_language_naive_solution_fails(tmp_path: Path, task_id: str) -> None:
    _require_language_tools(task_id)
    sc = _grade(tmp_path, task_id, _GOLDEN / task_id / "bad")
    assert sc.gate_result == "fail", [(v.check_name, v.status, v.details) for v in sc.verdicts]


def test_one_test_holding_six_rows_fails_with_counts(tmp_path: Path) -> None:
    sc = _grade(tmp_path, "narrow-language-data-driven-01",
                _GOLDEN / "narrow-language-data-driven-01" / "bad")
    count = next(v for v in sc.verdicts if v.check_name == "six_templated_tests_pass")
    assert count.status == "failed"
    assert "expected exactly 6 passed tests, got total=1 passed=1" in count.details


def test_naive_embedded_keyword_passes_dry_run_but_fails_hidden_suite(tmp_path: Path) -> None:
    sc = _grade(tmp_path, "narrow-language-embedded-01",
                _GOLDEN / "narrow-language-embedded-01" / "bad")
    by_name = {v.check_name: v for v in sc.verdicts}
    assert by_name["teams_dry_run"].status == "passed"
    assert by_name["teams_robot_unchanged"].status == "passed"
    hidden = by_name["hidden_suite_binds_cities"]
    assert hidden.status == "failed" and "Los" in hidden.details


def test_typed_arguments_on_rf71_fail_both_gates(tmp_path: Path) -> None:
    _require_language_tools("adv-language-rf71-typed-01")
    sc = _grade(tmp_path, "adv-language-rf71-typed-01",
                _GOLDEN / "adv-language-rf71-typed-01" / "bad")
    by_name = {v.check_name: v for v in sc.verdicts}
    assert by_name["suite_passes_on_rf_7_1_1"].status == "failed"
    assert by_name["no_typed_declarations"].status == "failed"
    assert "${quantity: int}" in by_name["no_typed_declarations"].details


@pytest.mark.parametrize(
    ("fixture", "target", "tests"),
    [
        ("sut-language-tests", "tests", 11),
        ("sut-language-keywords", "tests/env.robot", 2),
    ],
)
def test_language_fixture_passes_as_shipped(tmp_path: Path, fixture: str, target: str,
                                            tests: int) -> None:
    from rf_skill_eval.scoring.deterministic import check_robot_pass

    ws = tmp_path / fixture
    shutil.copytree(_FIXTURES / fixture, ws)
    now = datetime.now(UTC)
    run = Run(id="fx", task_id="fx", profile_name="treatment", started_at=now,
              artifacts_dir=tmp_path, workspace_dir=ws)
    v = check_robot_pass(run, "smoke", {"path": target, "expected_tests": tests,
                                        "expected_tests_exact": True})
    assert v.status == "passed", v.details


def test_language_fixture_layout() -> None:
    tests_fx = _FIXTURES / "sut-language-tests"
    assert not (tests_fx / "tests" / "api" / "__init__.robot").exists()
    assert "Tags" not in (tests_fx / "tests" / "api" / "users.robot").read_text()
    kw_fx = _FIXTURES / "sut-language-keywords"
    assert not (kw_fx / "resources" / "teams.resource").exists()
    assert "Select team Los Angeles Lakers" in (kw_fx / "tests" / "teams.robot").read_text()
    rf71 = _FIXTURES / "sut-rf71"
    assert 'robotframework==7.1.1' in (rf71 / "pyproject.toml").read_text()
    assert 'name = "robotframework"\nversion = "7.1.1"' in (rf71 / "uv.lock").read_text()
    for fx in (tests_fx, kw_fx, rf71):
        assert not (fx / ".venv").exists()
        for name in ("pyproject.toml", "README.md", ".gitignore"):
            assert (fx / name).is_file(), f"{fx.name}/{name}"


def test_sut_rf71_runs_on_pinned_robot_framework(tmp_path: Path) -> None:
    if not _rf71_available():
        pytest.skip("uvx --from robotframework==7.1.1 robot is unavailable (no uv or no network)")
    from rf_skill_eval.scoring.custom.language import pinned_robot_pass

    ws = tmp_path / "sut-rf71"
    shutil.copytree(_FIXTURES / "sut-rf71", ws)
    now = datetime.now(UTC)
    run = Run(id="fx", task_id="fx", profile_name="treatment", started_at=now,
              artifacts_dir=tmp_path, workspace_dir=ws)
    v = pinned_robot_pass(run, {"path": "tests", "expected_tests": 3})
    assert v.status == "passed", v.details
    assert "robotframework==7.1.1" in v.details


def test_hidden_graders_are_not_staged_into_workspaces() -> None:
    graders = _REPO / "eval" / "graders" / "language"
    assert (graders / "teams_binding.robot").is_file()
    assert not graders.is_relative_to(_FIXTURES)
    for task_id in LANGUAGE_TASKS:
        fixture = _task(task_id).fixture
        assert fixture and not list((_FIXTURES / fixture).rglob("*binding*"))


# --- rf-python-library tasks (add-rf-python-library-skill, tasks 6.1-6.2) -----------

PYLIB_TASKS = [
    "narrow-python-library-inventory-scope-01",
    "narrow-python-library-mode-literal-01",
    "narrow-python-library-flaky-listener-01",
]


@pytest.mark.parametrize("task_id", PYLIB_TASKS)
def test_pylib_task_is_graded_for_rf_python_library(task_id: str) -> None:
    task = _task(task_id)
    assert task.skill == "rf-python-library" and task.tier == "narrow"
    assert task.fixture == "sut-pylib"
    assert task.gating_checks
    assert all(c.type == "custom_python" for c in task.gating_checks)


@pytest.mark.parametrize("task_id", PYLIB_TASKS)
def test_pylib_gate_fails_on_unmodified_fixture(tmp_path: Path, task_id: str) -> None:
    sc = _grade(tmp_path, task_id, None)
    assert all(v.status in ("passed", "failed") for v in sc.gating_verdicts), [
        (v.check_name, v.status, v.reason) for v in sc.gating_verdicts
    ]
    assert sc.gate_result == "fail"


@pytest.mark.parametrize("task_id", PYLIB_TASKS)
def test_pylib_reference_solution_passes(tmp_path: Path, task_id: str) -> None:
    sc = _grade(tmp_path, task_id, _GOLDEN / task_id / "good")
    problems = [(v.check_name, v.status, v.details) for v in sc.verdicts if not v.passed]
    assert sc.gate_result == "pass", problems
    # The reference solutions also satisfy the non-gating checks.
    assert not [p for p in problems if p[0] != "loaded_rf_python_library_skill"], problems


@pytest.mark.parametrize("task_id", PYLIB_TASKS)
def test_pylib_naive_solution_fails(tmp_path: Path, task_id: str) -> None:
    sc = _grade(tmp_path, task_id, _GOLDEN / task_id / "bad")
    assert sc.gate_result == "fail", [(v.check_name, v.status, v.details) for v in sc.verdicts]


def test_default_scope_loses_state_in_third_test(tmp_path: Path) -> None:
    sc = _grade(tmp_path, "narrow-python-library-inventory-scope-01",
                _GOLDEN / "narrow-python-library-inventory-scope-01" / "bad")
    by_name = {v.check_name: v for v in sc.verdicts}
    hidden = by_name["hidden_suite_state_survives_tests"]
    assert hidden.status == "failed" and "Count Survives Between Tests: FAIL" in hidden.details
    assert by_name["checker_reports_no_leaks"].status == "failed"
    assert "state_in_test_scope" in by_name["checker_reports_no_leaks"].details


def test_pylib_fixture_passes_as_shipped(tmp_path: Path) -> None:
    from rf_skill_eval.scoring.deterministic import check_robot_pass

    ws = tmp_path / "sut-pylib"
    shutil.copytree(_FIXTURES / "sut-pylib", ws)
    now = datetime.now(UTC)
    run = Run(id="fx", task_id="fx", profile_name="treatment", started_at=now,
              artifacts_dir=tmp_path, workspace_dir=ws)
    v = check_robot_pass(run, "smoke", {"path": "tests/example.robot", "expected_tests": 1,
                                        "expected_tests_exact": True})
    assert v.status == "passed", v.details
    root = _FIXTURES / "sut-pylib"
    for name in ("pyproject.toml", "README.md", ".gitignore", "robot.toml"):
        assert (root / name).is_file(), name
    assert not list((root / "libraries").glob("*.py"))
    assert 'python-path = ["libraries"]' in (root / "robot.toml").read_text()


def test_pylib_hidden_graders_are_not_staged() -> None:
    graders = _REPO / "eval" / "graders" / "python-library"
    for suite in ("inventory.robot", "mode.robot", "flaky.robot", "flaky_real_failure.robot"):
        assert (graders / suite).is_file(), suite
        assert not list((_FIXTURES / "sut-pylib").rglob(suite))


# --- adv-legacy-syntax-01 (modernize-plugin-agents-and-hooks 7.1/7.3) ---------------


def test_legacy_style_fixture_passes_and_is_legacy(tmp_path: Path) -> None:
    """The fixture's own suite passes, and its resource really carries the
    deprecated constructs the task tempts the agent to copy."""
    import subprocess
    import sys

    ws = tmp_path / "ws"
    shutil.copytree(_FIXTURES / "sut-legacy-style", ws)
    proc = subprocess.run([sys.executable, "-m", "robot", "--outputdir", str(tmp_path / "out"), "tests"],
                          cwd=ws, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stdout[-2000:]
    if shutil.which("robocop") is None:
        pytest.skip("robocop CLI not installed")
    lint = subprocess.run(["robocop", "check", "--no-cache", "--select", "DEPR*", "resources", "tests"],
                          cwd=ws, capture_output=True, text=True, timeout=120)
    for rule in ("DEPR11", "DEPR08", "DEPR05", "DEPR07"):
        assert rule in lint.stdout, rule
    assert not (ws / ".robocop_cache").exists()


def test_legacy_syntax_bad_solution_fails_on_depr_checks(tmp_path: Path) -> None:
    """The copied-style solution runs green; only the deprecation checks fail it."""
    sc = _grade(tmp_path, "adv-legacy-syntax-01", _GOLDEN / "adv-legacy-syntax-01" / "bad")
    by_type = {v.check_type: v for v in sc.verdicts}
    assert by_type["robot_pass"].status == "passed"
    assert by_type["robot_dryrun"].status == "passed"
    assert by_type["file_not_contains"].status == "failed"
    if shutil.which("robocop") is not None:
        assert by_type["lint_clean"].status == "failed"
