"""Regression gate against the stored baseline (design D2, D4, D6).

Per gating task (tier != adversarial) in the treatment arm:

* any ``incomplete`` replicate -> **fail** (message names the skipped/errored
  gating check and its reason);
* no baseline entry, or task hash / model differs -> ``rebaseline-needed``
  (excluded from comparison, never counted as passing);
* pass rate significantly below the baseline -> **fail**. With a baseline of
  at least ``MIN_FISHER_BASELINE_RUNS`` replicates the default test is a
  one-sided Fisher exact test (p < ``FISHER_ALPHA``) on pass/fail counts;
  with a smaller baseline, or an explicit ``tolerance``, a drop of more than
  the tolerance (default one replicate's worth, i.e. > 1/N) fails;
* mean input tokens up by more than the budget (default 30%) -> **fail**.

Trigger check against ``eval/baselines/triggers.json``: when the baseline has
run-level counts, skill loads on should-trigger queries (recall) and non-loads
on should-not-trigger queries (precision) are each compared with a one-sided
Fisher exact test (p < ``FISHER_ALPHA``); older baselines fall back to
"validation accuracy may not drop by more than one query's worth". Every shipped skill's
description must be shown in every recorded skill listing (a name-only entry
means Claude Code's listing room is too small for all descriptions).

Exit codes: 0 pass, 1 fail, 3 only rebaseline-needed findings (not a pass).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from math import comb
from typing import Any, Literal

from ..domain.results import ReplicateStats
from ..domain.trigger import run_load_counts
from .baseline import baseline_entry
from .trigger_eval import TriggerEvalResult

FindingKind = Literal[
    "incomplete",
    "pass-rate",
    "tokens",
    "rebaseline-needed",
    "trigger-accuracy",
    "cost-cap",
    "listing",
]
_EPS = 1e-9
#: Stored trigger rates are rounded to 4 decimals.
_ROUNDING_EPS = 5e-4
#: A 3-run baseline cannot reach p < 0.05 against 3 PR runs (3/3 vs 0/3 gives
#: p = 0.05), so Fisher is used only when the baseline has this many runs.
MIN_FISHER_BASELINE_RUNS = 6
FISHER_ALPHA = 0.05


def fisher_lower_p(passes: int, runs: int, base_passes: int, base_runs: int) -> float:
    """One-sided Fisher exact p: chance of ``passes`` or fewer in ``runs`` if both
    samples share one pass rate (hypergeometric lower tail)."""
    total, successes = runs + base_runs, passes + base_passes
    denom = comb(total, runs)
    return (
        sum(comb(successes, i) * comb(total - successes, runs - i) for i in range(passes + 1))
        / denom
    )


@dataclass(frozen=True)
class GateFinding:
    kind: FindingKind
    subject: str
    message: str

    @property
    def blocking(self) -> bool:
        return self.kind != "rebaseline-needed"


@dataclass
class GateReport:
    findings: list[GateFinding] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)

    @property
    def status(self) -> Literal["pass", "fail", "rebaseline-needed"]:
        if any(f.blocking for f in self.findings):
            return "fail"
        if self.findings:
            return "rebaseline-needed"
        return "pass"

    @property
    def exit_code(self) -> int:
        return {"pass": 0, "fail": 1, "rebaseline-needed": 3}[self.status]

    def render(self) -> str:
        lines = [f"gate: {self.status.upper()} ({len(self.checked)} task(s) checked)"]
        for f in self.findings:
            lines.append(f"- [{f.kind}] {f.subject}: {f.message}")
        return "\n".join(lines)


def _pass_rate_finding(
    s: ReplicateStats, entry: Mapping[str, Any], tolerance: float | None
) -> GateFinding | None:
    base_rate = float(entry.get("pass_rate", 0.0))
    base_runs = int(entry.get("runs", 0))
    if tolerance is None and base_runs >= MIN_FISHER_BASELINE_RUNS:
        p = fisher_lower_p(s.passes, s.runs, round(base_rate * base_runs), base_runs)
        if p >= FISHER_ALPHA:
            return None
        return GateFinding(
            "pass-rate",
            s.task_id,
            f"treatment pass rate {s.pass_rate:.2f} (N={s.runs}) vs baseline "
            f"{base_rate:.2f} (N={base_runs}); Fisher p={p:.3f} < {FISHER_ALPHA}",
        )
    tol = tolerance if tolerance is not None else 1.0 / max(s.runs, 1)
    if base_rate - s.pass_rate <= tol + _EPS:
        return None
    return GateFinding(
        "pass-rate",
        s.task_id,
        f"treatment pass rate {s.pass_rate:.2f} vs baseline {base_rate:.2f} "
        f"(tolerance {tol:.2f}, N={s.runs})",
    )


def gate_tasks(
    current: Iterable[ReplicateStats],
    baseline: Mapping[str, Any] | None,
    task_hashes: Mapping[str, str],
    *,
    tolerance: float | None = None,
    token_budget: float = 0.30,
) -> GateReport:
    report = GateReport()
    for s in current:
        if s.arm != "treatment" or s.tier == "adversarial":
            continue
        report.checked.append(s.task_id)
        if s.incomplete:
            reasons = "; ".join(s.incomplete_reasons) or "no reason recorded"
            report.findings.append(
                GateFinding(
                    "incomplete",
                    s.task_id,
                    f"{s.incomplete}/{s.runs} run(s) incomplete: {reasons}",
                )
            )
        entry = baseline_entry(baseline, s.task_id, "treatment")
        if entry is None:
            report.findings.append(
                GateFinding("rebaseline-needed", s.task_id, "no stored baseline entry")
            )
            continue
        current_hash = task_hashes.get(s.task_id)
        if current_hash is not None and entry.get("task_hash") != current_hash:
            report.findings.append(
                GateFinding("rebaseline-needed", s.task_id, "task definition or fixture changed")
            )
            continue
        if entry.get("model") != s.model:
            report.findings.append(
                GateFinding(
                    "rebaseline-needed",
                    s.task_id,
                    f"model differs (baseline {entry.get('model')}, now {s.model})",
                )
            )
            continue
        finding = _pass_rate_finding(s, entry, tolerance)
        if finding is not None:
            report.findings.append(finding)
        base_tokens = entry.get("mean_input_tokens")
        if base_tokens and s.input_tokens is not None:
            increase = s.input_tokens.mean / float(base_tokens) - 1.0
            if increase > token_budget + _EPS:
                report.findings.append(
                    GateFinding(
                        "tokens",
                        s.task_id,
                        f"mean input tokens +{increase:.0%} ({float(base_tokens):.0f} -> "
                        f"{s.input_tokens.mean:.0f}; budget +{token_budget:.0%})",
                    )
                )
    return report


def gate_triggers(
    current: TriggerEvalResult,
    baseline: Mapping[str, Any] | None,
    report: GateReport | None = None,
    *,
    split: str = "validation",
) -> GateReport:
    report = report or GateReport()
    stored = (baseline or {}).get("skills", {})
    counts = run_load_counts(current.outcomes)
    for m in current.metrics:
        if m.split != split:
            continue
        subject = f"triggers:{m.skill}"
        report.checked.append(subject)
        base = stored.get(m.skill, {}).get(split)
        if not base or base.get("accuracy") is None:
            report.findings.append(
                GateFinding("rebaseline-needed", subject, "no stored trigger baseline")
            )
            continue
        if m.accuracy is None:
            continue
        if "positive_runs" in base:
            finding = _trigger_runs_finding(subject, split, base, counts.get((m.skill, m.split)))
            if finding is not None:
                report.findings.append(finding)
            continue
        one_query = 1.0 / max(m.total, 1)
        drop = float(base["accuracy"]) - m.accuracy
        if all(k in base for k in ("tp", "tn", "queries")) and int(base["queries"]) == m.total:
            # Compare whole queries: stored rates are rounded to 4 decimals, so a
            # one-query drop (e.g. 9/11 -> 8/11) would otherwise exceed 1/11 by rounding.
            regressed = (int(base["tp"]) + int(base["tn"])) - (m.tp + m.tn) > 1
        else:
            regressed = drop > one_query + _ROUNDING_EPS
        if regressed:
            report.findings.append(
                GateFinding(
                    "trigger-accuracy",
                    subject,
                    f"{split} accuracy {m.accuracy:.2f} vs baseline {float(base['accuracy']):.2f} "
                    f"(allowed drop: one query = {one_query:.2f})",
                )
            )
    for o in current.incomplete_queries:
        report.findings.append(
            GateFinding(
                "incomplete",
                f"triggers:{o.skill}:{o.query_id}",
                f"{o.incomplete} run(s) did not complete",
            )
        )
    return report


def _trigger_runs_finding(
    subject: str, split: str, base: Mapping[str, Any], cur: Mapping[str, int] | None
) -> GateFinding | None:
    """Run-level recall / precision regression (one-sided Fisher exact tests)."""
    if not cur:
        return None
    problems = []
    checks = (
        ("recall", "skill loads on should-trigger runs",
         cur["positive_loads"], cur["positive_runs"],
         int(base["positive_loads"]), int(base["positive_runs"])),
        ("precision", "no load on should-not-trigger runs",
         cur["negative_runs"] - cur["negative_loads"], cur["negative_runs"],
         int(base["negative_runs"]) - int(base["negative_loads"]), int(base["negative_runs"])),
    )
    for name, what, k, n, kb, nb in checks:
        if n == 0 or nb == 0:
            continue
        p = fisher_lower_p(k, n, kb, nb)
        if p < FISHER_ALPHA:
            problems.append(f"{name}: {what} {k}/{n} vs baseline {kb}/{nb} (Fisher p={p:.3f})")
    if not problems:
        return None
    return GateFinding("trigger-accuracy", subject, f"{split} " + "; ".join(problems))


def gate_listing(
    current: TriggerEvalResult, shipped: Iterable[str], report: GateReport | None = None
) -> GateReport:
    """Fail for each shipped skill listed name-only in any recorded skill listing."""
    report = report or GateReport()
    listings = [seen for o in current.outcomes for seen in o.visible_descriptions]
    if not listings:
        return report
    for skill in sorted(shipped):
        missing = sum(1 for seen in listings if skill not in seen)
        if missing:
            report.findings.append(
                GateFinding(
                    "listing",
                    f"listing:{skill}",
                    f"description not shown in {missing}/{len(listings)} skill listing(s): "
                    "the listing room is too small for all descriptions "
                    "(re-measure it, see tests/test_skill_descriptions.py)",
                )
            )
    return report


def gate_cost(report: GateReport, spent_usd: float, cap_usd: float | None) -> GateReport:
    if cap_usd is not None and spent_usd > cap_usd + _EPS:
        report.findings.append(
            GateFinding("cost-cap", "batch", f"reported cost ${spent_usd:.2f} exceeds cap ${cap_usd:.2f}")
        )
    return report
