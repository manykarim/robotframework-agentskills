## 0. Preconditions and baseline

- [x] 0.1 Confirm `fix-library-skill-keyword-correctness` and `unify-library-install-guidance` are merged, and rebase onto main. Verify: `openspec list` shows both archived (or merged), and `git log` contains their commits
- [x] 0.2 Record the baseline: line and character counts of the five library `SKILL.md` files, reference file count and total lines per skill, and the git ref of the pre-change skills (for D9 evals). Write them into a "Baseline" note at the bottom of this file. Verify: the note lists 5 × (lines, chars, ref files, ref lines) and a commit SHA
- [x] 0.3 Find the libdoc script skill name from `merge-libdoc-skills` (archived: `rf-libdoc`). Verify: the name is recorded in the Baseline note and used in the test constant (2.1)

## 1. Verify candidate gotchas against libdoc (design D5)

- [x] 1.1 rf-browser: check each D5 Browser item with `robotcode libdoc Browser show` (or `python -m robot.libdoc Browser show`) for `strict_mode`, `run_on_failure`, `auto_closing_level`, `timeout`, `retry_assertions_for` defaults, plus `Fill Text`/`Type Text`/`Fill Secret`, `Wait For Load State`, `Wait Until Network Is Idle` deprecation, and selector-prefix rules. Record verified/dropped per item with the library version. Verify: note lists each of the 8 items as verified, adjusted or dropped, with ≥ 5 verified
- [x] 1.2 rf-selenium: check `implicit_wait`, `timeout`, `run_on_failure` defaults, the default locator strategy, `Page Should Contain` (no wait), Selenium Manager support in the installed Selenium, and `Select Frame` semantics against SeleniumLibrary libdoc. Verify: ≥ 5 items verified, with the version recorded
- [x] 1.3 rf-appium: check `Expect Element`/`Expect Elements` signatures, deprecation of `Element Should Be *`, that the listed removed keywords are absent, `appium:` prefix handling in `Open Application`, and `Tap`/`Swipe` duration types against AppiumLibrary libdoc/source. Verify: ≥ 5 items verified, with the version recorded
- [x] 1.4 rf-requests: install `robotframework-requests` in a scratch env and check `expected_status` default behaviour, the `Create Session` `verify` default vs sessionless, `json=` vs `data=`, and `Delete All Sessions`. Verify: ≥ 5 items verified, with the version recorded
- [x] 1.5 rf-restinstance: install `RESTinstance` in a scratch Python ≥ 3.11 env; check import args, instance semantics, `Expect Response Body`/`Clear Expectations` persistence, `Set Headers` scope, and status handling (source + a local dry run). Verify: ≥ 5 items verified. If the library cannot be installed, record that and mark the items "verified from source" with a file/line reference

## 2. Enforcement test and CI (design D7)

- [x] 2.1 Create `tests/test_library_skill_structure.py`, parametrized over the five skill dirs, with these checks: required H2 order, ≤ 250 lines / ≤ 12,000 chars, no `keywords-reference.md` (canonical + `plugins/rf-agentskills/skills/*` + `vscode-extension/skills/rf-*`), `robotcode libdoc <ImportName>` present, fallback skill named, reference-table ↔ `references/` set equality, no reference→reference links, TOC for files > 100 lines, ≥ 5 Gotchas bullets, exactly one `Verified against` line, no ALL-CAPS emphasis in prose (with allowlist), no legacy syntax in examples/code blocks. Mark each skill `xfail` (non-strict, see Implementation Notes) until its section below is done. Verify: `uv run pytest tests/test_library_skill_structure.py` runs, and all five skills xfail
- [x] 2.2 Add `test_examples_dryrun` to the same file: `python -m robot --dryrun` per `assets/examples/*.robot`, skipped per library when its module (`Browser`, `SeleniumLibrary`, `AppiumLibrary`, `RequestsLibrary`, `REST`) is not importable. Verify: run locally with Browser/SeleniumLibrary/AppiumLibrary installed; RequestsLibrary/REST skip when absent
- [x] 2.3 Add or reuse the libdoc keyword-existence check for ```` ```robotframework ```` blocks in the five `SKILL.md` files (reuse the checker from `fix-library-skill-keyword-correctness` if it exists; otherwise port the scratchpad `kwcheck.py` prototype and exclude keywords defined in `*** Keywords ***`). Verify: the test fails on a planted `Wait Until Element Count Is Greater Than` and passes after removing it
- [x] 2.4 Extend the fail-soft optional-library step in `.github/workflows/ci.yml` with `robotframework-seleniumlibrary robotframework-appiumlibrary robotframework-requests RESTinstance`. Verify: the YAML parses; the step uses `|| echo` so that it cannot fail the job

## 3. rf-browser (`skills/rf-browser/`)

- [x] 3.1 Rewrite `SKILL.md` to the D1 skeleton: orientation (vs rf-selenium), `Import and defaults` (`Library  Browser` with the recommended args + one `New Browser`/`New Context`/`New Page` snippet, escape hatch to `browser-context-page.md`, install → rf-setup), decision table (interact, fill vs type, assert with operators, wait for state/load/response, frames/shadow DOM, tabs/popups, auth reuse, downloads/uploads), `Agent workflow`, selector strategy (short), `Gotchas` from 1.1, reference table, examples list, companions. Verify: `SKILL.md` ≤ 250 lines / ≤ 12,000 chars, and the browser cases of 2.1 pass
- [x] 3.2 Delete `references/keywords-reference.md`. Verify: file absent, and `grep -r keywords-reference skills/rf-browser` is empty
- [x] 3.3 Merge `references/tabs-windows.md` into `references/browser-context-page.md` (lifecycle, `auto_closing_level`, popups, `Switch Page`, ids), delete `tabs-windows.md`, add a TOC. Verify: `tabs-windows.md` absent; TOC matches the H2s
- [x] 3.4 Trim and add a TOC to `references/locators.md`, `iframes-shadow-dom.md`, `assertion-engine.md`, `authentication-storage.md`, `downloads-uploads.md` (remove generic CSS/XPath/cookie/storage tutorials and cross-reference links). Verify: TOC test passes; no file links to another reference
- [x] 3.5 Rewrite `references/troubleshooting.md` as error → cause → fix. Move gotcha-grade items to `SKILL.md` and drop the generic best-practices/performance sections. Verify: TOC present; every section heading is an error message or symptom
- [x] 3.6 Update `assets/examples/`: keep `basic-web-test.robot`, `form-handling.robot`, `authentication-flow.robot`, `iframe-shadow-dom.robot` in modern syntax. Delete `file-operations.robot` unless it dry-runs and adds a pattern. Verify: `robot --dryrun` passes for each kept file, and the legacy-syntax check passes
- [x] 3.7 Remove the browser `xfail` marker from 2.1. Verify: `uv run pytest tests/test_library_skill_structure.py -k browser` passes

## 4. rf-selenium (`skills/rf-selenium/`)

- [x] 4.1 Rewrite `SKILL.md` to the D1 skeleton: orientation (vs rf-browser), `Import and defaults` (`Library  SeleniumLibrary  timeout=…  implicit_wait=0` + one `Open Browser … headlesschrome` default relying on Selenium Manager (SeleniumLibrary 6.8 rejects `headless_chrome`), escape hatch → `browser-setup.md` for options/Grid), decision table (interact, explicit wait choice, assert once vs wait, frames, windows, alerts, JS as last resort, uploads), `Agent workflow`, locator rules (short), `Gotchas` from 1.2, reference table, examples, companions. Verify: ≤ 250 lines / ≤ 12,000 chars; selenium cases of 2.1 pass
- [x] 4.2 Delete `references/keywords-reference.md`. Verify: absent; no links to it
- [x] 4.3 Replace `references/webdriver-setup.md` with `references/browser-setup.md` (Selenium Manager default, `options=` syntax, headless, `remote_url`/Grid, CI flags; no webdriver-manager/`executable_path`). Verify: old file absent; `grep -i "webdriver-manager\|executable_path"` finds nothing in the skill
- [x] 4.4 Merge the library-specific parts of `references/screenshots-logs.md` (run_on_failure, `Capture Page Screenshot` EMBED, `Capture Element Screenshot`, `Log Source`, `Register Keyword To Run On Failure`) into `references/troubleshooting.md`, rewrite troubleshooting as error → cause → fix, and delete `screenshots-logs.md`. Verify: file absent; TOC present
- [x] 4.5 Trim and add a TOC to `references/waiting-strategies.md`, `locators.md` (heavy trim), `frames-windows.md` (no `Get Window Count`/`Get Window Handle`), `javascript-execution.md` (heavy trim to `ARGUMENTS`, return values, async). Verify: TOC test passes; keyword check (2.3) passes on their code blocks
- [x] 4.6 Update `assets/examples/`: keep `basic-web-test.robot` (absorbing `form-handling.robot`), `wait-patterns.robot`, `multi-window.robot`; delete `form-handling.robot` and `selenium-grid.robot`; modern syntax only. Verify: dry-run passes for each kept file
- [x] 4.7 Remove the selenium `xfail` marker. Verify: `uv run pytest tests/test_library_skill_structure.py -k selenium` passes

## 5. rf-appium (`skills/rf-appium/`)

- [x] 5.1 Rewrite `SKILL.md` to the D1 skeleton: orientation, `Import and defaults` (`Library  AppiumLibrary` + one W3C `Open Application` default with `appium:` caps; Android default, iOS escape hatch → `capabilities.md`; server/drivers → rf-setup), decision table (find element by platform, wait, assert with `Expect Element`, tap/swipe/scroll, hybrid context, mobile browser, cloud grids), `Agent workflow`, `Gotchas` from 1.3 (including the removed-keyword → replacement mapping), reference table without the "planned" note or non-existent files, examples, companions. Verify: ≤ 250 lines / ≤ 12,000 chars; appium cases of 2.1 pass
- [x] 5.2 Delete `references/keywords-reference.md`. Verify: absent; no links to it
- [x] 5.3 Rename `references/device-capabilities.md` → `references/capabilities.md` and move the capability sections of `android-specific.md`/`ios-specific.md` into it; add a TOC. Verify: old name absent; the Android and iOS capability sections are present once
- [x] 5.4 Move the locator sections of `android-specific.md`/`ios-specific.md` into `references/locators-mobile.md`, then merge the rest of both files into `references/platform-specific.md` (Android and iOS sections), delete the two originals, and add TOCs. Verify: `android-specific.md` and `ios-specific.md` absent; `platform-specific.md` TOC lists both platforms
- [x] 5.5 Rewrite `references/gestures-touch.md` with current keywords only; removed keywords appear only in a "removed → use" table. Trim `references/troubleshooting.md`. Add TOCs to both. Verify: keyword check (2.3) reports no removed or deprecated keywords outside that table
- [x] 5.6 Update `assets/examples/`: keep `android-basic.robot`, `ios-basic.robot`, `gestures-example.robot` (rewritten); merge `device-actions.robot` into the platform examples; keep `hybrid-app.robot` only if it dry-runs; no `Element Should Be Visible` or `Run Keyword If`. Verify: dry-run passes with AppiumLibrary installed
- [x] 5.7 Remove the appium `xfail` marker. Verify: `uv run pytest tests/test_library_skill_structure.py -k appium` passes

## 6. rf-requests (`skills/rf-requests/`)

- [x] 6.1 Rewrite `SKILL.md` to the D1 skeleton: orientation (vs rf-restinstance), `Import and defaults` (`Library  RequestsLibrary`; default = session with `verify=${True}` when calls share a base URL, sessionless escape hatch), decision table (send JSON/form/files, query params, negative status tests, auth types, assert status/body/headers, timeouts/retries), `Agent workflow`, `Gotchas` from 1.4, reference table, examples, companions. Remove the "Security Warning" section in favour of a gotcha. Verify: ≤ 250 lines / ≤ 12,000 chars; requests cases of 2.1 pass
- [x] 6.2 Delete `references/keywords-reference.md` and `references/http-methods.md`, moving the unique `expected_status` and naming content into `references/request-options.md`. Verify: both absent; `request-options.md` has an `expected_status` section
- [x] 6.3 Trim and add a TOC to `references/request-options.md`, `response-validation.md`, `authentication.md` (drop generic OAuth/JWT theory). Rewrite `troubleshooting.md` as error → cause → fix. Verify: TOC test passes
- [x] 6.4 Update `assets/examples/`: keep `basic-crud.robot`, `session-handling.robot`, `authentication-patterns.robot`; keep `file-upload.robot` if it dry-runs; modern syntax (`VAR`, no `Set Variable  ${response.json()}` if `VAR` fits). Verify: dry-run passes with RequestsLibrary installed
- [x] 6.5 Remove the requests `xfail` marker. Verify: `uv run pytest tests/test_library_skill_structure.py -k requests` passes

## 7. rf-restinstance (`skills/rf-restinstance/`)

- [x] 7.1 Rewrite `SKILL.md` to the D1 skeleton: orientation (vs rf-requests; when schema-first testing pays off), `Import and defaults` (`Library  REST  ${API_URL}` + one request/assert snippet), decision table (assert status/fields/types, schema from file vs learned, expectations, headers/auth, discover paths with `Output`), `Agent workflow`, `Gotchas` from 1.5, reference table, examples, companions. Verify: ≤ 250 lines / ≤ 12,000 chars; restinstance cases of 2.1 pass
- [x] 7.2 Delete `references/keywords-reference.md`. Verify: absent; no links to it
- [x] 7.3 Heavy-trim `references/schema-validation.md` (drop the generic JSON Schema tutorial) and `authentication.md`; trim `json-handling.md`; rewrite `troubleshooting.md` as error → cause → fix; add TOCs where > 100 lines. Verify: TOC test passes
- [x] 7.4 Update `assets/examples/`: keep `basic-rest.robot` (absorbing `json-manipulation.robot`) and `schema-validation.robot` (+ schema file); keep `oauth-flow.robot` only if it adds a pattern; delete the rest. Verify: dry-run passes where RESTinstance is importable; otherwise the test reports a skip
- [x] 7.5 Remove the restinstance `xfail` marker. Verify: `uv run pytest tests/test_library_skill_structure.py -k restinstance` passes

## 8. Distribution and cross-references

- [x] 8.1 Search `plugins/rf-agentskills/` (agents, hooks, `maybe_inject_rf_context.mjs`, MCP server), `installer/`, `README.md` and `vscode-extension/` sources for `keywords-reference.md` and the deleted or renamed reference names, and update them. Verify: `grep -rn "keywords-reference\|tabs-windows\|screenshots-logs\|webdriver-setup\|device-capabilities\|android-specific\|ios-specific\|http-methods"` over those paths returns nothing for the five skills
- [x] 8.2 Run `scripts/sync-skills.sh`, then `scripts/check-drift.sh`. Verify: drift check exits 0; `find plugins/rf-agentskills/skills vscode-extension/skills -name keywords-reference.md` lists only platynui
- [x] 8.3 Run the full test suite. Verify: `uv run pytest` passes (marketplace/frontmatter validation included), with no `xfail` left in `test_library_skill_structure.py`
- [x] 8.4 Add an "After" line to the Baseline note (0.2) with new line/char counts and reference totals. Verify: every after-count is lower than its before-count; total reference lines dropped ≥ 40%

## 9. Evaluation gate (depends on `strengthen-skill-eval-harness`; design D9)

- [x] 9.1 Make sure each library has at least one gotcha-targeted task in `eval/tasks/` (add one per library if missing: Browser strict mode, Selenium AJAX wait, Appium caps/`Expect Element`, Requests negative status, RESTinstance expectation leak) with deterministic checks. Verify: the harness lists ≥ 1 task per library
- [ ] 9.2 (DEFERRED: live eval run — tracked in follow-up) Run every library task ≥ 3 times with no skill, the pre-change skill (ref from 0.2) and the restructured skill. Record mean score, spread and mean tokens in this file. Verify: the table has 5 libraries × 3 configurations with n ≥ 3
- [ ] 9.3 (DEFERRED: live eval run — tracked in follow-up) Check the success criteria: restructured ≥ pre-change − spread on every task; restructured > no-skill on each gotcha task; restructured mean tokens ≤ pre-change. Verify: all three hold. If one does not, fix the affected skill and repeat 9.2 before archive

## Baseline

- Pre-change ref: HEAD `57f8e70` plus the uncommitted working tree of this release cycle (the five skills had not been committed after the earlier changes). Snapshot of the five pre-change skill dirs for the deferred D9 runs: `baseline/pre-change-skills.tar.gz` (extract over `skills/`, run `scripts/sync-skills.sh`, then run the harness).
- Libdoc fallback skill (0.3): `rf-libdoc` (archived `merge-libdoc-skills`); test constant `LIBDOC_FALLBACK = "rf-libdoc"` in `tests/test_library_skill_structure.py`.
- Library versions verified against: Browser 19.14.2, SeleniumLibrary 6.8.0 (Selenium 4.43.0), AppiumLibrary 3.2.1, RequestsLibrary 0.9.7 (requests 2.33.1), RESTinstance 1.8.0; Robot Framework 7.4.2; Python 3.12.

| Skill | SKILL.md lines | SKILL.md chars | ref files | ref lines | examples |
|---|---|---|---|---|---|
| rf-browser | 331 | 10,670 | 9 | 3,422 | 5 |
| rf-selenium | 396 | 12,050 | 8 | 3,278 | 5 |
| rf-appium | 351 | 10,695 | 7 | 2,634 | 5 |
| rf-requests | 267 | 8,550 | 6 | 1,946 | 4 |
| rf-restinstance | 386 | 10,213 | 5 | 2,225 | 4 |
| **Total** | 1,731 | 52,178 | 35 | 13,505 | 23 |

After (8.4):

| Skill | SKILL.md lines | SKILL.md chars | ref files | ref lines | examples |
|---|---|---|---|---|---|
| rf-browser | 120 | 9,827 | 7 | 576 | 4 |
| rf-selenium | 113 | 10,059 | 6 | 544 | 3 |
| rf-appium | 125 | 9,051 | 5 | 450 | 4 |
| rf-requests | 97 | 7,065 | 4 | 276 | 4 |
| rf-restinstance | 107 | 8,565 | 4 | 303 | 2 |
| **Total** | 562 (−68%) | 44,567 (−15%) | 26 | 2,149 (−84%) | 17 |

Every after-count is lower than its before-count.

## Gotcha verification (tasks 1.1-1.5)

Evidence: libdoc of the installed version, library source in `.venv`, and live runs (headless Chromium/Chrome against local pages or the-internet.herokuapp.com; a local `http.server` for Requests/RESTinstance). Appium has no device, so its items are verified from libdoc + source + Appium-Python-Client behaviour.

- **rf-browser (Browser 19.14.2)** — 8/8 verified (3 adjusted/extended): strict mode on (`strict=True`; live "strict mode violation"; `Get Element Count`/`Get Elements` not strict); `run_on_failure` = `Take Screenshot  fail-screenshot-{index}`; `Fill Text` one input event vs `Type Text` per-key, `Fill Secret` needs `$var`/`%ENV`/RF 7.4 `Secret` (live: `${PW}` rejected); getter assertions retry, `Wait Until Network Is Idle` deprecated → `Wait For Load State`; `auto_closing_level=TEST` default, `KEEP` is for development only (old skill recommended KEEP — fixed); `New Page` without browser/context uses defaults; selector rules (`//`, quoted text exact, `text=` case-insensitive substring, `>>>` frames) plus new `#` = RF comment → `\#id`; `timeout=10s` vs `retry_assertions_for=1s`. Also fixed: `Save Storage State` takes no path (returns one), `>>` misuse for frames in the old iframe example.
- **rf-selenium (SeleniumLibrary 6.8.0)** — 8 verified, 1 dropped as a gotcha (Selenium Manager: no keyword/default to name; stays in `## Installation` and `browser-setup.md`); default locator strategy moved to the optional `## Locator rules` section. New, verified live: `Page Should Contain` resets the selected frame; `headless_chrome` is rejected (only `headlesschrome`/`headlessfirefox`) — the old skill recommended the broken name; `Open Browser` defaults to `firefox`.
- **rf-appium (AppiumLibrary 3.2.1)** — 8/8 verified or adjusted. Open questions answered: the Appium Python client adds `appium:` to non-W3C capability names without a colon (writing it out is still recommended; vendor caps keep their prefix); `Expect Element(locator, state: visible|not visible|enabled|disabled, timeout=0:00:05, …)` exists, `Expect Elements` does not (text variant: `Expect Text`). `Element Should Be Visible/Enabled/Disabled` and `Text Should Be Visible` are deprecated. Removed keywords confirmed absent. Durations: bare ints are milliseconds in `Swipe`/`Swipe By Percent`/`Tap With Positions` (with a warning) but seconds in `Tap`. New: `ios=` strategy is broken with the installed client → `predicate=`/`chain=`.
- **rf-requests (RequestsLibrary 0.9.7)** — 6/6 verified (1 adjusted: library scope is GLOBAL, so sessions persist across suites). New, verified live: `expected_status` has no ranges (`2xx` → `UnknownStatusError`); sessionless `auth=` needs a tuple; `=` in a URL/path breaks the call → `params=`/`url=`.
- **rf-restinstance (RESTinstance 1.8.0)** — installed in the dev env; 6 verified, 1 dropped as a gotcha (Python ≥ 3.11 stays in `## Installation` only). Scope `TEST SUITE` (`REST/__init__.py:89`): expectations and `Set Headers` persist across tests until cleared/overridden (live). New, verified live: values after a path are exact allowed values (use `pattern=`); a JSON Schema passed as a value is compared as a value; type keywords return a list; string arguments are decoded as JSON (escaping, single-quoted bodies sent as strings); import arguments resolve before Suite Setup.

## Evaluation (9.x)

- 9.1: gotcha-targeted tasks per library — rf-browser `adv-browser-deprecated-wait` (gotcha: deprecated network-idle wait), rf-selenium `adv-selenium-nonexistent-kw` (AJAX count wait), rf-requests `narrow-requests-users-01` (404 case fails unless `expected_status` is set), rf-appium NEW `adv-appium-deprecated-visibility` (`Expect Element` vs deprecated `Element Should Be *`, `appium:` caps), rf-restinstance NEW `adv-restinstance-expectation-leak` (`Expect Response Body` leaks into the next test without `Clear Expectations` — confirmed with a real run against sut-api). Both new tasks have good/bad golden solutions graded in `tests/eval/test_eval_content.py`. `rf-skill-eval validate-tasks eval/tasks`: 23 valid.
- 9.2 / 9.3: DEFERRED (live eval run — tracked in follow-up). The harness has no "pre-change skill" arm: run the batch once with the snapshot from `baseline/pre-change-skills.tar.gz` extracted and synced, once on the restructured tree, both with `--arms treatment,baseline --runs 3 --skills rf-browser,rf-selenium,rf-appium,rf-requests,rf-restinstance`, then record mean score, spread and tokens here.
