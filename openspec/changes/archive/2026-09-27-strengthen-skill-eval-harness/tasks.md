## 1. Verdict states and gating

- [x] 1.1 Add `status` (`passed|failed|skipped|error`) and `reason` to `src/rf_skill_eval/domain/verdict.py`, with `passed` as a derived property; verify with new unit tests in `tests/eval/test_domain_verdict.py`
- [x] 1.2 Make `check_lint_clean`, `check_robot_pass` (robot missing) and `_no_transcript_verdict` return `skipped` with a reason, and make `RubricGrader` return `error` on grader exceptions; verify `tests/eval/test_scoring_deterministic.py` has a test asserting that robocop-missing gives `skipped` and not a pass
- [x] 1.3 Add `gating` and `category` (`outcome|process`) to `GraderCheck` with the defaults from design D4, and compute a per-run gate result (`pass|fail|incomplete`) in `domain/scorecard.py`; verify with tests covering a skipped gating check (→ `incomplete`) and a skipped non-gating check (→ `pass`)
- [x] 1.4 Change `Scorecard.pass_rate`/`total_score` so skipped and error verdicts never count as passed; verify with a unit test
- [x] 1.5 Add `status`/`reason` columns and a `schema_version` migration to `infrastructure/persistence/sqlite_repo.py`; verify with a round-trip test against a checked-in pre-migration `eval.db` fixture
- [x] 1.6 Extend `doctor` to report grader tools needed by selected tasks (`robot`, `robocop`, library importability); verify `tests/eval/test_cli_doctor.py`

## 2. Model and cost policy

- [x] 2.1 Replace `ALLOWED_MODELS`/`DEFAULT_MODEL` in `domain/task.py` with `claude-haiku-4-5-20251001`, `claude-sonnet-5`, `claude-opus-5-5`; reject Opus in YAML and give migration hints for old ids; verify `tests/eval/test_domain_task.py`
- [x] 2.2 Update every YAML under `eval/tasks/` to the new ids (narrow → Haiku, realistic/adversarial → Sonnet); verify with `uv run rf-skill-eval validate-tasks eval/tasks` (new command) exiting 0
- [x] 2.3 Add `--allow-opus` and `--max-cost-usd` to `run`, `run-batch`, `trigger` and `gate`. Stop dispatching at the cap and record unstarted runs as `incomplete` (reason `budget`); verify with a unit test using a fake runner that reports cost
- [x] 2.4 Parse `usage`, `num_turns`, `duration_ms` and `total_cost_usd` from the stream-json `result` line in `infrastructure/telemetry/session_parser.py` and store them on the run record; verify with a test on a recorded `stdout.stream.jsonl` fixture
- [x] 2.5 Update ADR-004 (model policy, skipped semantics, gate result) and `eval/tasks/README.md` model section; verify the docs name no old model ids (`grep -rn "claude-sonnet-4-6\|claude-haiku-4-5\b" eval docs/ci src` returns only historical notes)

## 3. Arms and replicates

- [x] 3.1 Rename the arm concept: `baseline` provisions no plugin parts, `treatment` provisions the plugin as shipped, and `control` stays as a deprecated alias; update `cli.py` and `ClaudeCodeRunner.execute`; verify with a runner test asserting that the baseline config dir and workspace contain no `skills/`, `agents/` or plugin hooks
- [x] 3.2 Make `rf-mcp` a per-task `mcp_servers` declaration applied identically in both arms (`config_builder.include_rf_mcp` default false); add `mcp_servers: [rf-mcp]` to the tasks that allow `mcp__rf-mcp__*`; verify `tests/eval/test_infrastructure_mcp_config.py`
- [x] 3.3 Add a post-run leak assertion: a baseline transcript with an rf-agentskills skill load marks the run `error`; verify with a transcript-fixture test
- [x] 3.4 Add `--arms` and `--runs N` (default 3) to `run-batch`, with a fresh workspace per replicate; make `bench` an alias; verify with a fake-runner test that 2 tasks × 2 arms × 3 runs gives 12 runs
- [x] 3.5 Implement replicate aggregation (pass rate, incomplete count, mean/stdev/min/max for tokens/turns/duration/cost, flaky flag); verify with unit tests including the 2-of-3 → 0.67 flaky case
- [x] 3.6 Extend the Markdown/JSON reports with per-arm columns, treatment-minus-baseline deltas (outcome checks only, "unavailable" when an arm is missing), skipped counts with reasons, and per-skill summaries; verify `tests/eval/test_reporting.py` snapshot tests

## 4. Coverage: checks, fixtures, tasks

- [x] 4.1 Add check types `file_not_contains`, `robot_dryrun` and `keywords_resolve` (libdoc-spec-based static resolution including suite/resource user keywords); verify with unit tests on small `.robot` samples (resolving, unknown keyword, missing spec → `skipped`)
- [x] 4.2 Add task validity rules: `skill` must be `plugin` or a shipped skill `name` read from `skills/*/SKILL.md`; verify a test that `skill: keyword-builder` is rejected
- [x] 4.3 Re-tag canary tasks (`narrow-non-rf-control-01`, `narrow-rf-injection-positive-01`) to `skill: plugin`, and re-tag libdoc tasks to the merged libdoc skill name once `merge-libdoc-skills` lands; verify `validate-tasks` passes (canaries and `narrow-rf-mcp-execute-01` re-tagged `plugin`; libdoc tasks were already `rf-libdoc` from `merge-libdoc-skills`/`align-skill-names-with-spec`)
- [x] 4.4 Create fixtures `sut-selenium`, `sut-api`, `sut-appium` (with committed AppiumLibrary libdoc spec), and `sut-platynui` (with committed libdoc spec) following `eval/fixtures/README.md`; verify each fixture's `tests/example.robot` passes (or `keywords_resolve` passes for the spec-only fixtures)
- [ ] 4.5 Add narrow tasks for browser, selenium, appium, requests, restinstance, platynui, robotcode and setup, each with an outcome gating check per design D8; verify by running each once locally with `--runs 1` and checking that the gating check produces `passed` or `failed` (not `skipped`) (DEFERRED: live eval run — tracked in follow-up. The 8 tasks exist and pass `validate-tasks`; offline, `tests/eval/test_eval_content.py` grades each against the unmodified fixture (gating checks `passed`/`failed`, never `skipped`) and against a reference solution in `tests/eval/golden/` (gate `pass`); the live `--runs 1` check needs model runs)
- [x] 4.6 Add adversarial tasks `adv-browser-deprecated-wait`, `adv-selenium-nonexistent-kw`, `adv-setup-system-pip`, `adv-web-wrong-library` and `adv-make-it-pass` under `eval/tasks/adversarial/`; verify `validate-tasks` passes and the report shows them as non-gating
- [x] 4.7 Add `rf-skill-eval coverage` that fails when a shipped skill lacks a narrow task or trigger set; verify it fails when a temp skill dir is added and passes on the repo
- [x] 4.8 Confirm that the generator-skill tasks are gone (deleted by `retire-generator-skills`) and that no task references a retired skill; verify with `coverage` and `validate-tasks`

## 5. Trigger evals

- [x] 5.1 Define the trigger-set schema and loader (min 8 per polarity, split required, known skill, model allow-list); verify with loader unit tests
- [x] 5.2 Implement skill-load detection from transcripts (Skill tool with/without `<plugin>:` prefix; Read of `/skills/<dir>/SKILL.md` via the frontmatter name→dir map), recording other-skill loads; verify with transcript fixtures for both detection paths and a negative case
- [x] 5.3 Implement the `trigger` command (treatment provisioning with hooks disabled, empty workspace, `--max-turns 3`, tools `Skill,Read,Glob,Grep`, `--runs` default 3, threshold 0.5, `--split`); verify with a fake-runner test of the rate/threshold maths including 1-of-3 → not triggered
- [x] 5.4 Add trigger reporting (per skill × split: TP/FP/TN/FN, precision, recall, accuracy, confusion list); verify with a report snapshot test
- [x] 5.5 Author `eval/triggers/<skill>.yaml` for every shipped skill with sibling near misses (browser↔selenium, requests↔restinstance, results/libdoc↔robotcode, setup↔all library skills), about 60/40 train/validation; verify with `coverage` and loader validation
- [x] 5.6 Document the train/validation discipline (do not tune on validation; rotate only on intent change) in `eval/triggers/README.md`; verify the file exists and is linked from `eval/tasks/README.md`

## 6. Baseline file and regression gate

- [x] 6.1 Define `eval/baselines/<tier>.json` and `eval/baselines/triggers.json` (per task×arm stats, model, harness version, Claude Code version, task hash); add `rf-skill-eval baseline update --from <runs-dir>`; verify with a unit test producing a deterministic file
- [x] 6.2 Implement `rf-skill-eval gate` (pass-rate tolerance default > 1/N, input-token budget default +30%, `rebaseline-needed` on hash/model mismatch, `incomplete` → fail, trigger validation-accuracy check); verify with unit tests for each failure mode and a clean pass
- [x] 6.3 Make PR reports read baseline-arm numbers from the stored file when the baseline arm was not run; verify with a report test

## 7. CI integration

- [x] 7.1 Add a preflight step to `.github/workflows/skill-evaluation.yml` mapping changed paths to skills and detecting frontmatter `description` changes; verify with a small script test in `tests/eval/` over sample path lists
- [ ] 7.2 Rewrite the PR job: narrow tier, treatment arm, `--runs 3`, Haiku, changed skills plus `plugin` canaries, `--max-cost-usd` from env, then `gate`, a conditional validation-split `trigger`, and the PR comment; verify on a test PR that changes one skill (DEFERRED: live eval run — tracked in follow-up. Workflow jobs `preflight`/`pr-eval` written and structurally tested in `tests/eval/test_ci_preflight.py`; verification needs a real PR with secrets)
- [ ] 7.3 Rewrite the scheduled and manual jobs: all tiers, `--arms treatment,baseline`, all trigger sets, weekly cap, and a `candidate-baseline/` artifact. The manual job gets `model`/`runs`/`allow_opus` inputs; verify via `workflow_dispatch` on a branch (DEFERRED: live eval run — tracked in follow-up. `full-eval` job and dispatch inputs written and structurally tested; verification needs a `workflow_dispatch` run)
- [x] 7.4 Handle missing credentials (fork PRs): write "not run: no credentials" to the summary and do not produce a passing gate; verify with `act` or a dry run with secrets unset (verified offline: `run-batch` with secrets unset prints "not run: no credentials" and exits 2 (`test_run_batch_without_credentials_reports_not_run`); the workflow skips the eval jobs and runs the `not-run` summary job, asserted in `test_ci_preflight.py`; `act` not used)
- [x] 7.5 Update ADR-005 and `docs/ci/usage.md` with the tier table, caps, baseline promotion flow and the rule that the gate becomes required after two weekly baselines; verify the docs match the workflow inputs

## 8. Wrap-up

- [x] 8.1 Run `uv run pytest tests/eval` and `uv run ruff check src tests/eval` and `uv run mypy`; all pass (also: pytest runs in the new `harness-tests` CI job)
- [ ] 8.2 Run one weekly-equivalent batch locally or via dispatch (both arms, N=3, all tiers, triggers) and commit the first baseline files through a reviewed PR; verify `gate` passes against it (DEFERRED: live eval run — tracked in follow-up. Machinery ready: `baseline update`, `gate`, `eval/baselines/README.md`)
