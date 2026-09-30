"""Stored baseline files (design D2, spec "Regression gate against a stored baseline").

``eval/baselines/<tier>.json`` — one entry per task×arm::

    {"kind": "tier-baseline", "schema_version": 1, "tier": "narrow",
     "harness_version": "…", "claude_code_version": "…",
     "entries": {"<task_id>|<arm>": {"task_id", "arm", "skill", "model",
                 "task_hash", "runs", "pass_rate", "outcome_pass_rate",
                 "incomplete", "mean_input_tokens", "mean_output_tokens",
                 "mean_turns", "mean_duration_s", "mean_cost_usd", "gating"}}}

``eval/baselines/triggers.json`` — per skill × split confusion counts.

Files are written with sorted keys and no wall-clock timestamps, so the same
inputs always produce byte-identical output (reviewable diffs). They are
produced by ``rf-skill-eval baseline update`` and committed via a PR.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import yaml

from ..domain.results import ReplicateStats, Spread
from .trigger_eval import TriggerEvalResult

BASELINE_SCHEMA_VERSION = 1
_FIXTURE_IGNORE_DIRS = {".venv", "__pycache__", ".pytest_cache", "node_modules", "browser"}
_FIXTURE_IGNORE_FILES = {"output.xml", "log.html", "report.html"}


def fixture_tree_hash(fixture_dir: Path) -> str:
    digest = hashlib.sha256()
    if not fixture_dir.is_dir():
        return "missing"
    for path in sorted(fixture_dir.rglob("*")):
        rel = path.relative_to(fixture_dir)
        if any(part in _FIXTURE_IGNORE_DIRS for part in rel.parts):
            continue
        if not path.is_file() or path.name in _FIXTURE_IGNORE_FILES or path.suffix == ".pyc":
            continue
        digest.update(rel.as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def task_hash(task_path: Path, fixtures_root: Path) -> str:
    """sha256 of the normalised task YAML plus its fixture tree hash."""
    text = task_path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) if task_path.suffix in (".yaml", ".yml") else json.loads(text)
    normalised = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    fixture = data.get("fixture") if isinstance(data, dict) else None
    fixture_hash = fixture_tree_hash(fixtures_root / str(fixture)) if fixture else "none"
    return hashlib.sha256(f"{normalised}\n{fixture_hash}".encode()).hexdigest()


def _mean(spread: Spread | None, digits: int = 4) -> float | None:
    return round(spread.mean, digits) if spread is not None else None


def entry_key(task_id: str, arm: str) -> str:
    return f"{task_id}|{arm}"


def build_tier_baseline(
    stats: Iterable[ReplicateStats],
    *,
    tier: str,
    task_hashes: Mapping[str, str],
    harness_version: str,
    claude_code_version: str,
) -> dict[str, Any]:
    entries: dict[str, Any] = {}
    for s in stats:
        if s.tier != tier:
            continue
        entries[entry_key(s.task_id, s.arm)] = {
            "task_id": s.task_id,
            "arm": s.arm,
            "skill": s.skill,
            "model": s.model,
            "task_hash": task_hashes.get(s.task_id, "unknown"),
            "runs": s.runs,
            "pass_rate": round(s.pass_rate, 4),
            "outcome_pass_rate": round(s.outcome_pass_rate, 4),
            "incomplete": s.incomplete,
            "mean_input_tokens": _mean(s.input_tokens, 1),
            "mean_output_tokens": _mean(s.output_tokens, 1),
            "mean_turns": _mean(s.turns, 2),
            "mean_duration_s": _mean(s.duration_s, 2),
            "mean_cost_usd": _mean(s.cost_usd, 6),
            "gating": tier != "adversarial",
        }
    return {
        "kind": "tier-baseline",
        "schema_version": BASELINE_SCHEMA_VERSION,
        "tier": tier,
        "harness_version": harness_version,
        "claude_code_version": claude_code_version,
        "entries": dict(sorted(entries.items())),
    }


def build_trigger_baseline(result: TriggerEvalResult, *, harness_version: str) -> dict[str, Any]:
    skills: dict[str, Any] = {}
    for m in result.metrics:
        skills.setdefault(m.skill, {})[m.split] = {
            "tp": m.tp,
            "fp": m.fp,
            "tn": m.tn,
            "fn": m.fn,
            "queries": m.total,
            "accuracy": None if m.accuracy is None else round(m.accuracy, 4),
            "precision": None if m.precision is None else round(m.precision, 4),
            "recall": None if m.recall is None else round(m.recall, 4),
        }
    return {
        "kind": "trigger-baseline",
        "schema_version": BASELINE_SCHEMA_VERSION,
        "harness_version": harness_version,
        "model": result.model,
        "skills": dict(sorted(skills.items())),
    }


def dump_json(data: Mapping[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def write_json(path: Path, data: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_json(data), encoding="utf-8")
    return path


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def baseline_entry(
    baseline: Mapping[str, Any] | None, task_id: str, arm: str
) -> dict[str, Any] | None:
    if not baseline:
        return None
    entry = baseline.get("entries", {}).get(entry_key(task_id, arm))
    return entry if isinstance(entry, dict) else None
