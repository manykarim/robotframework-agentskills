"""Trigger evaluation (design D6; corrected in tune-skill-descriptions D1-D5).

Each query of a trigger set runs ``runs`` times headlessly with the plugin
staged but hooks disabled, in a fresh copy of the neutral ``sut-trigger``
fixture, ``--max-turns 3`` and only the tools ``Skill,Read,Glob,Grep``
available (``claude --tools``). A run *loads* the target skill when the
transcript has a Skill call naming it or a Read of its ``SKILL.md``. The
query's trigger rate is loads / completed runs; it is *triggered* at
rate >= threshold.

Each finished query is appended to ``outcomes.jsonl`` (:class:`OutcomeStore`)
so an interrupted batch resumes where it stopped; queries run in a pool of at
most :data:`MAX_TRIGGER_CONCURRENCY` workers.

Each run's ``skill_listing`` attachment is parsed from its ``session.jsonl``
to record which rf-* descriptions the model was shown (design D14). The
listing budget (``--listing-budget``; ``None`` = Claude Code's default) is
part of the resume key and of the results metadata.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ..domain.trigger import (
    DescriptionVisibility,
    QueryOutcome,
    TriggerMetrics,
    TriggerQuery,
    TriggerSet,
    description_visibility,
    trigger_metrics,
)
from ..infrastructure.telemetry.skill_listing import read_skill_listing, visible_descriptions
from ..infrastructure.telemetry.skill_loads import detect_skill_loads_in_file, skill_dir_map
from .batch import Budget

TRIGGER_ALLOWED_TOOLS: tuple[str, ...] = ("Skill", "Read", "Glob", "Grep")
TRIGGER_MAX_TURNS = 3
TRIGGER_TIMEOUT_SECONDS = 180
#: ADR-002 cap on concurrent sessions under OAuth (design D4).
MAX_TRIGGER_CONCURRENCY = 2
#: File that holds one JSON line per finished query (design D3).
OUTCOMES_FILE = "outcomes.jsonl"


@dataclass(frozen=True)
class TriggerRun:
    """What one headless trigger session produced."""

    transcript: Path | None
    cost_usd: float = 0.0
    error: str | None = None
    #: Staged skills dir of the session (name -> dir map is read from it).
    skills_root: Path | None = None
    #: Captured ``session.jsonl`` (its ``skill_listing`` attachment, D14).
    session: Path | None = None


TriggerRunFn = Callable[[TriggerSet, TriggerQuery, int], TriggerRun]


def outcome_from_json(o: Mapping[str, Any]) -> QueryOutcome:
    return QueryOutcome(
        skill=str(o["skill"]),
        query_id=str(o["query_id"]),
        split=str(o["split"]),
        should_trigger=bool(o["should_trigger"]),
        runs=int(o["runs"]),
        loads=int(o["loads"]),
        threshold=float(o["threshold"]),
        other_skills=tuple(o.get("other_skills") or ()),
        incomplete=int(o.get("incomplete", 0)),
        query=str(o.get("query", "")),
        visible_descriptions=tuple(
            tuple(str(s) for s in seen) for seen in o.get("visible_descriptions") or ()
        ),
    )


OutcomeKey = tuple[str, str, str, str, str, str]


def budget_key(listing_budget: int | None) -> str:
    """Resume-key form of a listing budget: ``""`` for the CLI default."""
    return "" if listing_budget is None else str(listing_budget)


def outcome_key(
    variant_id: str, model: str, outcome: QueryOutcome, listing_budget: int | None = None
) -> OutcomeKey:
    """``(variant id, model, listing budget, skill, query id, split)`` (design D3, D14)."""
    return (
        variant_id,
        model,
        budget_key(listing_budget),
        outcome.skill,
        outcome.query_id,
        outcome.split,
    )


def _row_budget(row: Mapping[str, Any]) -> int | None:
    value = row.get("listing_budget")
    if value is None or value == "":
        return None
    return int(value)


class OutcomeStore:
    """Append-only ``outcomes.jsonl``: one line per finished query (design D3).

    Later lines win for the same key, so a query re-run after an incomplete
    attempt replaces the earlier line. Appends are serialized by a lock.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def load(self) -> dict[OutcomeKey, QueryOutcome]:
        out: dict[OutcomeKey, QueryOutcome] = {}
        if not self.path.is_file():
            return out
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                outcome = outcome_from_json(row)
                budget = _row_budget(row)
            except (ValueError, KeyError, TypeError):
                continue  # a line torn by a crash mid-write: that query re-runs
            key = outcome_key(
                str(row.get("variant_id", "")), str(row.get("model", "")), outcome, budget
            )
            out[key] = outcome
        return out

    def append(
        self,
        variant_id: str,
        model: str,
        outcome: QueryOutcome,
        listing_budget: int | None = None,
    ) -> None:
        row = {
            "variant_id": variant_id,
            "model": model,
            "listing_budget": listing_budget,
            **asdict(outcome),
        }
        line = json.dumps(row, sort_keys=True) + "\n"
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(line)
                fh.flush()


@dataclass
class TriggerEvalResult:
    outcomes: list[QueryOutcome] = field(default_factory=list)
    budget_stopped: int = 0
    spent_usd: float = 0.0
    model: str = ""
    #: Identity of the staged description set (design D5).
    variant_id: str = ""
    #: The ``--variant-root`` used, or "" for the shipped plugin.
    variant_root: str = ""
    #: Queries taken from ``outcomes.jsonl`` instead of being run again.
    resumed: int = 0
    #: ``SLASH_COMMAND_TOOL_CHAR_BUDGET`` given to the sessions; None = default.
    listing_budget: int | None = None

    @property
    def metrics(self) -> list[TriggerMetrics]:
        return trigger_metrics([o for o in self.outcomes if o.runs > 0])

    @property
    def incomplete_queries(self) -> list[QueryOutcome]:
        return [o for o in self.outcomes if o.incomplete]

    @property
    def visibility(self) -> list[DescriptionVisibility]:
        return description_visibility(self.outcomes)

    def to_json(self, *, harness_version: str) -> dict[str, Any]:
        return {
            "kind": "trigger-results",
            "harness_version": harness_version,
            "model": self.model,
            "variant_id": self.variant_id,
            "variant_root": self.variant_root,
            "listing_budget": self.listing_budget,
            "spent_usd": round(self.spent_usd, 6),
            "budget_stopped": self.budget_stopped,
            "visibility": {
                v.skill: {
                    "own_visible": v.own_visible,
                    "own_listed": v.own_listed,
                    "all_visible": v.all_visible,
                    "all_listed": v.all_listed,
                }
                for v in self.visibility
            },
            "outcomes": [
                {**asdict(o), "rate": round(o.rate, 4), "triggered": o.triggered, "passed": o.passed}
                for o in self.outcomes
            ],
        }

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> TriggerEvalResult:
        outcomes = [outcome_from_json(o) for o in data.get("outcomes", [])]
        return cls(
            outcomes=outcomes,
            budget_stopped=int(data.get("budget_stopped", 0)),
            spent_usd=float(data.get("spent_usd", 0.0)),
            model=str(data.get("model", "")),
            variant_id=str(data.get("variant_id", "")),
            variant_root=str(data.get("variant_root", "")),
            listing_budget=_row_budget(data),
        )

    def write(self, path: Path, *, harness_version: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_json(harness_version=harness_version), indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        return path


PlannedQuery = tuple[TriggerSet, TriggerQuery, OutcomeKey]


@dataclass
class _QueryRunner:
    """Runs one query's sessions; shared state is guarded by ``lock``."""

    run_fn: TriggerRunFn
    runs: int | None
    name_to_dir: Mapping[str, str] | None
    budget: Budget
    result: TriggerEvalResult
    store: OutcomeStore | None
    listing_budget: int | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)

    def _exhausted(self) -> bool:
        with self.lock:
            return self.budget.exhausted

    def _loaded(self, tset: TriggerSet, trun: TriggerRun) -> tuple[bool, set[str]] | None:
        """(target loaded, other skills) for a completed run, None if incomplete."""
        if trun.error or trun.transcript is None or not trun.transcript.is_file():
            return None
        mapping = dict(self.name_to_dir or {})
        if trun.skills_root is not None:
            mapping.update(skill_dir_map(trun.skills_root))
        found = detect_skill_loads_in_file(trun.transcript, mapping)
        others = {load.skill for load in found if load.skill != tset.skill}
        return any(load.skill == tset.skill for load in found), others

    def __call__(self, item: PlannedQuery) -> QueryOutcome:
        tset, query, key = item
        n_runs = self.runs or tset.runs
        loads = completed = incomplete = stopped = 0
        others: set[str] = set()
        seen_listings: list[tuple[str, ...]] = []
        for idx in range(n_runs):
            if self._exhausted():
                incomplete += 1
                stopped += 1
                continue
            trun = self.run_fn(tset, query, idx)
            with self.lock:
                self.budget.spent_usd += trun.cost_usd
            seen = self._loaded(tset, trun)
            if seen is None:
                incomplete += 1
                continue
            completed += 1
            loads += int(seen[0])
            others |= seen[1]
            visible = visible_descriptions(read_skill_listing(trun.session))
            if visible is not None:
                seen_listings.append(visible)
        outcome = QueryOutcome(
            skill=tset.skill,
            query_id=query.id,
            split=query.split,
            should_trigger=query.should_trigger,
            runs=completed,
            loads=loads,
            threshold=tset.threshold,
            other_skills=tuple(sorted(others)),
            incomplete=incomplete,
            query=query.query,
            visible_descriptions=tuple(seen_listings),
        )
        with self.lock:
            self.result.budget_stopped += stopped
        if self.store is not None and stopped < n_runs:
            self.store.append(key[0], key[1], outcome, self.listing_budget)
        return outcome


def _plan(
    sets: list[TriggerSet],
    splits: tuple[str, ...],
    variant_id: str,
    model_override: str | None,
    listing_budget: int | None,
) -> list[PlannedQuery]:
    budget = budget_key(listing_budget)
    return [
        (
            tset,
            query,
            (variant_id, model_override or tset.model, budget, tset.skill, query.id, query.split),
        )
        for tset in sets
        for query in tset.select(splits)
    ]


def evaluate_trigger_sets(
    sets: list[TriggerSet],
    run_fn: TriggerRunFn,
    *,
    splits: tuple[str, ...] = ("train", "validation"),
    runs: int | None = None,
    name_to_dir: Mapping[str, str] | None = None,
    budget: Budget | None = None,
    model: str = "",
    model_override: str | None = None,
    store: OutcomeStore | None = None,
    variant_id: str = "",
    variant_root: str = "",
    concurrency: int = 1,
    listing_budget: int | None = None,
) -> TriggerEvalResult:
    """Run every selected query; resume from ``store``; aggregate all outcomes.

    ``model_override`` is the ``--model`` given on the command line (else each
    set's own model); it is part of the persistence key. With a ``store``,
    queries whose persisted outcome is complete are not run again, and the
    result also includes every persisted outcome for the same variant and
    model(s) (design D3). ``concurrency`` (1..2) queries run at once.
    ``listing_budget`` is recorded only; the run function applies it. It is
    part of the key, so batches with different budgets never mix (D14).
    """
    if not 1 <= concurrency <= MAX_TRIGGER_CONCURRENCY:
        raise ValueError(f"concurrency must be 1..{MAX_TRIGGER_CONCURRENCY}, got {concurrency}")
    budget = budget or Budget()
    result = TriggerEvalResult(
        model=model,
        variant_id=variant_id,
        variant_root=variant_root,
        listing_budget=listing_budget,
    )
    persisted = store.load() if store is not None else {}
    planned = _plan(sets, splits, variant_id, model_override, listing_budget)

    done: dict[OutcomeKey, QueryOutcome] = {}
    todo: list[PlannedQuery] = []
    for item in planned:
        prior = persisted.get(item[2])
        if prior is not None and prior.incomplete == 0 and prior.runs > 0:
            done[item[2]] = prior
        else:
            todo.append(item)
    result.resumed = len(done)

    run_query = _QueryRunner(run_fn, runs, name_to_dir, budget, result, store, listing_budget)
    if concurrency == 1:
        done.update({item[2]: run_query(item) for item in todo})
    else:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            done.update(zip([item[2] for item in todo], pool.map(run_query, todo), strict=True))

    # Planned queries in plan order, then other persisted outcomes of the same
    # variant, model(s) and listing budget (e.g. other skills run earlier into
    # this directory).
    planned_keys = [key for _s, _q, key in planned]
    models = {key[1] for key in planned_keys}
    budget_id = budget_key(listing_budget)
    planned_set = set(planned_keys)
    result.outcomes = [done[key] for key in planned_keys]
    result.outcomes += [
        outcome
        for key, outcome in sorted(persisted.items())
        if key not in planned_set
        and key[0] == variant_id
        and key[1] in models
        and key[2] == budget_id
    ]
    result.spent_usd = budget.spent_usd
    return result
