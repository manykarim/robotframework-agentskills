# Changelog

This is the **content channel** version (also drives the Claude Code
plugin tarball and the skills tarballs). The `rf-agentskills` Python
installer is versioned independently — see `RELEASING.md` at the repo
root for the policy.

For Copilot users who want subagents, hooks, and MCP server in
addition to the chat skills shipped here, install the companion
`rf-agentskills` package:

```
pipx install rf-agentskills
rf-agentskills install --agent copilot
```

## 2.0.0 (unreleased)

Breaking content release. Later changes in this release cycle add their
entries here.

- **rf-language / rf-setup:** every documented `robocop check` / `robocop
  format` command passes `--no-cache` (Robocop otherwise leaves a
  `.robocop_cache/` directory in the project).
- **rf-appium:** duplicate H1 heading removed.
- **New skill `rf-language`:** writing and reviewing Robot Framework test
  cases (keyword-driven, data-driven, BDD), suites and `__init__.robot`,
  tags and selection, user keywords and arguments, embedded arguments,
  variables, resource and variable files, with a version gate, verified
  gotchas, a legacy-to-modern migration table (Robocop 9 rule IDs) and
  examples labelled "RF 7.0+". Its bundled `scripts/rf_conventions.py`
  detects the project's conventions. The Companion Skills tables of
  rf-setup, rf-robotcode and the six library skills link to it.
- **New skill `rf-python-library`:** writing and fixing Robot Framework
  keyword libraries and listeners in Python (template, scope by state
  lifetime per the RF User Guide, conversion, failures and logging,
  dynamic/hybrid APIs, listener API v3, libdoc), with a version gate,
  thirteen verified gotchas and examples labelled "RF 7.0+". Its bundled
  `scripts/check_library.py` checks project libraries for RF-specific defects
  before tests run. rf-language's description and Companion Skills table and
  rf-setup's project layout point to it.
- **Removed skills:** `rf-keyword-builder`, `rf-testcase-builder`,
  `rf-resource-architect` (and in the Claude Code plugin the slash commands
  `/rf-agentskills:keyword-builder`, `:testcase-builder`,
  `:resource-architect`), plus their scripts `keyword_builder.py`,
  `testcase_builder.py`, `resource_architect.py`.
- **Removed MCP tools** (`rf-tools` server): `rf_keyword_builder`,
  `rf_testcase_builder`, `rf_resource_architect`. Calling them returns the
  normal unknown-tool error.
- **Why:** the JSON → script → paste round trip cost more turns and tokens
  than writing Robot Framework directly, and the scripts lagged the language
  (no RF 7 typed arguments, unimplemented layout modes).
- **Use instead:** write keywords, test cases and resource files directly;
  check keyword names and arguments with `rf-libdoc`
  (or `robotcode libdoc`), and validate with
  `robot --dryrun`. The companion tables of the library skills, `rf-setup`
  and `rf-robotcode` no longer list the generators; the subagents follow the
  write-directly workflow.
- **Upgrade notes:** the VS Code extension and the Claude Code plugin replace
  the skill tree on update. `rf-agentskills` installer users re-run
  `rf-agentskills install` (0.7.0 prunes the old copies). Skills-tarball
  users delete `rf-keyword-builder/`, `rf-testcase-builder/` and
  `rf-resource-architect/` from their skills directory by hand. To keep the
  generators, stay on 1.2.0.
- **Merged skills:** `rf-libdoc-search` and `rf-libdoc-explain` are
  replaced by one skill, `rf-libdoc` (Claude Code plugin: slash command
  `/rf-agentskills:rf-libdoc` replaces `:libdoc-search` and `:libdoc-explain`).
  It finds keywords for a use case, explains a keyword's arguments (with
  search fallback) and lists a library's keywords, and points to
  `robotcode libdoc` when robotcode is installed. `rf_libdoc.py` flags and
  JSON output are unchanged; the MCP tools `rf_libdoc_search` and
  `rf_libdoc_explain` keep their names. The script ships as one regular file
  (no symlink). **Upgrade:** the extension and plugin replace the skill tree;
  installer users re-run `rf-agentskills install`; users who copied skill
  folders by hand delete `rf-libdoc-search/` and `rf-libdoc-explain/`.
- **One identifier per skill (Claude Code plugin, installer, tarballs).**
  Every skill's folder name now equals its `name` (`rf-<topic>`) in every
  channel. The VS Code extension already used these names, so **VS Code users
  see no change**. Elsewhere: repo/tarball folders `robotframework-browser-skill`,
  `-selenium-skill`, `-appium-skill`, `-requests-skill`, `-restinstance-skill`,
  `-platynui-skill`, `-robotcode-skill`, `-setup-skill` and
  `robotframework-results` become `rf-browser`, `rf-selenium`, `rf-appium`,
  `rf-requests`, `rf-restinstance`, `rf-platynui`, `rf-robotcode`, `rf-setup`
  and `rf-results`; the Claude Code plugin folders and slash commands change
  from the short names (`/rf-agentskills:browser`, `:setup`, `:results`,
  `:libdoc`, …) to `/rf-agentskills:rf-browser`, `:rf-setup`, `:rf-results`,
  `:rf-libdoc`, …. Installer users re-run `rf-agentskills install` (old
  folders are pruned); tarball users delete the old folders by hand
  (`rf-agentskills doctor` lists them).
- Every `SKILL.md` declares `license`, `compatibility` (runtime needs) and
  `metadata` (`author`, `version`); CI validates all channels against the
  agentskills.io frontmatter rules (`scripts/validate-skills.py`).
- **Skill scripts run in the project environment.** `rf-libdoc` and
  `rf-results` now document `uv run python scripts/rf_libdoc.py …` /
  `uv run python scripts/rf_results.py …` (paths relative to the skill folder)
  plus one fallback line for non-uv projects (`.venv/bin/python` /
  `poetry run python`, see rf-setup). Commands copied from 1.x
  (`python scripts/…`) still work but use whatever `python` is on PATH.
- **Script CLI contract:** exit codes `0` ok, `1` internal error, `2` usage,
  `3` Robot Framework missing or older than 7, `4` input not found or not
  loadable (previously `1` for all failures); diagnostics are `error:` /
  `warning:` / `hint:` lines on stderr (no JSON error on stderr, no
  `pip install` advice); `--help` works without Robot Framework and ends with
  examples. Both scripts carry PEP 723 metadata (`robotframework>=7`).
- **Bounded output:** `rf_libdoc.py --max-doc-chars` (default 4000, `0` = full
  text, truncation marker inside `doc`); `rf_results.py --limit` (default 50)
  caps `details` test entries (failed first) and each `errors` list and reports
  `omitted` counts; both scripts accept `--json-out FILE`.
- **Sharper skill descriptions:** every skill's `description` now opens with
  what it does and for which library or tool, has a `Use when` clause with the
  terms users type (`Library    Browser`, `output.xml`, `robot.toml`,
  `No module named 'Browser'`, `No keyword with name`) and ends with the
  sibling to use instead: rf-browser vs rf-selenium (by import; rf-browser is
  the default for new web tests), rf-requests vs rf-restinstance (by import or
  JSON Schema/OpenAPI; rf-requests is the default for API tests),
  rf-results / rf-libdoc vs rf-robotcode (robotcode installed or named), and
  rf-setup for installing and environment errors. No more "Guide AI agents…"
  phrasing.
- **Compact skill descriptions:** agents list skill descriptions only while
  they fit a character budget (about 8000 characters in Claude Code for
  200k-context models), so every description is now at most 160 characters
  and starts with a load-first cue ("Use first, before exploring or
  answering, for Robot Framework web tests with Browser Library (Playwright):
  selectors, waits."). The trigger terms, pasted errors and sibling boundaries
  moved into a `## When to use` block near the top of each `SKILL.md`.
- **Standard Companion Skills tables:** every skill (now including rf-libdoc
  and rf-results) has a `Need | Skill` table built from one shared catalogue,
  with rows for its sibling, `rf-setup`, keyword lookup (`rf-libdoc`, or
  `robotcode libdoc`) and result analysis (`rf-results`, or
  `robotcode results`).
- **Library skills restructured** (rf-browser, rf-selenium, rf-appium,
  rf-requests, rf-restinstance): one shared layout (Installation, Import and
  defaults, a "which keyword for which situation" table, an agent workflow
  with a libdoc → dry run → run → results → fix loop, verified Gotchas, a
  gated reference table). Breaking for anyone who read the files directly:
  every `references/keywords-reference.md` catalog is deleted (query libdoc
  with `robotcode libdoc <Library> list/show` or the rf-libdoc skill
  instead), and several references were merged or renamed (rf-browser
  `tabs-windows.md` → `browser-context-page.md`; rf-selenium
  `webdriver-setup.md` → `browser-setup.md`, `screenshots-logs.md` →
  `troubleshooting.md`; rf-appium `device-capabilities.md` →
  `capabilities.md`, `android-specific.md` + `ios-specific.md` →
  `platform-specific.md`; rf-requests `http-methods.md` →
  `request-options.md`). Examples were trimmed to suites that pass
  `robot --dryrun`.

Companion: `rf-agentskills` installer 0.7.0 ships the same content bundle
(`bundled content: 2.0.0`).

## 1.2.0 (2026-03-17)

- Fix: VS Code skill dirs now match the `name:` field per the Agent
  Skills spec (so chat skills resolve correctly in Copilot 1.108+).
- Architecture overhaul: MCP server, script drift, hooks, tests, and
  build infrastructure.

Companion: `rf-agentskills` installer ≥ 0.3.0 ships the same content
bundle (`bundled content: 1.2.0`).

## 1.1.0

- Iterative skill updates and minor fixes.

## 1.0.0 (2026-02-27)

- Initial release with 11 Robot Framework Agent Skills
- Skills for Browser, Selenium, Appium, Requests, RESTinstance libraries
- Keyword builder, test case builder, resource architect generators
- Library documentation search and explanation tools
- Results analysis for output.xml files
