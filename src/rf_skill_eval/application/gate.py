"""Regression gate against the stored baseline (design D2, D4, D6).

Per gating task (tier != adversarial) in the treatment arm:

* any ``incomplete`` replicate -> **fail** (message names the skipped/errored
  gating check and its reason);
* no baseline entry, or task hash / model differs -> ``rebaseline-needed``
  (excluded from comparison, never counted as passing);
* pass-rate drop > tolerance (default: more than one replicate's worth,
  i.e. > 1/N) -> **fail**;
* mean input tokens up by more than the budget (default 30%) -> **fail**.

Trigger check: validation-split accuracy may not drop by more than one
query's worth against ``eval/baselines/triggers.json``.

Exit codes: 0 pass, 1 fail, 3 only rebaseline-needed findings (not a pass).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from ..domain.results import ReplicateStats
from .baseline import baseline_entry
from .trigger_eval import TriggerEvalResult

FindingKind = Literal[
    "incomplete",
    "pass-rate",
    "tokens",
    "rebaseline-needed",
    "trigger-accuracy",
    "cost-cap",
]
_EPS = 1e-9


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
        tol = tolerance if tolerance is not None else 1.0 / max(s.runs, 1)
        base_rate = float(entry.get("pass_rate", 0.0))
        if base_rate - s.pass_rate > tol + _EPS:
            report.findings.append(
                GateFinding(
                    "pass-rate",
                    s.task_id,
                    f"treatment pass rate {s.pass_rate:.2f} vs baseline {base_rate:.2f} "
                    f"(tolerance {tol:.2f}, N={s.runs})",
                )
            )
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
        one_query = 1.0 / max(m.total, 1)
        drop = float(base["accuracy"]) - m.accuracy
        if drop > one_query + _EPS:
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


def gate_cost(report: GateReport, spent_usd: float, cap_usd: float | None) -> GateReport:
    if cap_usd is not None and spent_usd > cap_usd + _EPS:
        report.findings.append(
            GateFinding("cost-cap", "batch", f"reported cost ${spent_usd:.2f} exceeds cap ${cap_usd:.2f}")
        )
    return report
