## 1. Faithful trigger measurement (harness)

- [x] 1.1 In `claude_code_runner.py`, pass `--tools Skill,Read,Glob,Grep` for trigger profiles (D1), falling back to `--disallowedTools` for all other built-ins if `--tools` hides skills. Verify: one live trigger session (≤ $0.05) whose init record lists exactly those tools and still lists the rf-* skills; plus a unit test on the built command line.
- [x] 1.2 Add `eval/fixtures/sut-trigger/` (`pyproject.toml` with robotframework only, `tests/smoke.robot` using BuiltIn only, `resources/common.resource`, README) and provision a fresh copy per trigger session instead of the empty workspace (D2). Verify: `robot --dryrun eval/fixtures/sut-trigger/tests` passes; a unit test asserts that the trigger session workspace contains the three paths; the fixture imports no library other than BuiltIn (grep test).
- [x] 1.3 Extend `domain/trigger.py` splits with `holdout` (optional; excluded from the ≥ 8/8 count) and accept `--split holdout` (spec "Holdout split selectable"). Verify: unit tests for loading sets with and without holdout, and for rejecting an unknown split.
- [x] 1.4 Persist outcomes incrementally to `<output>/outcomes.jsonl`, keyed by (variant id, model, skill, query id, split), and resume by skipping persisted keys; the final `trigger-results.json` aggregates the file (D3). Verify: a test with a fake run function that raises after 3 of 6 queries, then re-invokes; it asserts 3 new executions and 6 outcomes in the result.
- [x] 1.5 Run queries with a worker pool of ≤ 2 (`--concurrency`, default 1, max 2), with thread-safe budget accounting (D4). Verify: unit test with a fake run function asserting max 2 in flight and correct totals; `--concurrency 3` is rejected.
- [x] 1.6 Add `--variant-root <dir>` to `trigger` (stage from `<dir>/plugins/rf-agentskills`; record `variant_root` and `variant_id` in the results) and `scripts/build-description-variant.py --candidates <yaml> --out <dir>` (D5). Verify: tests that the builder replaces only the listed descriptions (other files byte-identical), that the variant id is stable for identical input, and that `trigger --variant-root` records the root.
- [x] 1.7 Update `eval/triggers/README.md` and `docs/ci/usage.md` for `--tools`, the fixture, `holdout`, resume, concurrency and variants. Verify: `uv run pytest -q` (tests/eval) and `uv run pytest -q tests/ --ignore=tests/eval` pass; `uv run rf-skill-eval validate-tasks eval/tasks` and `coverage` pass.
- [x] 1.8 Add `trigger --listing-budget <chars>` (D14): set `SLASH_COMMAND_TOOL_CHAR_BUDGET` only when given, include the budget in the resume key and the results metadata, parse each session's `skill_listing` attachment, and record per run which rf-* descriptions were visible; report visibility counts per skill. Verify: unit tests with a recorded `session.jsonl` listing (3 descriptions visible, 9 by name only) and with two budgets in one output directory (separate keys).
- [x] 1.9 Keep candidate descriptions byte-exact in the variant builder (`load_candidates` must not collapse whitespace) (D14). Verify: a test that `Library    Browser` survives into the staged SKILL.md.
- [x] 1.10 Isolation checks report and never delete (D15, spec "Run isolation never deletes unrelated files"): attach violations to the run as an isolation error that marks it untrustworthy; delete nothing outside the workspace or artifacts directory; skip the repository snapshot for trigger profiles. Verify: tests for a concurrent file surviving a task run while being listed as a violation, a violation making the gate result not a pass, and no snapshot call for a trigger profile.

## 2. Re-baseline current descriptions

- [x] 2.1 Build a variant from the current descriptions (an empty candidates file, which yields an identical copy). Run `trigger --variant-root <it> --split train,validation --concurrency 2 --max-cost-usd 15` with output outside the repo. Verify: `trigger-results.json` covers all 12 skills on both splits with 0 incomplete queries. Copy it to `evidence/rebaseline.json` with a per-skill recall/accuracy table in `evidence/README.md`.
- [x] 2.2 From the re-baseline transcripts, write a short failure analysis per skill in `evidence/README.md`: the typical non-load behaviour (answered directly, Read a project file, Glob loop) and which query words were ignored. Verify: the section exists for all 12 skills and each entry cites at least 2 transcript examples by run id.

## 3. Description contract (tests)

- [x] 3.1 Update `tests/test_skill_descriptions.py` per D8:
  - accept both opening forms;
  - drop "this skill" from `META_RE`;
  - accept the `Use this skill when`/`whenever` clause;
  - add the keyword-catalog check (> 5 fails);
  - move the length warning to 600.

  Verify: new unit cases for each rule (accept imperative form, reject a 6-name catalog, reject "Guide AI agents"). The current 12 descriptions are then run through the new catalog check and any failure is recorded as a tuning target, not fixed yet. `uv run pytest -q tests/test_skill_descriptions.py` passes apart from those recorded failures, which are marked xfail with a reason.
- [x] 3.2 Update `tests/test_skill_descriptions.py` to the compact contract (D11, modified spec): ≤ 160 characters, combined listing lines ≤ 1700 (constant with a re-measure comment), RF or Robot Framework plus a library/tool/file term, a load cue starting "Use"/"Load", ≤ 2 keyword/API names, and a `## When to use` block within the first 20 body lines naming the required siblings (replacing the description-level sibling check). Verify: unit cases for each rule; the current 12 descriptions fail the length rule (expected, marked xfail(strict=True) until 6.1).

## 4. Tuning loop (train split only)

- [x] 4.1 Create `candidates/<skill>.yaml` for all 12 skills, with iteration 0 = the current description plus its re-baseline train numbers. Verify: the files exist and parse, and iteration 0 equals the current frontmatter text.
- [x] 4.2 Tune the four skills with 0 re-baseline validation loads first (rf-python-library, rf-results, rf-robotcode, rf-setup, per 2026-09 evidence; re-check after 2.1). For each skill:
  - run up to 5 iterations (D6/D7): write candidate → build variant → `trigger --skills <s> --split train --variant-root … --concurrency 2 --max-cost-usd 2` → record train loads and a rationale line;
  - stop early at train recall ≥ 0.9 with no should-not-trigger loads.

  Verify: each candidates file shows iterations with train numbers, and the kept candidate is the best train score.
- [x] 4.3 Tune the remaining eight skills the same way, lowest validation recall first. Verify: as in 4.2, and the running spend recorded in `evidence/README.md` stays ≤ $55 after this task.
- [x] 4.4 Write compact candidate set iteration 1 (all 12, D11) from the failure analysis and the rich tuning results, and draft each skill's `## When to use` body block from its selected rich candidate (D12), stored as `candidates/<skill>.yaml` fields `compact` and `when_to_use`. Verify: all compact texts pass the 3.2 rules offline (≤ 160 each, total ≤ 1700); the blocks name the required siblings.
- [x] 4.5 Tune the compact set together (D13): build one variant with all compact candidates, run `trigger --split train --concurrency 2 --max-cost-usd 9` under the default budget, record train loads and description visibility per skill, and revise; at most 3 iterations, selecting on summed train score with no loss of should-not-trigger accuracy. Verify: each iteration is recorded in the candidates files and evidence/README.md with spend, and every selected description was visible in 100% of its sessions.

## 5. Acceptance (combined validation run)

- [x] 5.1 (Revised: compact set, default listing budget.) Build one variant with every skill's best candidate. Run `trigger --variant-root … --split validation --concurrency 2 --max-cost-usd 12`. For each skill, apply rule (a) or (b) from the spec against the re-baseline, and revert any skill that fails to its current text. Verify: the per-skill decision table in `evidence/README.md` (recall and accuracy vs the re-baseline, the rule applied, accepted/reverted).
- [x] 5.3 Report the accepted compact set on the validation split with `--listing-budget 40000` (1M-context condition), not gating (`--max-cost-usd 7`). Verify: the table in evidence/README.md shows default vs 40000 per skill.
- [x] 5.2 If any skill was reverted or depends on a single query (recall change of exactly one query), rebuild the combined variant and repeat the validation run once (D6, Risks). Verify: the second run is recorded, the decisions are final, and no accepted skill's should-not-trigger accuracy is below its re-baseline.

## 6. Ship accepted descriptions

- [x] 6.1 Write the accepted compact descriptions and the `## When to use` body blocks into `skills/rf-*/SKILL.md` (line 3, JSON-quoted), run `bash scripts/sync-skills.sh`, and update the README skill table wording where it mirrors descriptions. Verify:
  - `bash scripts/check-drift.sh` passes;
  - `uv run python scripts/validate-skills.py --channel all` passes;
  - `uv run pytest -q tests/test_skill_descriptions.py` passes with no xfail left for accepted skills;
  - `uv build installer/` succeeds.
- [x] 6.2 Write `eval/baselines/triggers.json` from the accepted combined validation run (`baseline update`). It records the Claude Code and harness versions, the model and the variant id, plus a `shortfall` note per rule-(b) skill and `kept_current` per reverted skill (D10). Verify: `rf-skill-eval gate --trigger-results <run> --trigger-baseline eval/baselines/triggers.json` passes against its own source run.

## 7. Holdout and cross-model report

- [x] 7.1 Write 5 should-trigger and 5 should-not-trigger `holdout` queries per skill, after 6.1, in the users' voice. At least 2 of the should-not-trigger queries per skill are sibling near misses. Verify: `validate-tasks`/set loading passes, and each set has 10 holdout queries.
- [x] 7.2 Run the holdout split on the shipped descriptions (Haiku, 3 runs, `--max-cost-usd 10`), then the validation split on `claude-sonnet-5` with `--runs 1` (`--max-cost-usd 7`). Report both next to the validation results in `evidence/README.md`. Verify: the report table exists; both runs have 0 incomplete queries or record why.

## 8. Wrap-up

- [x] 8.1 Record the final numbers, total spend and follow-ups (routing hook, harder task evals, rf-mcp attachment, workspace venv pruning) in design.md "Implementation Notes". Add a CHANGELOG entry under the unreleased versions. Verify: `openspec validate tune-skill-descriptions --strict` passes; `uv run pytest -q` and `uv run pytest -q tests/ --ignore=tests/eval` pass.
