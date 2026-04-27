"""Task aggregate — one evaluation scenario."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..errors import ModelNotAllowedError

TaskTier = Literal["narrow", "realistic", "adversarial"]

#: The default model for evaluation runs. Haiku is cheap enough for the
#: narrow tier; Sonnet is used for realistic / adversarial tiers.
DEFAULT_MODEL: str = "claude-haiku-4-5"

#: Explicit allow-list. Opus is deliberately excluded — see ADR-004.
ALLOWED_MODELS: frozenset[str] = frozenset(
    {
        "claude-haiku-4-5",
        "claude-sonnet-4-6",
    }
)

#: Known grader check discriminator values.
GraderCheckType = Literal[
    "file_exists",
    "file_contains",
    "robot_pass",
    "no_deprecated_keywords",
    "lint_clean",
    "import_resolves",
    "custom_python",
    "tool_call_count",
    "tool_result_count",
    "tool_call_sequence",
]


def _missing(extras: dict[str, Any], *keys: str) -> str | None:
    """Return an error sentence if none of ``keys`` are set in ``extras``."""
    if any(extras.get(k) is not None and extras.get(k) != "" for k in keys):
        return None
    if len(keys) == 1:
        return f"requires '{keys[0]}'"
    alt = " or ".join(f"'{k}'" for k in keys)
    return f"requires {alt}"


def _require_file_contains(extras: dict[str, Any]) -> str | None:
    if not extras.get("path") or extras.get("regex") is None:
        return "requires 'path' and 'regex'"
    return None


def _require_custom_python(extras: dict[str, Any]) -> str | None:
    func_ref = extras.get("func_ref")
    if not func_ref or ":" not in str(func_ref):
        return "requires 'func_ref' as 'module:function'"
    return None


def _require_tool_call_sequence(extras: dict[str, Any]) -> str | None:
    patterns = extras.get("patterns")
    if not patterns:
        return "requires non-empty 'patterns' list"
    if not isinstance(patterns, (list, tuple)):
        return "requires 'patterns' to be a list"
    return None


_CHECK_FIELD_RULES: dict[str, Any] = {
    "file_exists": lambda e: _missing(e, "path"),
    "file_contains": _require_file_contains,
    "robot_pass": lambda e: _missing(e, "target", "path"),
    "no_deprecated_keywords": lambda e: _missing(e, "target", "path"),
    "lint_clean": lambda e: _missing(e, "target", "path"),
    "import_resolves": lambda e: _missing(e, "module", "path"),
    "custom_python": _require_custom_python,
    "tool_call_count": lambda e: _missing(e, "tool_pattern"),
    "tool_result_count": lambda e: _missing(e, "tool_pattern"),
    "tool_call_sequence": _require_tool_call_sequence,
}


class GraderCheck(BaseModel):
    """A single deterministic check applied to a run's output.

    The payload is intentionally loose — the type discriminator selects
    the scoring function, and per-type validators ensure the necessary
    fields are present (``path``, ``regex``, ``target``, ``tool``,
    ``func_ref``, ``module``). Unknown keys are preserved so that future
    check kinds do not require a schema change.
    """

    model_config = ConfigDict(extra="allow", frozen=True)

    type: GraderCheckType

    @model_validator(mode="after")
    def _require_type_fields(self) -> GraderCheck:
        extras = self.__pydantic_extra__ or {}
        rule = _CHECK_FIELD_RULES.get(self.type)
        if rule is None:
            return self
        missing_msg = rule(extras)
        if missing_msg:
            raise ValueError(f"grader_checks[type={self.type}] {missing_msg}")
        return self

    # Back-compat convenience: many callers (older code, logs, tests) refer
    # to the discriminator via ``kind`` and to the payload via ``params``.
    @property
    def kind(self) -> str:
        return self.type

    @property
    def name(self) -> str:
        """Human-friendly identifier for this check.

        Uses an explicit ``name`` extra if provided, otherwise synthesises
        one from the type and primary target field.
        """
        extras = self.__pydantic_extra__ or {}
        if extras.get("name"):
            return str(extras["name"])
        target = extras.get("target") or extras.get("path") or extras.get("module")
        return f"{self.type}:{target}" if target else self.type

    @property
    def params(self) -> dict[str, Any]:
        """All non-discriminator fields, for scoring dispatch."""
        return dict(self.__pydantic_extra__ or {})


class ExpectedFile(BaseModel):
    """A file expected to be produced by a run, with substring assertions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str = Field(min_length=1)
    must_contain: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("must_contain", mode="before")
    @classmethod
    def _coerce_must_contain(cls, value: Any) -> Any:
        if value is None:
            return ()
        if isinstance(value, list):
            return tuple(value)
        return value


class Task(BaseModel):
    """A declarative evaluation scenario.

    Tasks are loaded from YAML/JSON. The schema allows extra top-level
    keys so that fixture/metric metadata authored alongside tasks does
    not force lock-step schema migrations.
    """

    model_config = ConfigDict(frozen=True, extra="allow")

    id: str = Field(min_length=1, max_length=128)
    skill: str = Field(min_length=1, max_length=128)
    description: str = ""
    prompt: str = Field(min_length=1)
    allowed_tools: tuple[str, ...] = Field(default_factory=tuple)
    grader_checks: tuple[GraderCheck, ...] = Field(default_factory=tuple)
    expected_files: tuple[ExpectedFile, ...] = Field(default_factory=tuple)
    timeout_seconds: int = Field(default=600, gt=0, le=7200)
    model: str = Field(default=DEFAULT_MODEL)
    tier: TaskTier = "narrow"
    max_turns: int = Field(default=40, gt=0, le=200)
    fixture: str | None = None
    primary_metric: str | None = None

    @field_validator("model")
    @classmethod
    def _reject_forbidden_models(cls, value: str) -> str:
        if value not in ALLOWED_MODELS:
            raise ModelNotAllowedError(
                f"Model '{value}' is not allowed. "
                f"Permitted: {sorted(ALLOWED_MODELS)}. "
                f"Opus is intentionally excluded — see ADR-004."
            )
        return value

    @field_validator("allowed_tools", mode="before")
    @classmethod
    def _coerce_tools(cls, value: Any) -> Any:
        if value is None:
            return ()
        if isinstance(value, list):
            return tuple(value)
        return value

    @field_validator("grader_checks", mode="before")
    @classmethod
    def _coerce_checks(cls, value: Any) -> Any:
        if value is None:
            return ()
        if isinstance(value, list):
            return tuple(value)
        return value

    @field_validator("expected_files", mode="before")
    @classmethod
    def _coerce_files(cls, value: Any) -> Any:
        if value is None:
            return ()
        if isinstance(value, list):
            return tuple(value)
        return value
