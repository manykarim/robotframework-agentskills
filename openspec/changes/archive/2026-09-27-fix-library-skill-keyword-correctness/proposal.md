## Why

The library skills teach keywords that do not exist or are deprecated in the library versions they target (verified with libdoc against Browser 19.14.2, SeleniumLibrary 6.8.0, AppiumLibrary 3.2.1, RequestsLibrary 0.9.7, RESTinstance, PlatynUI 0.12.0.dev330 and RF 7.4.2). SKILL.md files were patched over time, but `references/` and `assets/examples/` were not, so an agent that loads a reference produces tests that fail at `robot --dryrun`. Nothing in CI catches this, so the defects come back.

## What Changes

- Fix every nonexistent, deprecated or malformed keyword call in the root `skills/` copies of rf-browser, rf-selenium, rf-appium and rf-requests (SKILL.md, `references/`, `assets/examples/`), then re-sync the plugin and VS Code copies with `scripts/sync-skills.sh`. Examples: Browser `Wait Until Network Is Idle` → `Wait For Load State    networkidle`, `Fill` → `Fill Text`, `Get Bounding Box` → `Get BoundingBox`; Selenium `Wait Until Element Count Is Greater Than`, `Go Forward`, `Title Should Contain`, `Get Window Handle`; Appium `Element Should Be Visible/Enabled/Disabled` → `Expect Element`, plus the removed `Long Press`, `Click A Point`, `Zoom`, `Pinch`, `*App*` keywords.
- Correct the rf-browser description of `Wait For Condition`. It wraps Browser assertion getters and is not a JavaScript wait. Also fix invalid `condition` values such as `Get Text` and `Get Page Ids`.
- Replace `Run Keyword If` with native `IF` in skill content. Drop the redundant `Run Keyword If Test Failed    Take Screenshot` teardown from rf-browser, because `run_on_failure` already takes the screenshot.
- Verify rf-restinstance and rf-platynui with the same checker. Both are clean today, and the CI gate keeps them that way.
- **BREAKING** (rf-results JSON contract): remove the `details.criticality` array from `rf_results.py` output and remove the criticality wording from the rf-results SKILL.md and description. Criticality was removed in Robot Framework 4.0. `details.tags` already covers tag-based grouping.
- Add `scripts/check-skill-keywords.py`, a deterministic checker promoted from the one-off evaluation script. It extracts keyword calls from ```robotframework blocks and `.robot`/`.resource` assets, skips user keywords the same skill defines, resolves the rest against libdoc of the skill's library plus the standard libraries, and fails on unknown or deprecated keywords and on `Run Keyword If`/`Unless`. An allowlist file records intentional exceptions.
- Add a CI job `check-skill-keywords` and a pytest (`tests/test_skill_keywords.py`) that run the checker. Add the target libraries, including RESTinstance, to the dev dependency group so the checker can verify them locally.

## Capabilities

### New Capabilities
- `skill-content-verification`: library-skill content only uses keywords that exist and are not deprecated in the targeted library versions, avoids legacy control-flow keywords, and a deterministic checker enforces this in CI and in pytest.

### Modified Capabilities
- `rf-script-output`: adds a requirement that `rf_results.py` output carries no criticality grouping. This documents the removal of `details.criticality` as a contract change.

## Impact

- Content: `skills/robotframework-{browser,selenium,appium,requests}-skill/**`, `skills/robotframework-results/SKILL.md`, and their synced copies under `plugins/rf-agentskills/skills/` and `vscode-extension/skills/`.
- Code: `skills/robotframework-results/scripts/rf_results.py` (plus the synced `plugins/rf-agentskills/scripts/rf_results.py`), new `scripts/check-skill-keywords.py`, new `scripts/skill-keywords-allowlist.toml`.
- Tests and CI: `tests/test_rf_results.py` (criticality assertion inverted), new `tests/test_skill_keywords.py`, new job in `.github/workflows/ci.yml`.
- Dependencies: dev group in `pyproject.toml` gains `robotframework-browser`, `robotframework-seleniumlibrary`, `robotframework-appiumlibrary`, `robotframework-requests`, `RESTinstance`, and pinned `robotframework-PlatynUI==0.12.0.dev330`. RESTinstance pulls in old transitive packages such as `flex`, which emit SyntaxWarnings on import.
- Consumers: no in-repo consumer reads `criticality`. The MCP server (`plugins/rf-agentskills/servers/`) passes through `rf_results` output, so external users of the `details` section lose one key.
- Out of scope: installation guidance (see change `unify-library-install-guidance`), deleting `keywords-reference.md` catalogs, and retiring the generator skills. Those are separate tracks.
