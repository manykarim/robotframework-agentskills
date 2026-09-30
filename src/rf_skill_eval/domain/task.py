"""Task aggregate — one evaluation scenario."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..errors import ModelNotAllowedError
from .verdict import CheckCategory

TaskTier = Literal["narrow", "realistic", "adversarial"]

#: Model allow-list (design D7). Opus is allowed only as an explicit run-time
#: opt-in (``--model claude-opus-5-5 --allow-opus --max-cost-usd <cap>``);
#: task YAML and trigger sets may declare Haiku or Sonnet only.
HAIKU_MODEL: str = "claude-haiku-4-5-20251001"
SONNET_MODEL: str = "claude-sonnet-5"
OPUS_MODEL: str = "claude-opus-5-5"

#: The default model for evaluation runs (narrow tier and trigger evals).
DEFAULT_MODEL: str = HAIKU_MODEL

ALLOWED_MODELS: frozenset[str] = frozenset({HAIKU_MODEL, SONNET_MODEL, OPUS_MODEL})

#: Models a task YAML / trigger set may declare as its own model.
YAML_ALLOWED_MODELS: frozenset[str] = frozenset({HAIKU_MODEL, SONNET_MODEL})

#: Retired ids -> replacement, used for targeted migration messages.
LEGACY_MODEL_IDS: dict[str, str] = {
    "claude-haiku-4-5": HAIKU_MODEL,
    "claude-sonnet-4-6": SONNET_MODEL,
    "claude-sonnet-4-5": SONNET_MODEL,
    "claude-3-5-haiku-latest": HAIKU_MODEL,
}

#: Tier -> default model when a task omits ``model``.
TIER_DEFAULT_MODELS: dict[str, str] = {
    "narrow": HAIKU_MODEL,
    "realistic": SONNET_MODEL,
    "adversarial": SONNET_MODEL,
}

#: Per-task MCP servers the harness knows how to provision (design D1).
KNOWN_MCP_SERVERS: frozenset[str] = frozenset({"rf-mcp"})

#: Pseudo-skill for bundle-level canary tasks (hooks, plugin as a whole).
PLUGIN_SKILL: str = "plugin"


def model_policy_error(model: str, *, in_yaml: bool) -> str | None:
    """Return an error message when ``model`` violates the policy, else ``None``."""
    if model in LEGACY_MODEL_IDS:
        return (
            f"Model '{model}' is a retired id; use '{LEGACY_MODEL_IDS[model]}'. "
            f"Permitted: {sorted(ALLOWED_MODELS)}."
        )
    if model not in ALLOWED_MODELS:
        return f"Model '{model}' is not allowed. Permitted: {sorted(ALLOWED_MODELS)}."
    if in_yaml and model not in YAML_ALLOWED_MODELS:
        return (
            f"Model '{model}' may not be declared in task YAML or trigger sets "
            f"(permitted there: {sorted(YAML_ALLOWED_MODELS)}); "
            "use --model with --allow-opus and --max-cost-usd at run time."
        )
    return None


#: Known grader check discriminator values.
GraderCheckType = Literal[
    "file_exists",
    "file_contains",
    "file_not_contains",
    "robot_pass",
    "robot_dryrun",
    "keywords_resolve",
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


def _require_keywords_resolve(extras: dict[str, Any]) -> str | None:
    missing = _missing(extras, "target", "path")
    if missing:
        return missing
    specs = extras.get("specs")
    if not specs or not isinstance(specs, (list, tuple)):
        return "requires non-empty 'specs' list (libdoc JSON spec paths)"
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


#: Checks that assert *how* the agent worked (design D4); excluded from deltas.
PROCESS_CHECK_TYPES: frozenset[str] = frozenset(
    {"tool_call_count", "tool_result_count", "tool_call_sequence"}
)

_CHECK_FIELD_RULES: dict[str, Any] = {
    "file_exists": lambda e: _missing(e, "path"),
    "file_contains": _require_file_contains,
    "file_not_contains": _require_file_contains,
    "robot_pass": lambda e: _missing(e, "target", "path"),
    "robot_dryrun": lambda e: _missing(e, "target", "path"),
    "keywords_resolve": _require_keywords_resolve,
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
    #: ``None`` -> gating iff ``type`` equals the task's ``primary_metric``.
    gating: bool | None = None
    #: ``None`` -> ``process`` for tool_* checks, ``outcome`` otherwise.
    category: CheckCategory | None = None

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
    def effective_category(self) -> CheckCategory:
        if self.category is not None:
            return self.category
        return "process" if self.type in PROCESS_CHECK_TYPES else "outcome"

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
    mcp_servers: tuple[str, ...] = Field(default_factory=tuple)
    max_turns: int = Field(default=40, gt=0, le=200)
    fixture: str | None = None
    primary_metric: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _default_model_per_tier(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("model") is None:
            data = dict(data)
            data["model"] = TIER_DEFAULT_MODELS.get(str(data.get("tier", "narrow")), DEFAULT_MODEL)
        return data

    @field_validator("model")
    @classmethod
    def _reject_forbidden_models(cls, value: str) -> str:
        problem = model_policy_error(value, in_yaml=True)
        if problem:
            raise ModelNotAllowedError(problem)
        return value

    @field_validator("mcp_servers", mode="before")
    @classmethod
    def _coerce_mcp_servers(cls, value: Any) -> Any:
        if value is None:
            return ()
        if isinstance(value, list):
            value = tuple(value)
        for name in value:
            if name not in KNOWN_MCP_SERVERS:
                raise ValueError(
                    f"unknown mcp_servers entry '{name}'. Known: {sorted(KNOWN_MCP_SERVERS)}"
                )
        return value

    def is_gating(self, check: GraderCheck) -> bool:
        """Design D4: explicit ``gating`` wins, else ``type == primary_metric``."""
        if check.gating is not None:
            return check.gating
        return self.primary_metric is not None and check.type == self.primary_metric

    @property
    def gating_checks(self) -> tuple[GraderCheck, ...]:
        return tuple(c for c in self.grader_checks if self.is_gating(c))

    @property
    def is_canary(self) -> bool:
        """Bundle-level canary (``skill: plugin``); excluded from per-skill stats."""
        return self.skill == PLUGIN_SKILL

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
