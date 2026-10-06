## Context

See proposal.md for the five recorded near-miss loads.

**Current state (main at 89e7edd):**
- Descriptions are listing lines of 136–143 characters each; the 12 lines total 1686 of the test's 1700 cap.
- The cap counts whole `- <name>: <description>` lines.
- The room measured on 2026-09-29 (Claude Code 2.1.284, Haiku, default budget 8000) was 1734 characters of *description text*: the bundled skills plus every `- <name>` prefix took 6266.
- Today's description text alone is about 1520 characters, so about 200 characters are unused, but the test can't see that.

**Harness.**
- The split type is `Literal["train", "validation", "holdout"]` in `src/rf_skill_eval/domain/trigger.py`.
- The report adds a Holdout column only when holdout queries ran (`reporting/trigger_report.py`).
- `--split` accepts train, validation and holdout.

**Stored acceptance results** (`eval/baselines/triggers.json`, pooled validation):
- rf-appium, rf-selenium, rf-libdoc and rf-results are at 1.00 recall.
- rf-robotcode is at 0.75 (rule b).
- rf-setup is at 1.00.

## Goals / Non-Goals

**Goals:**
- The recorded near-misses (moved to train) stop triggering the wrong skill.
- No recall loss for the edited skills or their named siblings, and every description stays visible.
- The combined-budget rule matches what Claude Code actually counts.

**Non-Goals:**
- Retuning the other eight descriptions.
- Changing `## When to use` blocks.
- The Sonnet false positive on a non-RF Selenium Grid request (`se-n09`) is reported, not targeted. It is a single run on a model that is not the tuning target.

## Decisions

### D1. Re-measure the room, count description text

Run one default-budget trigger session per skill on Claude Code 2.1.285, then read `skill_listing` from `session.jsonl`:

room = 8000 − (listing length − Σ len(": " + description) over the shown rf-* descriptions)

The test then sums description text, not whole lines, against `ROOM × 0.95` (floored). `ROOM`, the Claude Code version and the date are constants with a re-measure comment.
- *Rejected alternative:* raising the whole-line cap by hand. It would stay disconnected from the measurement.

### D2. Cue wording, shortest form that names signal and sibling

Draft cues, each appended to the existing description:

| Skill | Draft cue | Length |
|---|---|---|
| rf-appium | `Installs, drivers: rf-setup.` | ~28 |
| rf-selenium | `Installs, drivers: rf-setup.` | ~28 |
| rf-libdoc | `With robotcode: rf-robotcode.` | ~29 |
| rf-results | `With robotcode: rf-robotcode.` | ~29 |

If a description would go past 160 characters, shorten its capability list first (for example drop "gestures" or "Grid"). The load cue "Use first, before …" is never shortened, because it was the strongest lever in the tuning run. Candidates are tuned on train (D4). The final wording is chosen by train score, not by this draft.

### D3. Retire the inspected holdout; add `holdout2`

- All 12 sets' `holdout` queries were inspected in the 2026-09-30 evidence, so they move to `train`, keeping their ids and notes. This also puts the 4 targeted near-misses into train, where they are allowed to steer tuning.
- `holdout2` gets fresh queries for the 6 affected skills (rf-appium, rf-selenium, rf-libdoc, rf-results, rf-setup, rf-robotcode): 5 should-trigger and 5 should-not-trigger each, at least 3 of the negatives being sibling near-misses in the rf-setup / rf-robotcode direction.
- The harness accepts `holdout<N>` split names (a regex instead of the fixed Literal), and the report adds one column per holdout split that ran.

### D4. Measurement plan (Haiku 4.5, default budget, 3 runs per query, concurrency 2)

1. **Pre-change:** train (incl. moved holdout) + validation for the 6 affected skills, all current texts staged. This is the comparison point.
2. **Tuning:** at most 3 iterations on train, all 12 skills staged. Candidates change only the 4 edited descriptions.
3. **Acceptance:**
   - one combined validation run of all 12 skills;
   - holdout2 for the 6 skills;
   - a Sonnet 5 validation pass with 1 run per query (reported only);
   - a 40000-budget validation pass (reported only).
4. **Accept** when all of the following hold:
   - the 4 targeted train near-misses have a rate < 0.5;
   - validation recall of the 4 edited skills and of rf-setup and rf-robotcode is not below the stored baseline;
   - should-not-trigger accuracy is not below it;
   - visibility is 100%.

   If one skill fails, it keeps its current text, and the result is recorded.

### D5. Baseline and CI

- `eval/baselines/triggers.json` is updated from the acceptance validation run (validation split, gate reference).
- The PR trigger gate runs automatically, because the descriptions change.

## Risks / Trade-offs

- **Cues can steal recall.** "With robotcode: rf-robotcode" might make the model skip rf-libdoc when robotcode is merely mentioned. → Sibling recall is part of acceptance, and the validation sets contain robotcode-free positives.
- **The room can shrink** when Claude Code adds bundled skills. → The test records the version, and the re-measure procedure is documented. A shrinking room shows up in the visibility table of every trigger run.
- **Small sets:** 4 validation positives per skill. → Pooling as in `tune-skill-descriptions`: a second validation run whenever a decision hinges on one query.

## Revision 2026-10-01 (after task 2.1)

**Measured room.** On Claude Code 2.1.285/2.1.286 the room is **1600**, not about 1900. The proposal's "about 200 spare characters" assumed the 2026-09-29 room of 1734, and newer Claude Code versions take more space for bundled skills. Current description text uses **1528**, and the 95% limit is 1520.

**D2 revised (user decision).** The cues are paid for by trimming the four edited descriptions (rf-appium, rf-selenium, rf-libdoc, rf-results). Their capability lists give way to the cue, while the load cue "Use first, before …", Robot Framework, and the library/tool name stay. The other eight descriptions are untouched.
- The target total is ≤ 1520 (95% of 1600), so the four must shrink by at least 8 characters net while gaining their cues.
- Expected per-skill length: about 115–125 characters of listing text.

**Split-ratio rule (task 1.2).** The 60/40 train/validation ratio check now leaves out queries noted "retired holdout". The alternative was loosening the bound. Retired queries are extra training material and don't change the original split design.

## Implementation Notes

**Session packing (tasks 3.1–4.1).** Each trigger session takes about 4 MB on disk, about 1.4 MB once its `claude_config` folder is removed. There was too little free disk to keep every session unpacked. After each finished run, `claude_config` is removed and the remaining session folders (transcripts `session.jsonl`, `stdout.stream.jsonl`, the staged workspace) are packed into `<run>/sessions.tar.gz`. The archive is listed before the folders are removed. `trigger-results.json`, `outcomes.jsonl` and `trigger-report.md` stay unpacked. No transcript is lost. Run outputs stay in the session scratchpad, not in the repo.

**Visibility limitation (iteration 1).** In 1 of 414 iteration-1 train sessions (`rs-h06`), Claude Code's listing carried an extra bundled skill (`plugin-authoring`, about 180 characters). That shrank the room to 1423 for that session, and rf-setup, the last rf-* skill alphabetically, was listed by name only (visibility 413/414). The 5% margin (80 characters) cannot absorb a bundled skill that appears in some sessions only. This is recorded as a known limitation. It is Claude Code rollout variance, not a property of the candidate texts, and shows up in the visibility table of every trigger run. Selection treats a session like this as noise when every other session shows all 12 descriptions.

**Iteration 3 pooled (task 3.2).** D4 allows at most 3 tuning iterations. Iteration 3's set was run on train twice and pooled (6 runs per query), because its first run disagreed with iteration 2 for an identical text (`ap-h07` 0/3 in it2, 2/3 in it3). This is not a fourth candidate. Selection reads the pooled numbers. `rc-n04` (rf-robotcode, text unchanged) pooled exactly at the 0.5 threshold. It is recorded as borderline variance, because the same query varied between 0/3 and 2/3 across runs, and rf-robotcode's should-not-trigger accuracy is gated on validation in 4.1.

**Cue wording.** The final cues differ from the D2 draft.
- rf-appium and rf-selenium use the exclusion form "Not installs/drivers: rf-setup." The draft "Installs, drivers: rf-setup." pulled install queries into the library skills and cost rf-setup recall.
- rf-results uses the directive "With robotcode installed, use rf-robotcode."
- rf-libdoc keeps the draft "With robotcode: rf-robotcode."
- Capability lists were dropped to fit the budget:
  - rf-appium: "Android/iOS, locators, gestures";
  - rf-selenium: "(WebDriver): locators, waits, Grid";
  - rf-libdoc: "or 'No keyword with name' errors";
  - rf-results: "yourself", "explain", "(output.xml, rebot)" and "run".

**Room change during acceptance (task 4.1).**
- From about 17:16 UTC on 2026-10-01, every Haiku session listed the bundled `plugin-authoring` skill, still on Claude Code 2.1.286.
- The rf-* room fell from 1600 to 1423, and rf-setup, which sorts last, lost its description:
  - in the second validation run (0/297 sessions);
  - in most of holdout2 (67/180 sessions; none of rf-setup's own 30 sessions showed it).
- Acceptance is decided on the first validation run, in which all 12 descriptions were shown in every session. The second run is used only to pool rf-libdoc, whose decision hinged on `ld-v01`.
- The 1520 limit (95% of 1600) therefore no longer guarantees visibility. Before task 4.2 ships, the room must be re-measured (task 2.1 procedure) and the user must decide how to fit it. The options are in evidence/README.md under "Blocker for task 4.2".

## Revision 2026-10-02: room 1423, trim all 12 (user decision)

**What changed.** From about 2026-10-01 17:16 UTC, Claude Code 2.1.286 lists the built-in `plugin-authoring` skill in every Haiku session. The room for rf-* descriptions fell from 1600 to **1423**:
- rf-setup, which sorts last, is now listed by name only. This already applies to the descriptions shipped on main (1528).
- In those sessions rf-setup's validation recall fell to 0.25.

**Decision (user, 2026-10-02).** Trim all 12 descriptions so that the total is ≤ `floor(ROOM × 0.95)`, then re-accept. This supersedes the non-goal "retuning the other eight descriptions".

**D6. Trim strategy.**
1. Re-measure the room first, because it moved twice in three days.
2. The target total is ≤ 1351 with ROOM = 1423, or 95% of whatever the re-measurement gives. The selected texts total 1520, so about 170 characters have to go.
3. Trim levers, in order of expected risk:
   1. shorten capability lists to the one or two terms that carry intent;
   2. shorten the shared preamble "Use first, before exploring or answering," (7 skills) to a shorter form that keeps "Use first" and "before …";
   3. "Robot Framework" → "RF" only if needed.

   The four accepted sibling cues stay, with wording changed only if needed.
4. Tuning: at most 3 iterations on train for all 12 skills, staged together. The four targeted near-misses must stay below 0.5.
5. Acceptance: combined validation of all 12 skills, pooled across two runs, with visibility at 100% at the measured room; `holdout2` for the 6 skills; the Sonnet and 40000-budget passes reported only.
   - Every skill's validation recall must be ≥ the stored baseline (eval/baselines/triggers.json acceptance), except where the stored value came from a run in which the skill was not visible.
   - Should-not-trigger accuracy must not drop.

**D7. Known limitation.** The room depends on Claude Code's bundled-skill set and on the user's own skills. The skill that sorts last loses its description first. The test constant records the version and date, and `rf-skill-eval trigger` reports visibility per skill, so a shrinking room shows up in every trigger run.

**Trim tuning (tasks 3.3–3.4).**
- The re-measured room is 1423 in 99/99 sessions (Claude Code 2.1.286, `plugin-authoring` listed in every session), so the limit is 1351.
- Three iterations were run on train for all 12 skills; iteration 3 ran twice and was pooled.
- No iteration met every criterion as a whole:
  - iteration 1 lost rf-robotcode recall (REPL);
  - iteration 2 swung on rf-language (noise);
  - iteration 3 added `ri-h07`.
- The selected set therefore takes each skill's text from the iteration where that text scored best. This is the per-skill selection used in tune-skill-descriptions. Every chosen text was measured on train with all 12 staged.
- The assembled set (1348) was not itself run on train. Its first combined measurement is the 3.5 acceptance validation.
- A 6-skill reference train run of the pre-trim texts at room 1423 (`ref6-train`) was added for the 6 skills that had no train numbers in this change.

### Shipping (tasks 4.2, 4.3; 2026-10-02)

- **Descriptions shipped.** The 12 accepted texts (variant `e8dcbb109c1b`, total 1348 ≤ 1351) are on line 3 of each SKILL.md. `CUES_PENDING` is emptied and `LISTING_OVER_PENDING` is False.
- **`eval/baselines/triggers.json`** is built from the acceptance run `s-val`. The per-skill `acceptance` entries carry the recall pooled over `s-val` and `s-val-r2`, plus `listing_room: 1423` and Claude Code 2.1.286.
- **Gate fix.** The trigger gate falsely failed a one-query accuracy drop: the stored rate is rounded to 4 decimals, so 9/11 = 0.8182 against 8/11 exceeded the 1/11 allowance by 0.00002.
  - `application/gate.py` now compares correct-query counts (tp + tn) when the stored entry has them, and otherwise falls back to the rate with a 5e-4 rounding epsilon.
  - Regression tests are in `tests/eval/test_baseline_gate.py`.
  - Before the fix, the second acceptance run (`s-val-r2`) failed the gate on rf-language (3/6 vs 4/6). It passes now.
