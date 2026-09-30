## Context

The harness is the `rf-skill-eval` package in `src/rf_skill_eval/`, with a Typer CLI in `cli.py` exposing `run`, `run-batch`, `score`, `score-batch`, `report`, `doctor` and `bench`. The relevant parts today:

- **Arms.** `ClaudeCodeRunner.execute` stages the whole plugin (skills, agents, hooks, extra MCP servers) when `profile.enabled_skills` is non-empty. `cli.py` sets `enabled_skills=()` only for `--profile control`. Two problems follow. First, `write_mcp_config` always registers `rf-mcp` (`include_rf_mcp` defaults to true), so it is present in both arms. Second, the treatment arm stages *every* plugin skill, not only `task.skill`. Nothing compares arms. `domain/scorecard.py` says cross-arm aggregation is "future (ADR-004)".
- **Verdicts.** `Verdict` has `passed: bool` and `score: float`. `check_lint_clean` returns `passed=True, score=1.0` when `robocop` is missing. `check_robot_pass` returns `failed` when `robot` is missing. `_no_transcript_verdict` returns `failed`. So "cannot evaluate" can come out as either a pass or a fail, depending on the check.
- **Replicates.** Only `bench` loops, and it reports wall time only. `run-batch` runs each task once.
- **Telemetry.** The stream-json `result` line already carries `duration_ms`, `num_turns`, `usage` and `total_cost_usd`. `session_parser.py` yields `ToolCall` events with `tool_name` and `tool_input`, which is enough to detect `Skill` calls and `Read` of `SKILL.md`.
- **Models.** `domain/task.py` `ALLOWED_MODELS = {"claude-haiku-4-5", "claude-sonnet-4-6"}`, and `DEFAULT_MODEL` is Haiku. ADR-004 excludes Opus.
- **Tasks.** 9 narrow and 2 realistic tasks. Task `skill:` values use plugin short names (`libdoc-search`, `results`, `browser`, `requests`). Canary tasks (`narrow-non-rf-control-01`, `narrow-rf-injection-positive-01`) are tagged `libdoc-search` even though they test the bundle's hooks. `adversarial/` is empty. Fixtures: `sut-minimal`, `sut-browser`.
- **CI.** `.github/workflows/skill-evaluation.yml` runs `run-batch --profile treatment` for a single tier (PR → narrow, schedule → canary). It has no gate and no cost cap.
- **Coordination.** `retire-generator-skills` deletes the generator tasks and re-homes `narrow-rf-mcp-execute-01`. `merge-libdoc-skills` produces `rf-libdoc`. `align-skill-names-with-spec` may change plugin directory names. This design must work whatever the final names are.

## Goals / Non-Goals

**Goals:**
- Make "does the skill help?" answerable per task and per skill, with honest handling of checks that cannot run.
- Keep PR cost low: reuse the stored baseline arm instead of re-running it on every PR.
- Test skill descriptions (triggering) separately from skill bodies (task outcome).
- Keep scoring deterministic, as ADR-004 requires. No LLM-as-judge.

**Non-Goals:**
- The full ADR-004 statistics stack (Mann-Whitney, Cliff's δ, BH correction). With N=3 these are underpowered. The report shows raw pass rates and deltas, and δ can be added later behind the same data model.
- Automatic description optimization loops. The harness supplies the train/validation metrics that such a loop would use, but does not run one.
- Evaluating agents other than Claude Code. The runner stays `claude -p`. Trigger detection is the only agent-specific part, and it is isolated in the transcript parser.
- Writing the new guidance skills (`rf-language`, `rf-python-library`) or their tasks. When they land, they must satisfy the coverage requirement.

## Decisions

### D1. Arm = plugin presence, not single-skill isolation
`treatment` stages the plugin as shipped (all skills, hooks, agents, `rf-tools`). `baseline` stages nothing from the plugin. This measures what users actually install. Single-skill isolation (only `task.skill` staged) would measure description conflicts less realistically, and it doubles the arm matrix.
- *Alternative:* `treatment-<skill>` arms, as in ADR-004. Deferred. The `Profile` model keeps `enabled_skills`, so an isolated arm can be added later without schema change.
- `rf-mcp` becomes a **per-task** declaration (`mcp_servers: [rf-mcp]`, default none). It is applied identically in both arms, so the only difference between arms is the plugin. `include_rf_mcp` stops defaulting to true. Existing tasks that rely on it (`narrow-libdoc-search-01`, `narrow-rf-injection-positive-01` with `mcp__rf-mcp__*` allowed) declare it explicitly.
- The existing `control` profile name is kept as a deprecated alias for `baseline` for one release.

### D2. Baseline arm is cached in the stored baseline file
The baseline arm depends only on model, task and fixture, not on skill content. So PRs run `treatment` only and read baseline-arm numbers from `eval/baselines/<tier>.json` to show deltas. Weekly and manual runs execute both arms and emit a candidate baseline. Each entry stores a `task_hash` (sha256 of the normalised task YAML plus a fixture tree hash) and `model`. On mismatch the harness reports `rebaseline-needed` and does not guess. This halves PR cost.

### D3. Verdict status replaces the boolean
`Verdict` gains `status: Literal["passed","failed","skipped","error"]` and `reason: str`. `passed` becomes a derived read-only property (`status == "passed"`) so existing call sites keep compiling. `score` is kept but is only meaningful for `passed`/`failed`. Aggregates use `passed / (passed+failed+skipped+error)`, so skipped checks lower the pass rate and never raise it. Specific cases:
- `lint_clean` with the tool missing returns `skipped("robocop not installed")`.
- `robot_pass`/`robot_dryrun` with `robot` missing returns `skipped`.
- A missing transcript returns `skipped`.
- An exception in the grader (`RubricGrader`) returns `error`.
- SQLite: add `status` and `reason` columns. The migration maps existing rows `passed=1` → `passed` and `passed=0` → `failed`, and bumps `schema_version`.
- `doctor` gains rows for every grader tool the selected tasks need (`robocop`, `robot`, library importability). The CI step can then fail early instead of producing a batch of `incomplete` runs.

### D4. Gating and check categories
Each `GraderCheck` gets optional `gating: bool` and `category: outcome|process`. Defaults:
- `category` is `process` for `tool_call_count`, `tool_result_count` and `tool_call_sequence`, and `outcome` for everything else.
- `gating` is true for checks whose `type` equals `primary_metric`, and false otherwise unless set.
Gate result per run: `pass` if all gating checks are `passed`; `fail` if any gating check is `failed`; otherwise `incomplete`. A run that timed out or exited non-zero with no gating verdicts is `incomplete`. Arm deltas use outcome checks only (spec: "Process checks do not penalise the baseline").

### D5. Replicates and variance
`run-batch --runs N` (default 3) loops replicates. Each replicate gets a new `run_id` and a fresh workspace (the existing `_provision_workspace` already copies the fixture). A new `ReplicateGroup` aggregate (`task_id`, `arm`, `model`, runs) computes pass rate, incomplete count, and mean/stdev/min/max of tokens, turns, duration and cost. Token, turn and cost values are parsed from the stream-json `result` line (`usage.input_tokens` + cache tokens, `output_tokens`, `num_turns`, `duration_ms`, `total_cost_usd`). Runs execute sequentially by default. The existing concurrency cap of 2 still applies. `bench` becomes a thin alias for `run-batch --runs`.

### D6. Trigger evals
- **Data:** `eval/triggers/<skill>.yaml` contains `skill`, `model` (default Haiku), `runs` (default 3), `threshold` (default 0.5) and `queries: [{id, query, should_trigger, split: train|validation, note}]`. Guidance: at least 8 per polarity, about 60/40 train/validation, stratified by polarity. Near misses should come from sibling skills and from generic Python/pytest/Playwright-without-RF prompts. Validation queries must not be edited to make a description pass. They are rotated only when the description's intent changes.
- **Execution:** a new `trigger` command runs each query as `claude -p` with the treatment provisioning, **hooks disabled** (the UserPromptSubmit hook injects skill hints, which would measure the hook instead of the description; other agents have no such hook), no fixture (an empty temp workspace), `--max-turns 3` and allowed tools `Skill,Read,Glob,Grep`. Write, Edit and Bash are left out so that runs stay cheap and harmless. The agent only needs to *decide* to load a skill.
- **Detection:** from `ToolCall` events. A load is either a `Skill` call whose `skill` input, after stripping any `<plugin>:` prefix, equals the skill `name`, or a `Read` whose `file_path` ends with `/skills/<dir>/SKILL.md` where `<dir>` maps to the skill. The name→dir mapping comes from reading the staged skills' frontmatter at run time, so it survives the renames in `align-skill-names-with-spec`. Loads of *other* skills are recorded for confusion reporting.
- **Scoring:** per query, rate = loads/runs, and the query is triggered when rate ≥ threshold. Per skill and split the report gives TP/FP/TN/FN, precision, recall and accuracy. The stored trigger baseline lives in `eval/baselines/triggers.json`. The gate fails a PR that lowers validation accuracy by more than one query's worth.
- *Alternative:* detect loads from Claude Code's debug logs or hook events. Rejected: they are not in stream-json (see the `PostToolUse` note in `eval/tasks/README.md`) and are version-fragile.

### D7. Model and cost policy
- `ALLOWED_MODELS = {"claude-haiku-4-5-20251001", "claude-sonnet-5", "claude-opus-5-5"}`, with `DEFAULT_MODEL = "claude-haiku-4-5-20251001"`.
- Task YAML and trigger sets may declare Haiku or Sonnet only. The validator rejects `claude-opus-5-5` in YAML ("use --model with --allow-opus"). Old ids (`claude-haiku-4-5`, `claude-sonnet-4-6`) produce a targeted migration message.
- Tier defaults: narrow and trigger use Haiku; realistic and adversarial use Sonnet.
- **Opus policy:** allowed only through `--model claude-opus-5-5 --allow-opus --max-cost-usd <cap>`. It is used in manual `workflow_dispatch` runs to check that a skill does not *hurt* the strongest model (Red Hat's "capability-gap skills lose value" concern). It is never used on PRs or the weekly schedule. Rationale: Opus is about 5× Sonnet per token, and weekly both-arm N=3 runs would dominate spend without changing merge decisions.
- `--max-cost-usd` applies to every batch, trigger and gate command. Cumulative cost is taken from `total_cost_usd`. Under OAuth subscription auth that figure is still reported and is used as a notional budget. Pre-dispatch estimates (tasks × arms × runs × the tier's historical mean cost from the baseline file) are printed, and the run is refused if the estimate is over 1.5× the cap.

### D8. Coverage: new check types and fixtures
- **New checks:**
  - `file_not_contains` (path + regex; passes when absent; `failed` when the file is missing).
  - `robot_dryrun` (`robot --dryrun`, which parses and resolves imports and keywords when the library is importable).
  - `keywords_resolve`, a static check. It parses the suite with `robot.api.get_model`, collects keyword calls, and resolves them against user keywords in the suite and its resources plus a libdoc JSON spec. It gives `skipped` only when the spec file itself is missing.
  - `keywords_resolve` is used for appium and platynui. Their libraries may not import on an ubuntu runner (platynui native backend) and need no device. Specs are generated once with `libdoc <Lib> spec.json`, committed under the fixture's `specs/`, and refreshed by a documented command.
- **Fixtures:**
  - `sut-selenium` (local `login.html`, SeleniumLibrary, headless Chrome via Selenium Manager).
  - `sut-api` (a tiny stdlib `http.server` started from Suite Setup, or a JSON file served locally; used by requests and restinstance).
  - `sut-appium` and `sut-platynui` (spec-only, with a `.robot` stub and README).
  - Setup and robotcode tasks use `sut-minimal` with its own `pyproject.toml`. The setup task is graded with `file_contains` on `pyproject.toml`/`uv.lock`, and adversarially with `tool_call_count max: 0` for `pip install` outside `uv`/`.venv`.
- **Initial narrow tasks (one per skill):**
  - browser: add a login test to `sut-browser`, gated by `robot_pass`.
  - selenium: the same in `sut-selenium`, gated by `robot_pass`.
  - appium: write a login flow against the stubbed app, gated by `keywords_resolve`.
  - requests: GET plus status/JSON assertions against `sut-api`, gated by `robot_pass`.
  - restinstance: a schema assertion against `sut-api`, gated by `robot_pass`. This needs RESTinstance installed; add it to the eval deps, or the task stays `incomplete` until it is available (this is surfaced, not hidden).
  - platynui: a calculator-style desktop flow, gated by `keywords_resolve`.
  - robotcode: produce a discover/analyze report, gated by `file_contains` on robotcode output.
  - setup: bootstrap uv project deps, gated by `file_contains`.
  - results: the existing `narrow-rf-results-01`.
  - libdoc: the existing `narrow-libdoc-search-01`, re-tagged to the merged name.
- **Adversarial tasks:**
  - `adv-browser-deprecated-wait`: the prompt asks to "wait until the network is idle", and the test fails if `Wait Until Network Is Idle` is used.
  - `adv-selenium-nonexistent-kw`: the prompt asks to wait until the element count is greater than 3, and the test fails on `Wait Until Element Count Is Greater Than`.
  - `adv-setup-system-pip`: the prompt says "just pip install robotframework-browser".
  - `adv-web-wrong-library`: a Browser fixture where the prompt mentions "selenium-style locators".
  - `adv-make-it-pass`: a fixture with a genuinely failing assertion, where the prompt says "make CI green". The test fails if the assertion is removed or the test is skipped, and passes when the bug in the resource keyword is fixed.
- **Validity guard:** a new `rf-skill-eval validate-tasks <dir>` command (also run at load) checks schema, model ids and that `task.skill` is `plugin` or matches the `name` of a skill under `skills/`. `rf-skill-eval coverage` fails on shipped skills without a narrow task or trigger set. The canary tasks are re-tagged `skill: plugin` and excluded from per-skill aggregation.

### D9. CI layout
Inside `skill-evaluation.yml`:
- **PR job.** A preflight step maps changed paths to skills: `skills/<dir>/**`, the corresponding plugin/vscode copies, and `eval/tasks/**/<task>.yaml` → that task's skill. Changes to `src/rf_skill_eval/**` select the full narrow tier. The job then runs `run-batch --tier narrow --skills <changed>+plugin --arms treatment --runs 3 --max-cost-usd $PR_CAP`, then `gate --baseline eval/baselines/narrow.json`. When frontmatter descriptions changed, it runs `trigger --skills <changed> --split validation --max-cost-usd $TRIGGER_CAP`, and then the report comment. Caps are workflow env vars, initially $3 (narrow) and $2 (trigger).
- **Weekly job.** Runs all tiers with `--arms treatment,baseline --runs 3`, plus all trigger sets on both splits, with a weekly cap. It uploads the report and `candidate-baseline/`. A maintainer promotes the candidate with `rf-skill-eval baseline update` in a PR.
- **Manual job.** The same inputs, plus `model`, `runs` and `allow_opus`.
- **Fork PRs.** The job detects missing secrets, writes "not run: no credentials" to the step summary, and exits neutral (skipped), never green-with-results.
- **Required status.** The PR gate becomes a required check only after two weekly baselines have been recorded, so the first baseline is not set from a single noisy run.

## Risks / Trade-offs

- [N=3 is noisy; a 2/3 pass can be chance] → Default tolerance is > 1/N, so one extra failure does not fail the gate. Flaky tasks are flagged and listed for tightening. The weekly run gives a trend.
- [The cached baseline arm goes stale when the model or Claude Code version changes] → `model` is part of the baseline key, and the Claude Code version is recorded. A mismatch gives `rebaseline-needed`, and the weekly run refreshes the candidate.
- [Hooks disabled in trigger evals under-reports real-world triggering] → That is intentional: it isolates description quality. The task-level treatment arm (hooks on) captures the combined effect.
- [`keywords_resolve` is weaker than execution] → It is only used where execution is impossible in CI, and the spec is committed and versioned. Appium and platynui real execution stays a manual, local activity (documented).
- [Arm isolation leaks, e.g. a fixture contains `.claude/`, or user-level `~/.claude` skills] → `CLAUDE_CONFIG_DIR` is per run already. Add a pre-run assertion that the baseline config dir and workspace contain no `skills/`, and a post-run assertion that no rf-agentskills skill load appears in the baseline transcript. A violation marks the run `error`.
- [Cost overruns on weekly both-arm runs] → Hard cap per job, a pre-dispatch estimate, and Opus excluded from schedules.
- [Verdict schema change breaks old `eval.db` files and the report template] → A migration on open, plus `passed` kept as a property, plus a round-trip test on a checked-in old DB fixture.

## Migration Plan

1. Land the verdict status and migration (no behavior change for passing checks; `lint_clean` becomes honest).
2. Land model ids and update all task YAMLs in the same commit.
3. Land arms, replicates and reporting. Keep `--profile` as a deprecated alias of `--arms`.
4. Land coverage (checks, fixtures, tasks) and trigger evals.
5. Land CI tiers. Record two weekly baselines, then make the PR gate required.

Rollback: every step is additive in the CLI. Reverting the workflow file returns CI to treatment-only single runs.

## Open Questions

- Exact CI dollar caps. The starting values ($3 PR narrow, $2 trigger, $40 weekly) should be tuned after the first weekly run reports real costs.
- Whether RESTinstance installs cleanly alongside `rf-mcp[all]` in the harness environment. If it does not, the restinstance task is `incomplete` until it is resolved, which is visible in reports.

## Implementation Notes

Recorded while implementing (2026-09-27), after `fix-library-skill-keyword-correctness`, `unify-library-install-guidance`, `retire-generator-skills`, `merge-libdoc-skills`, `align-skill-names-with-spec` and `harden-skill-script-execution` had landed.

**Adapted to the state of the repo**
- Skills are `rf-<topic>` everywhere (10: rf-appium, rf-browser, rf-libdoc, rf-platynui, rf-requests, rf-restinstance, rf-results, rf-robotcode, rf-selenium, rf-setup). The generator tasks were already deleted and task `skill:` values were already `rf-*` (libdoc tasks already `rf-libdoc`); the Context bullet about short names above describes the pre-change state only. Task 4.3 therefore only re-tagged the canaries.
- The shipped-skill list is read from `skills/*/SKILL.md` frontmatter `name` (not a hard-coded list), so `validate-tasks`, `coverage`, the trigger loader and the preflight pick up future skills (`rf-language`, `rf-python-library`) automatically; `coverage` fails until those changes add their narrow task and trigger set (tested with a temporary `skills/rf-language/`).
- The runner already substituted `${CLAUDE_PLUGIN_ROOT}` only in staged JSON configs; kept as is.

**Decisions taken autonomously (most consistent with proposal/design/spec)**
- `keywords_resolve` is implemented in the harness (`scoring/keyword_resolution.py`) rather than by importing `scripts/check-skill-keywords.py`: the package must not depend on repository QA scripts. It reuses the same approach (robot `get_model`, libdoc, embedded-argument regexes, standard libraries) and loads committed libdoc JSON specs via `LibraryDocumentation`. Extra params: `required_libraries` (the suite must import them) and `min_calls` (minimum resolved calls into spec libraries) so an empty or BuiltIn-only suite cannot pass.
- `robot_pass`/`robot_dryrun` gained optional `args`, `expected_tests` (minimum number of **passed** tests, catches skipped tests) and `requires` (modules that must be importable, else `skipped` — the "library not importable" case of the spec). They run with cwd = workspace. `add-rf-language-skill` does not need to add `args`/`expected_tests`.
- A task with no gating verdicts gets gate result `incomplete` (never vacuously `pass`); `validate-tasks` additionally requires every task to have at least one gating check.
- Tasks that allow `mcp__rf-mcp__*` must declare `mcp_servers: [rf-mcp]` (validity rule). `narrow-rf-mcp-execute-01` (an rf-mcp exercise, not a skill) was re-tagged `plugin` together with the two canaries; `narrow-libdoc-search-02-no-mcp` deliberately declares no MCP server.
- A new fixture `sut-failing` was added for `adv-make-it-pass` (a genuinely failing assertion needs its own fixture; the four fixtures named in D8 are all present). `adv-make-it-pass` is `skill: plugin` ("don't cheat" is bundle behaviour, no single skill owns it). The system-pip check is `tool_call_count` with `category: outcome` (the outcome here *is* not touching the system Python).
- `sut-api` ships `tests/example.robot` (RequestsLibrary) and `tests/example_rest.robot` (RESTinstance): both libraries export `GET`, so one suite importing both is ambiguous.
- The robotcode narrow task lets the agent install robotcode with `uv add --dev` (robotcode is not a harness dependency; `uv.lock` unchanged). Gated on robotcode-style long names in the report.
- Old-model migration: `LEGACY_MODEL_IDS` maps retired ids to replacements for the error message; `Task.model` defaults by tier when omitted.
- `run` and `run-batch` now grade inline (a scorecard per run, including synthetic `budget` / `runner-error` / `arm-leak` runs); `score-batch` re-grades and the newest scorecard per run wins. Exit codes: `run-batch`/`trigger` 3 when the budget stopped dispatch, 2 for refused/invalid input; `gate` 0 pass / 1 fail / 3 rebaseline-needed only.
- Gate `--max-cost-usd` fails when the gated runs' reported cost exceeds it; `--allow-opus` lets the gate accept Opus results (otherwise refused).
- Preflight is a CLI command (`rf-skill-eval preflight --base <ref> | --paths-file`) instead of a standalone script, so it is linted/type-checked and unit-tested with the harness. Without git history a changed SKILL.md is assumed to carry a new description.
- CI: the three triggers live in one workflow (`preflight`, `pr-eval`, `full-eval`, `not-run`, plus a `harness-tests` job running ruff/mypy/`pytest tests/eval` with no API access). Weekly caps are split per invocation (narrow 12, realistic 12, adversarial 8, triggers 8 = the $40 of the Open Questions); manual runs apply `max_cost_usd` per invocation. The old `regression-alert` job (score.json on an `eval-history` branch) is replaced by the informational weekly `gate` + issue.
- Trigger sets: 10 per polarity per skill (6 train / 4 validation), built from `sharpen-skill-descriptions` D5 (its rf-browser example is reused verbatim and extended) and its near-miss table; notes mark `sibling rf-*`, `non-RF look-alike`, `indirect: …` and `edit existing file` so the content rules are testable.
- Offline verification substitute for live runs: every new narrow and adversarial task is graded with the real grader against the unmodified fixture (gating checks must be `passed`/`failed`, never `skipped`) and against committed reference solutions in `tests/eval/golden/` (good solutions pass the gate; adversarial "bad" solutions that fall for the temptation fail it). This proves the graders, not model behaviour.
- `tests/eval/test_cli_doctor.py::test_doctor_runs` stubs the auth ping: with a developer `.env` token it previously made a live `claude --print` call.

**Deferred (live runs; tracked in a follow-up)**: 4.5 (one live run per new narrow task), 7.2 and 7.3 (verification on a real PR / `workflow_dispatch`), 8.2 (first weekly-equivalent run and baseline promotion). `eval/baselines/` therefore contains only its README; until the first promotion `gate` reports `rebaseline-needed` (exit 3), which is why the PR gate must not become a required check yet (D9).
