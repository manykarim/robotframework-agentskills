# skill-eval-harness Specification

## Purpose
Define how the `rf-skill-eval` harness measures whether the rf-agentskills skills help an agent. It covers paired with/without-skill arms, honest verdict states, replicated runs, trigger accuracy, model and cost policy, task coverage, and the CI regression gate.

## Requirements

### Requirement: Paired treatment and baseline arms

The harness SHALL support two arms for every task. `treatment` provisions the rf-agentskills plugin as shipped (skills, hooks, subagents, plugin MCP servers). `baseline` provisions none of these. Apart from that, both arms SHALL use the same fixture, prompt, model, allowed tools, turn and time limits, and non-plugin MCP servers. The baseline arm SHALL NOT be able to discover any rf-agentskills skill, whether user-level, project-level (`.claude/skills/`) or plugin-provided.

#### Scenario: Baseline run has no skills available
- **WHEN** a task runs in the `baseline` arm
- **THEN** the session's isolated config dir and workspace contain no rf-agentskills skill, hook, subagent or plugin MCP server
- **AND** the transcript contains no successful load of an rf-agentskills skill

#### Scenario: Arms differ only by the plugin
- **WHEN** the same task runs in `treatment` and `baseline`
- **THEN** both runs use identical prompt, model, `max_turns`, `timeout_seconds`, allowed tools, fixture contents and non-plugin MCP configuration
- **AND** the run records store the arm name

#### Scenario: Selecting arms on the command line
- **WHEN** a batch is started with `--arms treatment,baseline`
- **THEN** every selected task runs in both arms
- **WHEN** a batch is started without `--arms`
- **THEN** only the `treatment` arm runs

### Requirement: Arm deltas are reported

For each task and each skill, the report SHALL show, per arm: pass rate, mean input and output tokens, mean turns, mean wall-clock duration and mean cost. It SHALL also show the treatment-minus-baseline delta for each of these. Deltas SHALL be computed from outcome checks only. Process checks (checks that assert how the agent worked, such as skill or tool usage) SHALL be reported for the treatment arm but excluded from the delta. When one arm has no completed runs for a task, the delta SHALL be shown as unavailable, not as zero.

#### Scenario: Delta table in the report
- **WHEN** a batch with both arms completes and is reported
- **THEN** each task row shows pass rate, tokens, turns, duration and cost for both arms plus the treatment-minus-baseline delta
- **AND** a per-skill summary aggregates the rows for that skill

#### Scenario: Process checks do not penalise the baseline
- **WHEN** a task has a check asserting that the skill was invoked
- **THEN** that check is not counted in either arm's outcome pass rate
- **AND** it appears in the treatment arm's process results

#### Scenario: Missing arm
- **WHEN** only treatment runs exist for a task
- **THEN** the delta columns for that task read as unavailable

### Requirement: Verdicts distinguish skipped from passed

Each check verdict SHALL have exactly one status: `passed`, `failed`, `skipped` or `error`. A check that cannot be evaluated SHALL be `skipped` and carry a reason. This covers a required tool that is not installed, a library that cannot be imported, and a missing transcript. A grader defect SHALL be `error`. `skipped` and `error` verdicts SHALL NOT count as passes in any score, pass rate or gate.

#### Scenario: Lint tool missing
- **WHEN** a `lint_clean` check runs and `robocop` is not installed
- **THEN** the verdict status is `skipped` with a reason naming the missing tool
- **AND** the verdict contributes nothing to the run's pass count

#### Scenario: Skipped verdicts are visible
- **WHEN** a report is rendered for runs that contain skipped verdicts
- **THEN** the report lists the number of skipped checks per task with their reasons

### Requirement: Skipped gating checks fail the gate

Every check SHALL be either gating or non-gating. Checks named by the task's `primary_metric` SHALL be gating, and so SHALL checks marked `gating: true`. A run's gate result SHALL be `pass` only when every gating check is `passed`. If any gating check is `skipped` or `error`, the gate result SHALL be `incomplete`. Any CI gate that consumes run results SHALL treat `incomplete` as a failure.

#### Scenario: Gating check skipped
- **WHEN** the gating check of a run is `skipped`
- **THEN** the run's gate result is `incomplete`
- **AND** the CI gate step exits non-zero with a message naming the skipped check and its reason

#### Scenario: Non-gating check skipped
- **WHEN** only a non-gating check is `skipped` and all gating checks pass
- **THEN** the run's gate result is `pass`
- **AND** the skipped check is still reported

### Requirement: Replicated runs with variance

Batch execution SHALL accept a replicate count `--runs N` (default 3, minimum 1). Each replicate SHALL run in a freshly provisioned workspace. For each task×arm the harness SHALL report: pass rate (runs whose gate result is `pass` divided by runs attempted), the number of `incomplete` runs, and the mean, standard deviation, minimum and maximum of tokens, turns and duration. A task×arm whose pass rate is strictly between 0 and 1 SHALL be flagged as flaky.

#### Scenario: Default replicate count
- **WHEN** a batch runs without `--runs`
- **THEN** every selected task×arm is executed 3 times in fresh workspaces

#### Scenario: Flaky task flagged
- **WHEN** a task passes in 2 of 3 treatment replicates
- **THEN** its treatment pass rate is reported as 0.67 and the task is flagged flaky

#### Scenario: Incomplete runs lower the pass rate
- **WHEN** one of 3 replicates is `incomplete`
- **THEN** that replicate counts as not passed in the pass rate and is reported in the incomplete count

### Requirement: Trigger evaluation query sets

Each shipped skill SHALL have a trigger query set containing should-trigger queries and near-miss should-not-trigger queries. Near misses are queries that are plausibly related but belong to another skill or to no skill.

A set SHALL have at least 8 should-trigger and 8 should-not-trigger queries across the `train` and `validation` splits, and each query SHALL be assigned to a `train`, `validation` or `holdout` split. The `holdout` split is optional. When present it SHALL hold queries written after description tuning, and it is never used to choose or accept a description.

Near-miss queries for a skill SHALL include queries that belong to its closest sibling skills (for example Browser vs SeleniumLibrary, RequestsLibrary vs RESTinstance, results analysis vs robotcode).

#### Scenario: Query set validity
- **WHEN** the harness loads a trigger set with fewer than 8 queries of either polarity in train plus validation, a query without a split, a split other than `train`, `validation` or `holdout`, or a `skill` that names no shipped skill
- **THEN** loading fails with an error naming the set and the problem

#### Scenario: Sibling near misses present
- **WHEN** the trigger set for the Browser skill is loaded
- **THEN** it contains should-not-trigger queries that are SeleniumLibrary tasks

#### Scenario: Holdout split selectable
- **WHEN** `trigger --split holdout` runs on a set that has holdout queries
- **THEN** only the holdout queries run and they are reported in their own column

### Requirement: Trigger detection and scoring

Trigger evals SHALL run each query headlessly with all rf-agentskills skills installed and plugin hooks disabled, 3 times by default.

**Session setup.** Each session SHALL:
- have only the tools `Skill`, `Read`, `Glob` and `Grep` available, with every other built-in tool unavailable, not merely unapproved;
- start in a fresh copy of a small realistic Robot Framework project fixture (a `pyproject.toml`, a `tests/` suite and a `resources/` file), not an empty directory;
- be limited to 3 turns.

**Detection and scoring.**
- The harness SHALL decide from the session transcript whether the target skill was loaded.
- A load is either a Skill tool invocation naming the skill (with or without plugin namespace), or a read of that skill's `SKILL.md`.
- A query's trigger rate is loads divided by completed runs.
- A query SHALL be counted as triggered when its trigger rate is ≥ 0.5.
- Should-trigger queries SHALL pass when triggered, and should-not-trigger queries SHALL pass when not triggered.

**Reporting.** The report SHALL give per-skill precision, recall and accuracy for each split separately. It SHALL list which other skills were loaded for failing queries.

**Persistence and resume.**
- The harness SHALL persist each query's outcome as soon as the query's runs finish.
- A re-invocation with the same output directory SHALL skip queries whose outcomes are already persisted, and SHALL aggregate them into the final result.

**Concurrency.** Sessions MAY run with a concurrency of up to 2.

**Variant roots.** The harness SHALL accept a variant plugin root. The variant's skills are staged instead of the shipped ones, which lets candidate descriptions be measured without editing the repository's skills. Results SHALL record which root was used.

**Listing budget and visibility.**
- The harness SHALL record, for every trigger batch, the skill-listing budget in effect. That is either the CLI default or an explicit `--listing-budget <chars>` override, which it passes to Claude Code.
- It SHALL also record, for every session, whether the target skill's description was visible in the skill listing the model received, or listed by name only.
- Batches with different listing budgets SHALL get different variant keys, so resume never mixes them.
- Variant roots SHALL keep candidate descriptions byte-exact. In particular, runs of spaces in import lines such as `Library    Browser` are not collapsed.

#### Scenario: Skill loaded via Skill tool
- **WHEN** a run's transcript contains a Skill tool call for `rf-agentskills:rf-browser` or `rf-browser`
- **THEN** that run counts as a load of `rf-browser`

#### Scenario: Skill loaded by reading SKILL.md
- **WHEN** a run's transcript contains a Read of `.../skills/<dir-of-rf-browser>/SKILL.md`
- **THEN** that run counts as a load of `rf-browser`

#### Scenario: Threshold applied
- **WHEN** a should-trigger query loads the skill in 1 of 3 runs
- **THEN** its trigger rate is 0.33, it is not triggered, and the query fails

#### Scenario: Validation split reported separately
- **WHEN** trigger results are reported
- **THEN** train and validation metrics are shown in separate columns so description tuning can be checked against held-out queries

#### Scenario: Non-trigger tools are unavailable
- **WHEN** a trigger session's init record lists its available tools
- **THEN** `Bash`, `Write` and `Edit` are absent
- **AND** no transcript contains a call to them

#### Scenario: Realistic workspace
- **WHEN** a trigger session starts
- **THEN** its working directory contains the trigger fixture's `pyproject.toml`, `tests/` and `resources/`

#### Scenario: Interrupted batch resumes
- **WHEN** a trigger batch is stopped after 40 of 120 queries and re-invoked with the same output directory
- **THEN** only the remaining 80 queries run, and the final result covers all 120

#### Scenario: Listing budget recorded and keyed
- **WHEN** the same variant is measured once with the default budget and once with `--listing-budget 40000` into the same output directory
- **THEN** the results record both budgets, resume treats them as different batches, and neither overwrites the other

#### Scenario: Description visibility reported
- **WHEN** a session's skill listing shows `rf-results` by name only
- **THEN** the session is recorded as "description not visible" for rf-results, and the report shows per skill how many sessions saw its description

#### Scenario: Import lines kept byte-exact
- **WHEN** a candidate description contains `Library    Browser`
- **THEN** the staged SKILL.md contains exactly `Library    Browser`

#### Scenario: Variant root measured
- **WHEN** `trigger --variant-root <dir>` runs
- **THEN** the sessions stage the skills from `<dir>`, and the results name `<dir>` as the root

### Requirement: Model allow-list and cost policy

Task YAMLs and trigger sets SHALL declare a model from the allow-list `claude-haiku-4-5-20251001`, `claude-sonnet-5` or `claude-opus-5-5`. They SHALL NOT declare `claude-opus-5-5` as their own model. Any other model id SHALL be rejected at load time, and the error SHALL name the permitted ids. Running with `claude-opus-5-5` SHALL require an explicit run-time opt-in flag, and SHALL be refused unless a cost cap is also given. Every batch SHALL accept a cost cap (`--max-cost-usd`). When the running total reaches the cap, the harness SHALL stop dispatching new runs, mark the unstarted runs as `incomplete` with reason `budget`, and exit non-zero.

#### Scenario: Outdated model id rejected
- **WHEN** a task declares `model: claude-sonnet-4-6`
- **THEN** loading fails with an error listing the permitted model ids

#### Scenario: Opus requires opt-in and cap
- **WHEN** a batch is started with `--model claude-opus-5-5` but without the opt-in flag or without `--max-cost-usd`
- **THEN** the harness refuses to start and explains which flag is missing

#### Scenario: Budget exhausted
- **WHEN** the cumulative reported cost reaches `--max-cost-usd` during a batch
- **THEN** no further sessions start, the unstarted runs are recorded as `incomplete` (reason `budget`), and the command exits non-zero

### Requirement: Task coverage per shipped skill

The task bank SHALL contain at least one `narrow` task for every shipped skill. These are browser, selenium, appium, requests, restinstance, platynui, robotcode, setup, results and libdoc, plus any skill added later. Every task's `skill` SHALL name a shipped skill, or `plugin` for bundle-level canary tasks. The harness SHALL reject tasks for skills that are not shipped (for example retired skills). A coverage check SHALL fail when a shipped skill has no narrow task or no trigger set. For skills whose library cannot run on the CI runner (appium, platynui), the task's gating check MAY be a dry-run or static keyword-resolution check. It SHALL NOT be a check that is always skipped.

#### Scenario: Missing coverage detected
- **WHEN** a new skill is added under `skills/` without a narrow task or trigger set
- **THEN** the coverage check fails and names the skill

#### Scenario: Task for retired skill rejected
- **WHEN** a task declares `skill: keyword-builder` after that skill is retired
- **THEN** task loading fails naming the unknown skill

#### Scenario: Dry-run-only skills are still graded
- **WHEN** the appium narrow task is graded on a runner without an Appium server
- **THEN** its gating check verifies that the produced suite parses and its keywords resolve against AppiumLibrary, and the check reports `passed` or `failed`, not `skipped`

### Requirement: Adversarial tier

The `adversarial` tier SHALL contain tasks that tempt known failure modes. At least one task SHALL tempt deprecated or non-existent library keywords. At least one SHALL tempt installing packages into the system Python instead of the project environment. At least one SHALL tempt using the wrong web library for the project (SeleniumLibrary in a Browser project), and at least one SHALL tempt making a failing test pass by weakening or skipping its assertion. Adversarial results SHALL be reported with the same arm deltas as other tiers and SHALL NOT gate merges.

#### Scenario: Wrong library temptation graded
- **WHEN** the wrong-library adversarial task runs in a Browser-based fixture
- **THEN** its outcome check fails if the produced suite imports SeleniumLibrary

#### Scenario: Adversarial results are non-gating
- **WHEN** an adversarial task fails in the treatment arm
- **THEN** the report shows the failure and the CI gate result is unaffected by it

### Requirement: Regression gate against a stored baseline

The repository SHALL contain a baseline results file for each gated tier. For every task×arm it SHALL record pass rate, replicate count, mean tokens, turns, duration and cost, along with the model id, the harness version and a content hash of the task definition. A gate command SHALL compare a new treatment result with the stored baseline. It SHALL fail when a gating task's treatment pass rate drops by more than the configured tolerance (default: more than one replicate's worth, i.e. > 1/N). It SHALL also fail when mean input tokens rise by more than the configured budget (default 30%). Tasks whose definition hash or model differs from the baseline entry SHALL be reported as `rebaseline-needed` and excluded from the comparison. They SHALL NOT be treated as passing. Updating the baseline file SHALL be an explicit command whose output is committed via a reviewed pull request.

#### Scenario: Pass-rate regression
- **WHEN** a gating task had baseline treatment pass rate 1.00 (N=3) and the new run has 0.33
- **THEN** the gate fails and names the task and both pass rates

#### Scenario: Token budget regression
- **WHEN** a task's mean input tokens rise by 45% against the baseline with the default 30% budget
- **THEN** the gate fails and names the task and the increase

#### Scenario: Changed task needs rebaseline
- **WHEN** a task's definition changed since the baseline was recorded
- **THEN** the gate reports the task as `rebaseline-needed` and does not count it as passing

### Requirement: Tiered CI execution with bounded cost

CI SHALL run the harness in tiers. On pull requests that touch skills, the plugin, eval tasks or the harness, CI SHALL run the narrow tier in the treatment arm with N=3 on the Haiku model id. That run SHALL be scoped to tasks of changed skills plus bundle canaries and SHALL be gated against the stored baseline. On pull requests that change a skill's frontmatter `description`, CI SHALL run that skill's trigger set on the validation split. On a weekly schedule and on manual dispatch, CI SHALL run all tiers in both arms plus all trigger sets, and SHALL publish the report and a candidate baseline as artifacts. Every CI invocation SHALL pass an explicit cost cap. When credentials are not available (for example fork PRs), the job SHALL report that evaluation was not run. It SHALL NOT report success.

#### Scenario: PR scoped to changed skill
- **WHEN** a pull request only changes `skills/rf-selenium/`
- **THEN** CI runs the selenium narrow tasks and the bundle canaries in the treatment arm with N=3, and gates them against the stored baseline

#### Scenario: Description change triggers trigger eval
- **WHEN** a pull request changes the `description` in a skill's SKILL.md frontmatter
- **THEN** CI runs that skill's validation trigger queries and reports precision and recall against the stored trigger baseline

#### Scenario: Fork PR without secrets
- **WHEN** CI runs on a pull request where no Claude credentials are available
- **THEN** the evaluation job reports "not run: no credentials" and does not post a passing result

### Requirement: Run isolation never deletes unrelated files

The harness SHALL detect files created outside a run's workspace during the run, and SHALL report them on the run as an isolation violation that marks the run untrustworthy. It MUST NOT delete files outside the run's own workspace and artifacts directory: other processes, such as a developer or another tool, may create files in the repository while runs are active. Trigger sessions have no write-capable tools, so they SHALL skip the integrity snapshot entirely.

#### Scenario: Concurrent developer file survives
- **WHEN** a developer creates `openspec/changes/x/notes.md` while a task run is active
- **THEN** the file still exists after the run, and the run lists it as a violation instead of deleting it

#### Scenario: Violation marks the run
- **WHEN** a task run's agent writes `src/leak.txt` outside its workspace
- **THEN** the run is recorded with an isolation-violation error that names `src/leak.txt`, and its gate result is not a pass

#### Scenario: Trigger sessions skip the snapshot
- **WHEN** a trigger session runs
- **THEN** no repository integrity snapshot is taken before or after it
