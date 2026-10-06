## Why

The compact descriptions shipped in `tune-skill-descriptions` (archived 2026-09-30) raised validation recall from 21/50 to 43/50. The trade-off was dropping sibling boundaries from the descriptions. They now sit in each `## When to use` body block, which the model reads only after it has loaded the skill.

The final runs recorded five should-not-trigger loads, all queries that belong to a neighbouring skill:

| Run | Skill loaded | Query | Belongs to | Loads |
|---|---|---|---|---|
| Holdout, Haiku | rf-appium | `ap-h07` (Appium driver install behind a proxy) | rf-setup | 3/3 |
| Holdout, Haiku | rf-selenium | `se-h08` (chromedriver in offline CI) | rf-setup | 3/3 |
| Holdout, Haiku | rf-libdoc | `ld-h06` ("robotcode installed … robotcode libdoc") | rf-robotcode | 2/3 |
| Holdout, Haiku | rf-results | `rs-h06` ("robotcode is set up … robotcode results") | rf-robotcode | 3/3 |
| Validation, Sonnet 5 | rf-selenium | `se-n09` (Selenium Grid for a Java team, not Robot Framework) | none | 1/1 |

A short cue in the description ("installing drivers → rf-setup", "with robotcode → rf-robotcode") should keep the model on the right skill before it loads the wrong one.

There is room for it. The 1700-character test cap counts whole `- name: description` lines, but the room measured on 2026-09-29 (1734 characters) covers description text only. Counted the way Claude Code lays out the listing, about 200 characters are unused.

## Revision (2026-10-02)

Claude Code started listing the built-in `plugin-authoring` skill, so the listing room fell to 1423 characters. rf-setup's description is now hidden, on main as well. By user decision, this change also trims all 12 descriptions to fit 95% of the re-measured room, and accepts them again (design.md "Revision 2026-10-02").

## What Changes

- **Re-measure the skill-listing budget** on the current Claude Code (2.1.285) with Haiku 4.5.
- **Recalibrate the combined-listing rule** to count what Claude Code counts: the description text of the rf-* skills. The limit becomes the measured room minus a 5% margin, with the Claude Code version and date recorded in the test.
- **Add sibling cues** to the descriptions of rf-appium and rf-selenium (installs and drivers → rf-setup), and of rf-libdoc and rf-results (robotcode installed → rf-robotcode). Each cue is at most about 35 characters, and every description stays at or under 160 characters.
- **Keep the `## When to use` blocks** unchanged as the detailed boundary. The cues are the short version.
- **Add fresh holdout queries.** The current holdout found these false positives, so it is no longer unseen. Add a second holdout (`holdout2`) with new sibling near-misses for the four skills, plus new should-trigger queries for them.
- **Measure and accept** on the train split (tuning), the combined validation split and `holdout2`, all under the default listing budget, with visibility at 100%.
- **Update `eval/baselines/triggers.json`.**

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `skill-triggering`:
  - "Descriptions lead with capability and a 'Use when' clause": the combined budget is counted over rf-* description text against a re-measured limit, and skills with observed near-miss loads carry a sibling cue.
  - "Descriptions meet trigger-accuracy thresholds": adds the near-miss acceptance criterion and the fresh-holdout rule.
- `skill-eval-harness`:
  - "Trigger evaluation query sets": allow further holdout splits (`holdout2`, …), so a holdout that has been used to find problems can be retired.

## Impact

- **Content:** the `description` of `skills/rf-{appium,selenium,libdoc,results}/SKILL.md`, synced to the plugin, VS Code and installer assets.
- **Tests:** `tests/test_skill_descriptions.py` (budget constant and counting, cue rule), plus the harness split handling in `src/rf_skill_eval/domain/trigger.py` and its tests.
- **Data:** `eval/triggers/rf-{appium,selenium,libdoc,results}.yaml` (holdout2 queries) and `eval/baselines/triggers.json`.
- **Cost:** live Haiku trigger runs, about $20–30 in total (the user has confirmed cost is not a constraint), plus one Sonnet 5 validation pass.
