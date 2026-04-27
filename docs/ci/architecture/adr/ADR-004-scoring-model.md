# ADR-004: Scoring Model — Deterministic Rubric with Effect-Size Gating

**Status:** Accepted
**Date:** 2026-04-14
**Deciders:** System Architecture
**Related:** ADR-002, ADR-006

---

## Context

"Did this skill help?" is the question the harness must answer. Three scoring
paradigms are mainstream in 2026:

1. **Deterministic rubric** — pre-declared metrics computed from logs + grader
   output; statistical comparison between arms; pre-declared shipping gate.
2. **LLM-as-judge** — a strong model reads each session transcript and scores
   quality on a Likert scale or pairwise preference.
3. **Hybrid** — deterministic grader for ground truth + LLM-as-judge for
   qualitative "was the agent's reasoning good?" assessment.

The parent docs make clear that the project has access to:

- Rich session telemetry (JSONL) — ~30 metrics already enumerated.
- A reliable grader — `robot` command + lint + custom Python criteria.
- RF-specific signals that are already **externally grounded** (test pass rate,
  execution-before-completion, library import resolves).

The shipping gate must be:

- **Defensible at RoboCon.** Reviewers will challenge arbitrary thresholds.
- **Resistant to self-scoring bias.** A skill that literally says "do not write
  'simplest'" will improve "simplest" rate without improving quality.
- **Affordable.** Running LLM-as-judge over 480 sessions × N scorecards has
  non-trivial cost.
- **Reproducible.** Same inputs → same scorecard, bit-for-bit.

---

## Decision

**Adopt a deterministic rubric with effect-size-based gating, applied to a
pre-declared set of primary metrics.**

No LLM-as-judge scoring in v1.

### Rubric structure

Metrics are partitioned into:

- **Primary metrics** (gating, ~4 per skill type). Pre-registered. Must be
  **externally grounded** (grader-derived or user-signal-derived), not
  self-reported by the model.
- **Secondary metrics** (reported, not gating). Model-self-reported metrics
  (reasoning loops, "simplest" rate) live here — useful context, but not a ship
  gate.
- **Cost metrics** (token and wall-time). Not gating individually but contribute
  to the budget rule.

### Primary metrics for RF skills (initial set, revisable)

1. `first_run_test_pass_pct` — grader verdict.
2. `executed_before_complete` — boolean per task (rf-mcp execution observed).
3. `user_interrupts_per_1k` — user interrupt count per 1000 tool calls.
4. `convention_violations_per_task` — grader-lint-derived.

All four are derived from external ground truth (grader or human signal), not
from the assistant's own output.

### Statistical model

For each `(primary_metric, skill_or_bundle)`:

1. Collect the per-session metric values for `control` and `treatment` arms.
2. Compute median + IQR per arm.
3. Run Mann-Whitney U (non-parametric; metrics are non-normal).
4. Compute Cliff's delta δ (effect size ∈ [-1, +1]).
5. Bootstrap 95% CI on the treatment-minus-control difference (N=10,000
   resamples).
6. Apply Benjamini-Hochberg correction at α=0.05 across the **primary set only**.

### Shipping gate

A skill (or bundle) earns **SHIP** iff:

1. At least one primary quality metric improves with `|δ| ≥ 0.33` ("medium"
   effect) and BH-corrected 95% CI excludes zero.
2. No primary quality metric regresses with `|δ| ≥ 0.33`.
3. `input_tokens_per_task` increase ≤ 30% (configurable per skill type).
4. End-to-end `task_success` rate does not decrease.

**ITERATE:** some primary metrics improve and some regress; or improvements are
small-but-positive. Ship is held pending next iteration.

**HOLD:** any primary metric regresses beyond the threshold, or cost blows the
budget.

Secondary metrics are **reported** in the scorecard (with δ and CI) but do not
affect the verdict. They are used for diagnostics, not gates.

### Self-scoring-bias guard

The gate rule explicitly forbids primary metrics that are computed from the
assistant's own output text. Model-self-reported metrics are secondary only.
This prevents trivial "don't say 'simplest'" skill games (flagged in the parent
plan §9).

### Anti-gaming for the grader

- Criteria include `lint_clean` and `no_deprecated_keywords` (not just "did it
  pass"), so the model can't trivially satisfy `robot_pass` by writing a
  tautological test.
- Tasks with `adversarial_flags` are graded, but their primary metrics are
  **reported only** in v1 — adversarial tier doesn't gate ship (per plan §10.3).

---

## Consequences

### Positive

- **Reproducible.** No model variance in the scoring itself. Same inputs → same
  verdict.
- **Defensible.** Every number traces to either a deterministic parser or the
  `robot` exit code. No "the judge model felt like it today."
- **Cheap.** Zero API cost for scoring. All computation is local (polars + scipy).
- **Fast iteration on the rubric.** Changing the gate rule is a config change;
  re-scoring 480 existing runs takes seconds.
- **Catches self-scoring bias by construction.** Primary metrics are grounded
  externally; a skill that manipulates only the model's own vocabulary cannot
  pass the gate.
- **Aligned with the issue #42796 methodology** described in the parent doc —
  that analysis was itself deterministic log mining.

### Negative

- **Cannot catch qualitative failures** that don't manifest in any declared
  metric. A session could be a subtly confused mess that still passes tests.
  Mitigated by: the metric catalog is broad (30+ metrics); the failure gallery
  in the scorecard (§7.1) surfaces examples for human eyeballing; we can add
  LLM-as-judge later if gaps appear.
- **Requires task authors to write good graders.** A weak `success_criteria`
  means the primary `first_run_test_pass_pct` is noisy. Mitigated by: composable
  criterion types let authors express "passes AND lints AND no deprecated
  keywords" in a few YAML lines.
- **Primary set is a human judgment call.** Four metrics encode what we think
  quality means; reasonable reviewers could pick a different four. Mitigated by:
  the set is versioned alongside the gate rule; changing it bumps the suite
  version and is a PR-visible decision.

### Neutral

- The scorecard shows secondary metrics even when they don't gate — reviewers
  still see "reasoning loops down, simplest rate down" as context for why a
  skill ships, even though those numbers didn't decide the outcome.

---

## Alternatives Considered

### LLM-as-judge (primary scoring)

- **Pros:** Catches qualitative issues deterministic metrics miss; simpler rubric
  authoring ("rate this session 1–5 on adherence to RF conventions").
- **Cons:** Expensive (~1K–10K judge calls per scorecard); non-reproducible (same
  judge model yields different scores across days); introduces a second model as
  a dependency; susceptible to judge-bias games (models favor outputs that look
  like their own).
- **Why rejected:** Reproducibility and cost. Also: we already have a grader
  (`robot`) that gives us ground-truth pass/fail for free.

### Hybrid (deterministic for gate + LLM-as-judge for diagnostic)

- **Pros:** Gets qualitative insight without compromising gate reproducibility.
- **Cons:** Adds complexity and a new dependency; cost overhead; judge drift.
- **Why deferred:** Plausible v2 extension once the deterministic harness is
  proven. Keep the seam by making the scoring pipeline pluggable at the
  `ArmComparison` level.

### Pairwise preference (A/B ranking of session pairs)

- **Pros:** Statistically robust; avoids calibration issues of absolute scores.
- **Cons:** Requires a judge model (same cost/reproducibility issue); doesn't
  give interpretable effect sizes per metric; harder to read in a scorecard.
- **Why rejected:** Worse interpretability for a harness whose output is a PR
  comment.

### Single-metric composite score ("one number per skill")

- **Pros:** Simplest possible reporting.
- **Cons:** Weights are arbitrary; hides which dimension regressed; encourages
  gaming the most-weighted component.
- **Why rejected:** A panel of metrics is more informative and harder to game.

### p-value-only gating

- **Pros:** Traditional.
- **Cons:** A significant but tiny effect (δ=0.02) passes p < 0.05 at large N
  and is operationally meaningless. Context-heavy skills must earn their cost
  with **real** effects, not just detectable ones.
- **Why rejected:** Effect-size gating is stricter and more useful.

---

## Implementation Notes

- The primary metric list and gate rule live in code (`domain/scoring/gate.py`),
  versioned, and snapshot into every scorecard as metadata. A scorecard always
  knows which rule produced its verdict.
- Benjamini-Hochberg correction is applied inside `domain/scoring/comparison.py`
  over the primary set. Secondary metrics are not corrected (they're
  exploratory).
- Bootstrap CI uses seeded RNG for determinism.
- When a cell has N < 5 replicates (e.g., timed-out runs excluded), the metric
  is marked `insufficient_data` rather than reported with a noisy CI.
- Add a "promote to primary" review cadence: quarterly, examine which secondary
  metrics have stabilized as leading indicators and consider promoting.

---

## References

- `docs/ci/claude-code-extension-quality-evaluation.md` §3.4 — stop-hook violation
  rate as a canary.
- `docs/ci/rf-agentskills-eval-implementation-plan.md` §5 — statistical approach
  (Mann-Whitney, Cliff's delta, bootstrap CI).
- Cliff, *Dominance Statistics* (1993) — effect size for ordinal data.
- Benjamini & Hochberg (1995) — FDR control.
