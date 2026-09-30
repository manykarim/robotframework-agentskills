"""Task domain model invariants."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from rf_skill_eval.domain.task import (
    ALLOWED_MODELS,
    DEFAULT_MODEL,
    ExpectedFile,
    GraderCheck,
    Task,
)
from rf_skill_eval.errors import ModelNotAllowedError


def _make(**overrides: object) -> Task:
    defaults: dict[str, object] = {
        "id": "t1",
        "skill": "rf-results",
        "prompt": "do a thing",
    }
    defaults.update(overrides)
    return Task(**defaults)  # type: ignore[arg-type]


def test_default_model_is_haiku() -> None:
    assert DEFAULT_MODEL == "claude-haiku-4-5-20251001"
    t = _make()
    assert t.model == DEFAULT_MODEL


def test_model_allowlist_is_the_design_d7_set() -> None:
    assert frozenset(
        {"claude-haiku-4-5-20251001", "claude-sonnet-5", "claude-opus-5-5"}
    ) == ALLOWED_MODELS


@pytest.mark.parametrize(
    "forbidden",
    [
        "claude-opus-4",
        "claude-opus-4-6",
        "claude-3-opus",
        "gpt-4",
        "",
    ],
)
def test_unknown_models_rejected(forbidden: str) -> None:
    # Pydantic wraps validator-raised exceptions in ValidationError; the test
    # asserts both that rejection happens and that the message names the
    # permitted ids.
    with pytest.raises(ValidationError) as exc_info:
        _make(model=forbidden)
    msg = str(exc_info.value)
    assert "not allowed" in msg.lower()
    assert "claude-haiku-4-5-20251001" in msg and "claude-sonnet-5" in msg


@pytest.mark.parametrize(
    ("old", "new"),
    [("claude-haiku-4-5", "claude-haiku-4-5-20251001"), ("claude-sonnet-4-6", "claude-sonnet-5")],
)
def test_retired_ids_get_a_migration_hint(old: str, new: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        _make(model=old)
    msg = str(exc_info.value)
    assert "retired id" in msg and f"use '{new}'" in msg
    assert "Permitted:" in msg


def test_opus_may_not_be_declared_in_task_yaml() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _make(model="claude-opus-5-5")
    assert "--allow-opus" in str(exc_info.value)


def test_model_validator_raises_model_not_allowed_directly() -> None:
    """The underlying validator raises the typed ``ModelNotAllowedError``."""

    with pytest.raises(ModelNotAllowedError):
        Task._reject_forbidden_models("claude-opus-4")  # type: ignore[arg-type]


def test_haiku_and_sonnet_accepted() -> None:
    _make(model="claude-haiku-4-5-20251001")
    _make(model="claude-sonnet-5")


@pytest.mark.parametrize(
    ("tier", "model"),
    [
        ("narrow", "claude-haiku-4-5-20251001"),
        ("realistic", "claude-sonnet-5"),
        ("adversarial", "claude-sonnet-5"),
    ],
)
def test_tier_default_models(tier: str, model: str) -> None:
    assert _make(tier=tier).model == model


def test_gating_defaults_follow_primary_metric_and_explicit_flag() -> None:
    task = _make(
        primary_metric="file_contains",
        grader_checks=[
            {"type": "file_contains", "path": "a", "regex": "x"},
            {"type": "file_exists", "path": "a"},
            {"type": "file_exists", "path": "b", "gating": True},
            {"type": "file_contains", "path": "c", "regex": "y", "gating": False},
        ],
    )
    gating = [task.is_gating(c) for c in task.grader_checks]
    assert gating == [True, False, True, False]
    assert len(task.gating_checks) == 2


def test_category_defaults_process_for_tool_checks() -> None:
    task = _make(
        grader_checks=[
            {"type": "tool_call_count", "tool_pattern": "Skill"},
            {"type": "tool_result_count", "tool_pattern": "Bash"},
            {"type": "tool_call_sequence", "patterns": ["Read", "Write"]},
            {"type": "file_exists", "path": "a"},
            {"type": "tool_call_count", "tool_pattern": "Bash", "category": "outcome"},
        ]
    )
    assert [c.effective_category for c in task.grader_checks] == [
        "process",
        "process",
        "process",
        "outcome",
        "outcome",
    ]
    # gating/category are fields, not scoring params
    assert "gating" not in task.grader_checks[0].params


def test_mcp_servers_declared_and_validated() -> None:
    assert _make(mcp_servers=["rf-mcp"]).mcp_servers == ("rf-mcp",)
    with pytest.raises(ValidationError, match="unknown mcp_servers"):
        _make(mcp_servers=["something-else"])


def test_new_check_types_validate_fields() -> None:
    _make(grader_checks=[{"type": "file_not_contains", "path": "a", "regex": "x"}])
    _make(grader_checks=[{"type": "robot_dryrun", "target": "tests"}])
    _make(grader_checks=[{"type": "keywords_resolve", "target": "t.robot", "specs": ["s.json"]}])
    with pytest.raises(ValidationError):
        _make(grader_checks=[{"type": "file_not_contains", "path": "a"}])
    with pytest.raises(ValidationError):
        _make(grader_checks=[{"type": "keywords_resolve", "target": "t.robot"}])


def test_timeout_bounds() -> None:
    with pytest.raises(Exception):  # pydantic ValidationError
        _make(timeout_seconds=0)
    with pytest.raises(Exception):
        _make(timeout_seconds=10_000)


def test_grader_checks_from_dict_list() -> None:
    t = _make(
        grader_checks=[
            {"type": "file_exists", "path": "x"},
        ],
    )
    assert isinstance(t.grader_checks, tuple)
    check = t.grader_checks[0]
    assert check.type == "file_exists"
    assert check.params["path"] == "x"


def test_grader_check_type_field_drives_dispatch() -> None:
    check = GraderCheck(type="file_contains", path="a.robot", regex="x")
    assert check.type == "file_contains"
    # Back-compat alias
    assert check.kind == "file_contains"
    assert check.params == {"path": "a.robot", "regex": "x"}


def test_grader_check_name_defaults_from_target() -> None:
    check = GraderCheck(type="robot_pass", target="tests/a.robot")
    assert check.name == "robot_pass:tests/a.robot"


def test_grader_check_requires_type_specific_fields() -> None:
    with pytest.raises(ValidationError):
        GraderCheck(type="file_exists")  # missing path
    with pytest.raises(ValidationError):
        GraderCheck(type="file_contains", path="x")  # missing regex
    with pytest.raises(ValidationError):
        GraderCheck(type="robot_pass")  # missing target/path
    with pytest.raises(ValidationError):
        GraderCheck(type="import_resolves")  # missing module
    with pytest.raises(ValidationError):
        GraderCheck(type="custom_python", func_ref="bad")  # no colon


def test_grader_check_allows_extra_fields() -> None:
    check = GraderCheck(
        type="lint_clean", tool="robotidy", target="resources/"
    )
    assert check.params["tool"] == "robotidy"
    assert check.params["target"] == "resources/"


def test_task_is_frozen() -> None:
    t = _make()
    with pytest.raises(Exception):  # ValidationError on assignment to frozen model
        t.id = "x"  # type: ignore[misc]


def test_grader_check_frozen() -> None:
    c = GraderCheck(type="file_exists", path="p")
    with pytest.raises(Exception):
        c.type = "file_contains"  # type: ignore[misc]


def test_unknown_top_level_fields_allowed() -> None:
    # Schema is loose at the Task level so future metadata (fixture,
    # primary_metric, etc.) does not break old tasks.
    t = _make(some_future_field="ignored")
    assert t.id == "t1"


def test_tier_validation() -> None:
    with pytest.raises(Exception):
        _make(tier="legendary")  # not in literal
    assert _make(tier="adversarial").tier == "adversarial"


def test_fixture_and_primary_metric_accepted() -> None:
    t = _make(fixture="sut-minimal", primary_metric="robot_pass")
    assert t.fixture == "sut-minimal"
    assert t.primary_metric == "robot_pass"


def test_expected_files_parsed_as_structured() -> None:
    t = _make(
        expected_files=[
            {
                "path": "tests/a.robot",
                "must_contain": ["Library    Browser", "Welcome"],
            }
        ],
    )
    assert isinstance(t.expected_files, tuple)
    ef = t.expected_files[0]
    assert isinstance(ef, ExpectedFile)
    assert ef.path == "tests/a.robot"
    assert ef.must_contain == ("Library    Browser", "Welcome")


def test_expected_file_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ExpectedFile(path="x", mystery=1)  # type: ignore[call-arg]
