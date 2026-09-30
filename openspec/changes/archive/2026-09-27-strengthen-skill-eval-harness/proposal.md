## Why

The eval harness (`src/rf_skill_eval/`, `eval/`) cannot yet show that a skill helps. It runs only the with-skill ("treatment") arm, once per task, and a check whose tool is missing counts as a pass (`lint_clean` returns `passed=True, score=1.0, "robocop not installed; skipped"`). Skill descriptions are never tested for triggering. Only four skills have tasks, `eval/tasks/adversarial/` is empty, and the model allow-list (`claude-haiku-4-5`, `claude-sonnet-4-6`) is out of date. Several changes now in flight (retire the generator skills, merge the libdoc skills, restructure the library skills, sharpen descriptions, add guidance skills) all need proof that they help and do not cause regressions, so the harness has to be fixed first.

## What Changes

- **Paired baseline arm.** Every task can run in two arms: `treatment` (the plugin as shipped: skills, hooks, agents, `rf-tools` MCP) and `baseline` (no plugin parts; everything else the same). Reports show per-task and per-skill deltas in pass rate, tokens, turns, duration and cost. The current `control` profile (it still stages `rf-mcp` and has no reporting) is replaced by this arm.
- **Tri-state verdicts.** A verdict is `passed`, `failed`, `skipped` or `error`. A check that cannot run (tool missing, library not installable, no transcript) is `skipped` with a reason. It is never scored as a pass, and a skipped **gating** check makes the run's gate result `incomplete`, which fails the gate. **BREAKING** for stored scorecards and report consumers: `Verdict.passed: bool` becomes a `status` field (the old DB rows are migrated as `passed`/`failed`).
- **Replicates.** `--runs N` (default 3) on batch commands. The harness reports pass rate, mean, stdev and min/max of tokens/turns/duration per task×arm, and flags flaky tasks (0 < pass rate < 1).
- **Trigger evals.** New per-skill query sets (`eval/triggers/<skill>.yaml`). Each set has should-trigger queries and near-miss should-not-trigger queries, split into `train` and `validation`. Each query runs 3 times headlessly. The harness finds out whether the skill was loaded from the stream-json transcript and counts a query as triggered when the trigger rate is ≥ 0.5. It reports precision and recall per skill and per split.
- **Model policy update.** The allow-list becomes `claude-haiku-4-5-20251001`, `claude-sonnet-5` and `claude-opus-5-5`. Aliases for the old ids are rejected with a migration hint. Opus is allowed only as an explicit run-time opt-in in manual/scheduled runs, under a cost cap. Task YAML may not default to Opus. **BREAKING** for task YAMLs that pin old ids.
- **Coverage.** Add at least one narrow task per remaining skill: browser, selenium, appium (dry-run grader), requests, restinstance, platynui (dry-run grader), robotcode, setup, results and libdoc. Fill `eval/tasks/adversarial/` with tasks that tempt deprecated or non-existent keywords, `pip install` into the system Python, the wrong web library (Selenium in a Browser project), and "make it pass" shortcuts. Add grader check types `file_not_contains`, `robot_dryrun` and `keywords_resolve`. Add fixtures `sut-selenium`, `sut-api`, `sut-appium` and `sut-platynui`. The harness rejects any task (and trigger set) whose `skill` names no existing skill.
- **CI tiers and regression gate.** On PRs: narrow tier, treatment only, N=3, Haiku, scoped to changed skills plus canaries, compared against a committed baseline file (`eval/baselines/`). Trigger evals run on PRs that change a SKILL.md `description`. Weekly/manual: all tiers, both arms, trigger evals, and a candidate baseline refresh. Every run has an explicit cost cap. When the cap is reached, the remaining runs are marked `incomplete`; they are not treated as passes.

## Capabilities

### New Capabilities
- `skill-eval-harness`: the behavior contract of the `rf-skill-eval` harness: arms and paired comparison, verdict states and gating, replicates and variance, trigger evaluation, model/cost policy, task coverage and validity rules, adversarial reporting, and the CI regression gate against a stored baseline.

### Modified Capabilities
<!-- None. No existing spec in openspec/specs/ covers the eval harness. -->

## Impact

- **Code**: `src/rf_skill_eval/` affects `domain/{task,verdict,scorecard,profile,run}.py`, `scoring/{deterministic,rubric,session_based}.py`, `infrastructure/runner/claude_code_runner.py` (arm provisioning, trigger mode), `infrastructure/mcp/config_builder.py`, `infrastructure/telemetry/session_parser.py` (usage and Skill-load extraction), `infrastructure/persistence/sqlite_repo.py` (schema migration), `reporting/*` (arm deltas, variance, triggers), and `cli.py` (new `--runs`, `--arms`, `trigger`, `baseline`, `gate` and `--max-cost-usd` options/commands).
- **Eval content**: `eval/tasks/{narrow,realistic,adversarial}/`, new `eval/triggers/`, new `eval/baselines/`, new fixtures under `eval/fixtures/`, `eval/tasks/README.md`, `eval/fixtures/README.md`.
- **CI**: `.github/workflows/skill-evaluation.yml` and `scripts/eval-*.sh`.
- **Docs**: `docs/ci/architecture/adr/ADR-004-scoring-model.md` (model policy, skipped semantics) and ADR-005 (tiers), `docs/ci/usage.md`.
- **Tests**: `tests/eval/` (new tests for verdict states, arms, replicates, trigger detection, gate).
- **Coordination**: tasks for the retired generator skills are deleted by `retire-generator-skills`. Task/trigger `skill` values follow the names set by `align-skill-names-with-spec` and `merge-libdoc-skills` (`rf-libdoc`). `restructure-library-skills` and the planned guidance skills (`rf-language` from `add-rf-language-skill`, `rf-python-library` from `add-rf-python-library-skill`) use this harness to show uplift; `add-rf-language-skill` adds optional `args` / `expected_tests` to `robot_pass` / `robot_dryrun` if this change has not.
- **Cost**: roughly 2× runs per task when both arms run (the PR tier avoids this by reusing the stored baseline arm), plus about 3 × (number of queries) short sessions per skill for trigger evals.
