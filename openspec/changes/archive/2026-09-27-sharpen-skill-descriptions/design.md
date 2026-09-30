## Context

See proposal.md (Why). The facts that shape the design:

- **Current descriptions.**
  - Five start with "Guide AI agents in creating…": appium, browser, platynui, requests, restinstance. rf-robotcode and rf-setup use "Guide AI agents in using/installing…".
  - rf-results still advertises "criticality", which was removed in RF 4.0. `fix-library-skill-keyword-correctness` removes it from the body and the JSON.
  - None names a sibling to use instead. Lengths range from about 190 to 620 characters.
- **Where descriptions are read.** Claude Code (plugin and `.claude/skills/`), Codex and Goose (`.agents/skills/`), Cursor, OpenCode and VS Code `chatSkills` read the root text through sync and the installer. Claude Code plugin skills are listed as `rf-agentskills:<name>`. Several agents truncate long descriptions in the skill list, so the first ~200 characters carry most of the signal.
- **Constraints from existing specs.**
  - robotcode-skill requires the rf-robotcode description to mention robotcode, discovery, debugging and results.
  - setup-skill requires the rf-setup description to mention installing Robot Framework, uv, venv/pip and Poetry.
  - The drafts below keep both.
- **Harness.** `strengthen-skill-eval-harness` defines `eval/triggers/<skill>.yaml`: `skill`, `model` (default Haiku), `runs` (default 3), `threshold` (default 0.5), and `queries: [{id, query, should_trigger, split, note}]`. It adds a `rf-skill-eval trigger` command that runs with hooks disabled and detects loads from Skill/Read tool calls. It also adds `eval/baselines/triggers.json` and a PR job that runs validation-split triggers when a description changes. This change supplies the data and the acceptance rule. The harness supplies the runner.
- **Skill set after the other changes:** rf-appium, rf-browser, rf-libdoc, rf-platynui, rf-requests, rf-restinstance, rf-results, rf-robotcode, rf-selenium and rf-setup, at `skills/rf-*/` (after `align-skill-names-with-spec`).

## Goals / Non-Goals

**Goals:**
- Each description tells an agent within about 200 characters what the skill does and which library, tool or file it is for. It then lists trigger terms and names the sibling to use instead.
- Cross-references between skills are consistent and cannot go stale silently.
- Trigger accuracy is measured before and after the change, with thresholds decided up front.

**Non-Goals:**
- Editing skill bodies beyond the Companion Skills section. `restructure-library-skills` owns library bodies.
- An automated description-optimisation loop. Tuning is manual against the train split.
- Tuning for the UserPromptSubmit hook. Trigger evals run with hooks off. The hook text is only kept consistent with the descriptions.
- Per-agent description variants. One text serves every channel.

## Decisions

### D1: Description template

`<Verb-s> <what> with <library/tool> (<package / technology>): <5–8 concrete capabilities using real keyword or CLI names>. Use when <import line / file / CLI / error / user phrasing>. <Boundary: For X use rf-Y.>`

- Third-person verb first ("Writes and fixes", "Drives", "Parses", "Installs"). Not "Guide AI agents". The first ~120 characters name Robot Framework and the library.
- Trigger terms are what users paste or type: `Library    Browser`, `output.xml`, `robot.toml`, `rfbrowser`, `ModuleNotFoundError`, `No keyword with name`. Real keyword names help matching (`Open Browser` vs `New Page`).
- The boundary comes last. It is the least important text if the description is truncated, and it only matters when the sibling is also a candidate.
- Target ≤ 500 characters, hard cap 1024 (enforced by `align-skill-names-with-spec`'s validator). The test warns above 500.
- YAML: these texts contain `: `, quotes and backticks, so they are written as one double-quoted scalar (`description: "…"`) with `\"` escapes where needed. The spec validator from `align-skill-names-with-spec` must parse quoted scalars. A task below confirms this.

Alternative considered: a trigger-keyword list only ("Triggers: selenium, webdriver, …"). Rejected. Agents match better on natural prose plus terms, and keyword lists read like spam in skill pickers.

### D2: Boundary rules (why these signals)

| Pair | Signal | Default when no signal |
|---|---|---|
| rf-browser ↔ rf-selenium | `Library    Browser` vs `Library    SeleniumLibrary` in the suite or resource; "Playwright" vs "WebDriver/chromedriver/Selenium Grid" in the prompt | rf-browser. It is the recommended library for new RF web projects, and rf-setup already treats it as the default web library. **Confirmed by the user (2026-09-27).** |
| rf-requests ↔ rf-restinstance | `Library    RequestsLibrary` vs `Library    REST`; "JSON Schema", "OpenAPI/Swagger spec" in the prompt → rf-restinstance | rf-requests (more widely used, fewer install constraints; RESTinstance needs Python ≥ 3.11) **Confirmed by the user (2026-09-27).** |
| rf-robotcode ↔ rf-results / rf-libdoc | "robotcode", `robot.toml`, `robot-debug`, "REPL" → rf-robotcode; otherwise the script skill, which tells the agent to switch if `robotcode` is on PATH (existing body guidance) | The script skill. It works without extra installs. |
| rf-setup ↔ library skills | install/setup/"add library"/environment errors → rf-setup; writing or fixing test code → library skill | Library skill for test-code requests, rf-setup for any install verb |
| rf-appium / rf-platynui ↔ web skills | mobile (apk/ipa/emulator) vs desktop app vs browser | none. These are disjoint domains. |

The two defaults for requests that name no library (web → rf-browser, API → rf-requests) were confirmed by the user on 2026-09-27 (cross-change decision 1). They are no longer open for tuning: if trigger evals show a conflict, the boundary sentences are strengthened, not the defaults changed.

Later changes add pairs to this table and the description test's sibling list when their skills ship: `rf-language` ↔ `rf-python-library` (signal: `.robot`/`.resource` code vs Python library or listener code; added by `add-rf-language-skill` and `add-rf-python-library-skill`).

The signal is something observable: the import line in the project, or a technology name. An agent can check the import with one grep, so the descriptions say "when a .robot or .resource file imports …".

Shared-ambiguity rule for evals: a query such as "summarise the failures in output.xml" is valid for both rf-results and rf-robotcode. It is a should-trigger for rf-results. It is not used as a should-not-trigger for rf-robotcode (see spec).

### D3: Draft descriptions

Character counts are measured on the draft text. The final text may change during train-split tuning (D6).

| Skill | Chars | Draft |
|---|---|---|
| rf-browser | ~490 | Writes and fixes Robot Framework web UI tests with Browser Library (robotframework-browser, Playwright): New Browser/Context/Page, CSS/text/XPath selectors, auto-waiting, assertion getters (Get Text  ==), iframes (>>>), shadow DOM, tabs, downloads, storage state. Use when a .robot or .resource file imports `Library    Browser`, or the user mentions Browser Library, Playwright or rfbrowser. For SeleniumLibrary/WebDriver suites use rf-selenium; for installing the library use rf-setup. |
| rf-selenium | ~470 | Writes and fixes Robot Framework web UI tests with SeleniumLibrary (Selenium WebDriver): Open Browser, id:/css:/xpath: locators, explicit Wait Until … keywords, frames, windows, alerts, Execute JavaScript, Selenium Grid and Remote WebDriver. Use when a .robot or .resource file imports `Library    SeleniumLibrary`, or the user mentions SeleniumLibrary, WebDriver, chromedriver or Selenium Grid with Robot Framework. For Browser Library/Playwright suites use rf-browser. |
| rf-appium | ~505 | Writes and fixes Robot Framework mobile tests with AppiumLibrary for Android and iOS native, hybrid and mobile-web apps: Open Application with W3C capabilities (UiAutomator2, XCUITest), accessibility_id/id/xpath locators, waits, swipes and scrolling, WEBVIEW context switching. Use when a suite imports `Library    AppiumLibrary`, or the user mentions Appium, an .apk/.ipa, an emulator or simulator with Robot Framework. For desktop apps use rf-platynui; for desktop browsers use rf-browser or rf-selenium. |
| rf-requests | ~480 | Writes and fixes Robot Framework HTTP/REST API tests with RequestsLibrary (robotframework-requests): GET/POST/PUT/PATCH/DELETE with or without sessions, expected_status, headers, bearer/basic auth, JSON bodies, file uploads, response.json() checks. Use when a suite imports `Library    RequestsLibrary`, or the user wants API tests in Robot Framework without naming a library. For suites that import `REST` (RESTinstance) or need JSON Schema/OpenAPI assertions, use rf-restinstance. |
| rf-restinstance | ~450 | Writes and fixes Robot Framework REST API tests with RESTinstance (`Library    REST`): requests with JSON-path assertions on the response (Integer response status, String/Object/Array response body), JSON Schema validation and generation, OpenAPI/Swagger spec checks. Use when a suite imports `REST`, or the user mentions RESTinstance or schema-driven API testing in Robot Framework. For RequestsLibrary suites or generic API tests, use rf-requests. |
| rf-platynui | ~490 | Writes and fixes Robot Framework native desktop UI tests with PlatynUI (PlatynUI.BareMetal, new_core) over Windows UI Automation and Linux AT-SPI2: XPath queries over the desktop tree, window scoping, pointer and keyboard input, attribute checks, platynui-cli and the inspector for building locators. Use when the user wants to automate a desktop application (Calculator, Notepad, a Qt/GTK/WPF/WinForms app) with Robot Framework or mentions PlatynUI. Not for web browsers or mobile apps. |
| rf-robotcode | ~520 | Drives the robotcode CLI for Robot Framework projects: test discovery (suites, tests, tags), keyword docs via robotcode libdoc, runs with robot.toml profiles, non-interactive REPL exploration, debugging failing tests with robot-debug, results analysis of output.xml (summary, failures, stats, diffs) and static checks with robotcode analyze code. Use when robotcode is installed or a robot.toml exists, or the user mentions robotcode, robot.toml profiles or robot-debug. Without robotcode, use rf-results and rf-libdoc. |
| rf-setup | ~570 | Installs Robot Framework, its test libraries and tooling into the project environment and verifies them, following the tool the project already uses: uv (default for new projects), Python venv + pip, or Poetry. Covers Python version floors, rfbrowser install/init, Appium server and drivers, PlatynUI pre-releases, project layout and CI. Use for installing or setting up Robot Framework, adding a library, or errors like ModuleNotFoundError, No module named 'Browser', externally-managed-environment or a wrong interpreter. Writing tests belongs to the library skills. |
| rf-libdoc | ~450 | Searches and explains Robot Framework keyword documentation with a bundled libdoc script: finds keywords for a task across libraries, resource files and suites, and returns exact names, arguments, defaults and docs as JSON. Use when the user asks which keyword does X, what arguments a keyword takes, or hits No keyword with name '…' found or wrong-argument-count errors. Prefer rf-robotcode (robotcode libdoc) when the robotcode CLI is installed. |
| rf-results | ~475 | Parses Robot Framework output.xml with a bundled script into JSON: pass/fail totals, suite and test breakdowns, tag statistics, failure and keyword error messages, execution errors, slowest tests and keywords, and merging or combining several outputs via rebot. Use when the user asks why tests failed, wants a run summarised, or needs output.xml files merged (for example after pabot or a rerun). Prefer rf-robotcode (robotcode results) when the robotcode CLI is installed. |

rf-setup and rf-robotcode are slightly over 500 characters. Both carry spec-mandated terms. They are trimmed during tuning if the ≤ 500 warning matters, but the 1024 cap is far away. rf-results drops "criticality" (in step with `fix-library-skill-keyword-correctness`). Keyword names quoted in drafts must be checked against libdoc when finalised (for example `Integer    response status`, `Get Text` with the `==` assertion operator).

### D4: Companion Skills catalogue

One section per skill, headed `## Companion Skills`. It is a two-column `| Need | Skill |` table. rf-robotcode keeps its three-column `Need | With robotcode | Without robotcode` form, and the test accepts "first column Need, last column a skill".

Rows are taken verbatim from this catalogue:

| Key | Need | Skill |
|---|---|---|
| setup | Install Robot Framework or a library, fix the environment | `rf-setup` |
| libdoc | Look up keyword names, arguments and docs | `rf-libdoc` (or `rf-robotcode`: `robotcode libdoc`) |
| results | Analyze output.xml results | `rf-results` (or `rf-robotcode`: `robotcode results`) |
| robotcode | Discover, run, debug and statically check with the robotcode CLI | `rf-robotcode` |
| browser | Web UI tests with Browser Library (Playwright) | `rf-browser` |
| selenium | Web UI tests with SeleniumLibrary (WebDriver) | `rf-selenium` |
| requests | API tests with RequestsLibrary | `rf-requests` |
| restinstance | API tests with RESTinstance / JSON Schema | `rf-restinstance` |
| appium | Mobile app tests with AppiumLibrary | `rf-appium` |
| platynui | Native desktop tests with PlatynUI | `rf-platynui` |

Required rows per skill. Other catalogue rows are optional.

| Skill | Required rows |
|---|---|
| rf-browser | selenium, setup, libdoc, results, robotcode |
| rf-selenium | browser, setup, libdoc, results, robotcode |
| rf-appium | setup, libdoc, results, robotcode |
| rf-requests | restinstance, setup, libdoc, results, robotcode |
| rf-restinstance | requests, setup, libdoc, results, robotcode |
| rf-platynui | setup, libdoc, results, robotcode |
| rf-robotcode | setup, libdoc, results (as the "Without robotcode" column), browser, requests |
| rf-setup | robotcode, browser, selenium, appium, requests, restinstance, platynui |
| rf-libdoc | robotcode, setup, results |
| rf-results | robotcode, libdoc, setup |

The robotcode-skill spec's scenarios still hold: rf-robotcode names rf-setup and the result/keyword fallbacks, and the script skills point back to rf-robotcode. The fallback names become `rf-libdoc` through `merge-libdoc-skills`.

Keys added by later changes (not part of this change's required rows): `language` ("Write tests, suites, user keywords, resources and variables in Robot Framework syntax" → `rf-language`, added by `add-rf-language-skill` to rf-setup, rf-robotcode and the six library skills) and `python-library` ("Write or fix a Python keyword library or listener" → `rf-python-library`, added by `add-rf-python-library-skill`).

Why a catalogue: the tables currently differ per skill, and the retirement and merge changes would otherwise edit ten tables ad hoc. A fixed wording lets a test check the tables, and keeps "Need" phrasing identical wherever the same skill is recommended.

### D5: Trigger query sets

Location and format are owned by the harness (`eval/triggers/<skill-name>.yaml`). The content rules come from this change's spec. Example (rf-browser, abbreviated to the required minimum):

```yaml
skill: rf-browser
model: claude-haiku-4-5-20251001
runs: 3
threshold: 0.5
queries:
  # should trigger (train)
  - {id: br-t01, split: train, should_trigger: true, query: "Write a Robot Framework test that logs into http://localhost:8000 with Browser library and checks the dashboard heading"}
  - {id: br-t02, split: train, should_trigger: true, query: "my suite has Library    Browser and New Page times out on the login page, how do I wait for the network to settle?"}
  - {id: br-t03, split: train, should_trigger: true, query: "How do I click a button inside a shadow DOM in robot framework playwright?"}
  - {id: br-t04, split: train, should_trigger: true, query: "rfbrowser test: switch to the new tab that opens after clicking 'Export'"}
  - {id: br-t05, split: train, should_trigger: true, query: "Assert the text of .price equals 9.99 using Get Text in my .robot file"}
  # should trigger (validation)
  - {id: br-v01, split: validation, should_trigger: true, query: "Add a file-download test to tests/web/checkout.robot (we use Browser)"}
  - {id: br-v02, split: validation, should_trigger: true, query: "Reuse the logged-in state across RF web tests with storage state instead of logging in every time"}
  - {id: br-v03, split: validation, should_trigger: true, query: "Fill the form inside the iframe #payment with Robot Framework Browser library"}
  # should NOT trigger (train): siblings + look-alikes
  - {id: br-n01, split: train, should_trigger: false, note: sibling rf-selenium, query: "Our suite imports SeleniumLibrary; make Open Browser use headless Chrome on the Selenium Grid"}
  - {id: br-n02, split: train, should_trigger: false, note: sibling rf-selenium, query: "Wait Until Element Is Visible keeps failing with StaleElementReferenceException in my Robot test"}
  - {id: br-n03, split: train, should_trigger: false, note: sibling rf-setup, query: "rfbrowser init fails with 'node not found' — how do I install Browser library without Node?"}
  - {id: br-n04, split: train, should_trigger: false, note: non-RF look-alike, query: "Write a pytest-playwright test that checks the login page title"}
  - {id: br-n05, split: train, should_trigger: false, note: non-RF look-alike, query: "Convert this Cypress test to Playwright TypeScript"}
  # should NOT trigger (validation)
  - {id: br-n06, split: validation, should_trigger: false, note: sibling rf-selenium, query: "Switch to the second window with SeleniumLibrary and close the first"}
  - {id: br-n07, split: validation, should_trigger: false, note: sibling rf-requests, query: "Call the /login REST endpoint from a Robot Framework test and check the token"}
  - {id: br-n08, split: validation, should_trigger: false, note: non-RF look-alike, query: "Scrape product prices with Playwright for Python and save them as CSV"}
```

Note `br-n03`: installing Browser belongs to rf-setup. The description's "for installing the library use rf-setup" boundary is what this query tests.

Near-miss sources per skill. At least 3 sibling and at least 2 non-RF look-alikes are required; aim for 10–12 per polarity.

| Skill | Sibling near-misses | Non-RF look-alikes |
|---|---|---|
| rf-browser | SeleniumLibrary tasks, rf-setup install of Browser, RequestsLibrary API | pytest-playwright, Playwright TS/Python scripting, Cypress |
| rf-selenium | Browser/Playwright RF tasks, rf-setup driver install, Appium mobile web | Selenium in Python/Java unittest, Selenide |
| rf-appium | PlatynUI desktop, Browser/Selenium desktop web, rf-setup (install Appium server) | Espresso/XCUITest native tests, Appium in Java/TestNG |
| rf-requests | RESTinstance/JSON-Schema RF tasks, Browser UI tests, rf-results | Python `requests` scripts, Postman/Newman collections, pytest API tests |
| rf-restinstance | RequestsLibrary suites, generic "API test" with no library named, rf-setup (install RESTinstance) | jsonschema in Python, Schemathesis/OpenAPI fuzzing |
| rf-platynui | Appium mobile, Browser web, rf-setup (install PlatynUI) | pywinauto/AutoIt scripts, WinAppDriver in C# |
| rf-robotcode | rf-setup (install robotcode), library test-writing, VS Code extension settings questions | pytest `--collect-only`, pdb debugging of Python code |
| rf-setup | writing Browser/Requests tests, rf-robotcode `robot.toml` profile usage, rf-results | "pip install" for a Django app, conda env for data science |
| rf-libdoc | writing tests with a library, rf-results failure analysis, rf-setup "No module named" | Python `help()`/pydoc, Sphinx API docs |
| rf-results | rf-libdoc keyword lookup, rf-robotcode "robotcode results diff" (explicit robotcode), library test writing | JUnit XML report parsing, pytest HTML report, Allure |

Should-trigger coverage per skill: at least 2 queries that do not name the library, using pasted errors, file names or intent only (for example "Why did 3 tests fail in results/output.xml?" for rf-results), and at least 1 query that phrases the request as an edit to an existing file.

### D6: Acceptance procedure and thresholds

1. Before editing any description, run `rf-skill-eval trigger --skills <all 10> --split train,validation --runs 3` on the current descriptions. Record the results as the pre-change baseline (`eval/baselines/triggers.json` via the harness).
2. Tune each description against the **train** split only.
3. Accept per skill when, on **validation** at 3 runs and threshold 0.5:
   - recall (should-trigger) ≥ 0.80;
   - should-not-trigger accuracy ≥ 0.90;
   - neither is lower than the pre-change baseline.
4. Model: Haiku (harness default). A Sonnet spot check is optional and informative only.

Why these numbers: with 3–5 validation queries per polarity, 0.80 recall allows one miss out of five. 0.90 specificity effectively means no validation false positive in small sets. False positives are costlier here, because a wrong library skill steers the agent toward the wrong keywords. The "not worse than before" clause stops a change from passing thresholds while making a previously good skill worse.

If a sibling pair cannot reach both thresholds, the boundary sentence is strengthened in both descriptions. The fix is not made by dropping the conflicting validation queries.

### D7: Enforcement test (`tests/test_skill_descriptions.py`)

A static test that needs no network. For each `skills/*/SKILL.md` it checks:
- the description starts with an uppercase verb ending in "s" and does not match `/guide ai agents|this skill|helps? (the )?ai/i`;
- it contains "Use when";
- it is at most 1024 characters, with a warning above 500;
- sibling names from D2 are present;
- the Companion Skills table is parsed: every skill cell is an existing `skills/*` name, is not self, required rows from D4 are present, and no retired names appear;
- `eval/triggers/<name>.yaml` exists with ≥ 8/≥ 8 queries and splits on both polarities. This duplicates the harness loader check on purpose, so it runs in the plain `pytest` CI job without harness extras.

## Risks / Trade-offs

- [Concrete keyword names in descriptions go stale] → only names verified with libdoc are used, and the keyword-correctness checker from `fix-library-skill-keyword-correctness` can be extended to scan frontmatter.
- [N=3 at Haiku is noisy, and small validation sets make thresholds jumpy] → aim for 10–12 queries per polarity. The "no regression" rule compares with the same queries. Borderline results are re-run once before a decision.
- [Hooks-off trigger evals differ from real Claude Code sessions with the plugin's UserPromptSubmit hook] → intentional (it isolates the description). Other agents have no hook.
- [Defaulting generic web requests to rf-browser biases users away from Selenium] → rf-selenium still wins whenever the project imports SeleniumLibrary. The rf-browser description says so and the trigger set tests it.
- [Concurrent edits to the same SKILL.md files by restructure and retirement changes] → this change touches only the frontmatter `description` and the Companion Skills section. The others are told to leave those alone.

## Migration Plan

1. After `retire-generator-skills`, `merge-libdoc-skills` and `align-skill-names-with-spec` land: author the 10 trigger sets and record the pre-change baseline. This needs the harness `trigger` command.
2. Apply the descriptions and companion tables in one PR, run sync, and run the static test.
3. Run the validation trigger evals and tune on train until accepted. Commit the new baseline.
4. Rollback: revert the SKILL.md frontmatter. The trigger sets and baseline stay useful.

If the harness `trigger` command is not ready yet, steps 2 and the static test can merge first. Acceptance (step 3) is then recorded as a follow-up gate in the harness PR.

## Open Questions

- ~~Does `strengthen-skill-eval-harness` also seed `eval/triggers/*.yaml`?~~ Resolved: it does (10 sets, 10 + 10 queries each, reusing D5). This change reviewed and extended them (one typo-style train positive per set) instead of recreating them.

## Implementation Notes

Implemented after `fix-library-skill-keyword-correctness`, `unify-library-install-guidance`, `retire-generator-skills`, `merge-libdoc-skills`, `align-skill-names-with-spec`, `harden-skill-script-execution` and `strengthen-skill-eval-harness`. Details per task are in tasks.md ("Implementation Notes"); the design-level deviations:

- **D1:** confirmed that both parsers of `scripts/validate-skills.py` (PyYAML and the stdlib fallback) and the installer's PyYAML parser accept the double-quoted scalar; `name`/`description` stay on frontmatter lines 2–3 (tools read `head -5`). The D7 warning above 500 characters is a `UserWarning` in pytest.
- **D2:** the confirmed defaults are stated in both default skills' descriptions (rf-browser "or wants a web test with no library chosen yet", rf-requests "without naming a library") and in the non-default siblings' boundaries. rf-appium ↔ rf-platynui name each other (plus the web skills) instead of "Not for …" wording, so every description ends with a named skill.
- **D3:** final texts live in `skills/rf-*/SKILL.md`; differences from the drafts are listed in tasks.md 3.2 (notably `Execute Javascript`, the libdoc spelling; rf-setup "Use when" instead of "Use for"; rf-libdoc keeps "signatures"). The pre-change texts are preserved in `pre-change-descriptions.yaml` for the deferred baseline run.
- **D4:** rf-libdoc and rf-results gained a `## Companion Skills` section (they had none). Optional rows used: rf-appium ↔ rf-platynui. The `language` and `python-library` keys are not added here; `add-rf-language-skill` / `add-rf-python-library-skill` add them to `CATALOGUE` / `REQUIRED_ROWS` in `tests/test_skill_descriptions.py` together with their rows.
- **D6:** all live measurement (pre-change baseline, train tuning, validation acceptance, committed `eval/baselines/triggers.json`) is deferred to a follow-up run; the static contract (descriptions, companion catalogue, trigger-set shape) is enforced now.
- **D7:** the test additionally checks that the boundary appears after `Use when`, that every named `rf-*` skill is shipped and not the skill itself, per-skill trigger terms, the default clauses, and that no trigger query contains a skill id.
- Hook: `maybe_inject_rf_context.mjs` gained a single "Pick by import" routing line consistent with D2 (tested in `tests/test_hook_scripts.py`); the name-list lines are unchanged.
