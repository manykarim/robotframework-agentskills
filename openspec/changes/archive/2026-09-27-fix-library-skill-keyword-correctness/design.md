## Context

- Libraries in `.venv` on 2026-09-27: robotframework 7.4.2, robotframework-browser 19.14.2, SeleniumLibrary 6.8.0, AppiumLibrary 3.2.1, RequestsLibrary 0.9.7. RESTinstance and PlatynUI (`0.12.0.dev330`) are **not** in the dev group. Both were checked ephemerally with `uv run --with RESTinstance --with robotframework-PlatynUI==0.12.0.dev330`, and both came out clean.
- A one-off checker (evaluation scratchpad `kwcheck.py`) only looked at indented first cells and ignored user keywords, so it both missed defects and reported false positives. An improved prototype (`kwcheck2.py`) does these things:
  - dedents fenced blocks
  - handles `*** Settings ***` lines (including bare `Library …` lines in fragments), assignments and control structures
  - strips `Library.` prefixes
  - excludes keywords the same skill defines under `*** Keywords ***`
  - prints close-match suggestions

  Its output is the defect list in `tasks.md`.
- Most skill code blocks are fragments without section headers, so `robot.api.get_model` cannot parse them as they are. `.robot` files under `assets/examples/` do parse. The CI job `validate-robot-syntax` already runs `get_model` over them.
- Channels: root `skills/` is canonical. `scripts/sync-skills.sh` copies to `plugins/rf-agentskills/skills/<short>/` and `vscode-extension/skills/rf-*`, and `scripts/check-drift.sh` gates CI.
- `rf_results.py` computes `details.criticality` from tags `critical`/`noncritical`. Only `tests/test_rf_results.py::test_details_section` asserts it. The MCP tool `rf_results_analyze` returns the script's dict unchanged.

## Goals / Non-Goals

**Goals:**
- Zero unknown or deprecated keyword calls in the six library skills, and the result is enforced in CI.
- A checker that is fast (libdoc only, no browser or device), deterministic, and gives messages an agent or human can act on: file, line, keyword and suggestion.

**Non-Goals:**
- Full argument validation. The only argument check is the closed-vocabulary check for Browser `Wait For Condition` (see D6).
- Checking non-library skills (rf-setup, rf-robotcode, the generator skills that are being retired) or Python snippets inside the skills.
- Rewriting or deleting `keywords-reference.md` catalogs. Only the wrong entries get fixed.
- Running the examples (`robot --dryrun` against live libraries). That is a possible follow-up.

## Decisions

### D1: Standalone repo script, not a shipped skill script
The script is `scripts/check-skill-keywords.py`, next to `check-drift.sh`. It is repository QA tooling, so it does not go under `skills/*/scripts/` and does not ship to users. It depends only on `robotframework` and the libraries under test.

### D2: Two extractors
- `.robot`/`.resource` files: use `robot.api.get_model` and visit `KeywordCall`, `Setup`, `Teardown`, `TestTemplate` and `KeywordName` nodes. This is exact, and it yields the defined user keywords.
- Fenced ```robotframework / ```robot blocks in `.md`: use a line-based extractor (from `kwcheck2.py`) on the dedented block. It tracks a section only when a block contains `*** … ***`. A fragment without headers is treated as a keyword body, and bare settings lines (`Library`, `Suite Setup`, …) are recognized by their first cell. Wrapping fragments into a synthetic suite was rejected: fragments mix settings, test bodies and keyword bodies, so wrapping produces spurious parse errors.
- Cells are split on two or more spaces, a tab, or ` | `. A single-space call such as `Get Element States button#submit` shows up as an unknown keyword, which is the right outcome because it is also a defect.

### D3: Resolution scope
The checker resolves in this order:
1. the skill's library (a fixed map from skill dir to import name: `Browser`, `SeleniumLibrary`, `AppiumLibrary`, `RequestsLibrary`, `REST`, `PlatynUI.BareMetal`)
2. the standard libraries `BuiltIn`, `Collections`, `String`, `OperatingSystem`, `DateTime`, `Process`, `XML`, `Screenshot`
3. user keywords defined anywhere in the same skill

Matching follows RF rules: case-insensitive, spaces and underscores ignored, and an optional `LibraryName.` prefix. Embedded-argument user keywords are matched with RF's own `EmbeddedArguments` regex. User keywords defined in one skill do not count for another skill.

### D4: What counts as a failure
- `UNKNOWN`: the name is not resolved and looks like a keyword (starts with a letter and has no `=`, `/`, `<`, `>` or quotes).
- `DEPRECATED`: libdoc `deprecated` is true.
- `LEGACY`: `Run Keyword If` or `Run Keyword Unless`.
- The checker also checks the keyword-name argument of wrapper keywords: `Run Keyword*`, `Wait Until Keyword Succeeds`, `Run Keyword And Return Status`, `Run Keyword If Test Failed`, and setup/teardown settings. This catches wrapped calls such as `Run Keyword If Test Failed    Capture Page Screenshot`.

### D5: Allowlist as TOML with stale-entry detection
The allowlist is `scripts/skill-keywords-allowlist.toml`, a list of `[[allow]]` entries with the fields `skill`, `file`, `keyword` and `reason`. It is meant for illustrative application keywords that are left undefined on purpose (for example `Create New Item` in rf-browser `references/tabs-windows.md`). An entry that no longer matches any call fails the run, so the list cannot rot. The default is to *define* a stub user keyword in the snippet rather than allowlist it. The allowlist is for places where a stub would bloat an example. Python 3.11+ reads the file with `tomllib`, and the repo requires 3.12.

### D6: Browser `Wait For Condition` vocabulary check
If the first argument of `Wait For Condition` is a literal, it is validated against the members of the `ConditionInputs` type in Browser's libdoc `type_docs`, after normalizing case and spaces or underscores. Variables are skipped. This single targeted rule covers the defect class in the findings (`Get Text`, `Get Page Ids`). A generic enum-argument validator was rejected for now: assertion-operator enums accept both member names and values (`==`, `contains`), which needs more care to avoid false positives.

### D7: Skipped libraries
If a library does not import, the skill is reported as `SKIPPED`. With `--require-all`, which CI passes, a skip fails the run. The pytest calls `pytest.importorskip` per library, so a contributor without RESTinstance still gets the other five skills checked.

### D8: Dev dependencies
Add the six target libraries to `[dependency-groups] dev` in `pyproject.toml`: Browser, SeleniumLibrary, AppiumLibrary, Requests, RESTinstance, and PlatynUI pinned to `==0.12.0.dev330`. A normal `uv sync` then makes the checker complete. An exact `==…dev330` pin is accepted by uv without any prerelease setting. A separate `skill-libs` group was considered. It was rejected because the existing CI `test` job already pip-installs these libraries fail-soft, and one group is simpler for contributors.

### D9: Criticality removal is a contract change, not a rename
`details.criticality` is removed outright and not kept as a deprecated alias. RF 4+ output has no criticality, so the field only echoed tag names that `details.tags` already reports. The change is recorded under "Unreleased → Changed (BREAKING)" in the installer CHANGELOG, together with the matching rf-script-output requirement.

### D10: Replacement choices for removed keywords

| Removed or nonexistent | Replacement taught |
|---|---|
| Browser `Wait Until Network Is Idle` | `Wait For Load State    networkidle` |
| Browser `Fill` | `Fill Text` |
| Browser `Get Bounding Box` | `Get BoundingBox` |
| Browser `Get Context Id` | `Get Context Ids    CURRENT` (returns a list) |
| Browser `Get Page Catalog` | `Get Browser Catalog` |
| Browser `Promise To Wait For Response/Request` | `Promise To    Wait For Response    …` |
| Browser `Route` / `Unroute` | Section removed. Browser has no routing keywords, so the section points to `Wait For Response` and states that request mocking needs a JS extension. |
| Selenium `Wait Until Element Count Is*` | `Wait Until Keyword Succeeds` + `Get Element Count` / `Should Be True` |
| Selenium `Go Forward` | `Execute Javascript    history.forward()` |
| Selenium `Title Should Contain/Start With/Match` | `Get Title` + `Should Contain` / `Should Start With` / `Should Match` |
| Selenium `Element Attribute Value Should Not Be` | `Get Element Attribute` + `Should Not Be Equal` |
| Selenium `Get Cookie Value` | `Get Cookie` → `${cookie.value}` |
| Selenium `Get Window Handle` | `Get Window Handles` / `Switch Window    MAIN` |
| Selenium `Get Browser Capabilities` | Define a user keyword via `Execute Javascript`, or remove it. `Get Chrome Driver` goes with the webdriver-manager removal in `unify-library-install-guidance`. |
| Appium `Element Should Be Visible/Enabled/Disabled`, `Element Should Not Be Visible` | `Expect Element    locator    visible \| enabled \| disabled \| not visible` |
| Appium `Wait Until Element Is Not Visible` | `Wait Until Page Does Not Contain Element` |
| Appium `Long Press` | `Tap    locator    duration=2s` |
| Appium `Click A Point` | `Tap With Positions    500ms    ${{ (x, y) }}` |
| Appium `Zoom` / `Pinch` | `Execute Script    mobile: pinchOpenGesture` / `pinchCloseGesture` (UiAutomator2), with a note that iOS uses `mobile: pinch` |
| Appium `Quit Application` / `Launch App` / `Reset Application` | `Close Application` / `Activate Application` / removed (use `noReset`/`fullReset` capabilities) |
| Appium `Background App` / `Activate App` / `Terminate App` / `Remove App` | `Background Application` / `Activate Application` / `Terminate Application` / `Remove Application` |
| Appium `Query App State`, `Is App Installed`, `Set/Get Clipboard`, `Get Appium Attribute` | `Execute Script    mobile: queryAppState` / `mobile: isAppInstalled` / `mobile: setClipboard` / `mobile: getClipboard`; orientation via `Landscape` / `Portrait` |
| Appium `Set Orientation`, `Get Window Size`, `Get Url`, `Get Title`, `Click Button` | `Landscape`/`Portrait`, `Get Window Width` + `Get Window Height`, `Get Window Url`, `Get Window Title`, `Click Element`/`Click Text` |
| `Length Should Be Greater Than` | `${n}=    Get Length    …` + `Should Be True    ${n} > 10` |
| Requests `Open File` / `Write To File` / `Close File` | `Create Binary File    ${path}    ${response.content}` (OperatingSystem) |

Each `mobile:` command is confirmed against the Appium UiAutomator2/XCUITest driver docs during implementation (task 2.x).

## Risks / Trade-offs

- [The line heuristic misreads prose-like code, such as a test-case name inside a fragment] → The block is dedented and the checker tracks sections when headers exist. Remaining false positives go to the allowlist, each with a reason. The fixture tests pin the heuristic's behaviour.
- [A library upgrade deprecates more keywords and CI turns red without any skill change] → This is intended: that is exactly the drift the check exists to catch. The failure message names the replacement from libdoc's deprecation text.
- [RESTinstance brings old transitive packages (`flex`, …) that emit SyntaxWarnings or break on future Python versions] → The checker suppresses warnings during libdoc load. If RESTinstance stops installing, D7 marks that skill as skipped and the `--require-all` CI job fails loudly instead of passing silently.
- [Removing `details.criticality` breaks an external consumer] → The field was near-meaningless on RF ≥ 4. The CHANGELOG entry and the version bump signal the break.
- [PlatynUI requires Python 3.12+ and a pre-release] → The CI job runs on 3.12. The repo already requires Python ≥ 3.12.
- [Overlap with parallel changes] → `restructure-library-skills` deletes the five `keywords-reference.md` catalogs *after* this change. Fixes in those files therefore need only be minimal and correct, not polished. The checker survives the deletion unchanged. `sharpen-skill-descriptions` owns frontmatter descriptions, but this change still removes the word "criticality" from the rf-results description, because it is a factual error. Whichever change lands second rebases onto the other.

## Migration Plan

1. Land the checker with the allowlist while defects still exist, and confirm it reports them (red).
2. Fix the content in root `skills/`, sync, and confirm the checker is green.
3. Remove criticality, update the test, and add the CHANGELOG entry.
4. Enable the CI job.

Rollback: revert the commit. Content-only fixes carry no runtime risk.

## Open Questions

- Should the checker also run `robot --dryrun` on `assets/examples/*.robot`? That would catch argument-count errors. It is deferred because it widens the scope from keyword names to arguments and needs every example's variables and resources to resolve.
- Should the generic enum-argument check (D6) be extended to all keywords in a later change?

## Implementation Notes

- **Checker scope extended (D2/D4).** `scripts/check-skill-keywords.py` also joins `...` continuation rows in Markdown blocks, so wrapped keyword names on continuation lines (for example `Run Keyword And Return Status` + `...    Element Should Be Visible`) are checked. It also checks inline `IF` branches, `[Setup]`/`[Teardown]`/`[Template]`, `Run Keywords` (with and without `AND`) and `Promise To`. Test bodies driven by `Test Template` / `[Template]` are skipped because their rows are data. In header-less fragments, a single-cell column-0 line followed by an indented line is treated as a test/keyword name, not a call (it is not registered as a user keyword either).
- **UNKNOWN heuristic narrowed (D4).** A cell is exempt from UNKNOWN only when it contains `/ < > " ' ( )` or an ellipsis. `=` and `:` do **not** exempt it: that surfaced one more real defect (`Element Should Not Be Visible css=.error` in rf-selenium SKILL.md, single-space separator) and caused no false positives.
- **Extra finding class `BAD-ARG`** is used for the D6 `Wait For Condition` rule. Output format: `SKILL FILE:LINE CLASS KEYWORD ~ detail`, then `--`, one summary line per skill and `RESULT: OK|FAIL`. The skill key is the short name (`browser`, `selenium`, …), identical for root and plugin copies, so the allowlist works for both.
- **Additional defects fixed beyond the task list** (all found by the checker or while editing the same snippets): rf-requests `DELETE ${URL}` single-space separator (SKILL.md, `references/response-validation.md`); rf-appium deprecated `Element Should Be Visible` in `assets/examples/gestures-example.robot`, `assets/examples/hybrid-app.robot` and three wrapped calls in `references/gestures-touch.md`; nonexistent `mobile: pinchOpen`/`pinchClose` → `pinchOpenGesture`/`pinchCloseGesture` with `${element.id}`; positional `Swipe` calls (AppiumLibrary 3.x `Swipe` takes keyword-only arguments) rewritten to `start_x=… duration=…ms`; `Execute Script    mobile: …    {json}` strings rewritten to named arguments; `Install App` given its required `app_package`; rf-browser `Get Element Count    @{Get Page Ids}` and `Wait For Response    url=` (→ `matcher=`).
- **2.2.7:** the task text suggests `IF … END` on one line. Inline IF takes no `END` (`robot --dryrun` fails on it), so the fix is `IF    ${data}[newsletter]    Select Checkbox    id=newsletter`.
- **2.2.x replacements:** exact-count waits use `Wait Until Keyword Succeeds … Page Should Contain Element … limit=N`; "at least one" uses `Wait Until Page Contains Element`; other comparisons use SeleniumLibrary's JavaScript `Wait For Condition    return document.querySelectorAll(…).length > N`, which is shorter than a WUKS + `Get Element Count` + `Should Be True` user keyword. `Get Window Handle` → `${h}=    Switch Window    CURRENT` (documented to return the current handle) rather than `Get Window Handles`.
- **2.1.6:** context ids come from the return value of `New Context`; a comment shows the `Get Context Ids    CURRENT` alternative.
- **Stubs vs allowlist (D5):** `Create New Item`, `Delete Item`, `Create Item` and `Get Fresh Token` are stubbed as user keywords in their snippets. The allowlist holds one entry: rf-selenium `references/webdriver-setup.md` `Get Chrome Driver` (reason: removed by `unify-library-install-guidance`). That change must delete the entry, or the stale-entry check fails.
- **`mobile:` commands** were checked against the UiAutomator2 driver (`README.md`, `docs/android-mobile-gestures.md`) and the XCUITest driver (`docs/reference/execute-methods.md`) on 2026-09-27. The sources are named in `references/gestures-touch.md`.
- **Dev environment:** use `uv sync --all-packages`. A plain `uv sync` uninstalls the workspace member `rf-agentskills`, which `tests/installer/` imports.
- **CI:** besides the `check-skill-keywords` job (root and plugin copies, `--require-all`), the `lint` job now also lints `scripts/check-skill-keywords.py`. `tests/test_skill_keywords.py` skips on Python 3.10 (no `tomllib`) and per missing library.
- Nothing from the task list was dropped or deferred.
