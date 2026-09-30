## Context

See proposal.md (Why) for the measured problem. Constraints that shape the approach:

- **Trigger runs today.** `trigger` runs query by query through `ClaudeCodeRunner` with `--allowedTools Skill,Read,Glob,Grep --permission-mode bypassPermissions`. In bypass mode `--allowedTools` only pre-approves tools, so Bash and Write stay available. The 2026-09 transcripts show Haiku using `find`/`ls` and `Write` in its 3 turns instead of loading a skill.
  - The Claude Code CLI (2.1.283) has `--tools <tools...>`, which sets the built-in tool set that is available at all.
  - Workspaces are empty (`isolated_workspace=True` creates `artifacts/<run>/workspace`).
  - Results are written only after the whole batch. An ENOSPC crash after 547 of about 770 runs lost the aggregation, and it was reconstructed offline with `scratchpad/score_existing_triggers.py`.
- **Plugin root.** The runner stages the plugin from `<cwd>/plugins/rf-agentskills`. The 2026-09 comparison of old and new descriptions ran from a copied tree (`v1-old-descriptions/`), with a `skills/` copy so task validation found the names.
- **Trigger sets.** 12 sets live in `eval/triggers/<skill>.yaml`, with 10–14 queries per polarity. The validation split holds 4 should-trigger and 4 should-not-trigger queries for most skills (rf-language: 6/5). Validation recall therefore moves in steps of 0.25.
- **Description rules.** `tests/test_skill_descriptions.py` enforces:
  - the text starts with a capitalized verb ending in "s" (`LEADING_VERB_RE`);
  - no "this skill" (`META_RE`);
  - `Use when`;
  - named siblings;
  - ≤ 1024 characters, with a warning above 500.
  The validator also requires `name` and `description` to be the first two frontmatter lines.
- **Measured baseline (Haiku 4.5, 2026-09):** validation-split loads per skill, current descriptions vs pre-sharpen descriptions:

  | Skill | Current | Pre-sharpen |
  |---|---|---|
  | rf-appium | 6/12 | 8/12 |
  | rf-browser | 8/12 | 2/12 |
  | rf-libdoc | 8/12 | 11/12 |
  | rf-platynui | 3/12 | 2/12 |
  | rf-requests | 4/12 | 6/12 |
  | rf-restinstance | 9/12 | 9/12 |
  | rf-results | 0/12 | 0/12 |
  | rf-robotcode | 0/12 | 3/12 |
  | rf-selenium | 5/12 | 4/12 |
  | rf-setup | 2/12 | 3/12 |
  | rf-language | 1 of 6 queries triggered | n/a |
  | rf-python-library | 0 of 4 queries triggered | n/a |

  Should-not-trigger accuracy was 100% everywhere.

## Goals / Non-Goals

**Goals:**
- Make the trigger measurement reflect real use: only trigger tools, a realistic project directory, and no lost results.
- Raise validation recall for every skill without losing should-not-trigger accuracy, using a repeatable and budgeted procedure.
- Leave an auditable record of every candidate and its train and validation numbers.

**Non-Goals:**
- Changing skill bodies, the routing hook (UserPromptSubmit), or task evals.
- Tuning for models other than Haiku 4.5; Sonnet 5 is only reported.
- Using Claude Code–only frontmatter such as `when_to_use`, because it isn't portable across agents (agentskills.io spec).

## Decisions

### D1. Restrict tools with `--tools`, keep `--allowedTools`

The trigger profile passes `--tools Skill,Read,Glob,Grep` in addition to `--allowedTools`. `Skill` must stay in `--tools`, or Claude Code will not offer skills at all; this is verified in task 1.1 against the init record's `tools` list. If `--tools` does not accept `Skill`, the fallback is `--disallowedTools` listing every other built-in tool (Bash, Write, Edit, MultiEdit, NotebookEdit, WebFetch, WebSearch, Task/Agent, TodoWrite).
- *Rejected alternative:* keeping `bypassPermissions` with the allow-list alone. The runs showed it doesn't restrict anything.

### D2. A neutral trigger fixture `eval/fixtures/sut-trigger/`

The fixture contains:
- `pyproject.toml`, declaring `robotframework` only;
- `tests/smoke.robot`, using BuiltIn keywords only;
- `resources/common.resource`;
- a short `README.md`.

It imports no test library, so no library skill is favoured by the files, and the query alone decides. It gives the model something realistic to look at: an empty directory invites `Glob` and `Read` loops and "let me explore" turns.
- *Rejected alternative:* per-skill fixtures. They would leak the answer, for example a `Library    Browser` import.
- *Rejected alternative:* reusing `sut-minimal`. It is coupled to task evals and could change for them.

### D3. Incremental persistence and resume

Each finished query appends one JSON line to `<output>/outcomes.jsonl`, keyed by `(variant_root_id, model, skill, query_id, split)`. On start, the command loads the existing lines, skips queries whose key is present, and runs the rest. The final `trigger-results.json` aggregates everything in the file. A run interrupted mid-query loses only that query.
- *Rejected alternative:* reading the run directories after the fact, as the offline rescue did. It is fragile, because it depends on directory naming and mtimes.

### D4. Concurrency up to 2

Queries run in a pool of ≤ 2 workers, the ADR-002 cap. Budget accounting is serialized. With the observed ~80 s per session, a train pass for one skill takes about 40 runs, roughly 27 minutes. A full 12-skill validation pass takes about 30 minutes.

### D5. Variant roots built from a candidates file

`scripts/build-description-variant.py --candidates <yaml> --out <dir>`:
1. copies `plugins/rf-agentskills`, plus the `skills/` name list the task validator needs;
2. replaces the `description:` line of each listed skill with a JSON-quoted candidate;
3. prints the variant id, a hash of the candidates.

`trigger --variant-root <dir>` stages from `<dir>/plugins/rf-agentskills`. The results record `variant_root` and `variant_id`.
- Candidates live in `openspec/changes/tune-skill-descriptions/candidates/<skill>.yaml`. That is the audit trail: iteration number, text, train loads, and a rationale line.
- *Rejected alternative:* editing `skills/` in place for each iteration. It would churn sync, drift and the tests, and mix candidates into the working tree.

### D6. Tuning loop per skill; accept on a combined validation run

For each skill, in order of the lowest re-baselined validation recall first:
1. Analyse the failing train transcripts. Which query words were present? What did the model do instead: answer directly, or Read a file?
2. Write candidate *k* following the pattern in D7.
3. Run the train split for that skill with 3 runs (about 40 sessions).
4. Keep the candidate if its train score beats the best so far. The train score is loads on should-trigger queries, with any should-not-trigger load disqualifying.
5. Stop at train recall ≥ 0.9 with no should-not-trigger loads, or after 5 iterations.

Descriptions interact, because all skills are installed. So acceptance is decided on **one combined validation run** that stages all best candidates together (about 300 sessions). Each skill's candidate is then judged by rule (a) or (b) from the spec. A skill that fails keeps its current text, and the combined run is repeated only if at least one skill was reverted and a sibling's negative accuracy could have changed.
- *Rejected alternative:* per-skill validation runs. Cheaper, but blind to sibling interference, such as a sharper rf-browser now stealing rf-selenium queries.

### D7. Description pattern

At most about 600 characters. In order:
1. **Intent sentence.** "Use this skill whenever a Robot Framework project <does X> with <Library/tool> …", or a third-person "Writes and fixes …" sentence. Name the library or package and the import line.
2. **"Use when" triggers.** Phrased as user requests and symptoms: "writing or fixing a …", "a test fails with 'X'", "pasting output.xml". No list of keyword names; at most 5 API names in total.
3. **Nudge.** "…even if the user only says '<generic phrasing>' and doesn't name <library>". Always with concrete situations, never a generic "always use".
4. **Boundary.** "Not for <sibling signal> — use `rf-<sibling>`."

Example for rf-python-library, a draft for iteration 1:

> "Use this skill whenever Robot Framework keywords or listeners are written in Python: a library class or module under libraries/, @keyword or @library decorators, library scope, argument types, a listener that changes results. Use when a Python library 'contains no keywords', loses state between tests, shows unexpected keywords such as Join, or needs libdoc docs — even if the user just says 'custom keyword in Python' or 'Robot plugin'. Not for keywords written in .robot/.resource files — use `rf-language`."

### D8. Contract changes in the description test

- `LEADING_VERB_RE` accepts either `^[A-Z][a-z]+s\b` or `^Use this skill (when|whenever)\b`.
- `META_RE` drops "this skill" and keeps "guide ai agents" and "helps the ai".
- The trigger clause accepts `Use when` or `Use this skill when`/`whenever`.
- A new catalog check counts backtick spans that aren't `rf-*` skill names, plus the TitleCase keyword names in the shipped keyword lists (e.g. `New Browser`, `Get Text`). It fails above 5.
- The length warning threshold moves to 600 characters.

### D9. Model and budget

- Tuning and acceptance use `claude-haiku-4-5-20251001`: it undertriggers most, and it is the cheapest. The Sonnet 5 validation pass is reported only.
- Every command gets a `--max-cost-usd` cap:
  - re-baseline: $15
  - per-skill train pass: $2
  - combined validation pass: $12
  - holdout: $10
  - Sonnet 5 pass: $12
- Total cap: $80. If the cap is reached, stop, record the stop, and accept only what has been validated.

### D10. Recording results

- `eval/baselines/triggers.json` is rewritten from the accepted combined validation run. It records the Claude Code version, the harness version, the model and `variant_id`. Per skill it adds a `shortfall` note when rule (b) applied, and `kept_current: true` when neither rule applied.
- The 2026-09 evidence files stay in the change's `evidence/` folder for history. They are not comparable with post-D1/D2 numbers.

## Risks / Trade-offs

- **Small validation sets** (4 positives), so recall moves in 0.25 steps and 3-run noise can flip one query. → The combined validation run is repeated once for any skill whose acceptance depends on a single query. The holdout split is reported as a second, independent signal.
- **Overfitting to train phrasing.** → Validation and holdout are never used for selection. Failed train queries are not pasted into descriptions. The holdout is written after tuning.
- **Hooks are off in trigger evals**, while real sessions have the routing hook. → Measured recall is a floor. The hook is a separate follow-up.
- **Fixture bias.** Even a neutral RF project nudges toward rf-language or rf-setup. → Both have their own near-miss queries. We compare against the re-baseline measured on the same fixture.
- **Claude Code version drift** changes skill-selection behaviour. → The CLI version is recorded, and the gate reports `rebaseline-needed` when it changes (existing behaviour).
- **Cost overrun.** → Hard caps per command plus the $80 total (D9).

## Implementation Notes

### Tasks 1.1–1.7 and 3.1 (2026-09-29)

- **D1 verified live.** One trigger session (Haiku 4.5, `--max-turns 1`, query `rs-v01`, cost $0.0154) with `--tools Skill,Read,Glob,Grep`: the init record listed exactly `tools: [Glob, Grep, Read, Skill]` (no Bash/Write/Edit, no MCP tools) and `skills` still listed all 12 `rf-*` skills. The `--disallowedTools` fallback was not needed. Claude Code 2.1.284.
- **Where the settings live.** The trigger-specific behaviour is carried by three new `Profile` fields instead of runner constructor arguments, so one runner serves both task and trigger evals: `restrict_tools` (adds `--tools` next to `--allowedTools`), `workspace_fixture` (a fresh copy of `eval/fixtures/sut-trigger/` per session when the task has no fixture; no workspace preamble is prepended, so the query is sent verbatim) and `plugin_root` (the variant plugin to stage).
- **Persistence (D3).** Outcomes whose runs were all budget-stopped are not written. An outcome with any incomplete run is written but not treated as done: a resume runs it again and the later line wins. `trigger-results.json` holds the planned queries in plan order, followed by any other outcomes in `outcomes.jsonl` with the same variant id and model(s). For example, other skills measured earlier into the same `--output`.
- **Concurrency (D4).** The pool unit is one query, and its runs stay sequential. Budget checks, spend and the `budget_stopped` count are updated under one lock. `OutcomeStore.append` has its own lock. With 2 workers the cap can be overshot by at most one in-flight session.
- **Variant id (D5).** This deviates from "a hash of the candidates". The id is a 12-hex SHA-256 of the `{name: description}` map of every skill in the staged plugin. It is stable for identical input. Two roots with the same descriptions share an id, so an empty-candidates variant has the shipped plugin's id. Runs without `--variant-root` are keyed by that shipped id, which means editing a shipped description changes the resume key. The builder also writes `<out>/variant.json` (id, source, candidates). `--candidates` can be repeated. Each file is either a plain `{skill: text}` mapping or the per-skill audit file (`skill`, `iterations[]`, optional `selected`; without `selected` the last iteration is used). The core logic lives in `src/rf_skill_eval/application/variant.py`; `scripts/build-description-variant.py` is a thin wrapper. With `--variant-root`, trigger-set skill names are validated against `<dir>/skills`.
- **Holdout (1.3).** `REQUIRED_SPLITS = (train, validation)` drives the ≥ 8 count and the both-polarities rule, and `holdout` is optional. The report adds Holdout columns only when holdout outcomes are present, so existing reports and snapshots are unchanged.
- **Catalog check (3.1).** The keyword names come from the shipped skills themselves: calls on indented lines of fenced `robot`/`robotframework` blocks and of `.robot`/`.resource` files under `skills/`. Only multi-word names are used (217 of them), because single words such as `Click` or `Integer` collide with prose. The count is backtick spans that are not `rf-*` names, plus the longest non-overlapping TitleCase phrases that match a keyword name. All 12 current descriptions pass the > 5 rule; the maximum is rf-restinstance with 4 (`Library    REST`, `REST`, Expect Response Body, Output Schema). So no parameter is xfailed. `CATALOG_TUNING_TARGETS` exists, empty, for 4.x. Two descriptions exceed the new 600-character warning: rf-language (675) and rf-python-library (722).

### Tasks 2.1–4.3 (2026-09-29)

- **Re-baseline (2.1).** Variant `25e6b4b2b5f8` (current descriptions), both splits, 256 queries × 3 runs, 0 incomplete, $16.16, Claude Code 2.1.284. Copied to `evidence/rebaseline.json`; table and failure analysis (2.2) in `evidence/README.md`.
- **Skill-listing budget: 9 of 12 descriptions were never shown.** Claude Code builds the skill listing (the `skill_listing` attachment in `session.jsonl`) under a character budget of `context window × 4 × skillListingBudgetFraction` (default 0.01), i.e. 8000 characters for Haiku 4.5's 200k window; `SLASH_COMMAND_TOOL_CHAR_BUDGET` overrides it. Bundled skills always keep their descriptions; the others are ordered by the user's usage score (0 in a fresh config, so alphabetical) and each keeps its description only while it still fits, otherwise it is listed by name only. In every re-baseline session the bundled skills and all names used 6266 characters, which left 1734 for the rf-* descriptions: rf-appium, rf-browser and rf-language fit (1708), rf-libdoc … rf-setup were names only. So the re-baseline measures names, not descriptions, for 9 skills, and the same cap applies to real users of 200k-context models. With `SLASH_COMMAND_TOOL_CHAR_BUDGET=40000` (what a 1M-context model gets) every description is listed: rf-results train went from 2/21 loads (name only) to 8/21 with its current text visible and 21/21 with candidate 1.
- **Deviation: tuning measured with every description visible.** All tuning runs after the first set `SLASH_COMMAND_TOOL_CHAR_BUDGET=40000` in the environment of `rf-skill-eval trigger` (the runner passes its environment to `claude`). Without it, rewording 9 of the 12 descriptions could not change anything. The first rf-results candidate run ($0.85) was made without it and is recorded as such. Iteration 0 numbers in `candidates/*.yaml` are the re-baseline's (default listing); only rf-results has iteration 0 re-measured with the override. The results files do not record the listing budget, and a run with and without the override shares the variant id, so these runs use separate `--output` directories. **Before task 5** the listing condition has to be chosen, and the re-baseline repeated under it if it changes:
  - measure acceptance with the override (every description visible; representative of 1M-context models, not of Haiku's default); or
  - keep the default budget and make the whole set fit: about 1700 characters for 12 descriptions (≈ 140 each), which the current contract (required terms, sibling boundaries, `Use when` clause) does not allow; or
  - both, reporting the default-budget result as the Haiku floor.
  The selected candidates total about 9.2k characters; under the default Haiku budget only rf-appium and rf-browser would be shown. The harness should also record the listing budget (or the listed/names-only skills from the `skill_listing` attachment) in each outcome.
- **Order and budget (4.2/4.3).** Order by re-baseline weakness as instructed: rf-results, rf-language, rf-python-library, rf-libdoc, rf-requests, then rf-platynui, rf-robotcode, rf-setup, then rf-appium, rf-browser, rf-restinstance, rf-selenium (runs were batched a few skills at a time, so the order is by batch). Tuning budget $35 for this task; spent $28.75 in 26 train runs (ledger in `evidence/README.md`), $44.91 for the change so far.
- **Outcome.** 10 skills reached the stop rule (query recall ≥ 0.9, 0 negative loads) within 1–3 iterations. rf-language stopped after 4 (candidate 4 met the rule on queries, 8/8, but with fewer single-run loads than candidate 2, 19/24 vs 22/24, so candidate 2 is selected by the D6 score; 7/8 queries). rf-libdoc stopped after 4 at 18/21 (6/7): an explicit "search our <file>.resource for keywords" request is always answered with `Grep`. Strong skills used at most 2 iterations. Candidates that raised recall but added a negative load (rf-libdoc 1, rf-setup 1–2) were not selected.
- **What worked.** The imperative form "Use this skill whenever <user intent>, and load it first, before exploring the project / reading <file> / answering from memory: <capabilities in user terms>" moved every skill; the model's failure modes were answering directly and exploring first, and naming both in the description stopped them. Symptoms phrased as the user sees them ("an element cannot be located on a device", "a click or selector times out", "a library that loses its state between tests"), "even if they only say …" nudges, and boundaries written as instructions ("When the user asks for a test to be written or fixed, use the library skills instead, even if the library is not installed yet") removed the remaining secondary loads. Splitting the capability list into its own sentence ("It covers …") was neutral to negative (rf-language 3 worse, rf-python-library 3 better).
- **Candidates files.** `candidates/<skill>.yaml` uses the builder's schema (`skill`, `selected`, `iterations[]` with `iteration`, `text`), plus `listing`, `train_pos_loads`, `train_pos_runs`, `train_query_recall`, `train_neg_loads`, `variant_id`, `spent_usd`, `run` and `rationale`. Run directories (transcripts) stay in the session scratchpad, not in the repo. All selected texts pass `description_problems`, `boundary_problems`, `catalog_problems` and `REQUIRED_TERMS`; all but rf-restinstance exceed the 600-character warning (rf-language 991, rf-python-library 959).
- **Harness caveats found.**
  - `load_candidates` normalises whitespace (`" ".join(text.split())`), so `Library    X` import lines were measured as `Library X` in variants; the candidates files keep the four spaces that the contract requires.
  - Workspace-violation cleanup in `ClaudeCodeRunner` deletes any file that appears anywhere in the repository while a trigger session runs (it cannot tell who created it); two evidence files written during runs were deleted and had to be recreated. Create new repository files only while no eval run is active, or run evals from a copy.
  - Queries that name a file the neutral fixture does not have (`results/output.xml`, `tests/web/checkout.robot`) plus `--max-turns 3` end some sessions before a late `Skill` call ("let me find the output.xml, then use the rf-results skill"). The load-first wording removes most of this.

### Tasks 1.8–1.10 and 3.2 (2026-09-29)

- **Listing budget (1.8).** `trigger --listing-budget <chars>` puts `SLASH_COMMAND_TOOL_CHAR_BUDGET` into the session environment through a new `Profile.listing_budget`; without the flag nothing is set. The resume key is now (variant id, model, listing budget, skill, query id, split); `outcomes.jsonl` rows carry `listing_budget` (`null` = default), and rows written before this change read as the default budget. That is wrong for the 4.2/4.3 tuning runs made with the variable exported, but those used their own `--output` directories.
- **Deviation: one results file per budget.** Spec scenario "Listing budget recorded and keyed" says both budgets in one output directory must not overwrite each other. So a default batch writes `trigger-results.json`/`trigger-report.md`, and a budget batch writes `trigger-results-budget-<N>.json`/`trigger-report-budget-<N>.md`. Both record `listing_budget`, and each aggregates only its own budget's outcomes. `baseline update` globs `trigger-results.json` only, so a budget run never becomes the gating baseline by accident.
- **Deviation: an exported budget is adopted.** The runner passes its environment to `claude`. If `SLASH_COMMAND_TOOL_CHAR_BUDGET` is exported and `--listing-budget` is not given, the CLI prints a note and records the exported value as the budget. Otherwise the session would silently run under an override while the results said "default".
- **Visibility (1.8).** `infrastructure/telemetry/skill_listing.py` reads every `skill_listing` attachment in the run's captured `session.jsonl` (`TriggerRun.session`). `- <name>: <text>` lines count as shown, and `- <name>` lines as names only; plugin prefixes are stripped and continuation lines are ignored. Each `QueryOutcome` gets `visible_descriptions`: one sorted tuple of shown rf-* skills per completed run that had a listing. From it the results derive a `visibility` map per skill: `own_visible/own_listed` over the skill's own queries' sessions, and `all_visible/all_listed` over every session. The report adds a "Description visibility" table only when a listing was recorded, so the existing report snapshot changed only in its header line (budget). Fixture: `tests/eval/fixtures/transcripts/skill-listing-default-budget.session.jsonl`, trimmed from a re-baseline session (paths sanitised, bundled-skill texts shortened). It shows the 3 visible and 9 names-only rf-* entries verbatim.
- **Byte-exact candidates (1.9).** `load_candidates` keeps the text as YAML parsed it and strips only leading/trailing whitespace, such as the newline of a `|` block scalar. Runs of spaces are no longer collapsed. Variant ids of candidates that contain `Library    X` therefore differ from the ids recorded in 4.2/4.3.
- **Isolation (1.10).** `ClaudeCodeRunner` no longer deletes anything, and its `cleanup_violations` argument is gone. Violations go to `workspace_violations.json` (`"deleted": false`). The run gets `error = "isolation-violation: N file(s) created outside the workspace during the run: <repo-relative paths>"`, appended after an arm-leak error if there is one. Through `Run.error` the scorecard's `incomplete_reason` makes the gate result `incomplete`. The snapshot is skipped when the profile restricts tools (`--tools`) to a set without `Write`, `Edit`, `MultiEdit`, `NotebookEdit` or `Bash` (`needs_isolation_check`), which is every trigger profile.
- **Compact contract test (3.2).** Constants at module top: `MAX_COMPACT = 160`, `MAX_LISTING_TOTAL = 1700` (with the measurement and re-measure comment), `WHEN_TO_USE_WITHIN = 20` and `MAX_API_NAMES = 2`. The D8 rules (leading verb, `Use when` clause with a trigger term, catalog > 5, warning at 600) and the description-level boundary check are replaced:
  - `portability_problems`: ≤ 1024, meta-phrasing, XML tags, shipped skill names. It still gates today.
  - `compact_problems`: ≤ 160; "Robot Framework" or `\bRF\b`; one of the skill's `SUBJECT_TERMS`; a load cue (a sentence starting with `Use`/`Load`); ≤ 2 keyword/API names by the D8 catalog counter, where an import line in backticks counts as one.
  - `listing_problems`: `len("\n".join("- <name>: <description>"))` ≤ 1700, reporting the total and the three longest.
  - `when_to_use_problems`: a `## When to use` heading within the first 20 body lines. Its block must contain the `SIBLINGS` needles, the `DEFAULTS` wording and the former `REQUIRED_TERMS`, which move from the description to the block.

  "States the user intent" is not machine-checked. All 12 compact-rule params, all 12 block params and the combined-listing test are `xfail(strict=True, reason="compact rewrite pending (tasks 4.4–6.1)")`, driven by `COMPACT_PENDING`/`WHEN_TO_USE_PENDING`; 6.1 empties both sets. Offline, the current texts fail on length (467–722 characters); rf-browser (3), rf-selenium (3) and rf-restinstance (4) also exceed 2 API names. The combined listing is 6590 characters.
  - The 1700 limit counts the `- <name>: ` prefixes, which the measured 1734 characters of room did not include (names were already part of the 6266). So it is conservative by about 180 characters. With 12 skills the total, not the 160 cap, is the binding limit (about 125 characters each on average).

## Revision 2026-09-29: compact descriptions under the default listing budget (user decision)

The tuning run (tasks 4.1–4.3) found that Claude Code lists skill descriptions only while they fit a budget of `context window × 4 × 1%` characters. For 200k-context models that is about 8000; for 1M-context models, 40000.
- Bundled skills are listed first, then the others alphabetically.
- Each skill keeps its description only while it still fits; after that it is listed by name.
- Under the Haiku default only rf-appium, rf-browser and rf-language were shown with descriptions (verified in `session.jsonl` `skill_listing` attachments: 7974 characters).
- The rich candidates from 4.2/4.3 reach 18–22 of 21 train loads, but only with `SLASH_COMMAND_TOOL_CHAR_BUDGET=40000`.

On 2026-09-29 the user chose to optimize and accept **compact descriptions under the default budget**, and to fix the runner cleanup that deleted unrelated repository files. This revision supersedes D7, D8 and the acceptance condition of D6 where they conflict.

### D11. Compact description contract

- Each description is at most 160 characters.
- All shipped `- <name>: <description>` listing lines together are at most 1700 characters. That is the room left after bundled skills and names in Claude Code 2.1.284 with Haiku, as measured. The constant lives in the test with a comment on how to re-measure it.
- Each description names RF / Robot Framework and the library, tool or file; states the user intent; and carries a load cue ("Use when/for …", "Load first when …").
- At most 2 keyword or API names.
- Pattern: `"<Intent> for Robot Framework <Library/tool>. Use first when <top trigger>."`

The "load it first, before exploring / answering from memory" instruction, which was the strongest lever in 4.x, is kept in a shortened form where space allows.

### D12. Rich text moves into a "When to use" body block

The tuned rich texts from 4.2/4.3 become a `## When to use` block within the first 20 lines of each SKILL.md body. It holds:
- trigger terms, symptoms and pasted errors;
- the sibling boundary, per the modified "Sibling skills state their boundary" requirement.

This text only helps after the skill has loaded, when it tells the model whether it picked the right skill and which sibling to switch to. It does not change the listing.

### D13. Tuning compact candidates together

The listing is shared, so compact candidates are tuned as one set, all staged together, on the train split under the default budget.
- At most 3 iterations for the whole set, because each full train pass is about 390 sessions and about $8.
- Selection uses the train score summed over skills. A candidate set that loses any should-not-trigger accuracy is rejected.
- Every session records whether each description was visible, so a set that overflows the budget shows up directly.

### D14. Listing budget and visibility in the harness

- `trigger --listing-budget <chars>` sets `SLASH_COMMAND_TOOL_CHAR_BUDGET` for the sessions. The default is not to set it.
- The budget is part of the resume key and the results metadata.
- The runner parses the `skill_listing` attachment from `session.jsonl` and records, per run, which rf-* descriptions were visible.
- The variant builder keeps descriptions byte-exact; `load_candidates` no longer collapses whitespace.

### D15. Isolation checks report, never delete

- `_detect_workspace_violations` results are attached to the run as an isolation-violation error, which makes the run untrustworthy. Files outside the run's workspace and artifacts directory are never deleted.
- Trigger profiles (no write tools) skip the before/after repository snapshot entirely.

### D9 (revised). Budget

The change total is raised from $80 to **$90**. Spent so far: $44.91.

| Item | Cost |
|---|---|
| Compact set tuning (≤ 3 × ~$8) | ≤ $24 |
| Combined validation, default budget | ~$6 |
| Validation at 40000 (report) | ~$6 |
| Holdout (3 runs) | ~$8 |
| Sonnet 5 validation (1 run/query) | ~$6 |

If spend reaches $90: stop, record, and ship what has been validated.

### Tasks 4.4–5.3 (2026-09-29/30)

- **Compact set (4.4).** Pattern: `"Use first, before exploring or answering, for Robot Framework <intent> with <Library>: <2–4 user terms>."` The load-first cue from 4.x is kept in every text; its object is the failure mode seen for that skill (rf-results: "before reading output.xml yourself"; rf-language: "before reading .robot/.resource files"; rf-setup: "before reading pyproject.toml"; rf-libdoc: "not memory"). Sibling boundaries only where they fit and were needed (rf-setup "Not for writing tests.", rf-robotcode "Not VS Code extension."). The selected set totals 1697 characters of listing lines (125.8 characters per description on average). `when_to_use` blocks (8–11 lines) were drafted from the selected rich texts and pass `when_to_use_problems`; they include the heading line so 6.1 can paste them.
- **Candidates schema.** Each `candidates/<skill>.yaml` got `compact` (`rebaseline_train`, `selected`, `iterations[]` with text, chars, train numbers, variant id, run, rationale, and `remeasured_with_later_sets` when a later set run re-measured the same text) and `when_to_use`. The builder still reads only the rich `iterations`/`selected`, so variants were built from plain `{skill: text}` mappings in the scratchpad (`tune/compact/it{1,2,3}.yaml`).
- **Deviation: partial set iterations (4.5).** A full train pass cost $12.25 (not ~$8; sessions that load a skill are longer), so only iteration 1 was a full pass. Iteration 2 re-ran the two changed skills (rf-language, rf-robotcode) plus the two siblings that took their queries (rf-libdoc, rf-results); iteration 3 re-ran rf-robotcode only. Unchanged skills keep their iteration-1 numbers. Iterations 1 and 2 were rejected because rf-robotcode lost negative accuracy on rc-n04 (RobotCode VS Code extension); iteration 3 fixed it (0 negative loads) and is selected: 232/252 train loads vs 120/252 at the re-baseline.
- **Visibility (4.5).** All 12 descriptions were visible in 100% of sessions of every compact run (listing 7931 of 8000 characters). The earlier visibility probe (rf-setup validation queries, 1 run each, $0.20) only checked the listing and was not used for selection.
- **Acceptance (5.1).** 6 skills under rule (a) (rf-appium, rf-platynui, rf-requests, rf-results, rf-selenium, rf-setup), 4 under rule (b) with recorded shortfalls (rf-language 0.50, rf-libdoc 0.75, rf-python-library 0.50, rf-robotcode 0.75), 2 meeting neither (rf-browser, rf-restinstance: 0.75 = re-baseline, loads +1 each). No skill lost should-not-trigger accuracy. Table in `evidence/README.md`.
- **Deviation: no revert.** Task 5.1 says to revert a failing skill to its current text; the revised spec requirement ("A skill meeting neither (a) nor (b) SHALL still ship a compact description") takes precedence, because the current texts break the 160-character rule. rf-browser and rf-restinstance ship their compact texts, recorded as not meeting the target (6.2 should record this in place of `kept_current`).
- **Deviation: 5.2 not run.** rf-python-library and rf-robotcode are accepted by exactly one query, and rf-browser/rf-restinstance miss rule (a) by one query, so 5.2's condition holds. The repeat was not run: the $32 allotted to 4.5–5.3 was spent ($31.97). A repeat costs about $7.5; if it is funded later, it should use the same variant (`7cfa7e52981c`) and a new `--output`.
- **5.3 partial.** The 40000-budget validation run stopped at its cap with 18 rf-setup runs (6 queries) not started and was not resumed. Under the compact set every description is visible at both budgets, so the default and 40000 columns differ only by noise (122/150 vs 119/144 positive loads).
- **Budget caps and resume.** Both capped runs (train it1, validation) were completed by re-invoking with the same `--output`; the aggregated `trigger-results.json` then reports only the last invocation's `spent_usd`, so the evidence ledger adds both parts.
- **Spend.** 4.5: $17.54 (with the probe); 5.1: $7.50; 5.3: $6.93. Change total $76.88 of $90.

### Tasks 6.1, 6.2 and 7.1 (2026-09-30)

- **Shipped texts (6.1).** Each skill's `compact.selected` text is on frontmatter line 3 (JSON-quoted, `name`/`description` stay the first two lines), and its `when_to_use` block is inserted verbatim right before the first `## ` heading of the body, i.e. after the H1 and the orientation lines. The heading lands on body line 4–14 (rf-results is the latest at 14), within the 20-line window. `COMPACT_PENDING`/`WHEN_TO_USE_PENDING` are empty, so no xfail is left in `tests/test_skill_descriptions.py`. rf-browser and rf-restinstance ship their compact texts as well and are recorded as not meeting the target (not `kept_current`), per the Revision note under 4.4–5.3.
- **Deviation: one block line reworded (rf-browser).** `tests/test_library_install_guidance.py` allows `rfbrowser init` only next to "Node" (the Node.js escape hatch). The drafted block said "installing the library or `rfbrowser init` errors use `rf-setup`"; the shipped line says "installing the library or errors in its Node.js `rfbrowser init` step use `rf-setup`". The listing text is unchanged, so the measured variant id (`7cfa7e52981c`) still describes what ships; the body block is only read after a load.
- **Structure tests adjusted for the new block.** The block is a new H2 section before the first existing one, so the tests that pin the H2 list or order were extended minimally, without relaxing anything else:
  - `tests/test_library_skill_structure.py` (5 library skills): `LEADING_SECTION = "When to use"` is accepted only as the first H2, before `Installation`; the required order and the optional-section window are unchanged. The main spec `openspec/specs/library-skill-structure/spec.md` ("a short orientation …, `Installation`, …") does not name the block yet; it should get "an optional `When to use` block between the orientation and `Installation`" when this change is archived (follow-up; no delta spec was added here).
  - `tests/test_language_skill.py` and `tests/test_python_library_skill.py`: `"When to use"` prepended to their exact section lists.
  - Description-content checks that assumed the long D7 descriptions now check the compact description for the core terms and the `## When to use` block for the moved ones: `test_language_skill.py::test_description_boundary` (terms and boundary now read from the block), `test_libdoc_skill.py::test_description_covers_both_jobs` (description: ≤ 160, starts with "Use", keyword/argument/libdoc; block: "which keyword", arguments, signature), `test_robotcode_skill.py::test_skill_frontmatter` ("result" is checked in the block).
  - rf-language's SKILL.md is now 312 lines, above the 300-line target of `test_language_skill.py` (a warning; the hard limit is 500). The library skills stay within 250 lines / 12,000 characters; rf-setup and rf-robotcode within 200 lines.
- **README.** The README skill table is a human summary (short task lines per skill), not a copy of the descriptions, so it was left unchanged.
- **Trigger baseline (6.2).** `baseline update --from <dir>` with `evidence/compact-validation.json` copied as `trigger-results.json` (written to a scratch output dir first, so the tier baselines were not touched, then copied). The builder writes only `harness_version`, `model` and per-skill split metrics, and the task forbids harness changes, so the other fields were added by hand to `eval/baselines/triggers.json`: `claude_code_version` `2.1.285` (from the validation run's `session.jsonl` records; the re-baseline used 2.1.284), `variant_id` `7cfa7e52981c`, `listing_budget` `null`, `runs_per_query`, `split`, `source`, `rebaseline_source`, `target`, and per skill an `acceptance` object (`rule` a/b/none, `decision`, validation and re-baseline recall; `shortfall` + `shortfall_note` for rule (b): rf-language 0.30, rf-libdoc 0.05, rf-python-library 0.30, rf-robotcode 0.05; `not_meeting_target: true` with a shortfall of 0.05 for rf-browser and rf-restinstance). `gate` reads only `skills.<name>.<split>`, so the extra keys are ignored: `rf-skill-eval gate --trigger-results <copy> --trigger-baseline eval/baselines/triggers.json` → `PASS (12 task(s) checked)`. The baseline now holds the validation split only (the source run was validation-only); `gate` checks validation by default. `baseline update` should learn to carry these fields itself (follow-up).
- **Holdout (7.1).** Each `eval/triggers/<skill>.yaml` got ids `<prefix>-h01…h10`, `split: holdout`: 5 should-trigger and 5 should-not-trigger queries, written after 6.1 in users' phrasing (including indirect forms: pasted errors, symptoms, file names, intent only). Every set has 2–3 sibling near misses (`note: "sibling rf-…"`) and 2 non-RF look-alikes. They were checked against all train/validation queries of all 12 sets to avoid copies or paraphrases (for example, no "slowest tests", "new tab", "list the keywords of <file>.resource" or "robot.toml ci profile"). None has been run (7.2).

### Tasks 7.2 and 8.1 (2026-09-30), final numbers

**Final numbers, shipped compact set, Haiku 4.5, default listing budget:**
- validation: 41/50 should-trigger queries triggered (re-baseline 21/50); positive loads 122/150 (re-baseline 63/150); should-not-trigger accuracy 100%;
- holdout, 10 measured skills: recall 0.90, 3 sibling-boundary false positives;
- Sonnet 5 validation, 10 fully measured skills: recall 0.98, no false positives;
- descriptions visible in 100% of sessions (listing 7931 of 8000 characters).

**Spend and gaps.** Total spend: $90.02 against the $90 cap.
- Task 5.2 (repeat validation for single-query decisions) was **not run** for lack of budget. Four decisions depend on a single query: rf-python-library, rf-robotcode, rf-libdoc, rf-language.
- 7.2 is budget-truncated: rf-selenium and rf-setup were not measured on the holdout, and are partial on Sonnet 5.

**Follow-ups:**
1. Fund 5.2 and the missing holdout and Sonnet queries. Resume by re-running the same commands into the same `--output`.
2. Add short sibling cues where the 1700-character budget allows ("not install", "robotcode users: rf-robotcode"), and re-measure the 3 holdout false positives.
3. Re-measure the 1700 constant whenever Claude Code's bundled-skill set changes. A user's other installed skills compete for the same listing, and names sort alphabetically after bundled skills.
4. Route the UserPromptSubmit hook to name the matching skill.
5. Harder library task evals.
6. rf-mcp attachment bug in task runs.
7. Eval sessions inherit `VIRTUAL_ENV` and can install packages into the harness environment (observed 2026-09-28).
8. Prune agent-created workspace venvs after grading (disk).
9. Add the `## When to use` leading section to the `library-skill-structure` spec (tests already allow it).
10. rf-language SKILL.md is 312 lines, above its 300-line target.

### Completion runs (2026-09-30, extra budget approved by the user)

- **5.2:** the repeat validation ran. Decisions now pool both validation runs (6 runs per query): 7 skills meet rule (a), 3 rule (b) (rf-language 0.30, rf-python-library 0.05 and rf-robotcode 0.05 short of target), and rf-browser and rf-restinstance do not meet the target. rf-libdoc moved from (b) to (a).
- **`eval/baselines/triggers.json`:** the `acceptance` entries were updated to these pooled decisions. The gate still compares against the first run's `validation` metrics, the conservative reference, and PASSes.
- **Holdout (Haiku), complete:** recall 0.92, accuracy 0.93. The 4 false positives are all sibling handoffs, to rf-setup or rf-robotcode.
- **Sonnet 5 validation, complete:** recall 0.98, accuracy 0.98.
- **40000 budget, complete:** same as the default budget within noise.
- **Total spend:** $100.99. Follow-ups 1 (fund 5.2 / missing queries) and the budget-gap notes above are resolved. Follow-up 2 (short sibling cues) is now backed by 4 holdout false positives and 1 Sonnet false positive.
