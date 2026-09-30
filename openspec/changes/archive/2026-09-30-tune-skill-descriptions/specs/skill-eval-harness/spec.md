## MODIFIED Requirements

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

## ADDED Requirements

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
