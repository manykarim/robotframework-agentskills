"""Trigger query sets and trigger-eval results (design D6)."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..errors import ModelNotAllowedError
from .task import DEFAULT_MODEL, model_policy_error

#: Splits that count toward the ">= 8 per polarity" rule and must be present.
REQUIRED_SPLITS: tuple[str, ...] = ("train", "validation")
#: Optional holdout splits: ``holdout`` or ``holdout<N>`` (``holdout2``, ...).
#: Written after tuning, never used for selection; an inspected holdout is
#: retired to ``train`` and a fresh numbered one added (add-sibling-cues).
HOLDOUT_RE = re.compile(r"^holdout\d*$")
#: Human-readable list of the accepted split names (error and help texts).
SPLIT_NAMES = "train, validation, holdout, holdout<N>"


def is_holdout_split(name: str) -> bool:
    return bool(HOLDOUT_RE.fullmatch(name))


def is_valid_split(name: str) -> bool:
    return name in REQUIRED_SPLITS or is_holdout_split(name)


def _split_key(name: str) -> tuple[int, int, str]:
    if name in REQUIRED_SPLITS:
        return (REQUIRED_SPLITS.index(name), 0, name)
    if is_holdout_split(name):
        digits = name[len("holdout") :]
        return (len(REQUIRED_SPLITS), int(digits) if digits else 1, name)
    return (99, 0, name)


def ordered_splits(names: Iterable[str]) -> tuple[str, ...]:
    """Distinct split names in report order: train, validation, holdout, holdout2, ..."""
    return tuple(sorted(set(names), key=_split_key))


#: Minimum queries per polarity in a set (spec: Trigger evaluation query sets).
MIN_PER_POLARITY = 8


class TriggerQuery(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    query: str = Field(min_length=1)
    should_trigger: bool
    split: str
    note: str = ""

    @field_validator("split")
    @classmethod
    def _split_name(cls, value: str) -> str:
        if not is_valid_split(value):
            raise ValueError(f"unknown split {value!r} (expected {SPLIT_NAMES})")
        return value


class TriggerSet(BaseModel):
    """``eval/triggers/<skill>.yaml``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    skill: str = Field(min_length=1)
    model: str = DEFAULT_MODEL
    runs: int = Field(default=3, ge=1, le=20)
    threshold: float = Field(default=0.5, gt=0.0, le=1.0)
    queries: tuple[TriggerQuery, ...]

    @field_validator("model")
    @classmethod
    def _model_policy(cls, value: str) -> str:
        problem = model_policy_error(value, in_yaml=True)
        if problem:
            raise ModelNotAllowedError(problem)
        return value

    @model_validator(mode="after")
    def _shape(self) -> TriggerSet:
        counted = [q for q in self.queries if q.split in REQUIRED_SPLITS]
        pos = [q for q in counted if q.should_trigger]
        neg = [q for q in counted if not q.should_trigger]
        problems: list[str] = []
        if len(pos) < MIN_PER_POLARITY:
            problems.append(
                f"{len(pos)} should-trigger queries (minimum {MIN_PER_POLARITY})"
            )
        if len(neg) < MIN_PER_POLARITY:
            problems.append(
                f"{len(neg)} should-not-trigger queries (minimum {MIN_PER_POLARITY})"
            )
        for polarity, items in (("should-trigger", pos), ("should-not-trigger", neg)):
            splits = {q.split for q in items}
            for split in REQUIRED_SPLITS:
                if items and split not in splits:
                    problems.append(f"no {polarity} queries in the {split} split")
        ids = [q.id for q in self.queries]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            problems.append(f"duplicate query ids {dupes}")
        if problems:
            raise ValueError("; ".join(problems))
        return self

    def select(self, splits: tuple[str, ...]) -> tuple[TriggerQuery, ...]:
        return tuple(q for q in self.queries if q.split in splits)


@dataclass(frozen=True)
class QueryOutcome:
    """Result of running one query ``runs`` times."""

    skill: str
    query_id: str
    split: str
    should_trigger: bool
    runs: int
    loads: int
    threshold: float
    other_skills: tuple[str, ...] = field(default_factory=tuple)
    incomplete: int = 0
    query: str = ""
    #: One entry per completed run whose ``session.jsonl`` had a skill listing:
    #: the sorted rf-* skills listed *with* their description (design D14).
    #: Runs without a parsed listing add no entry.
    visible_descriptions: tuple[tuple[str, ...], ...] = field(default_factory=tuple)

    @property
    def listed_runs(self) -> int:
        """Completed runs whose skill listing was parsed."""
        return len(self.visible_descriptions)

    @property
    def description_visible_runs(self) -> int:
        """Runs in which this query's target skill was listed with its description."""
        return sum(1 for seen in self.visible_descriptions if self.skill in seen)

    @property
    def rate(self) -> float:
        return self.loads / self.runs if self.runs else 0.0

    @property
    def triggered(self) -> bool:
        return self.runs > 0 and self.rate >= self.threshold

    @property
    def passed(self) -> bool:
        """A query with no completed run never passes (it is incomplete)."""
        return self.runs > 0 and self.triggered == self.should_trigger


@dataclass(frozen=True)
class TriggerMetrics:
    skill: str
    split: str
    tp: int
    fp: int
    tn: int
    fn: int

    @property
    def total(self) -> int:
        return self.tp + self.fp + self.tn + self.fn

    @property
    def precision(self) -> float | None:
        denom = self.tp + self.fp
        return self.tp / denom if denom else None

    @property
    def recall(self) -> float | None:
        denom = self.tp + self.fn
        return self.tp / denom if denom else None

    @property
    def accuracy(self) -> float | None:
        return (self.tp + self.tn) / self.total if self.total else None

    @property
    def negative_accuracy(self) -> float | None:
        denom = self.tn + self.fp
        return self.tn / denom if denom else None


@dataclass(frozen=True)
class DescriptionVisibility:
    """How often a skill's description was in the listing (design D14)."""

    skill: str
    #: Runs of this skill's own queries: listed with description / with a listing.
    own_visible: int
    own_listed: int
    #: Every run in the result (any skill's query): same counts.
    all_visible: int
    all_listed: int


def description_visibility(outcomes: list[QueryOutcome]) -> list[DescriptionVisibility]:
    """Per skill visibility counts; empty when no run recorded a listing."""
    runs = [(o.skill, seen) for o in outcomes for seen in o.visible_descriptions]
    if not runs:
        return []
    skills = sorted({o.skill for o in outcomes} | {s for _k, seen in runs for s in seen})
    out: list[DescriptionVisibility] = []
    for skill in skills:
        own = [seen for owner, seen in runs if owner == skill]
        out.append(
            DescriptionVisibility(
                skill=skill,
                own_visible=sum(1 for seen in own if skill in seen),
                own_listed=len(own),
                all_visible=sum(1 for _o, seen in runs if skill in seen),
                all_listed=len(runs),
            )
        )
    return out


def run_load_counts(outcomes: list[QueryOutcome]) -> dict[tuple[str, str], dict[str, int]]:
    """Per skill × split: skill loads and completed runs of should- / should-not-trigger queries.

    Run-level counts keep borderline queries (load rate near the threshold)
    from flipping a whole query between samples, which query-level majority
    votes do.
    """
    cells: dict[tuple[str, str], dict[str, int]] = {}
    for o in outcomes:
        c = cells.setdefault(
            (o.skill, o.split),
            {"positive_loads": 0, "positive_runs": 0, "negative_loads": 0, "negative_runs": 0},
        )
        side = "positive" if o.should_trigger else "negative"
        c[f"{side}_loads"] += o.loads
        c[f"{side}_runs"] += o.runs
    return cells


def trigger_metrics(outcomes: list[QueryOutcome]) -> list[TriggerMetrics]:
    """Per skill × split confusion counts (sorted by skill, then split)."""
    cells: dict[tuple[str, str], list[int]] = {}
    for o in outcomes:
        c = cells.setdefault((o.skill, o.split), [0, 0, 0, 0])
        if o.should_trigger and o.triggered:
            c[0] += 1
        elif not o.should_trigger and o.triggered:
            c[1] += 1
        elif not o.should_trigger and not o.triggered:
            c[2] += 1
        else:
            c[3] += 1
    return [
        TriggerMetrics(skill, split, tp=c[0], fp=c[1], tn=c[2], fn=c[3])
        for (skill, split), c in sorted(
            cells.items(), key=lambda kv: (kv[0][0], _split_key(kv[0][1]))
        )
    ]
