"""Arm-aware evaluation report (design D3–D5, spec "Arm deltas are reported").

``build_report`` turns graded run results into a deterministic, JSON-ready
dict; ``render_markdown`` renders it for PR comments / step summaries.

* Per task: per-arm pass rate (gate), outcome pass rate, incomplete count,
  mean tokens/turns/duration/cost, flaky flag, and the treatment-minus-
  baseline delta computed from **outcome** checks only. A missing arm makes
  the delta ``None`` (rendered "unavailable", never 0).
* When the baseline arm was not run (PR tier), its numbers are read from the
  stored baseline file and marked ``source: stored``.
* Skipped/errored checks are listed with reasons; process checks are shown
  for the treatment arm only; adversarial tasks are marked non-gating.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from ..application.baseline import baseline_entry
from ..domain.results import ReplicateStats, RunResult, Spread, aggregate_replicates
from ..domain.task import PLUGIN_SKILL

_METRICS = ("input_tokens", "output_tokens", "turns", "duration_s", "cost_usd")


def _mean(spread: Spread | None) -> float | None:
    return None if spread is None else round(spread.mean, 4)


def _arm_block(s: ReplicateStats) -> dict[str, Any]:
    return {
        "source": "run",
        "model": s.model,
        "runs": s.runs,
        "pass_rate": round(s.pass_rate, 4),
        "outcome_pass_rate": round(s.outcome_pass_rate, 4),
        "incomplete": s.incomplete,
        "flaky": s.flaky,
        "input_tokens": _mean(s.input_tokens),
        "output_tokens": _mean(s.output_tokens),
        "turns": _mean(s.turns),
        "duration_s": _mean(s.duration_s),
        "cost_usd": _mean(s.cost_usd),
        "stdev": {
            m: (None if getattr(s, m) is None else round(getattr(s, m).stdev, 4))
            for m in _METRICS
        },
    }


def _stored_block(entry: Mapping[str, Any], current_hash: str | None) -> dict[str, Any]:
    stale = current_hash is not None and entry.get("task_hash") != current_hash
    return {
        "source": "stored (rebaseline-needed)" if stale else "stored",
        "model": entry.get("model"),
        "runs": entry.get("runs"),
        "pass_rate": entry.get("pass_rate"),
        "outcome_pass_rate": entry.get("outcome_pass_rate"),
        "incomplete": entry.get("incomplete", 0),
        "flaky": None,
        "input_tokens": entry.get("mean_input_tokens"),
        "output_tokens": entry.get("mean_output_tokens"),
        "turns": entry.get("mean_turns"),
        "duration_s": entry.get("mean_duration_s"),
        "cost_usd": entry.get("mean_cost_usd"),
        "stdev": {},
    }


def _delta(t: Mapping[str, Any] | None, b: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not t or not b:
        return None
    if not t.get("runs") or not b.get("runs"):
        return None
    out: dict[str, Any] = {}
    for key in ("outcome_pass_rate", *_METRICS):
        tv, bv = t.get(key), b.get(key)
        out[key] = None if tv is None or bv is None else round(float(tv) - float(bv), 4)
    return out


def build_report(
    results: Iterable[RunResult],
    *,
    stored_baseline: Mapping[str, Any] | None = None,
    task_hashes: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    results = list(results)
    stats = aggregate_replicates(results)
    hashes = task_hashes or {}
    by_task: dict[str, dict[str, ReplicateStats]] = {}
    for s in stats:
        by_task.setdefault(s.task_id, {})[s.arm] = s

    tasks: list[dict[str, Any]] = []
    for task_id in sorted(by_task):
        arms = by_task[task_id]
        first = next(iter(arms.values()))
        blocks: dict[str, Any] = {arm: _arm_block(s) for arm, s in sorted(arms.items())}
        if "baseline" not in blocks:
            entry = baseline_entry(stored_baseline, task_id, "baseline")
            if entry is not None:
                blocks["baseline"] = _stored_block(entry, hashes.get(task_id))
        treatment = arms.get("treatment")
        tasks.append(
            {
                "task_id": task_id,
                "skill": first.skill,
                "tier": first.tier,
                "gating": first.tier != "adversarial",
                "arms": blocks,
                "delta": _delta(blocks.get("treatment"), blocks.get("baseline")),
                "skipped": sorted({r for s in arms.values() for r in s.skipped_reasons}),
                "incomplete_reasons": sorted(
                    {r for s in arms.values() for r in s.incomplete_reasons}
                ),
                "process": [
                    {"check": name, "passed": ok, "runs": n}
                    for name, ok, n in (treatment.process_results if treatment else ())
                ],
            }
        )

    skills: list[dict[str, Any]] = []
    for skill in sorted({t["skill"] for t in tasks if t["skill"] != PLUGIN_SKILL}):
        rows = [t for t in tasks if t["skill"] == skill]
        skills.append(_skill_summary(skill, rows))

    summary = {
        "runs": len(results),
        "pass": sum(1 for r in results if r.gate_result == "pass"),
        "fail": sum(1 for r in results if r.gate_result == "fail"),
        "incomplete": sum(1 for r in results if r.gate_result == "incomplete"),
        "skipped_checks": sum(
            1 for r in results for v in r.scorecard.verdicts if v.status in ("skipped", "error")
        ),
        "cost_usd": round(
            sum(r.run.usage.total_cost_usd for r in results if r.run.usage is not None), 6
        ),
    }
    return {"kind": "eval-report", "summary": summary, "tasks": tasks, "skills": skills}


def _avg(values: list[Any]) -> float | None:
    nums = [float(v) for v in values if v is not None]
    return round(sum(nums) / len(nums), 4) if nums else None


def _skill_summary(skill: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    def arm_values(arm: str, key: str) -> list[Any]:
        return [r["arms"][arm][key] for r in rows if arm in r["arms"]]

    deltas = [r["delta"] for r in rows if r["delta"] is not None]
    return {
        "skill": skill,
        "tasks": len(rows),
        "treatment_outcome_pass_rate": _avg(arm_values("treatment", "outcome_pass_rate")),
        "baseline_outcome_pass_rate": _avg(arm_values("baseline", "outcome_pass_rate")),
        "delta": (
            None
            if not deltas
            else {
                key: _avg([d[key] for d in deltas])
                for key in ("outcome_pass_rate", *_METRICS)
            }
        ),
        "tasks_with_delta": len(deltas),
    }


# --- rendering -------------------------------------------------------------------


def _fmt(value: Any, pct: bool = False, digits: int = 1) -> str:
    if value is None:
        return "–"
    if pct:
        return f"{float(value) * 100:.0f}%"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _fmt_delta(value: Any, pct: bool = False, digits: int = 1) -> str:
    if value is None:
        return "unavailable"
    v = float(value)
    if pct:
        return f"{v * 100:+.0f} pp"
    return f"{v:+.{digits}f}"


def _task_rows(t: Mapping[str, Any]) -> list[str]:
    tier = t["tier"] + ("" if t["gating"] else " (non-gating)")
    rows: list[str] = []
    for arm, b in t["arms"].items():
        arm_label = arm if b["source"] == "run" else f"{arm} ({b['source']})"
        flaky = "–" if b["flaky"] is None else ("yes" if b["flaky"] else "no")
        rows.append(
            f"| `{t['task_id']}` | {t['skill']} | {tier} | {arm_label} | {_fmt(b['runs'])} | "
            f"{_fmt(b['pass_rate'], pct=True)} | {_fmt(b['outcome_pass_rate'], pct=True)} | "
            f"{_fmt(b['incomplete'])} | {_fmt(b['input_tokens'], digits=0)} | "
            f"{_fmt(b['output_tokens'], digits=0)} | {_fmt(b['turns'])} | "
            f"{_fmt(b['duration_s'])} | {_fmt(b['cost_usd'], digits=4)} | {flaky} |"
        )
    d = t["delta"] or {}
    rows.append(
        f"| `{t['task_id']}` | {t['skill']} | {tier} | Δ T−B | | | "
        f"{_fmt_delta(d.get('outcome_pass_rate'), pct=True)} | | "
        f"{_fmt_delta(d.get('input_tokens'), digits=0)} | "
        f"{_fmt_delta(d.get('output_tokens'), digits=0)} | {_fmt_delta(d.get('turns'))} | "
        f"{_fmt_delta(d.get('duration_s'))} | {_fmt_delta(d.get('cost_usd'), digits=4)} | |"
    )
    return rows


def _skills_section(report: Mapping[str, Any]) -> list[str]:
    out = [
        "",
        "## Skills",
        "",
        "| Skill | Tasks | Treatment outcome pass | Baseline outcome pass | Δ outcome pass | "
        "Δ input tok | Δ turns | Δ cost $ |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for sk in report["skills"]:
        d = sk["delta"] or {}
        out.append(
            f"| {sk['skill']} | {sk['tasks']} | "
            f"{_fmt(sk['treatment_outcome_pass_rate'], pct=True)} | "
            f"{_fmt(sk['baseline_outcome_pass_rate'], pct=True)} | "
            f"{_fmt_delta(d.get('outcome_pass_rate'), pct=True)} | "
            f"{_fmt_delta(d.get('input_tokens'), digits=0)} | {_fmt_delta(d.get('turns'))} | "
            f"{_fmt_delta(d.get('cost_usd'), digits=4)} |"
        )
    return out


def _listing(title: str, items: list[str]) -> list[str]:
    return ["", f"## {title}", "", *(items or ["_None._"])]


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report["summary"]
    out: list[str] = [
        "# rf-skill-eval report",
        "",
        f"**Runs:** {s['runs']} · **pass:** {s['pass']} · **fail:** {s['fail']} · "
        f"**incomplete:** {s['incomplete']} · **skipped checks:** {s['skipped_checks']} · "
        f"**reported cost:** ${s['cost_usd']:.2f}",
        "",
        "Pass rate = runs whose gate result is `pass` / runs attempted. Deltas are "
        "treatment − baseline over **outcome** checks only.",
        "",
        "## Tasks",
        "",
        "| Task | Skill | Tier | Arm | Runs | Pass rate | Outcome pass | Incomplete | "
        "Input tok | Output tok | Turns | Duration s | Cost $ | Flaky |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for t in report["tasks"]:
        out += _task_rows(t)
    out += _skills_section(report)
    tasks = report["tasks"]
    out += _listing(
        "Skipped / errored checks",
        [
            f"- `{t['task_id']}` ({len(t['skipped'])} skipped): {r}"
            for t in tasks
            for r in t["skipped"]
        ],
    )
    out += _listing(
        "Incomplete runs",
        [f"- `{t['task_id']}`: {r}" for t in tasks for r in t["incomplete_reasons"]],
    )
    out += _listing(
        "Process checks (treatment arm, not in deltas)",
        [
            f"- `{t['task_id']}` `{p['check']}`: {p['passed']}/{p['runs']}"
            for t in tasks
            for p in t["process"]
        ],
    )
    out += _listing(
        "Adversarial tier (reported only, never gates)",
        [
            f"- `{t['task_id']}`: treatment pass rate "
            + (_fmt(t["arms"]["treatment"]["pass_rate"], pct=True) if "treatment" in t["arms"] else "–")
            for t in tasks
            if not t["gating"]
        ],
    )
    out.append("")
    return "\n".join(out)


def write_report(report: Mapping[str, Any], path: Path, fmt: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        path.write_text(render_markdown(report), encoding="utf-8")
    return path
