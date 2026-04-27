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
        "skill": "keyword-builder",
        "prompt": "do a thing",
    }
    defaults.update(overrides)
    return Task(**defaults)  # type: ignore[arg-type]


def test_default_model_is_haiku() -> None:
    assert DEFAULT_MODEL == "claude-haiku-4-5"
    t = _make()
    assert t.model == DEFAULT_MODEL


def test_model_allowlist_contains_only_haiku_and_sonnet() -> None:
    assert frozenset({"claude-haiku-4-5", "claude-sonnet-4-6"}) == ALLOWED_MODELS


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
def test_opus_and_other_models_rejected(forbidden: str) -> None:
    # Pydantic wraps validator-raised exceptions in ValidationError; the test
    # asserts both that rejection happens and that the message traces back to
    # our ModelNotAllowedError branch.
    with pytest.raises(ValidationError) as exc_info:
        _make(model=forbidden)
    errors = exc_info.value.errors()
    assert any("not allowed" in str(err["msg"]).lower() for err in errors)


def test_model_validator_raises_model_not_allowed_directly() -> None:
    """The underlying validator raises the typed ``ModelNotAllowedError``.

    Pydantic wraps validator exceptions into :class:`ValidationError`
    when called via the model constructor, but callers can still invoke
    the classmethod directly (e.g., from a deserialiser) and get the
    precise exception type.
    """

    with pytest.raises(ModelNotAllowedError):
        Task._reject_forbidden_models("claude-opus-4")  # type: ignore[arg-type]


def test_haiku_and_sonnet_accepted() -> None:
    _make(model="claude-haiku-4-5")
    _make(model="claude-sonnet-4-6")


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
