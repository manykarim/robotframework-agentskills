# Evidence: add-sibling-cues-to-descriptions

## 2.1 Listing room re-measurement (2026-10-01)

- **Run:** `rf-skill-eval trigger --split validation --runs 1 --concurrency 2` under the default budget with `claude-haiku-4-5-20251001`. That gave 99 sessions on Claude Code 2.1.285 and 2.1.286 (the CLI updated during the run).
- **Room:** 8000 − (listing length − Σ len(": " + description) over the shown rf-* descriptions) = **1600 in all 99 sessions**. All 12 rf-* descriptions were visible in every session.
- **Compared with 2026-09-29:** the room was 1734 then (Claude Code 2.1.284), so newer versions take 134 more characters for bundled skills and names.
- **Current usage:** Σ len(": " + description) = **1528**, which is 72 below the room and 8 above the 95% limit (1520).
- **Consequence:** the ~112 characters of cues in design D2 cannot simply be added. Per the user decision (2026-10-01), they are paid for by trimming the four edited descriptions; see design.md "Revision".

## 3.1 Pre-change run (2026-10-01)

- **Setup:** current texts staged as an identical variant (`7cfa7e52981c`, same id as the 2.1 run), Claude Code 2.1.286, `claude-haiku-4-5-20251001`, default listing budget, 3 runs per query, concurrency 2. Skills: rf-appium, rf-selenium, rf-libdoc, rf-results, rf-setup, rf-robotcode. Outputs in the session scratchpad (`cues/pre-train`, `cues/pre-val`), not in the repo.
- **Spend:** train $10.65 (414 sessions), validation $3.63 (144 sessions). 0 incomplete.
- **Visibility:** all 12 rf-* descriptions shown in 414/414 (train) and 144/144 (validation) sessions.

| Skill | Train TP/FP/TN/FN | Train recall | Train neg acc | Val TP/FP/TN/FN | Val recall | Val neg acc |
|---|---|---|---|---|---|---|
| rf-appium | 12/1/10/0 | 1.00 | 0.91 | 4/0/4/0 | 1.00 | 1.00 |
| rf-selenium | 12/1/10/0 | 1.00 | 0.91 | 4/0/4/0 | 1.00 | 1.00 |
| rf-libdoc | 9/1/10/3 | 0.75 | 0.91 | 4/0/4/0 | 1.00 | 1.00 |
| rf-results | 9/1/10/3 | 0.75 | 0.91 | 4/0/4/0 | 1.00 | 1.00 |
| rf-setup | 12/1/10/0 | 1.00 | 0.91 | 4/0/4/0 | 1.00 | 1.00 |
| rf-robotcode | 11/0/11/1 | 0.92 | 1.00 | 3/0/4/1 | 0.75 | 1.00 |

**Targeted near-misses (train, loads/runs of the wrong skill): all four reproduced (rate ≥ 0.5).**

| Query | Wrong skill | Rate |
|---|---|---|
| `ap-h07` | rf-appium | 3/3 = 1.00 |
| `se-h08` | rf-selenium | 3/3 = 1.00 |
| `ld-h06` | rf-libdoc | 2/3 = 0.67 |
| `rs-h06` | rf-results | 2/3 = 0.67 |

Other failing train queries (the comparison point for "no recall loss"):
- rf-libdoc positives `ld-h04`, `ld-t01` (rf-browser / rf-selenium loaded instead) and `ld-t05`: 0/3 each.
- rf-results positives `rs-h01`, `rs-h05` and `rs-t06`: 0/3 each.
- rf-robotcode positive `rc-t03` (robot-debug): 0/3.
- rf-setup negative `su-n01` (Browser login test): 2/3.

Failing validation query: rf-robotcode `rc-v02` (robotcode results diff) at 1/3.

## 3.2 Tuning (2026-10-01)

**Setup.** Same harness, model and budget as 3.1. All 12 skills were staged, and only the 4 edited descriptions changed. Each run covered the train split of the 6 skills (414 sessions). Every candidate set passed the compact rules and the 1520 total offline before it ran. Full texts and per-iteration notes are in `candidates.yaml`.

| Iteration | rf-appium | rf-selenium | rf-libdoc | rf-results | Total |
|---|---|---|---|---|---|
| pre-change | 127 | 128 | 128 | 126 | 1528 |
| 1 | 128 `Installs, drivers: rf-setup.` | 122 (same cue) | 124 `With robotcode: rf-robotcode.` | 127 (same cue) | 1520 |
| 2 | 126 `Not installs/drivers: rf-setup.` | 125 (same cue) | 124 (it1) | 126 `Not via robotcode: rf-robotcode.` | 1520 |
| 3 | 126 (it2) | 125 (it2) | 124 (it1) | 126 `With robotcode installed, use rf-robotcode.` | 1520 |

Train TP/FP/TN/FN:

| Skill | pre-change | it1 | it2 | it3 run 1 | it3 run 2 | it3 pooled (6 runs) |
|---|---|---|---|---|---|---|
| rf-appium | 12/1/10/0 | 12/2/9/0 | 12/0/11/0 | 12/1/10/0 | 12/0/11/0 | 12/0/11/0 |
| rf-selenium | 12/1/10/0 | 12/1/10/0 | 12/0/11/0 | 12/0/11/0 | 11/0/11/1 | 12/0/11/0 |
| rf-libdoc | 9/1/10/3 | 11/0/11/1 | 11/0/11/1 | 10/0/11/2 | 9/0/11/3 | 10/0/11/2 |
| rf-results | 9/1/10/3 | 11/1/10/1 | 9/1/10/3 | 9/0/11/3 | 10/0/11/2 | 11/0/11/1 |
| rf-setup | 12/1/10/0 | 10/0/11/2 | 12/0/11/0 | 12/0/11/0 | 12/0/11/0 | 12/0/11/0 |
| rf-robotcode | 11/0/11/1 | 12/0/11/0 | 11/0/11/1 | 9/0/11/3 | 11/1/10/1 | 11/1/10/1 |

Targeted near-misses (loads of the wrong skill / runs):

| Query | pre | it1 | it2 | it3 run 1 | it3 run 2 | it3 pooled |
|---|---|---|---|---|---|---|
| `ap-h07` rf-appium | 3/3 | 2/3 | 0/3 | 2/3 | 0/3 | **2/6** |
| `se-h08` rf-selenium | 3/3 | 0/3 | 0/3 | 1/3 | 1/3 | **2/6** |
| `ld-h06` rf-libdoc | 2/3 | 0/3 | 0/3 | 1/3 | 1/3 | **2/6** |
| `rs-h06` rf-results | 2/3 | 3/3 | 2/3 | 0/3 | 1/3 | **1/6** |

Visibility and spend:

| Run | Visibility | Spend |
|---|---|---|
| it1 | 413/414 for rf-setup (one session with an extra bundled skill, see design.md Implementation Notes); 414/414 for the others | $10.81 |
| it2 | 414/414 all 12 | $10.52 |
| it3 run 1 | 414/414 all 12 | $10.74 |
| it3 run 2 | 414/414 all 12 | $10.76 |

**Findings.**
- **Iteration 1.** The "Installs, drivers: rf-setup." wording read as a capability.
  - rf-appium took `ap-n03` (2/3) and rf-selenium took `se-h07` (2/3).
  - rf-setup recall fell from 12/12 to 10/12 (`su-h02` and `su-t05` went to rf-appium and rf-browser).
  - `ap-h07` stayed at 2/3 and `rs-h06` rose to 3/3. Rejected.
- **Iteration 2.** The exclusion form "Not installs/drivers: rf-setup." fixed rf-appium and rf-selenium: near-misses 0/3, no should-not-trigger loads, and rf-setup back to 12/12. The libdoc cue held. The rf-results exclusion cue did not: `rs-h06` was 2/3. Rejected as a set.
- **Iteration 3.** Only rf-results changed, to a directive cue. On the first run, `ap-h07` (2/3) disagreed with iteration 2 for the identical rf-appium text (0/3), so per the pooling rule the set was run a second time. Pooled over 6 runs:
  - all four targeted near-misses are below 0.5;
  - train recall is at or above pre-change for all 6 skills;
  - the 4 edited skills have 0 should-not-trigger loads (1 each pre-change);
  - visibility is 100%.
- **Caveat.** `rc-n04` (rf-robotcode, text unchanged) pooled 3/6 = 0.50, which is exactly the threshold. Across runs it went 0/3, 0/3, 1/3, 1/3 and 2/3. This is in line with the variance of other negatives (`ap-n03` went 1, 2, 0, 0, 1; `su-n01` went 2, 0, 0, 0, 0), so it is recorded as borderline and checked again on validation.

**Selected: iteration 3** (total 1520).

## 4.1 Acceptance (2026-10-01, selected set = iteration 3, variant `f7eb140ac494`)

**Selected texts** (the other 8 descriptions are unchanged; total Σ len(": " + d) = **1520** ≤ 1520):

| Skill | Length | Text |
|---|---|---|
| rf-appium | 126 | Use first, before exploring or answering, for Robot Framework mobile tests with AppiumLibrary. Not installs/drivers: rf-setup. |
| rf-selenium | 125 | Use first, before exploring or answering, for Robot Framework web tests with SeleniumLibrary. Not installs/drivers: rf-setup. |
| rf-libdoc | 124 | Use first, not memory, for exact Robot Framework keyword names, arguments and docs via libdoc. With robotcode: rf-robotcode. |
| rf-results | 126 | Use first, before reading output.xml, to summarise, merge Robot Framework results. With robotcode installed, use rf-robotcode. |

**Runs.** All runs used Claude Code 2.1.286, concurrency 2, 0 incomplete.

| Run | Model / budget | Runs/query | Sessions | Visibility | Spend |
|---|---|---|---|---|---|
| Validation, all 12 (`acc-val`) | Haiku, default | 3 | 297 | **297/297 all 12** | $7.52 |
| Validation repeat, all 12 (`acc-val-r2`) | Haiku, default | 3 | 297 | **rf-setup 0/297**, others 297/297 | $7.45 |
| holdout2, 6 skills (`acc-h2`) | Haiku, default | 3 | 180 | **rf-setup 67/180**, others 180/180 | $4.84 |
| Validation, all 12 (`acc-sonnet`) | `claude-sonnet-5`, default | 1 | 99 | 99/99 all 12 | $6.79 |
| Validation, all 12 (`acc-40k`) | Haiku, `--listing-budget 40000` | 3 | 297 | 297/297 all 12 | $7.48 |

### Claude Code change during the acceptance runs: the room dropped to 1423

From about 17:16 UTC on 2026-10-01, every Haiku session's skill listing carried an extra bundled skill, `plugin-authoring`. It was first seen in 1 of 414 iteration-1 sessions; see design.md Implementation Notes.
- The room for rf-* descriptions fell from 1600 to **1423**.
- rf-setup sorts last and was listed by name only:
  - holdout2: 113 of 180 sessions, all 30 rf-setup sessions included (0/30);
  - validation repeat: all 297 sessions.
- `acc-val` finished before the change and showed all 12 descriptions in every session.
- The Claude Code version did not change (2.1.286), so this is a server-side rollout.
- It does not depend on the candidate: the pre-change texts (1528) lose rf-setup at a room of 1423 in the same way.
- The effect is large. With rf-setup invisible:
  - rf-setup validation recall fell from 4/4 to 1/4 (`su-v01` 1/3, `su-v02` 0/3, `su-v04` 1/3);
  - rf-requests took `rq-n08` ("Install RequestsLibrary into our Poetry-managed RF project") at 2/3;
  - holdout2 rf-setup recall was 3/5.

### Validation, per skill

| Skill | Stored baseline (pooled recall / val recall / neg acc) | Pre-change 3.1 | `acc-val` TP/FP/TN/FN | `acc-val-r2` | Pooled (6 runs) | Sonnet 5 (1 run) | 40k |
|---|---|---|---|---|---|---|---|
| rf-appium | 1.00 / 1.00 / 1.00 | 4/0/4/0 | 4/0/4/0 | 4/0/4/0 | 4/0/4/0 | 4/0/4/0 | 4/0/4/0 |
| rf-selenium | 1.00 / 1.00 / 1.00 | 4/0/4/0 | 4/0/4/0 | 4/0/4/0 | 4/0/4/0 | 4/0/4/0 | 4/0/4/0 |
| rf-libdoc | 1.00 / 0.75 / 1.00 | 4/0/4/0 | 3/0/4/1 (`ld-v01` 1/3) | 4/0/4/0 (`ld-v01` 3/3) | 4/0/4/0 (`ld-v01` 4/6) | 4/0/4/0 | 4/0/4/0 |
| rf-results | 1.00 / 1.00 / 1.00 | 4/0/4/0 | 4/0/4/0 | 4/0/4/0 | 4/0/4/0 | 4/0/4/0 | 4/0/4/0 |
| rf-setup | 1.00 / 1.00 / 1.00 | 4/0/4/0 | 4/0/4/0 | 1/0/4/3 (not visible) | 3/0/4/1 (mixed visibility) | 4/1/3/0 (`su-n09`, non-RF Node.js) | 3/0/4/1 (`su-v02` 1/3) |
| rf-robotcode | 0.75 / 0.75 / 1.00 | 3/0/4/1 | 4/0/4/0 | 4/0/4/0 | 4/0/4/0 | 4/0/4/0 | 4/0/4/0 |
| rf-browser | 0.75 / 0.75 / 1.00 | – | 3/0/4/1 | 3/0/4/1 | 3/0/4/1 | 4/0/4/0 | 4/0/4/0 |
| rf-language | 0.50 / 0.50 / 1.00 | – | 4/0/5/2 | 3/0/5/3 | 4/0/5/2 | 6/0/5/0 | 4/0/5/2 |
| rf-platynui | 1.00 / 1.00 / 1.00 | – | 4/0/4/0 | 4/0/4/0 | 4/0/4/0 | 4/0/4/0 | 4/0/4/0 |
| rf-python-library | 0.75 / 0.50 / 1.00 | – | 2/0/4/2 | 3/0/4/1 | 3/0/4/1 | 4/0/4/0 | 3/0/4/1 |
| rf-requests | 1.00 / 1.00 / 1.00 | – | 4/0/4/0 | 4/1/3/0 (`rq-n08`, rf-setup invisible) | 4/0/4/0 | 4/0/4/0 | 4/0/4/0 |
| rf-restinstance | 0.75 / 0.75 / 1.00 | – | 4/0/4/0 | 4/0/4/0 | 4/0/4/0 | 4/0/4/0 | 3/0/4/1 |

The Sonnet 5 false positive `se-n09` from the proposal did not recur (rf-selenium 4/0/4/0). Sonnet's listing showed all 12 descriptions.

### holdout2 (6 skills, reported, not gating)

| Skill | TP/FP/TN/FN | Recall | Neg acc | Note |
|---|---|---|---|---|
| rf-appium | 5/0/5/0 | 1.00 | 1.00 | |
| rf-selenium | 5/0/5/0 | 1.00 | 1.00 | |
| rf-libdoc | 5/0/5/0 | 1.00 | 1.00 | |
| rf-results | 4/0/5/1 | 0.80 | 1.00 | `rs-k03` (shrink a 300 MB log.html) 1/3 |
| rf-robotcode | 5/0/5/0 | 1.00 | 1.00 | |
| rf-setup | 3/0/5/2 | 0.60 | 1.00 | rf-setup not visible in any of its 30 sessions; `su-k04` 0/3, `su-k05` 0/3 (rf-appium loaded) |

All holdout2 should-not-trigger queries, including the sibling near-misses, stayed below the 0.5 rate (should-not-trigger accuracy 1.00 for all 6).

### Decision (design D4 step 4 + spec "Near-miss fixes")

| Skill | Near-miss (train, it3 pooled) < 0.5 | Validation recall ≥ stored baseline | Neg acc ≥ stored | Visibility 100% | Decision |
|---|---|---|---|---|---|
| rf-appium | `ap-h07` 2/6 = 0.33 ✓ | 1.00 ≥ 1.00 ✓ | 1.00 ✓ | ✓ (all runs) | **accepted** |
| rf-selenium | `se-h08` 2/6 = 0.33 ✓ | 1.00 ≥ 1.00 ✓ | 1.00 ✓ | ✓ | **accepted** |
| rf-libdoc | `ld-h06` 2/6 = 0.33 ✓ | `acc-val` 0.75; it hinges on `ld-v01`, so pooled with `acc-val-r2`: 1.00 ≥ 1.00 ✓ | 1.00 ✓ | ✓ | **accepted** (pooled) |
| rf-results | `rs-h06` 1/6 = 0.17 ✓ | 1.00 ≥ 1.00 ✓ | 1.00 ✓ | ✓ | **accepted** |
| rf-setup (sibling, unchanged) | – | `acc-val` 1.00 ≥ 1.00 ✓ (the only run with rf-setup visible) | 1.00 ✓ | ✓ in `acc-val`; ✗ in `acc-val-r2` and holdout2 (Claude Code room change, see above) | **protected under the gating run**; the visibility shortfall is caused by Claude Code, not by the cues |
| rf-robotcode (sibling, unchanged) | – | 1.00 ≥ 0.75 ✓ | 1.00 ✓ | ✓ | **protected** |

**Outcome.**
- All 4 edited skills are accepted with the iteration-3 texts, so no skill keeps its current text.
- The total stays at 1520 against the 1520 limit.

**Blocker for task 4.2 (needs a user decision).** The 1520 limit was derived from a room of 1600. Since the `plugin-authoring` rollout the room is 1423 in every Haiku session, so a total of 1520 hides rf-setup. This holds equally for the shipped pre-change texts (1528).
- **Minimal fix:** to make all 12 descriptions visible again, the total must drop to ≤ 1423, which means cutting 97 characters.
- **Fix with margin:** re-measuring per D1 and keeping the 5% margin gives ≤ 1351, which means cutting 169 characters.
- **Not feasible within this change's scope:** trimming only the 4 edited descriptions. That would leave them around 85–100 characters each and remove most of what makes them trigger.
- **Options:**
  - (a) re-run 2.1, set `LISTING_ROOM = 1423`, and trim all 12 descriptions by about 8–14 characters each, then re-accept;
  - (b) ship as is and record that rf-setup loses its description whenever `plugin-authoring` is bundled;
  - (c) rename or reorder so that the skill that drops is the least harmful one. Claude Code fills alphabetically, so the last-sorted skill is always the one that loses.

## 3.3 Listing room re-measurement (2026-10-02)

- **Run:** `rf-skill-eval trigger --split validation --runs 1 --concurrency 2`, all 12 skills, shipped texts (variant `7cfa7e52981c`), default budget, `claude-haiku-4-5-20251001`. That gave 99 sessions, all on Claude Code **2.1.286**. Spend $2.48. Output: scratchpad `cues/room2`.
- **Room:** 8000 − (listing length − Σ len(": " + description) over the shown rf-* descriptions) = **1423 in all 99 sessions**.
- **`plugin-authoring`:** the bundled skill was listed in **99/99** sessions. The shipped total of 1528 > 1423 leaves rf-setup listed by name only in all 99 sessions (visibility 0/99).
- **Test constants updated:**
  - `LISTING_ROOM = 1423`, `LISTING_ROOM_CLAUDE_CODE = "2.1.286"`, `LISTING_ROOM_MEASURED = "2026-10-02"`;
  - `MAX_DESCRIPTION_TEXT` = floor(1423 × 0.95) = **1351**.
  - `test_contract_constants` and `test_combined_listing_budget` were adjusted to the new numbers, still with one total under and one over the limit.
  - `uv run pytest -q tests/test_skill_descriptions.py`: 82 passed, 5 xfailed. `LISTING_OVER_PENDING` and `CUES_PENDING` are untouched (task 4.2).

## 3.4 Trim tuning, all 12 skills (2026-10-02)

**Setup.**
- Room 1423, limit 1351. Haiku 4.5, Claude Code 2.1.286, default budget, 3 runs per query, concurrency 2.
- All 12 trimmed texts were staged and run on the train split of all 12 skills: 277 queries, 831 sessions per run.
- Every set passed the compact rules, the sibling-cue rule and the new 1351 limit offline before it ran.
- Full texts are in `candidates.yaml` (`trim_iterations`, `trim_selected`).

**Iterations.**

| Iteration | Change | Total |
|---|---|---|
| 1 (`d2a1ff1f8713`) | D6 levers 1 and 2: capability lists cut to 1–2 terms; "before exploring or answering" → "before answering" (7 skills); cues kept; "Robot Framework" kept. rf-setup drops "Not for writing tests.", rf-robotcode drops "REPL". | 1338 |
| 2 (`5095b114b78b`) | "REPL" restored in rf-robotcode. | 1344 |
| 3 (`8125b869eba0`, run twice, pooled) | "tag runs" restored (rf-language), "JSON types" restored (rf-restinstance); paid for by rf-setup "(uv, pip)" and rf-platynui "desktop tests". | 1350 |

**Reference.**
- rf-appium, rf-selenium, rf-libdoc, rf-results, rf-setup and rf-robotcode: the cue-tuning iteration-3 pooled result (room 1600).
- The other 6 skills: `ref6-train` with their pre-trim texts at room 1423 ($11.03). rf-setup was invisible in that run, so the install-type negatives loaded the library skills there.

Train TP/FP/TN/FN:

| Skill | Reference | Trim 1 | Trim 2 | Trim 3 pooled (6 runs) |
|---|---|---|---|---|
| rf-appium | 12/0/11/0 | 12/0/11/0 | 12/0/11/0 | 12/0/11/0 |
| rf-browser | 12/2/9/0 | 12/0/11/0 | 12/0/11/0 | 12/0/11/0 |
| rf-language | 12/0/12/1 | 12/0/12/1 | 9/0/12/4 | 12/0/12/1 |
| rf-libdoc | 10/0/11/2 | 10/0/11/2 | 10/0/11/2 | 9/0/11/3 |
| rf-platynui | 12/2/9/0 | 12/0/11/0 | 12/0/11/0 | 12/0/11/0 |
| rf-python-library | 11/0/11/0 | 11/0/11/0 | 11/0/11/0 | 11/0/11/0 |
| rf-requests | 12/1/10/0 | 12/0/11/0 | 12/0/11/0 | 12/0/11/0 |
| rf-restinstance | 12/0/11/0 | 11/0/11/1 | 11/0/11/1 | 12/1/10/0 |
| rf-results | 11/0/11/1 | 12/0/11/0 | 12/0/11/0 | 12/0/11/0 |
| rf-robotcode | 11/1/10/1 | 9/0/11/3 | 10/0/11/2 | 11/1/10/1 |
| rf-selenium | 12/0/11/0 | 12/0/11/0 | 12/1/10/0 | 12/1/10/0 |
| rf-setup | 12/0/11/0 | 12/0/11/0 | 12/0/11/0 | 12/0/11/0 |
| **Sum** | – | 137/0/133/7 | 135/1/132/9 | 139/3/130/5 |

Targeted near-misses, visibility and spend:

| | Trim 1 | Trim 2 | Trim 3 pooled |
|---|---|---|---|
| `ap-h07` | 0/3 | 0/3 | 2/6 |
| `se-h08` | 1/3 | 0/3 | 1/6 |
| `ld-h06` | 0/3 | 0/3 | 0/6 |
| `rs-h06` | 0/3 | 1/3 | 1/6 |
| Visibility (all 12) | 831/831 | 831/831 | 1662/1662 |
| Spend | $21.65 | $21.55 | $21.74 + $21.48 |

**Per-query findings.**
- `rc-t06` (REPL) went to 0/3 when "REPL" was dropped, and back to 3/3 with it.
- "JSON types" fixed `ri-t05` (2/3 twice, against 1/3 and 0/3 without it). It also pulled in `ri-h07`, a generic /health endpoint test that belongs to rf-requests: 4/6, against 0/3 in the reference and 1/3, 0/3 in trim 1/2.
- rf-language swung from 12/13 to 9/13 between trim 1 and 2 on an identical text, so run-to-run noise is up to 3 queries for that skill.
- `se-h07` and `rc-n04` sit at 0–2 of 3 on unchanged texts in every run.

**Selection: per skill among the three measured iterations** (the per-skill method of tune-skill-descriptions; see design.md Implementation Notes). Total **1348** ≤ 1351, variant `e8dcbb109c1b`.
- **rf-language:** iteration 3 ("tag runs").
- **rf-restinstance:** iterations 1/2, without "JSON types". This avoids the new `ri-h07` load, at the cost of `ri-t05`.
- **rf-platynui:** iterations 1/2 ("desktop app tests").
- **rf-setup:** iterations 1/2 ("(uv, pip, venv)").
- **rf-robotcode:** with "REPL".
- **The other 7:** one text across all iterations.
- **Targeted near-misses:** all < 0.5 in every run.
- **Visibility:** 100% in every run.

## 3.5 Re-acceptance of the trimmed set (2026-10-02, variant `e8dcbb109c1b`, total 1348 ≤ 1351)

**Runs.** All runs used Claude Code 2.1.286, room 1423 (`plugin-authoring` bundled), concurrency 2 and 0 incomplete. **Every default-budget session showed all 12 descriptions.**

| Run | Model / budget | Runs/query | Visibility | Spend |
|---|---|---|---|---|
| Validation, all 12 (`s-val`) | Haiku, default | 3 | 297/297 all 12 | $7.47 |
| Validation repeat (`s-val-r2`) | Haiku, default | 3 | 297/297 all 12 | $7.44 |
| holdout2, 6 skills (`s-h2`) | Haiku, default | 3 | 180/180 all 12 | $4.70 |
| Validation (`s-sonnet`) | `claude-sonnet-5`, default | 1 | 99/99 | $6.76 |
| Validation (`s-40k`) | Haiku, `--listing-budget 40000` | 3 | 297/297 | $7.42 |

### Validation per skill against the stored baseline

The stored values are `eval/baselines/triggers.json` acceptance: pooled validation recall over 6 runs per query, and validation accuracy. They come from the tune-skill-descriptions compact set at the room measured before `plugin-authoring` (description text ≈1520 < room), so every skill was visible in that run. None of the stored acceptance values comes from a run where the skill was hidden. The re-baseline values in that file do, but they are not the gate.

| Skill | Stored pooled recall | `s-val` TP/FP/TN/FN | `s-val-r2` | Pooled (6 runs) recall | Neg acc (stored 1.00) | Sonnet 5 | 40k |
|---|---|---|---|---|---|---|---|
| rf-appium | 1.00 | 4/0/4/0 | 4/0/4/0 | **1.00** | 1.00 | 4/0/4/0 | 4/0/4/0 |
| rf-browser | 0.75 | 4/0/4/0 | 4/0/4/0 | **1.00** | 1.00 | 3/0/4/1 | 4/0/4/0 |
| rf-language | 0.50 | 4/0/5/2 | 3/0/5/3 | **0.67** (4/6) | 1.00 | 6/0/5/0 | 3/0/5/3 |
| rf-libdoc | 1.00 | 4/0/4/0 | 4/0/4/0 | **1.00** | 1.00 | 4/0/4/0 | 4/0/4/0 |
| rf-platynui | 1.00 | 4/0/4/0 | 4/0/4/0 | **1.00** | 1.00 | 4/0/4/0 | 4/0/4/0 |
| rf-python-library | 0.75 | 3/0/4/1 | 3/0/4/1 | **0.75** | 1.00 | 4/0/4/0 | 3/0/4/1 |
| rf-requests | 1.00 | 4/0/4/0 | 4/0/4/0 | **1.00** | 1.00 | 4/0/4/0 | 4/0/4/0 |
| rf-restinstance | 0.75 | 4/0/4/0 | 4/0/4/0 | **1.00** | 1.00 | 4/0/4/0 | 4/0/4/0 |
| rf-results | 1.00 | 4/0/4/0 | 4/0/4/0 | **1.00** | 1.00 | 4/0/4/0 | 4/0/4/0 |
| rf-robotcode | 0.75 | 3/0/4/1 | 2/0/4/2 | **0.75** (`rc-v01` 2/6) | 1.00 | 4/0/4/0 | 3/0/4/1 |
| rf-selenium | 1.00 | 4/0/4/0 | 4/0/4/0 | **1.00** | 1.00 | 4/0/4/0 | 4/0/4/0 |
| rf-setup | 1.00 | 4/0/4/0 | 3/0/4/1 | **1.00** (`su-v02` 3/6) | 1.00 | 4/0/4/0 | 4/0/4/0 |

### holdout2 (6 skills, reported, not gating)

| Skill | TP/FP/TN/FN | Note |
|---|---|---|
| rf-appium | 5/1/4/0 | `ap-k07` (npm install -g appium EACCES on an RF CI agent, belongs to rf-setup) 2/3: a fresh sibling near-miss the cue did not stop |
| rf-selenium | 5/0/5/0 | |
| rf-libdoc | 5/0/5/0 | |
| rf-results | 5/0/5/0 | |
| rf-robotcode | 5/0/5/0 | |
| rf-setup | 3/0/5/2 | rf-setup visible this time; `su-k04` (bump the robotframework pin) 1/3, `su-k05` (which Appium driver for iOS; rf-appium loaded) 0/3 |

### Decision (design D6 step 5)

Gates: pooled validation recall ≥ stored, should-not-trigger accuracy ≥ stored, visibility 100% at the measured room. The 4 targeted near-misses were < 0.5 in every trim-tuning run (3.4).

| Skill | Recall gate | Neg-acc gate | Visibility | Decision |
|---|---|---|---|---|
| rf-appium | 1.00 ≥ 1.00 ✓ | ✓ | ✓ | accepted |
| rf-browser | 1.00 ≥ 0.75 ✓ | ✓ | ✓ | accepted |
| rf-language | 0.67 ≥ 0.50 ✓ | ✓ | ✓ | accepted (still below 0.80, rule-b shortfall as stored) |
| rf-libdoc | 1.00 ≥ 1.00 ✓ | ✓ | ✓ | accepted |
| rf-platynui | 1.00 ≥ 1.00 ✓ | ✓ | ✓ | accepted |
| rf-python-library | 0.75 ≥ 0.75 ✓ | ✓ | ✓ | accepted (rule-b shortfall as stored) |
| rf-requests | 1.00 ≥ 1.00 ✓ | ✓ | ✓ | accepted |
| rf-restinstance | 1.00 ≥ 0.75 ✓ | ✓ | ✓ | accepted |
| rf-results | 1.00 ≥ 1.00 ✓ | ✓ | ✓ | accepted |
| rf-robotcode | 0.75 ≥ 0.75 ✓; equal to the baseline, and the pooled decision rests on `rc-v01` (2/6), so it is already pooled over 2 runs | ✓ | ✓ | accepted (rule-b shortfall as stored) |
| rf-selenium | 1.00 ≥ 1.00 ✓ | ✓ | ✓ | accepted |
| rf-setup | 1.00 ≥ 1.00 ✓ (`su-v02` 3/6, exactly at threshold) | ✓ | ✓ | accepted |

**All 12 trimmed descriptions are accepted.** Total 1348 ≤ 1351.

Spend for 3.3–3.5:
- 3.3 room: $2.48.
- 3.4 tuning: $21.65 + $21.55 + $21.74 + $21.48, plus the reference run $11.03.
- 3.5 acceptance: $7.47 + $7.44 + $4.70 + $6.76 + $7.42.
- Total: **$133.72**.
