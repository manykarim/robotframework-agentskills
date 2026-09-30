## 1. Checker and dev dependencies

- [x] 1.1 Add `robotframework-browser`, `robotframework-seleniumlibrary`, `robotframework-appiumlibrary`, `robotframework-requests`, `RESTinstance` and `robotframework-PlatynUI==0.12.0.dev330` to `[dependency-groups] dev` in `pyproject.toml` (design D8), then run `uv sync`. Verify: `uv run python -c "import Browser, SeleniumLibrary, AppiumLibrary, RequestsLibrary, REST; from PlatynUI import BareMetal"` exits 0
- [x] 1.2 Create `scripts/check-skill-keywords.py`, promoted from the evaluation prototype `kwcheck2.py`. It needs:
  - the two extractors (D2) and the resolution order with RF name normalization and embedded-arg matching (D3)
  - the UNKNOWN / DEPRECATED / LEGACY classes plus wrapper-keyword arguments (D4)
  - the `Wait For Condition` vocabulary rule (D6)
  - SKIPPED handling with a `--require-all` flag (D7)
  - `--skills-root` (default `skills`) and `--allowlist` options
  - output lines `SKILL FILE:LINE CLASS KEYWORD ~ suggestions`, then a per-skill summary

  Verify: `uv run python scripts/check-skill-keywords.py --help` works, and a run on the current tree reproduces every defect listed in group 2
- [x] 1.3 Create `scripts/skill-keywords-allowlist.toml` (`[[allow]] skill/file/keyword/reason`) with stale-entry detection (D5). Start it empty, and add entries only for the illustrative app keywords kept in 2.1.5/2.1.6 if they are not stubbed. Verify: an entry that matches nothing makes the checker exit 1 and names the entry
- [x] 1.4 Create `tests/test_skill_keywords.py` with these cases, run on fixture skills under `tests/fixtures/skill_keywords/`:
  - (a) a clean fixture passes
  - (b) a deprecated keyword fails
  - (c) a nonexistent keyword fails and gets a suggestion
  - (d) a locally defined user keyword (including embedded args) passes
  - (e) `Run Keyword If` fails
  - (f) an allowlisted call passes and a stale entry fails
  - (g) `Wait For Condition    Get Text …` fails
  - (h) settings lines, `${a}    ${b}=` multi-assign, `IF/FOR/VAR`, and indented fenced blocks inside list items produce no false positives

  Also add (i) a real-tree test per library skill, which uses `pytest.importorskip` for the library and asserts exit 0. Verify: `uv run pytest tests/test_skill_keywords.py` passes after group 2, and cases (a)–(h) pass before group 2

## 2. Fix keyword defects in root `skills/` (defects found by the prototype checker on 2026-09-27; line numbers are first occurrences)

### 2.1 rf-browser (`skills/robotframework-browser-skill/`)
- [x] 2.1.1 `SKILL.md`:
  - L121: `Get Element States button#submit` uses a single-space separator. Change it to `Get Element States    button#submit`.
  - L249: rewrite the `Wait For Condition` comment. It is a timed wrapper around assertion getters, not a JavaScript condition.
  - L252–253: `Wait Until Network Is Idle` is deprecated. Change it to `Wait For Load State    networkidle    timeout=10s`.
  - L211: replace `Test Teardown    Run Keyword If Test Failed    Take Screenshot` with a note that `run_on_failure` (default `Take Screenshot`) already covers this.

  Verify: the checker reports rf-browser `SKILL.md` clean
- [x] 2.1.2 `Fill` → `Fill Text` everywhere: `references/iframes-shadow-dom.md` (12, from L34), `references/authentication-storage.md` (10, from L22), `references/locators.md` (6, from L169), `references/keywords-reference.md` (3, from L70; fix the heading too), `references/tabs-windows.md` (3, from L145), `references/browser-context-page.md` (2, from L116), `references/troubleshooting.md` (2, from L271). Verify: `grep -rnE '^\s*Fill\s{2,}' skills/robotframework-browser-skill` returns nothing
- [x] 2.1.3 `references/keywords-reference.md`:
  - L280: `Get Bounding Box` → `Get BoundingBox`
  - L595–607: remove the `Route`/`Unroute` sections and replace them with a short note (D10)
  - L333–338: replace the `Wait For Condition    condition` placeholder with real condition names

  `references/troubleshooting.md`:
  - L157: `Promise To Wait For Response` → `Promise To    Wait For Response`
  - L366: `Promise To Wait For Request` → `Promise To    Wait For Request`
  - L352: remove the `Route` example
  - L393: `Get Bounding Box` → `Get BoundingBox`

  Verify: the checker reports both files clean
- [x] 2.1.4 `Wait For Condition` arguments:
  - `references/downloads-uploads.md` L253: `Get Text` → `Text`
  - `references/tabs-windows.md` L261: `Get Page Ids    validate` is not a valid condition. Rewrite it with `Wait Until Keyword Succeeds` + `Get Page Ids`.
  - `assets/examples/file-operations.robot` L178 (commented example): `Get Text` → `Text`

  Verify: the D6 rule passes
- [x] 2.1.5 `references/tabs-windows.md`: L103 `Get Page Catalog` → `Get Browser Catalog`. L304 `Create New Item` and L313 `Delete Item` are illustrative app keywords: add stub definitions in a `*** Keywords ***` part of the snippet, or add allowlist entries with reasons. Verify: the checker reports the file clean
- [x] 2.1.6 `references/browser-context-page.md`: L267 (2×) `Get Context Id    CURRENT` → `Get Context Ids    CURRENT`, and take the first element (or use `Switch Context` with the returned id from `New Context`). L277 `Create Item`: stub it or allowlist it as in 2.1.5. Verify: the checker reports the file clean

### 2.2 rf-selenium (`skills/robotframework-selenium-skill/`)
- [x] 2.2.1 `SKILL.md`:
  - L123: `Go Forward` does not exist. Change it to `Execute Javascript    history.forward()`, or drop it.
  - L218: `Title Should Contain` → `${title}=    Get Title` + `Should Contain`.
  - L253–255 and a second `Wait Until Element Count Is Greater Than` near L307: replace `Wait Until Element Count Is` / `… Greater Than` / `… Less Than` with `Wait Until Keyword Succeeds    10s    500ms    <count assertion>` using `Get Element Count`, or with `Page Should Contain Element    locator    limit=N` for exact counts.

  Verify: the checker reports rf-selenium `SKILL.md` clean
- [x] 2.2.2 `references/waiting-strategies.md`: the same `Wait Until Element Count Is*` fix (6 calls, from L56). Verify: the checker reports the file clean
- [x] 2.2.3 `references/keywords-reference.md`:
  - L63: `Get Window Handle` → `Get Window Handles`
  - L95: remove `Go Forward`
  - L291–293: `Wait Until Element Count Is*` (as in 2.2.1)
  - L330: `Element Attribute Value Should Not Be` → `Get Element Attribute` + `Should Not Be Equal`
  - L337: `Title Should Start With` → `Get Title` + `Should Start With`
  - L338: `Title Should Match` → `Get Title` + `Should Match`
  - L439: `Get Cookie Value` → `${cookie}=    Get Cookie    name` / `${cookie.value}`

  Verify: the checker reports the file clean
- [x] 2.2.4 `references/frames-windows.md`: `Get Window Handle` (8 calls, from L13) → `Get Window Handles`, or `Switch Window    MAIN` / `NEW` where the handle is only used to switch back. Keep the locally defined `Get Window Count` user keyword (L176) and confirm that its body uses real keywords. Verify: the checker reports the file clean
- [x] 2.2.5 `references/locators.md` L294: `Get Element Index` does not exist. Rewrite it using `Get Element Count` over the preceding siblings `xpath=//th[text()='Name']/preceding-sibling::th`. Verify: the checker reports the file clean
- [x] 2.2.6 `assets/examples/selenium-grid.robot` L162 and `references/webdriver-setup.md` L426: `Get Browser Capabilities` → user keyword via `Execute Javascript    return navigator.userAgent` or remove it. The `Get Chrome Driver` / `browser_setup.py` webdriver-manager section (L30–40) is removed by change `unify-library-install-guidance`. If that change lands later, allowlist it temporarily with reason `removed by unify-library-install-guidance`. Verify: `uv run python -c "from robot.api import get_model; get_model('skills/robotframework-selenium-skill/assets/examples/selenium-grid.robot')"` passes and the checker is clean
- [x] 2.2.7 `assets/examples/form-handling.robot` L100: `Run Keyword If    ${data}[newsletter]    Select Checkbox    id=newsletter` → `IF    ${data}[newsletter]    Select Checkbox    id=newsletter    END` (inline IF) or a block IF. Verify: the file still parses and the checker reports no LEGACY entry

### 2.3 rf-appium (`skills/robotframework-appium-skill/`)
- [x] 2.3.1 `SKILL.md` L145–146: `Element Should Be Visible` / `Element Should Be Enabled` (deprecated in 3.2.1) → `Expect Element    locator    visible` / `enabled`. Verify: the checker reports `SKILL.md` clean
- [x] 2.3.2 `references/keywords-reference.md`:
  - L114–116: these assign `${visible}=` etc. from assertion keywords, which return `None`. Change them to `${visible}=    Run Keyword And Return Status    Expect Element    locator    visible` (likewise `enabled`/`disabled`)
  - L162–165: `Element Should Be Visible` / `Element Should Not Be Visible` / `Element Should Be Enabled` / `Element Should Be Disabled` → `Expect Element … visible|not visible|enabled|disabled`
  - L128: `Wait Until Element Is Not Visible` → `Wait Until Page Does Not Contain Element`
  - L33: `Quit Application` → `Close Application`
  - L52: `Reset Application` → remove, with a note on `noReset`/`fullReset`
  - L53–56: `Background App` / `Activate App` / `Terminate App` / `Launch App` → `Background Application` / `Activate Application` / `Terminate Application` / `Activate Application`
  - L59, L67–68: `Query App State` / `Remove App` / `Is App Installed` → `Execute Script    mobile: queryAppState` / `Remove Application` / `Execute Script    mobile: isAppInstalled`
  - L78: `Click Button` → `Click Element` / `Click Text`
  - L81–82, L259: `Long Press` → `Tap    locator    duration=2s`
  - L85: `Click A Point` → `Tap With Positions`
  - L190–191: `Pinch` / `Zoom` → `Execute Script    mobile: pinchCloseGesture` / `pinchOpenGesture` (D10)
  - L236–237: `Get Url` / `Get Title` → `Get Window Url` / `Get Window Title`
  - L295: remove `Get Appium Attribute`
  - L298: `Set Orientation` → `Landscape` / `Portrait`
  - L305: `Get Window Size` → `Get Window Width` + `Get Window Height`
  - L202: drop `Run Keyword If Test Failed    Capture Page Screenshot` in favour of the note that `run_on_failure` captures on failure

  Verify: the checker reports the file clean
- [x] 2.3.3 `references/gestures-touch.md`:
  - L185–199 (5 calls): `Long Press` → `Tap … duration=`
  - L215–232 (4 calls): `Click A Point` → `Tap With Positions`
  - L240–263 (7 calls): `Pinch` / `Zoom` → `mobile:` gesture commands
  - L51 and others (6 calls in total): `Get Window Size` → `Get Window Width` / `Get Window Height`
  - L176: `Length Should Be Greater Than` → `Get Length` + `Should Be True`

  Confirm each `mobile:` command name and argument set against the UiAutomator2 and XCUITest driver docs, and note the source in the file. Verify: the checker reports the file clean
- [x] 2.3.4 `references/android-specific.md`:
  - L272–288: `Query App State`, `Remove App`, `Is App Installed`, `Terminate App`, `Activate App` → the `*Application` keywords or `mobile:` commands
  - L295–298: `Set Clipboard` / `Get Clipboard` → `Execute Script    mobile: setClipboard` / `mobile: getClipboard`
  - L305: remove `Get Appium Attribute`
  - L308: `Set Orientation` → `Landscape` / `Portrait`
  - L343: `Get Window Size` → `Get Window Width` / `Get Window Height`

  `references/ios-specific.md`:
  - L248: remove `Get Appium Attribute`
  - L251: `Set Orientation` → `Landscape` / `Portrait`
  - L302: `Get Window Size` → `Get Window Width` / `Get Window Height`

  Verify: the checker reports both files clean

### 2.4 rf-requests (`skills/robotframework-requests-skill/`)
- [x] 2.4.1 `references/http-methods.md` L127: `OPTIONS On Session myapi` uses a single-space separator. Change it to `OPTIONS On Session    myapi`. `references/troubleshooting.md`:
  - L389–393: replace the `Open File` / `Write To File` / `Close File` pseudo-code with `Create Binary File    ${OUTPUT_DIR}/large_file.bin    ${response.content}`, and note that streaming to disk needs a Python helper
  - L112: define `Get Fresh Token` in the snippet, or allowlist it with a reason

  Verify: the checker reports rf-requests clean

### 2.5 rf-restinstance and rf-platynui
- [x] 2.5.1 Run the checker with RESTinstance and PlatynUI installed. Both were clean in the 2026-09-27 prototype run. Verify: both skills are reported as checked (not SKIPPED) with 0 findings

## 3. rf-results criticality removal (BREAKING contract change)

- [x] 3.1 `skills/robotframework-results/scripts/rf_results.py`: delete `_critical_group`, `critical_stats` and the `details.criticality` key. Verify: `uv run python skills/robotframework-results/scripts/rf_results.py --output <fixture> --sections details` has no `criticality` key
- [x] 3.2 `skills/robotframework-results/SKILL.md`: remove "criticality" from the frontmatter description and body (L3, L11, L47, L53). The description keeps "tag stats". Verify: `grep -ni critical skills/robotframework-results/SKILL.md` returns nothing
- [x] 3.3 `tests/test_rf_results.py::test_details_section`: replace `assert "criticality" in details` with `assert "criticality" not in details`. Verify: `uv run pytest tests/test_rf_results.py` passes
- [x] 3.4 Add an "Unreleased → Changed (BREAKING)" entry to `installer/CHANGELOG.md`: `rf_results` / `rf_results_analyze` no longer emit `details.criticality` (removed in RF 4.0; use `details.tags`). Verify: the entry is present

## 4. Sync, CI and verification

- [x] 4.1 Run `bash scripts/sync-skills.sh`, then `bash scripts/check-drift.sh`. Verify: no drift. `plugins/rf-agentskills/scripts/rf_results.py` and `plugins/rf-agentskills/skills/{browser,selenium,appium,requests,results}/` reflect the fixes
- [x] 4.2 Add a `check-skill-keywords` job to `.github/workflows/ci.yml`: ubuntu-latest, Python 3.12, `pip install robotframework robotframework-browser robotframework-seleniumlibrary robotframework-appiumlibrary robotframework-requests RESTinstance "robotframework-PlatynUI==0.12.0.dev330"` (or `uv sync`), then `python scripts/check-skill-keywords.py --require-all`. Verify: the job YAML parses, and a local `act`-free dry run of the same commands exits 0
- [x] 4.3 Run the checker against the plugin copies with `--skills-root plugins/rf-agentskills/skills` (short dir names map to the same libraries). Verify: the same result as on root
- [x] 4.4 Full verification: `uv run python scripts/check-skill-keywords.py --require-all`, `uv run pytest tests/ --ignore=tests/eval`, `ruff check scripts/check-skill-keywords.py --select E,F,W --ignore E501`, and the `validate-robot-syntax` snippet. Verify: all exit 0. Run the checker twice to confirm deterministic output (identical stdout)
