## Why

An agent decides whether to load a skill from its frontmatter `description` alone, and Codex, Claude Code and VS Code truncate long descriptions. Most of our descriptions start with meta-phrasing ("Guide AI agents in creating…"), which wastes the front-loaded tokens. They also leave out the words users actually type (`Library    Browser`, `output.xml`, `robot.toml`, `No module named 'Browser'`) and draw no boundaries between siblings. rf-browser and rf-selenium both claim "web UI tests", rf-requests and rf-restinstance both claim "REST API tests", and rf-results and rf-libdoc overlap rf-robotcode. The wrong skill loads, or none does, and nothing measures it. The Companion Skills tables also point at skills that are being retired or merged.

## What Changes

- Rewrite the `description` of every skill that remains after the retirement and merge changes (rf-browser, rf-selenium, rf-appium, rf-requests, rf-restinstance, rf-platynui, rf-robotcode, rf-setup, rf-results, rf-libdoc). Each description:
  - starts with a third-person capability statement that names Robot Framework and the library/tool;
  - has a "Use when…" clause with concrete trigger terms: library import lines, package names, file names (`output.xml`, `.robot`, `.resource`, `robot.toml`), CLI names (`rfbrowser`, `robotcode`, `robot-debug`, `rebot`) and error messages;
  - ends with an explicit boundary that names the sibling skill to use instead;
  - uses no meta-phrasing ("Guide AI agents…", "This skill…") and no XML tags;
  - is at most 1024 characters, with a target of ≤ 500.
  The draft texts are in design.md.
- Boundary rules between siblings, written into both sides' descriptions:
  - **rf-browser vs rf-selenium**: decided by the library the project imports (`Browser` vs `SeleniumLibrary`), or by the named technology (Playwright vs WebDriver/Grid). A new project with no preference goes to rf-browser (default confirmed by the user, 2026-09-27).
  - **rf-requests vs rf-restinstance**: decided by the import (`RequestsLibrary` vs `REST`). Generic "API test in Robot Framework" with no library named goes to rf-requests (default confirmed by the user, 2026-09-27). JSON Schema/OpenAPI-driven assertions go to rf-restinstance.
  - **rf-robotcode vs rf-results / rf-libdoc**: prompts that mention robotcode, `robot.toml` or `robot-debug` go to rf-robotcode. Generic output.xml analysis and keyword lookup go to the script skills, which say "prefer rf-robotcode when the robotcode CLI is installed".
  - **rf-setup vs the library skills**: installing, environments, missing-module/PEP 668/interpreter errors, `rfbrowser init` go to rf-setup. Writing or fixing test code goes to the library skill.
- Standardise the `## Companion Skills` section in every remaining skill. It is a `Need | Skill` table (rf-robotcode keeps its extra "With robotcode" column), rows come from one shared catalogue in design.md, every skill has a row for its boundary sibling(s), rf-setup, rf-libdoc and rf-results/rf-robotcode, and no row names a retired or merged skill.
- Add a trigger query set per skill at `eval/triggers/<skill>.yaml` in the format defined by `strengthen-skill-eval-harness`, with ≥ 8 should-trigger and ≥ 8 near-miss should-not-trigger queries each, split into train and validation. Near-misses are drawn from sibling skills and from non-RF look-alikes (pytest + Playwright, plain Selenium in Python, Postman, Appium in Java).
- Acceptance criteria per skill on the validation split: a query counts as triggered at a trigger rate ≥ 0.5 over 3 runs; recall ≥ 0.80, should-not-trigger accuracy ≥ 0.90, and no regression against the pre-change descriptions measured with the same query set.
- Add a static test that enforces the description rules (length, no meta-phrasing, "Use when" clause, sibling named) and the companion-table rules.

Dependencies and ordering:
- **After** `retire-generator-skills` and `merge-libdoc-skills`: the descriptions and companion tables cover only the remaining skills, and `rf-libdoc` exists.
- **After** `align-skill-names-with-spec`: file paths are `skills/rf-*/`, and that change's validator already checks length and tags.
- **Before or together with** `restructure-library-skills`. That change leaves `description` to this one and rewrites bodies, so it must keep the companion rows defined here.
- **Measurement depends on** `strengthen-skill-eval-harness`: its `trigger` command, detection and report. The text edits and static tests can land first, but the acceptance thresholds are checked only once the runner exists.

## Capabilities

### New Capabilities
- `skill-triggering`: the contract for how skill descriptions are written (structure, trigger terms, sibling boundaries, length), the standard Companion Skills cross-reference section, the per-skill trigger query sets, and the trigger-accuracy acceptance thresholds.

### Modified Capabilities
<!-- None. The rf-robotcode and rf-setup description scenarios in robotcode-skill / setup-skill (must mention robotcode + discovery/debugging/results; installing RF + uv/venv/pip/poetry) remain satisfied by the new text. The rf-libdoc-search/explain references in robotcode-skill are updated by merge-libdoc-skills. -->

## Impact

- **Skills (canonical)**: frontmatter `description` and the `## Companion Skills` section of `skills/rf-{browser,selenium,appium,requests,restinstance,platynui,robotcode,setup,results,libdoc}/SKILL.md`. Plugin and VS Code copies are regenerated by `scripts/sync-skills.sh`.
- **Other description surfaces kept consistent**: the skill table in `README.md`, and the hook text in `plugins/rf-agentskills/scripts/maybe_inject_rf_context.mjs`. That text describes skills in one line each and must not contradict the boundaries. It is not a trigger surface for evals, since trigger evals run with hooks disabled.
- **Eval data**: new `eval/triggers/*.yaml` (10 files). Baseline trigger results for the old descriptions are recorded before the rewrite.
- **Tests**: new `tests/test_skill_descriptions.py`.
- **Users**: better skill selection. No API or path change.
