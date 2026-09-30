## Why

The first live trigger evaluation (2026-09-28/29, Haiku 4.5, 3 runs per query) shows that the skills rarely get loaded:
- No skill fired on any should-not-trigger query: 48/48 were correct.
- On should-trigger queries in the validation split, the skill loaded in only 45 of 120 runs.
- Every skill misses the accepted recall target of ≥ 0.80.
- rf-results, rf-robotcode, rf-setup and rf-python-library loaded on none of their validation queries.

The task evals show the same thing: rf-browser, rf-selenium, rf-platynui and rf-python-library were loaded in 0/3 task runs. So most of the plugin's measured benefit comes from its hooks, not its skills.

The descriptions rewritten in `sharpen-skill-descriptions` did no better than the ones they replaced (48 loads out of 120 before, 45 after). Their structure was never tuned against measurements. They are catalogs of keywords and features, while the trigger queries are phrased as user intents and symptoms.

The transcripts also show that the trigger measurement itself is off:
- Trigger runs used `Bash` and `Write` although only `Skill,Read,Glob,Grep` are meant to be allowed.
- They start in an empty workspace, which pushes the model to explore instead of loading a skill.
- A crash in the middle of a batch lost every result, because results are only written at the end.

This change first makes the measurement faithful, then tunes the descriptions in an evaluation-driven loop until they meet the acceptance criteria or a documented stopping rule.

Evidence: `evidence/trigger-results-current-2026-09-28.json` (current descriptions, both splits) and `evidence/trigger-results-pre-sharpen-validation-2026-09-29.json` (pre-sharpen descriptions, validation split).

## Revision (2026-09-29)

During tuning we found that Claude Code lists skill descriptions only within a character budget: about 8000 characters for 200k-context models. Under Haiku, 9 of the 12 rf-* skills were listed **by name only**. The user decided:
- to optimize and accept **compact descriptions** under the default budget: at most 160 characters each, and at most 1700 in total;
- to move trigger terms and sibling boundaries into a `## When to use` block at the top of each SKILL.md;
- to report the 1M-context budget of 40000 characters as well, but not gate on it;
- to fix the runner's isolation cleanup, which deleted unrelated repository files during runs.

The budget cap rises to $90. See design.md "Revision 2026-09-29".

## What Changes

- **Faithful trigger measurement** in the eval harness:
  - Enforce the trigger tool set, so no Bash or Write is available.
  - Run each query in a small realistic Robot Framework project fixture instead of an empty directory.
  - Persist outcomes query by query, and resume an interrupted batch.
  - Allow concurrency up to the ADR-002 cap of 2.
  - Add a `--variant-root` option, so a candidate description set can be measured without editing the shipped skills.
- **Re-baseline** the current descriptions under the corrected harness on both splits before any description is edited. The 2026-09 numbers remain as historical evidence only.
- **Description tuning loop**, per skill, on the train split only:
  1. Rewrite from a pattern.
  2. Measure on train.
  3. Keep the best candidate.
  4. At most 5 iterations per skill.

  Candidates are selected on train, and acceptance is decided on validation. The pattern is:
  - lead with the user's intent;
  - "Use when…" triggers phrased as the user would say them, including symptoms and pasted errors;
  - an explicit "even if the user doesn't mention <library/tool>" nudge;
  - a sibling boundary;
  - no catalog of keyword names.
- **Fresh holdout check**: add 5 new should-trigger and 5 new should-not-trigger queries per skill that are written after tuning and never used to choose a candidate. Report them as a final sanity check.
- **Cross-model check**: after acceptance, run the validation split once on `claude-sonnet-5`. It is reported, not gating.
- **Description contract updates**:
  - Allow the leading "Use this skill when…/whenever…" imperative form alongside the third-person capability form.
  - Allow the "even if … doesn't mention" nudge.
  - Keep the 1024-character hard limit and the sibling-boundary requirement.
- **Acceptance rule update**: the ≥ 0.80 recall / ≥ 0.90 negative-accuracy targets stay. A skill that misses the recall target after 5 iterations may still ship its best candidate if all of the following hold:
  - it improves validation recall over the re-baselined current description by at least 0.25 (1 of 4 queries);
  - it does not lose negative accuracy;
  - the shortfall is recorded in `eval/baselines/triggers.json` and in the design.
- **Baselines**: store the accepted trigger results as the new `eval/baselines/triggers.json`, recording the harness version and model.

Out of scope, recorded as follow-ups:
- routing the plugin's UserPromptSubmit hook to name the matching skill;
- harder library task evals;
- the rf-mcp attachment bug;
- pruning workspace venvs after grading.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `skill-triggering`:
  - "Descriptions lead with capability and a 'Use when' clause": allow the imperative trigger-first form and the "even if … doesn't mention" nudge.
  - "Descriptions meet trigger-accuracy thresholds": pre-change re-baseline under the corrected harness, the per-skill 5-iteration loop, the stopping and fallback acceptance rule, the fresh holdout and the cross-model report.
- `skill-eval-harness`:
  - "Trigger detection and scoring": enforced tool set, realistic fixture workspace, incremental persistence and resume, concurrency ≤ 2, and variant roots for candidate measurement.

## Impact

- **Harness code:**
  - `src/rf_skill_eval/application/trigger_eval.py`
  - `src/rf_skill_eval/cli.py` (the `trigger` command)
  - `src/rf_skill_eval/infrastructure/runner/claude_code_runner.py` (tool restriction and workspace provisioning)
  - `eval/fixtures/` (a trigger fixture)
  - tests in `tests/eval/`
- **Trigger sets:** `eval/triggers/*.yaml` gains the fresh-holdout queries (a new `holdout` split).
- **Content:**
  - the frontmatter `description` of all 12 `skills/rf-*/SKILL.md`, synced to the plugin, VS Code and installer assets;
  - README skill table wording where it mirrors descriptions.
- **Tests:** `tests/test_skill_descriptions.py` gets rule updates for the allowed forms.
- **Baselines:** `eval/baselines/triggers.json`.
- **Cost:** every run is capped with `--max-cost-usd`.
  - A full train pass over 12 skills is about 400 Haiku sessions, roughly $12.
  - The tuning budget is capped at $80 in total, plus about $10 for the Sonnet check.
- **No change** to skill bodies, scripts, MCP tools, hooks or installer behaviour.
