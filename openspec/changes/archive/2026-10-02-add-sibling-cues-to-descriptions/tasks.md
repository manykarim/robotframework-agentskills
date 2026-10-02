## 1. Harness and data

- [x] 1.1 Accept `holdout<N>` split names in `src/rf_skill_eval/domain/trigger.py` (regex, still optional and excluded from the ≥ 8/8 count), `--split` in `cli.py`, and one report column per holdout split that ran in `reporting/trigger_report.py` (D3). Verify: unit tests for loading, selecting `--split holdout2`, rejecting `holdoutX`/`hold2`, and the report column; `uv run pytest -q` passes.
- [x] 1.2 Retire the inspected holdout: move every `split: holdout` query in `eval/triggers/*.yaml` to `split: train`, keeping ids and adding `note: "retired holdout (2026-09-30 evidence)"` (D3). Verify: no `split: holdout` remains; trigger-set tests pass; `rf-skill-eval coverage` passes.
- [x] 1.3 Add `holdout2` queries (5 should-trigger + 5 should-not-trigger) to the sets of rf-appium, rf-selenium, rf-libdoc, rf-results, rf-setup and rf-robotcode. Write them fresh, not paraphrases of existing queries, with ≥ 3 sibling near-misses per set in the rf-setup / rf-robotcode direction (D3). Verify: each of the 6 sets has 10 `holdout2` queries; a duplicate check against all existing queries finds no near-identical text.

## 2. Budget re-measurement and contract

- [x] 2.1 Re-measure the listing room on the installed Claude Code: one default-budget trigger session per skill (validation, `--runs 1`), then compute the room per D1 from `session.jsonl`. Record it in `evidence/README.md` with the CC version and date. Verify: the room is reported for 12 sessions and they agree (±5 characters).
- [x] 2.2 Update `tests/test_skill_descriptions.py`:
  - sum description text against `floor(ROOM × 0.95)`, with `ROOM`, the CC version and the date as constants and the re-measure comment updated;
  - add the sibling-cue rule for rf-appium/rf-selenium → rf-setup and rf-libdoc/rf-results → rf-robotcode, marked `xfail(strict=True)` until 4.1.

  Verify: unit cases for the new counting and the cue rule; `uv run pytest -q tests/test_skill_descriptions.py` passes (with the strict xfails).

## 3. Measure and tune (Haiku 4.5, default budget, 3 runs/query, concurrency 2, outputs outside the repo)

- [x] 3.1 Pre-change run: train + validation for the 6 affected skills with the current texts (D4 step 1). Record per-skill numbers and the 4 targeted near-miss rates in `evidence/README.md`. Verify: 0 incomplete; the targeted near-misses are reproduced (rate ≥ 0.5) or the evidence says they were not.
- [x] 3.2 Tuning, at most 3 iterations: candidates in `candidates.yaml`, built with `scripts/build-description-variant.py`. Run the train split for the 6 skills with all 12 staged, and select by train score: targeted near-misses < 0.5, no recall loss, visibility 100% (D2, D4 step 2). Verify: each iteration is recorded with spend and visibility; every description is ≤ 160 characters and the total fits the 2.2 limit.

## 3b. Room 1423: trim all 12 (revision 2026-10-02)

- [x] 3.3 Re-measure the listing room as in 2.1 (≥ 50 default-budget sessions). Record the room, the CC version and the date. Update `LISTING_ROOM`, `LISTING_ROOM_CLAUDE_CODE` and `LISTING_ROOM_MEASURED` in `tests/test_skill_descriptions.py`. Verify: the sessions agree, and the test limit equals floor(room × 0.95).
- [x] 3.4 Trim tuning for all 12 skills (design D6), at most 3 iterations on train with all 12 staged. Each candidate set must pass the compact rules offline with a total ≤ the new limit and keep the four sibling cues. Select by train score with the targeted near-misses < 0.5 and visibility 100%. Verify: each iteration is recorded in candidates.yaml and evidence/README.md with texts, lengths, total, numbers and spend.
- [x] 3.5 Re-acceptance with the trimmed set: combined validation for all 12 (two runs, pooled), `holdout2` for the 6 skills, Sonnet 5 validation with `--runs 1`, and validation at 40000 (reported). Apply D6 step 5. Verify: a decision table against the stored baseline is in evidence/README.md, and visibility is 100% in every default-budget session.

## 4. Accept and ship

- [x] 4.1 Acceptance runs (D4 step 3): combined validation for all 12 skills, `holdout2` for the 6 skills, Sonnet 5 validation with `--runs 1`, and validation at `--listing-budget 40000`. Apply D4 step 4 per skill and pool a second validation run where a decision hinges on one query. Verify: a decision table in `evidence/README.md` compares against the stored baseline.
- [x] 4.2 Write the accepted descriptions to `skills/rf-*/SKILL.md` (line 3, JSON-quoted), remove the strict xfails, sync, and update the CHANGELOG entries. Verify:
  - `bash scripts/sync-skills.sh`, `bash scripts/check-drift.sh`, `uv run python scripts/validate-skills.py --channel all`, `uv run pytest -q` and `uv run pytest -q tests/ --ignore=tests/eval` all pass;
  - `uv build installer/` succeeds.
- [x] 4.3 Update `eval/baselines/triggers.json` from the acceptance validation run (`baseline update` into a scratch dir, then copy `triggers.json` only). Verify: `rf-skill-eval gate --trigger-results <run> --trigger-baseline eval/baselines/triggers.json` passes.
