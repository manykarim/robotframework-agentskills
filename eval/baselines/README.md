# Stored baselines

Reference results the CI regression gate compares against
(`rf-skill-eval gate`). They are **produced by the harness, never edited by
hand**, and promoted through a reviewed pull request.

| File | Content | Written by |
|---|---|---|
| `narrow.json` (and `realistic.json`, `adversarial.json`) | Per task × arm: pass rate, replicate count, incomplete count, mean input/output tokens, turns, duration and cost, model id, task hash (normalised task YAML + fixture tree), harness and Claude Code versions | `rf-skill-eval baseline update --from <runs-dir>` |
| `triggers.json` | Per skill × split: TP/FP/TN/FN, accuracy, precision, recall, model | same command, from a `trigger-results.json` |

## Promotion flow

1. The weekly (or a manual) *Skill Evaluation* run executes all tiers in both
   arms with `--runs 3` plus all trigger sets, and uploads a
   `candidate-baseline/` artifact produced by `baseline update`.
2. A maintainer downloads it, copies the files here and opens a PR
   (`chore(eval): promote baseline from run <id>`), linking the run.
3. Review: pass-rate / token changes should be explained by skill or task
   changes in the same period.

Until the first weekly baseline is promoted these files do not exist and
`gate` reports every task as `rebaseline-needed` (exit 3 — never a pass). The
PR gate becomes a *required* status check only after two weekly baselines
have been recorded.

A task whose definition or fixture changed (hash mismatch), or whose model
differs, is reported as `rebaseline-needed` and excluded from comparison until
the next promotion.
