## Context

See proposal.md (Why). Current state of the five Gen-1 library skills:

| Skill | SKILL.md lines | references (lines) | `keywords-reference.md` | examples |
|---|---|---|---|---|
| rf-browser | 309 | 9 files, 3,393 | 606 | 5 |
| rf-selenium | 393 | 8 files, 3,328 | 604 | 5 |
| rf-appium | 341 | 7 files, 2,596 | 362 | 5 |
| rf-requests | 260 | 6 files, 1,941 | 343 | 4 |
| rf-restinstance | 379 | 5 files, 2,225 | 524 | 4 |

- Every reference file is over 100 lines and none has a table of contents. rf-appium's reference table lists two files that do not exist (`locators-android.md`, `locators-ios.md`) and says the files are "planned".
- The Gen-2 skills (`skills/rf-robotcode/SKILL.md` 129 lines, `skills/rf-setup/` 123, `skills/rf-platynui/` 249) set the pattern: quick orientation, availability/default, decision table, numbered workflow, "Top traps", gated reference table, companion skills.
- `scripts/sync-skills.sh` runs `rm -rf` on each plugin skill's `references/` and `assets/`, and on the whole VS Code skills tree, before copying. Deleted files therefore disappear from both channels, and `scripts/check-drift.sh` sees the result.
- CI (`.github/workflows/ci.yml`) already installs optional libraries fail-soft (PlatynUI, Browser, robotcode) so that tests skip rather than fail. `tests/test_setup_skill.py::test_smoke_example_passes_dryrun` is the existing pattern for dry-running an example.
- Preconditions from other changes: `fix-library-skill-keyword-correctness` removes the known wrong, deprecated and removed keywords (and may add a keyword checker); `unify-library-install-guidance` moves install steps to rf-setup; `merge-libdoc-skills` renames the libdoc script skill (assumed `rf-libdoc`); `sharpen-skill-descriptions` owns frontmatter descriptions; `strengthen-skill-eval-harness` adds with/without-skill baselines and repeated runs.

## Goals / Non-Goals

**Goals:**
- One skeleton shared by all five library skills, so agents and maintainers find the same things in the same place.
- Measurably smaller `SKILL.md` files that still carry the library-specific traps.
- No hand-maintained keyword catalogs; libdoc is the single source for signatures.
- References that are all linked, gated by a "when", navigable (TOC), and not redundant.
- Examples that CI proves still parse and resolve.

**Non-Goals:**
- Changing frontmatter `description` text (owned by `sharpen-skill-descriptions`).
- Fixing individual wrong keywords (owned by `fix-library-skill-keyword-correctness`; this change only keeps them fixed).
- Install instructions (owned by `unify-library-install-guidance` / rf-setup).
- rf-platynui, rf-robotcode, rf-setup: already Gen-2. rf-platynui's `keywords-reference.md` stays for now, because BareMetal is a pre-release whose libdoc is the only other source. A later change can apply the same rule to it.
- Changes to the eval harness itself.

## Decisions

### D1. Standard library SKILL.md skeleton

```markdown
---
name: rf-<lib>
description: <unchanged here>
---

# <Library> Skill

<2–5 lines: what the library is for; when to use the sibling skill instead
(Browser ↔ Selenium, Requests ↔ RESTinstance).>
Verified against <library> <x.y.z>, Robot Framework <x.y>.

## Installation
<Unchanged block from unify-library-install-guidance: **rf-setup** pointer,
the uv command(s) from rf-setup Step 4, the post-install essential.
The only place install commands appear.>

## Import and defaults
<One recommended Library import with recommended arguments, each with a
short "because". One recommended open/session snippet.
Escape hatch: "Use X when Y — see references/<file>.md".>

## Which keyword for which situation
| Situation | Use | Details |
<8–15 rows; keyword or approach; reference file or "—".>

## Agent workflow
1. Look up signatures: `robotcode libdoc <Lib> show "<Keyword>"`
   (list: `robotcode libdoc <Lib> list "*text*"`; without robotcode: rf-libdoc).
2. Write the test (patterns above; keywords exactly as libdoc shows them).
3. `robot --dryrun --outputdir results/dryrun <suite>` — fix every error.
4. Run: `robot --outputdir results <suite>` (or `robotcode robot …`).
5. Read the results: `robotcode results summary --failed` / `results log --failed`
   (without robotcode: rf-results). Don't parse output.xml by hand.
6. Fix, then go back to step 3. Stop when green or when the failure is shown
   to be in the system under test, and report which.

## <optional: Locator strategy / one short pattern>

## Gotchas
- **<trap>** — <what happens> because <library default/design>. Write <X> instead.
<≥5 items>

## When to read the references
| Read | When |

Examples in `assets/examples/`: <list>.

## Companion Skills
| Need | Skill |
```

Why this skeleton: it matches the Gen-2 skills that already work (decision table → workflow → traps → gated references), puts defaults before choices, and makes the validation loop explicit, which Gen-1 skills lack. The section names are fixed so a test can check them. Alternative considered: reuse the Gen-2 headings verbatim ("Quick Reference", "Top traps"). Rejected, because "Quick Reference" invites a keyword list again and "Top traps" suggests a subset. "Gotchas" matches agentskills.io wording.

Workflow wording: the libdoc and results steps name both the robotcode command and the script-skill fallback, as rf-robotcode's companion table does. That keeps the skill usable without robotcode.

### D2. Size budget: ≤ 250 lines and ≤ 12,000 characters

Lines are what humans review. Characters/4 is a stable, dependency-free stand-in for tokens that a test can compute (no tokenizer dependency in CI). 12,000 characters ≈ 3,000 tokens. rf-platynui (249 lines) shows that a complete library skill fits. Targets per skill are about 150–200 lines. What goes: generic HTTP, CSS, XPath, JSON Schema and WebDriver explanations; per-keyword example blocks the libdoc lookup replaces; duplicated "Common Patterns"; install sections.

### D3. Delete `keywords-reference.md`; point to libdoc

The catalogs duplicate libdoc, have drifted (removed and non-existent keywords are listed), and are the biggest token sink. `robotcode libdoc <Lib> list/show` (or the libdoc script) always matches the installed version. Import names used in the instruction: `Browser`, `SeleniumLibrary`, `AppiumLibrary`, `RequestsLibrary`, `REST`. Coordination: the fallback skill name follows `merge-libdoc-skills`, which shipped it as `rf-libdoc` (script `uv run python scripts/rf_libdoc.py`, see `skills/rf-libdoc/SKILL.md`). The test reads the fallback name from one constant (`LIBDOC_FALLBACK`).

Alternative considered: generate the catalogs from libdoc in CI. Rejected, because the agent can query libdoc directly and a generated catalog still costs tokens to read.

### D4. Reference review (keep / merge / delete)

Rules: a file stays only if it holds library-specific knowledge that is not in `SKILL.md` and that the model is unlikely to know or often gets wrong. Generic tutorial content is deleted, not moved. Every remaining file over 100 lines gets a TOC. There are no cross-links between references.

**rf-browser**

| File | Decision | Rationale |
|---|---|---|
| `keywords-reference.md` | delete | Catalog; libdoc replaces it (D3). |
| `locators.md` | keep, trim, TOC | Playwright selector engines, `>>` chaining, `nth=`, `:has()`/visible filters, strict-mode interaction are library-specific. Drop generic CSS/XPath basics. |
| `iframes-shadow-dom.md` | keep, trim, TOC | `>>>` frame piercing and automatic open-shadow-root piercing are non-obvious. Remove its troubleshooting section (moves to troubleshooting). |
| `assertion-engine.md` | keep, trim, TOC | Operators, retry semantics, `validate`, `then` are the library's core idea. Fix the `Wait For Condition` description if the precondition change hasn't. |
| `browser-context-page.md` + `tabs-windows.md` | **merge** → `browser-context-page.md` | Tabs are pages. Both files explain `New Page`/`Switch Page`/`Close Page` and ids. One lifecycle file covers browser/context/page, popups, `auto_closing_level`. |
| `authentication-storage.md` | keep, trim, TOC | `storageState` save/reuse via `New Context  storageState=` is the high-value pattern. Drop generic cookie/localStorage/IndexedDB tutorials. |
| `downloads-uploads.md` | keep, trim | `Promise To Wait For Download`, `Upload File By Selector`, `acceptDownloads` context flag are library-specific. Probably < 100 lines after the trim. |
| `troubleshooting.md` | keep, rewrite, TOC | Organize it by error message → cause → fix. Anything that is really a gotcha moves to `SKILL.md`. Drop "Best Practices" and generic performance advice. |

**rf-selenium**

| File | Decision | Rationale |
|---|---|---|
| `keywords-reference.md` | delete | D3. |
| `webdriver-setup.md` | **rewrite** → `browser-setup.md` | Currently recommends `webdriver-manager` and `executable_path`, which Selenium Manager (Selenium ≥ 4.6) makes obsolete. Keep: `Open Browser` vs `Create Webdriver`, `options=` syntax, headless, Grid/`remote_url`, CI flags. Delete the webdriver-manager and manual-driver sections. |
| `waiting-strategies.md` | keep, trim, TOC | Waits are the main Selenium failure source. Keep `Wait Until …` keyword choice, timeout scopes (`timeout`, `Set Selenium Timeout`, `implicit_wait`), and why implicit+explicit is bad. |
| `locators.md` | keep, heavy trim, TOC | Keep strategy prefixes, the default id/name strategy, `//` auto-xpath, `Add Location Strategy`, WebElement arguments. Drop generic CSS/XPath tutorial and `sizzle`/`jquery` detail (rarely valid today). |
| `frames-windows.md` | keep, trim, TOC | `Select Frame`/`Unselect Frame` context and `Switch Window` locators (`NEW`, `MAIN`, title/url) are library-specific. Must not list `Get Window Count` / `Get Window Handle`. |
| `javascript-execution.md` | keep, heavy trim | Keep only `Execute Javascript` `ARGUMENTS` marker, returning values, `Execute Async Javascript` callback, and when JS is a workaround. Drop the generic DOM/form/storage JS cookbook. |
| `screenshots-logs.md` | **merge** into `troubleshooting.md` | Only `run_on_failure`, `Capture Page Screenshot` (`EMBED`), `Capture Element Screenshot`, `Log Source` and `Register Keyword To Run On Failure` are library-specific. Video recording is out of scope. |
| `troubleshooting.md` | keep, rewrite, TOC | Error message → cause → fix (stale element, intercepted click, no such frame, session not created/driver mismatch), plus the merged debugging-artifacts section. |

**rf-appium**

| File | Decision | Rationale |
|---|---|---|
| `keywords-reference.md` | delete | D3. |
| `device-capabilities.md` | keep → `capabilities.md`, TOC | Single home for W3C caps with the `appium:` prefix, Android and iOS capability sets (moved here from the platform files), cloud vendor options, timeouts. |
| `locators-mobile.md` | keep, TOC | Absorbs the locator sections of `android-specific.md` / `ios-specific.md` (UiAutomator2 `android=`, `-ios predicate string`/`nsp=`, class chain `chain=`). One file for locator strategy across platforms. |
| `android-specific.md` + `ios-specific.md` | **merge** → `platform-specific.md`, TOC | After removing duplicated capability and locator sections, what is left (key codes, permissions/alerts, activities, `mobile:` commands, simulator vs device notes) is small and parallel. One file with Android and iOS sections is easier to gate. |
| `gestures-touch.md` | keep, rewrite, TOC | Must use current keywords (`Tap` with duration, `Swipe`, `Scroll`, `mobile:` gestures via `Execute Script`). Removed keywords (`Long Press`, `Click A Point`, `Zoom`, `Pinch`) appear only in a "removed → use" table. |
| `troubleshooting.md` | keep, trim, TOC | Server connection/base path, session creation, driver, hybrid context issues. |
| SKILL.md reference table | fix | Remove the "planned" note and the non-existent `locators-android.md` / `locators-ios.md` rows. |

**rf-requests**

| File | Decision | Rationale |
|---|---|---|
| `keywords-reference.md` | delete | D3. |
| `http-methods.md` | **delete** (unique bits → `request-options.md`) | Mostly one generic example per HTTP verb, which the model knows. The unique content (sessionless vs `… On Session` naming, `expected_status` values) moves to `request-options.md` / SKILL.md. |
| `request-options.md` | keep, trim, TOC | `json=` vs `data=` vs `files=`, `params`, `verify`/`cert`, `timeout`, `allow_redirects`, session-level vs per-request options, `expected_status`. |
| `response-validation.md` | keep, trim, TOC | Response object (`requests.Response`), `Status Should Be`, `Request Should Be Successful`, JSON access in RF syntax. Drop generic "performance validation". |
| `authentication.md` | keep, trim, TOC | `auth=` tuple, `Create Digest Session`, `Create Ntlm Session`, `Create Client Cert Session`, bearer header patterns. Drop generic OAuth/JWT explanations and AWS SigV4 unless RequestsLibrary supports it natively. |
| `troubleshooting.md` | keep, rewrite, TOC | Error → cause → fix (HTTPError from the default `expected_status`, SSL warnings, JSON decode errors, session alias not found). |

**rf-restinstance**

| File | Decision | Rationale |
|---|---|---|
| `keywords-reference.md` | delete | D3. |
| `schema-validation.md` | keep, heavy trim, TOC | Keep RESTinstance-specific parts: type keywords as schema builders, `Expect Response Body` / `Expect Request` / `Clear Expectations`, `Output Schema`, schema learning, `spec=` OpenAPI. Drop the generic JSON Schema tutorial (string/number/array/object/conditional basics). |
| `json-handling.md` | keep, trim, TOC | Response path syntax (`response body user name`, `$..` JSONPath), type keywords with `enum`/`minimum` etc., `Output`, storing values. |
| `authentication.md` | keep, heavy trim | Only `Set Headers` persistence, `Set Client Authentication`, `Set Client Cert`, per-request `headers=`. Probably < 100 lines after the trim. |
| `troubleshooting.md` | keep, rewrite, TOC | Error → cause → fix. |

Expected result: 35 → 26 reference files across the five skills (−5 catalogs; −3 by merge: `tabs-windows.md`, `screenshots-logs.md`, and `android-specific.md` + `ios-specific.md` → `platform-specific.md`; −1 delete: `http-methods.md`; plus renames `webdriver-setup.md` → `browser-setup.md` and `device-capabilities.md` → `capabilities.md`). The total reference line count drops by at least 40%.

### D5. Candidate gotchas per library

Every item is a **candidate, to verify against libdoc/source of the pinned version during implementation** (tasks 1.x). Items that don't hold are dropped, and ones that turn out generic don't count toward the five.

**rf-browser (Browser library, Playwright)**
1. Strict mode is on by default (`strict_mode=True`): a selector that matches several elements fails for actions and getters. Make the selector unique, or use `>> nth=<n>`; don't turn strict mode off globally.
2. `run_on_failure` defaults to taking a screenshot (`Take Screenshot  fail-screenshot-{index}`). A `Run Keyword If Test Failed  Take Screenshot` teardown only duplicates it.
3. `Fill Text` sets the value in one step (input/change events, no per-key events). Use `Type Text` or `Press Keys` for autocomplete, key listeners or masked inputs. `Fill Secret`/`Type Secret` take `$var` (not `${var}`) so that the value is not logged.
4. Actions auto-wait for actionability, and getter assertions (`Get Text  sel  ==  x`) retry until timeout. `${t}=  Get Text` followed by `Should Be Equal` does not retry. For disappearance or other states use `Wait For Elements State`; for page load use `Wait For Load State` (`Wait Until Network Is Idle` is deprecated). No `Sleep`.
5. `auto_closing_level` (default `TEST`) closes contexts and pages opened during a test at test end. Open shared browser/context in Suite Setup. `KEEP`/`SUITE` change this, with state-leak trade-offs.
6. `New Page` without a prior `New Browser`/`New Context` silently creates a default headless Chromium and context, so `viewport`, `storageState` or `acceptDownloads` you meant to set are missing.
7. Selector defaults: a string starting with `//` or `..` is XPath, a quoted string is exact text, otherwise CSS. `text=Foo` matches a case-insensitive substring. Frames need `>>>`.
8. Two timeouts: `timeout` (actions/waits, default 10 s) and `retry_assertions_for` (assertion retry, default 1 s). A slow assertion needs the second one raised, not the first.

**rf-selenium (SeleniumLibrary)**
1. Keep `implicit_wait=0` (the default) and use explicit `Wait Until …` keywords. Mixing both can multiply wait times and hide real failures.
2. The import `timeout` (default 5 s) applies only to `Wait Until …` keywords, not to `Click Element` etc. Those fail immediately if the element isn't there yet.
3. `Page Should Contain*` / `Element Should Be Visible` check once and do not wait. Use `Wait Until Page Contains*` / `Wait Until Element Is Visible` after navigation or AJAX.
4. Stale elements: a WebElement stored in a variable goes stale when the DOM re-renders. Keep locators in variables, not elements, and re-find after page updates.
5. Selenium Manager (Selenium ≥ 4.6) downloads matching drivers. Don't add `webdriver-manager` or `executable_path`.
6. A locator without a prefix matches `id` or `name` only. A string starting with `//` is XPath. Use `css:`/`xpath:` explicitly for anything else.
7. `Select Frame` changes context until `Unselect Frame`. Locators outside the frame then fail with "element not found", not with a frame error.
8. `Click Element` on a covered or off-screen element raises "element click intercepted". Wait for the overlay to go away or use `Scroll Element Into View`. Use JS click only as a last resort.
9. `run_on_failure` defaults to `Capture Page Screenshot`. Don't add a screenshot teardown.

**rf-appium (AppiumLibrary)**
1. Appium 2 uses W3C capabilities. Every non-standard capability needs the `appium:` prefix (`appium:automationName`, `appium:app`), and the default server URL has no `/wd/hub`. Check how AppiumLibrary 3.x handles unprefixed caps.
2. `Element Should Be Visible/Enabled/Disabled` are deprecated in 3.2.x. Use `Expect Element` / `Expect Elements` (verify signature and states).
3. Removed keywords that models still write: `Long Press`, `Click A Point`, `Zoom`, `Pinch`, `Quit Application`, `Reset Application`, `Background App`. The replacements are `Tap … duration=`, `Tap With Positions`, `mobile:` gestures via `Execute Script`, `Close Application`, `Background Application`.
4. Element keywords do not auto-wait the way Browser does. Use `Wait Until Element Is Visible` / `Wait Until Page Contains Element` (timeout from `timeout` import arg / `Set Appium Timeout`).
5. Prefer `accessibility_id=` (same id on both platforms). XPath on mobile is slow and fragile. Use `android=` UiAutomator / `-ios predicate string` / `chain=` for performance.
6. Hybrid apps: after `Switch To Context  WEBVIEW_…`, locators are web locators. Switch back to `NATIVE_APP` before native steps.
7. `Swipe`/`Tap` duration arguments are timedeltas (for example `0:00:01` / `1s`) in 3.x, not milliseconds (verify).
8. Teardown with `Close All Applications` (or `Close Application`) so that the next test doesn't reuse a stale session.

**rf-requests (RequestsLibrary)**
1. Two styles: sessionless `GET`/`POST`… take a full URL, while `GET On Session` etc. need an alias from `Create Session` and take a path. Default: sessionless for a few calls, session when several calls share a base URL, headers or auth.
2. `expected_status` defaults to raising on any 4xx/5xx. For negative tests pass `expected_status=404` (or `anything`) instead of wrapping the call in `Run Keyword And Expect Error`.
3. TLS verification differs: `Create Session` defaults to `verify=False` (verify), while sessionless calls follow `requests` (`verify=True`). Set `verify=${True}` explicitly on sessions.
4. `json=${dict}` sends JSON with the right Content-Type. `data=${dict}` form-encodes. Don't `Evaluate  json.dumps` yourself.
5. The response is a `requests.Response`: `${resp.json()}[id]`, `${resp.status_code}`, `${resp.headers}[Content-Type]`. `Status Should Be` and `Request Should Be Successful` are the library assertions.
6. Session-level headers, cookies and auth persist for the alias across tests in the suite. `Delete All Sessions` in Suite Teardown.

**rf-restinstance (RESTinstance)** — library not installed in the dev venv; all items unverified until task 1.5.
1. The import `Library  REST  <url>` sets the base URL. Request keywords (`GET`, `POST`…) take paths, and assertions apply to the **last request's instance**.
2. Assertions are type keywords with a path: `Integer  response status  200`, `String  response body name  Alice`. They also add to the instance's schema.
3. Schema learning: each type keyword tightens the schema of the current instance, and `Expect Response Body` persists for later requests until `Clear Expectations`. Expectations leak into later requests and tests if not cleared.
4. `Set Headers` persists for the library instance (suite scope). Auth headers set in one test apply to all later tests in the suite.
5. 4xx/5xx responses do not fail the request. The test fails only if you assert the status. Always assert `response status`.
6. `Output` / `Output Schema` print the instance or schema. Use them to discover paths instead of guessing.
7. Python ≥ 3.11 and maintenance status: point to rf-setup. Mention the version line only.

### D6. Examples

Keep one to four examples per skill, each a self-contained suite. Web examples use `https://example.com` or a local file fixture that dry-runs without network. API examples use a placeholder base URL (dry-run doesn't send requests). Modern syntax only. Proposed:

- rf-browser: keep `basic-web-test.robot`, `form-handling.robot`, `authentication-flow.robot` (storageState reuse), `iframe-shadow-dom.robot`. Delete `file-operations.robot` if it duplicates `downloads-uploads.md` without a runnable target.
- rf-selenium: keep `basic-web-test.robot`, `wait-patterns.robot`, `multi-window.robot` (fixed). Merge `form-handling.robot` into `basic-web-test.robot`. Delete `selenium-grid.robot` (needs a grid; `browser-setup.md` has the snippet).
- rf-appium: keep `android-basic.robot`, `ios-basic.robot`, `gestures-example.robot` (rewritten). Merge `device-actions.robot` into the platform examples. Keep `hybrid-app.robot` only if it dry-runs.
- rf-requests: keep `basic-crud.robot`, `session-handling.robot`, `authentication-patterns.robot`. Keep `file-upload.robot` if it dry-runs.
- rf-restinstance: keep `basic-rest.robot`, `schema-validation.robot` (plus its schema file). Merge `json-manipulation.robot` into `basic-rest.robot`. Keep `oauth-flow.robot` only if it adds a pattern not in `authentication.md`.

Dry-run test: `tests/test_library_skill_structure.py::test_examples_dryrun[<skill>-<file>]`, skipped per library when `importlib.util.find_spec(<module>)` is None (`Browser`, `SeleniumLibrary`, `AppiumLibrary`, `RequestsLibrary`, `REST`). Browser dry-run needs no browser binaries because dry-run does not run keywords (confirm). CI: extend the fail-soft install step with `robotframework-seleniumlibrary robotframework-appiumlibrary robotframework-requests RESTinstance`.

### D7. Enforcement test

A new `tests/test_library_skill_structure.py`, parametrized over the five skill dirs:
- required H2 headings present and ordered (spec: skeleton);
- ≤ 250 lines, ≤ 12,000 characters;
- no `keywords-reference.md` in canonical skills or distribution copies; `robotcode libdoc <ImportName>` present;
- reference table paths == `references/*` set; no reference → reference links; TOC for > 100 lines (a list of links or names matching all H2s within the first 15 lines);
- `Gotchas` has ≥ 5 bullets;
- the `Verified against` line appears once;
- no ALL-CAPS emphasis words in prose (fenced and inline code stripped; allowlist for acronyms such as `CSS`, `JSON`, `HTTP`, `API`, `URL`, `TLS`, `W3C`, `iOS`, `NATIVE_APP`, `WEBVIEW`, `KEEP`, `TEST`, `SUITE`);
- no legacy syntax (`Run Keyword If`, `Run Keyword Unless`, `Exit For Loop`, `[Return]`) in examples or robotframework code blocks;
- example dry-run (D6).

Keyword existence in SKILL.md code blocks: reuse the checker from `fix-library-skill-keyword-correctness` if it ships one (the scratchpad `kwcheck.py` prototype resolves first-cell keywords against libdoc and must exclude user keywords defined in `*** Keywords ***`). Otherwise add it here as a libdoc-gated test.

### D8. Glossary (consistent terminology)

Per skill, one term per concept, used in SKILL.md and references:
- Browser: *browser*, *context*, *page* (not tab/window except when explaining the mapping); *selector* (Browser's term), not locator; *assertion operator*.
- Selenium / Appium: *locator*, *strategy*; *explicit wait*; Appium: *capabilities*, *session*, *context* (native/webview).
- Requests: *session* (alias), *sessionless keyword*, *response*.
- RESTinstance: *instance*, *expectation*, *schema*, *path*.
- All: *libdoc* for keyword lookups, *dry run* for `robot --dryrun`.

### D9. Evaluation (success criteria)

This change adds no harness code. Once `strengthen-skill-eval-harness` provides no-skill baselines and N-run aggregation:
- Add at least one gotcha-targeted task per library under `eval/tasks/` if that change doesn't (for example, a Browser task where a naive selector hits strict mode; a Requests negative test where the default `expected_status` raises; a Selenium AJAX wait; an Appium caps/`Expect Element` task; a RESTinstance expectation-leak task). Where no live system exists, use deterministic checks (dry-run passes, forbidden keywords absent, required keyword present).
- Run each task ≥ 3 times in three configurations: no skill, pre-change skill (git ref before this change), restructured skill.
- Pass: restructured ≥ pre-change − run-to-run spread on every task; restructured > no-skill on each gotcha task; mean tokens with the restructured skill ≤ pre-change.
- Record the numbers in the change's task notes before archive.

## Risks / Trade-offs

- [Libdoc lookups need Robot Framework and the library installed] → rf-setup is already the precondition for all library skills. The workflow step names the script fallback, and a missing library shows up at the dry-run step anyway.
- [Deleting generic content removes help for weaker models] → the eval gate (D9) includes the smaller model the harness uses. If a regression appears, restore the specific missing fact as a gotcha or table row, not the catalog.
- [Candidate gotchas may be wrong (especially RESTinstance, unverified)] → each is verified against libdoc/source before it is written. Unverifiable items are left out, and the `Verified against` line states the version.
- [The ALL-CAPS style test may flag legitimate constants] → allowlist plus code stripping. Constants belong in inline code anyway.
- [Parallel changes edit the same files (correctness, install guidance, descriptions)] → strict ordering in proposal.md. This change rebases on the first two and touches only the body of SKILL.md, never the frontmatter description.
- [Dry-run of Browser/Appium examples in CI may be slow or need optional deps] → fail-soft installs and per-library skips. Skipped counts as skipped, not passed (spec).

## Migration Plan

1. Land after `fix-library-skill-keyword-correctness` and `unify-library-install-guidance`. Rebase.
2. Implement one skill per commit (browser, selenium, appium, requests, restinstance), each including sync (`scripts/sync-skills.sh`) and a passing `scripts/check-drift.sh`.
3. Add the structure test and the CI step (they can land first with the five skills xfail-marked, then un-marked per skill).
4. Run the evals (D9), record the results, then archive.
Rollback: revert the per-skill commit. The catalogs and old references come back from git, and the sync regenerates the channels.

## Open Questions

- Final libdoc script skill name from `merge-libdoc-skills` (assumed `rf-libdoc`). It only changes one constant and the companion rows.
- Whether AppiumLibrary 3.x auto-prefixes `appium:` capabilities and the exact `Expect Element` signature. This decides how gotchas 1–2 are phrased, not whether they exist.
- Whether RESTinstance can be installed in CI (Python ≥ 3.11). If not, its dry-run and keyword checks stay skipped, and the gotchas are verified manually from source.

## Implementation Notes

- **Adapted to the changes archived before this one:** paths are `skills/rf-<topic>/` in every channel (align-skill-names-with-spec), the libdoc fallback is `rf-libdoc` (merge-libdoc-skills), the heading is `## Companion Skills` with catalogue rows kept verbatim (`tests/test_skill_descriptions.py`), and frontmatter descriptions are unchanged (sharpen-skill-descriptions).
- **`## Installation` stays in the skeleton.** The archived `library-skill-install-guidance` spec and `tests/test_library_install_guidance.py` require a short install block in each library SKILL.md: the **rf-setup** pointer, the uv command(s) from rf-setup Step 4 and the post-install essential. That conflicted with the original "no install commands; a single sentence pointing to rf-setup" rule. It is resolved in the delta spec: `Installation` is a required section between the orientation and `Import and defaults`, and it is the only place install commands (`uv add`, `pip install`, `npm install`) may appear. `test_install_commands_only_in_installation_section` enforces that.
- **The enforcement test reuses the existing keyword checker.** Keyword existence in fenced blocks, references and examples is checked by `scripts/check-skill-keywords.py` (CI job plus `tests/test_skill_keywords.py`). `tests/test_library_skill_structure.py` only adds a libdoc check for inline-code keywords in the decision table's `Use` column (≥ 2 Title-case words; RF settings excluded). It includes a planted `Wait Until Element Count Is Greater Than` self-test.
- **The xfail markers were non-strict (task 2.1).** Strict xfail was impossible because many rules (for example the example dry runs) already held for the old content. `PENDING` is empty now.
- **TOC rule, as implemented:** a bullet list that starts within the first 15 lines and names every H2. It is required for files over 100 lines.
- **Style test word list:** NEVER, ALWAYS, MUST, CRITICAL, IMPORTANT, WARNING, NOTE, DO, DON'T, NOT, SHOULD, REQUIRED. The test checks prose only, with fenced and inline code stripped.
- **Additional required-structure checks:** orientation ≤ 6 non-empty lines including the `Verified against <Lib> <x.y.z>, Robot Framework 7.4.` line; exactly one `Library` line inside `Import and defaults` fences; ≥ 6 decision-table rows; ≥ 5 Gotchas bullets, each with inline code; 1–4 examples, each named in SKILL.md.
- **Default configurations and scope that differ from D5/D6:**
  - rf-browser: imports a bare `Library    Browser`, because the library defaults are the recommendation and libdoc says `KEEP` is for development only.
  - rf-selenium: opens with `headlesschrome`, because `headless_chrome` is rejected by SeleniumLibrary 6.8.
  - rf-restinstance: deletes `oauth-flow.robot` (its patterns are in `authentication.md`) and adds `assets/examples/schemas/user.json`.
  - rf-requests: keeps `file-upload.robot`, because it dry-runs.
  - rf-appium: keeps `hybrid-app.robot`, because it dry-runs; hybrid/WebView guidance lives in `platform-specific.md`.
  - rf-restinstance: all references ended up at 100 lines or fewer.
- **Gotcha candidates dropped or moved** (details in the tasks.md "Gotcha verification" note):
  - Selenium Manager and Python ≥ 3.11 stay in `## Installation` only.
  - Selenium's default locator strategy moved to the optional `## Locator rules` section.
  - rf-appium: the `/wd/hub` base path is server behaviour and lives only in `troubleshooting.md`.
- **Eval (D9):** two gotcha tasks were added: `adv-appium-deprecated-visibility` and `adv-restinstance-expectation-leak`. The other three libraries reuse existing tasks. Live runs 9.2/9.3 are deferred. The pre-change snapshot is `baseline/pre-change-skills.tar.gz`, because the pre-change content was never committed.
- **CI:** the unit-test job installs SeleniumLibrary, AppiumLibrary, RequestsLibrary and RESTinstance fail-soft (one `|| echo` line each), so the example dry runs skip rather than fail when a library is missing.
