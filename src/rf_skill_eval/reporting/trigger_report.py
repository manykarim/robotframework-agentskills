"""Trigger-eval report: per skill × split confusion metrics, description
visibility in the skill listing (when recorded) and a confusion list."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..application.trigger_eval import TriggerEvalResult
from ..domain.trigger import REQUIRED_SPLITS, TriggerMetrics


def _pct(value: float | None) -> str:
    return "–" if value is None else f"{value * 100:.0f}%"


def _cell(m: TriggerMetrics | None) -> list[str]:
    if m is None:
        return ["–", "–", "–", "–"]
    return [f"{m.tp}/{m.fp}/{m.tn}/{m.fn}", _pct(m.precision), _pct(m.recall), _pct(m.accuracy)]


def render_trigger_markdown(
    result: TriggerEvalResult, *, baseline: Mapping[str, Any] | None = None
) -> str:
    metrics = {(m.skill, m.split): m for m in result.metrics}
    skills = sorted({o.skill for o in result.outcomes})
    stored = (baseline or {}).get("skills", {})
    # Holdout columns only appear when holdout queries ran (spec: own column).
    splits: tuple[str, ...] = REQUIRED_SPLITS
    if any(o.split == "holdout" for o in result.outcomes):
        splits = (*REQUIRED_SPLITS, "holdout")
    head = {"train": "Train", "validation": "Val", "holdout": "Holdout"}
    header = " | ".join(
        f"{head[s]} TP/FP/TN/FN | {head[s]} P | {head[s]} R | {head[s]} Acc" for s in splits
    )
    budget = "default" if result.listing_budget is None else f"{result.listing_budget} characters"
    out = [
        "# rf-skill-eval trigger report",
        "",
        f"Model `{result.model or 'default'}` · skill-listing budget {budget} · "
        "a query is *triggered* when its trigger rate "
        "(loads / runs) is >= its set's threshold. TP/FP/TN/FN per split; train and "
        "validation are reported separately (tune on train only).",
        "",
        f"| Skill | {header} | Stored Val Acc |",
        "|---|" + "---|---|---|---|" * len(splits) + "---|",
    ]
    for skill in skills:
        cells: list[str] = []
        for split in splits:
            cells += _cell(metrics.get((skill, split)))
        stored_acc = stored.get(skill, {}).get("validation", {}).get("accuracy")
        out.append(f"| {skill} | " + " | ".join(cells) + f" | {_pct(stored_acc)} |")
    out += _visibility_section(result)
    failing = [o for o in result.outcomes if not o.passed]
    out += ["", "## Failing queries", ""]
    if not failing:
        out.append("_None._")
    for o in failing:
        expect = "should trigger" if o.should_trigger else "should NOT trigger"
        status = "incomplete" if o.runs == 0 else f"rate {o.loads}/{o.runs}"
        others = ", ".join(o.other_skills) if o.other_skills else "none"
        out.append(
            f"- `{o.skill}` `{o.query_id}` ({o.split}, {expect}): {status}; "
            f"other skills loaded: {others} — {o.query[:120]}"
        )
    out.append("")
    return "\n".join(out)


def _frac(num: int, den: int) -> str:
    return f"{num}/{den}" if den else "–"


def _visibility_section(result: TriggerEvalResult) -> list[str]:
    """Per skill: sessions whose skill listing showed its description (D14)."""
    rows = result.visibility
    if not rows:
        return []
    out = [
        "",
        "## Description visibility",
        "",
        "Sessions whose skill listing showed the skill's description (the rest listed it "
        "by name only). *Own* counts the sessions of the skill's own queries, *All* every "
        "session in this result.",
        "",
        "| Skill | Own sessions | All sessions |",
        "|---|---|---|",
    ]
    for v in rows:
        out.append(
            f"| {v.skill} | {_frac(v.own_visible, v.own_listed)} | "
            f"{_frac(v.all_visible, v.all_listed)} |"
        )
    return out
