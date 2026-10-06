# Changelog — rf-agentskills installer

The `rf-agentskills` package is versioned independently from the
content bundle (Claude Code plugin, VS Code extension, skills
tarballs). See `RELEASING.md` at the repo root for the policy.

## 0.7.0 — 2026-10-06

Installer minor release that bundles **content 2.0.0** (a breaking content
release: three skills removed, the `rf-tools` MCP server and its tools
removed, see below).

### Bundled content
- **rf-agentskills plugin manifest: 2.0.0** (Claude Code plugin, marketplace
  entry and VS Code extension move in lockstep).

### Added
- **Plugin hook `rf_error_hints.mjs`** (PostToolUse on Bash): the first time a Robot Framework error such as `No keyword with name`, `Multiple keywords with name`, `Invalid argument syntax`, a failing variable or a failed library import appears in a session, it injects a short hint naming the skill to load and the fix. It never blocks.
- **Deprecated-syntax warnings on edit (plugin hooks):** `validate_robot.mjs`
  now classifies its single Robocop pass by rule ID. Error-severity findings
  still block exactly as before (exit 2); deprecations (`DEPR03/04/07–11`:
  `WITH NAME`, singular headers, `Force/Default Tags`, `Run Keyword If`,
  loop-exit keywords, `Return From Keyword`, `[Return]`) and `VAR` hints
  (`DEPR05/06`) are **non-blocking** additional context, listed for the lines
  the edit touched (with the modern replacement), counted for other lines,
  capped at 10 findings / 2,000 characters and not repeated within a session.
  `RF_AGENTSKILLS_DEPRECATION_CHECK=warn|off` (default `warn`; any other value,
  including `block`, means `warn` — deprecations never block). The project's
  Robocop config (`ignore = ["DEPR08"]`) and Robocop's RF-version gating apply.
- **Opt-in per-file dry run:** `RF_AGENTSKILLS_FILE_DRYRUN=1` runs
  `robot --dryrun` on each written `.robot` suite (not `.resource` /
  `__init__.robot`) and reports "No keyword with name" and `[ ERROR ]` lines as
  advisory context. Off by default.
- Hook timeouts: every process the hooks start has a timeout (Robocop 10 s,
  dry run 20 s, probes 5 s, project-wide Stop checks 120 s) and `hooks.json`
  declares `timeout` 45 s (PostToolUse) / 15 s (UserPromptSubmit,
  SessionStart). A timeout skips the check silently.
- Eval: adversarial task `adv-legacy-syntax-01` (fixture `sut-legacy-style`);
  the `lint_clean` grader takes an optional `select` list, passed as repeated
  `--select` options.
- **Robot Framework language skill** (`/rf-agentskills:rf-language`) — one
  skill for writing and reviewing `.robot` and `.resource` code: test cases in
  keyword-driven, data-driven (`Test Template`) and BDD style, suites and
  `__init__.robot` rules, tags and test selection, user keywords and
  arguments (typed arguments gated to RF 7.3+), embedded arguments, `VAR`
  scopes, control structures, resource and variable files, and a
  legacy-to-modern table with Robocop 9 rule IDs. It ships a version gate,
  verified gotchas (named-argument spacing, the "Los Angeles Lakers"
  embedded-argument trap, typed arguments on RF < 7.3, `__init__.robot`
  keyword visibility), dry-runnable examples labelled "RF 7.0+" and a
  validation loop (dry run, robocop, targeted real run, results). It
  replaces the retired resource architect as the home for resource layout.
- **`rf_conventions` script** — `skills/rf-language/scripts/
  rf_conventions.py` reports a project's Robot Framework version and feature
  availability, separator/assignment/naming style, embedded and typed
  arguments, duplicate keyword names, BDD and template usage, tags, legacy
  constructs with Robocop rule IDs, resource/variable-file layout and the web
  library in use, as bounded JSON (`schema: rf-conventions/1`). Installed
  with the skill for every agent that ships skills (absolute script path for
  agents that do not expand `${CLAUDE_SKILL_DIR}`).
- **Python keyword library skill** (`/rf-agentskills:rf-python-library`) —
  writing and fixing Robot Framework keyword libraries and listeners in
  Python: a default `@library`/`@keyword` template, a scope table that follows
  the RF User Guide (`TEST` by default, `SUITE`/`GLOBAL` with a cleanup keyword
  only when state must span tests), module vs class and static/hybrid/dynamic
  decisions, type-hint conversion (Enum, Literal, TypedDict, `Secret`, custom
  converters), exceptions and logging, threads and timeouts, listener API v3,
  libdoc and packaging; a version gate (RF 6.1–7.5), thirteen verified
  gotchas and runnable examples labelled "RF 7.0+".
- **`check_library` script** —
  `skills/rf-python-library/scripts/check_library.py` loads each project
  library like libdoc does, in a child process with a timeout and only inside
  the project root, and reports keywords, scope and API style plus findings
  (`import_failed`, `keyword_creation_failed`, `no_keywords`,
  `leaked_keyword`, `public_method_not_keyword`, `listener_method_exposed`,
  `signature_lost`, `union_with_str`, `state_in_test_scope`,
  `output_during_import`, `broad_except`, `untyped_argument`,
  `positional_only_argument`, `missing_doc`, `library_doc_missing`) as bounded
  JSON (`schema_version` 1). Installed with the skill for every agent that ships
  skills.
- **rf-setup `project-layout.md`** now points to `rf-python-library` for the
  contents of `libraries/`.
- **rf-setup `project-layout.md`** now points to `rf-language`, puts
  `libraries/` on the python-path, states that YAML variable files need
  `uv add pyyaml`, and shows `--variablefile` for plain `robot` (which does not
  read `robot.toml`) next to a robotcode `variable-files` profile.
- **Re-install prunes files the bundle no longer ships.** Running
  `rf-agentskills install` again for an (agent, scope) that already has a
  manifest record now deletes files the previous install wrote that the
  current bundle does not plan to write — with the same safety rules as
  `uninstall`: only files whose hash still matches are deleted, empty parent
  directories are pruned up to the install root, and user-modified files are
  kept, reported and dropped from tracking. Only categories being installed
  are pruned (`--what skills` never touches agents, hooks or MCP entries).
  `--dry-run` lists the files as `remove` rows; the install summary reports
  the count. Manifest file entries now carry a `category`; records from older
  installers derive it from the path.
- **robotcode CLI skill** (`/rf-agentskills:rf-robotcode`) — guides agents
  through the `robotcode` CLI: test discovery, `libdoc`, running with
  `robot.toml` profiles and wrappers, piped REPL sessions, `robot-debug`
  (stop at failures, breakpoints, live keywords), `results`
  (summary/show/log/stats/diff) and `analyze code`. Includes agent-safe
  invocation rules and version-stamped known limitations (robotcode 2.7.0).
  The results and libdoc skills now point to it when `robotcode` is
  installed; they are unchanged otherwise.
- The context-injection hook now triggers on `robotcode`, `robot-debug` and
  `robot.toml`, and lists the robotcode skill.
- **Setup skill** (`/rf-agentskills:rf-setup`) — installs Robot Framework,
  test libraries and tooling into the project environment with uv
  (preferred), venv + pip or Poetry: tool detection from lockfiles, Python
  version floors (3.12 recommended), library post-install steps (Browser
  `[bb]` + `rfbrowser install` or Node + `rfbrowser init`, Appium server and
  drivers, PlatynUI pre-release), project layout, GitHub Actions example and
  troubleshooting. Every recipe was run against uv 0.9.26, Poetry 2.4.1 and
  pip 26. The SessionStart environment check and the context-injection
  hook now point to it.

- **`doctor` flags legacy skill folders.** `rf-agentskills doctor` now
  scans every adapter's skills folder (user and project scope) for pre-2.0
  rf-agentskills skill folders (`browser/`, `setup/`, `results/`,
  `robotframework-*-skill/`, …) that the manifest does not own and whose
  `SKILL.md` carries one of our old names, and prints a warning with an
  `rm -r` hint. It never deletes them; someone else's `browser` skill is
  left alone.
- Every bundled `SKILL.md` now declares `license: Apache-2.0`, a
  `compatibility` line (Python / Robot Framework floors, library package and
  external runtimes such as Node.js, the Appium server, robotcode or uv) and
  `metadata` (`author`, `version` = content version).

- **Skill script CLI contract** (`rf_libdoc.py`, `rf_results.py`): PEP 723
  metadata (`robotframework>=7`), `--help` examples that work without Robot
  Framework, `--json-out FILE`, `rf_libdoc.py --max-doc-chars` (default 4000)
  and `rf_results.py --limit` (default 50, with `omitted` counts).
- **Installer renders skill script paths per agent.** Adapters carry an
  `expands_skill_dir` flag: Claude Code keeps `${CLAUDE_SKILL_DIR}` (it
  substitutes it itself); Codex, Cursor, Copilot, Goose and OpenCode get the
  absolute installed skill path (`transforms.substitute_skill_dir`). The
  per-skill scripts are also staged under
  `rf-agentskills-files/skills/<skill>/scripts/` for the hooks (the Stop hook
  runs `rf_results.py`).
- **(Superseded below: the rf-tools MCP server was removed.) rf-tools MCP server uses the project environment:** it runs a script
  in-process when its own interpreter has Robot Framework 7+ and the requested
  libraries, else in a subprocess with the project interpreter (`uv run
  --frozen python` for a uv project, `.venv`, `$VIRTUAL_ENV`; 120 s timeout).
  Script errors come back as tool errors with `hints`; the server keeps
  running. New optional tool inputs: `max_doc_chars` (libdoc tools), `limit`
  (`rf_results_analyze`).

### Changed
- **Skill descriptions re-fitted to the skill listing:** Claude Code 2.1.288 leaves 1274 characters for them (1423 with 2.1.286, 1734 with 2.1.284), so all 12 descriptions now total 1210 and every description stays visible (rf-setup was listed by name only). The library-named skills say "RF" instead of "Robot Framework"; rf-appium/rf-selenium say "Not installs/drivers: rf-setup.", rf-restinstance "Not installs: rf-setup.", and rf-libdoc/rf-results point to rf-robotcode, fixing recorded wrong-skill loads. Accepted on the validation split (6 runs per query) and checked on holdout2.
- **Subagents rewritten as thin routers** (`rf-test-architect`,
  `rf-keyword-consultant`, `rf-migration-guide`, `rf-debug-expert`, ≤ 120
  lines each): they keep only agent-owned content (library selection, layout,
  lookup method, migration procedure and library-migration tables, failure
  classification), route everything else to the skills (`rf-language`,
  `rf-python-library`, `rf-libdoc`/`rf-robotcode`, `rf-results`, library
  skills, `rf-setup`) and share one verification loop (write → libdoc →
  `robot --dryrun` → `robocop check` → run → results). Removed: the keyword
  consultant's cross-library map and stdlib list (it listed `Run Keyword If`,
  `Set Variable`, `Create List`), the migration guide's invalid
  `${name}: str` typed-argument example (its syntax table now lives in
  `rf-language/references/migration.md`; migrations are verified with
  `robocop check --select "DEPR*"` and `--threshold E`), and the debug
  expert's `Wait Until Keyword Succeeds` / timeout-bump flakiness advice.
- **Hooks prefer the project interpreter:** new `scripts/_python_env.mjs`
  resolves Python as `$VIRTUAL_ENV` → `<cwd>/.venv` → `python_runtime.json` →
  `python3`/`python`, so Robocop sees the project's Robot Framework version.
  Hooks never run `uv run`.
- **Context injection** (`UserPromptSubmit`) is a ≤ 450-character routing
  text (tests/keywords/resources/variables → `rf-language`, Python libraries
  → `rf-python-library`, library usage → the library skill, keyword lookups →
  `rf-libdoc` / `robotcode libdoc`, RF 7 syntax reminder) instead of skill and
  subagent lists; pasted RF section headers (`*** Keywords ***`, …) now
  trigger it.
- **SessionStart report** reports Robocop availability ("checks on edit are
  disabled" without it), uses the project interpreter, and replaces the
  `pip install` / `rfbrowser init` advice with `uv add` lines and a pointer
  to the rf-setup skill.
- Subagents (`rf-keyword-consultant`, `rf-debug-expert`, `rf-migration-guide`)
  no longer embed script paths; they load the `rf-libdoc` / `rf-results`
  skill. The Stop-hook reminder prints
  `uv run python "<absolute path>/skills/rf-results/scripts/rf_results.py" …`
  computed from the hook's own location.
- The eval harness rewrites `${CLAUDE_PLUGIN_ROOT}` only in staged JSON
  configs (hooks, MCP); SKILL.md files are staged unchanged, so evals exercise
  the real script-path resolution.
- Library skills (browser, selenium, appium, requests, restinstance,
  platynui) defer installation to the setup skill: each `## Installation`
  block now shows only the `uv add` line from the setup skill's library
  table plus the library-specific post-install step, and every skill lists
  the setup skill as a companion. Browser defaults to
  `robotframework-browser[bb]` + `rfbrowser install` (the Node.js
  `rfbrowser init` path is a labelled escape hatch); Selenium relies on
  Selenium Manager (webdriver-manager, `browser_setup.py`, manual driver
  downloads and `executable_path` guidance removed; CI examples use
  `uv sync --locked`); PlatynUI shows the pre-release pin/opt-in in uv form.
  A new test forbids bare `pip install` recipes in library skills.
- Skill descriptions rewritten (bundled content 2.0.0): each starts with a
  third-person capability statement naming Robot Framework and the library or
  tool, has a `Use when` clause with concrete trigger terms (import lines,
  `output.xml`, `robot.toml`, CLI names, pasted errors) and ends with the
  sibling skill to use instead (rf-browser ↔ rf-selenium, rf-requests ↔
  rf-restinstance, rf-results / rf-libdoc ↔ rf-robotcode, rf-setup ↔ library
  skills). With no library named, web requests go to rf-browser and API
  requests to rf-requests. Every `## Companion Skills` table (rf-libdoc and
  rf-results gained one) uses rows from one shared catalogue; the plugin's
  context-injection hook adds a one-line "Pick by import" routing hint. New
  `tests/test_skill_descriptions.py` enforces the description and companion
  rules and the trigger-set shape; each `eval/triggers/<skill>.yaml` gained a
  typo-style user query. Trigger-rate acceptance runs are pending.
- **Compact skill descriptions** (bundled content 2.0.0, openspec change
  `tune-skill-descriptions`): Claude Code lists skill descriptions only while
  they fit a character budget (about 8000 characters for 200k-context models),
  and 9 of the 12 previous descriptions were never shown. Every description is
  now at most 160 characters (all 12 listing lines: 1697 characters) with a
  load-first cue, e.g. rf-results: "Use first, before reading output.xml
  yourself, to summarise, explain or merge Robot Framework run results
  (output.xml, rebot)." The trigger terms and sibling boundaries moved into a
  new `## When to use` block near the top of each `SKILL.md`. Measured on the
  validation split (Haiku 4.5, 3 runs per query, default listing budget):
  41/50 should-trigger queries loaded their skill (was 21/50), with no
  should-not-trigger regressions. `eval/baselines/triggers.json` is rebased on
  that run and records the per-skill shortfalls (rf-language, rf-libdoc,
  rf-python-library, rf-robotcode) and the two skills not meeting the target
  (rf-browser, rf-restinstance). Each `eval/triggers/<skill>.yaml` gained 10
  `holdout` queries.

### Changed (BREAKING)
- **`rf-tools` MCP server removed** (openspec change
  `drop-rf-tools-mcp-server`). It wrapped the skills' scripts as the tools
  `rf_libdoc_search`, `rf_libdoc_explain`, `rf_results_analyze`,
  `rf_conventions` and `rf_check_library`, but every skill runs its script
  directly, evals never used the server, and it crashed at startup on machines
  whose `python3` lacked the `mcp` package. No agent gets an MCP server entry
  any more; `--what mcp` is accepted and ignored with a note. **Re-installing
  removes the `rf-tools` entry** older installers merged into `.mcp.json`,
  `.vscode/mcp.json`, Cursor `mcp.json`, Codex `config.toml`, OpenCode
  `opencode.json`, Goose `config.yaml` and `claude_desktop_config.json`
  (foreign entries are kept) and deletes the staged `servers/` files.
  Subagents and rf-language name the skill and its command instead of the
  tools. Goose and OpenCode no longer get the `rf-agentskills-files/` support
  copy (it only served the server).
- **Claude Desktop gets the skills:** `install --agent claude-desktop` now
  writes one upload-ready `<skill>.zip` per skill (skill folder at the archive
  root) to `~/rf-agentskills-claude-desktop/` and explains the upload
  (Customize → Skills → Upload a skill; code execution enabled). It no longer
  touches `claude_desktop_config.json`. CI artifacts and GitHub releases carry
  the same archives (`scripts/build-skill-zips.py`).
- **Library skills restructured; keyword catalogs removed.** rf-browser,
  rf-selenium, rf-appium, rf-requests and rf-restinstance now share one
  SKILL.md layout (Installation, Import and defaults, decision table, agent
  workflow with a libdoc → `robot --dryrun` → run → results → fix loop,
  libdoc-verified Gotchas, gated reference table) within 250 lines /
  12,000 characters. Their `references/keywords-reference.md` files are
  deleted (agents query `robotcode libdoc <Library> list/show` or rf-libdoc),
  and several references were merged or renamed (rf-browser `tabs-windows.md`
  → `browser-context-page.md`; rf-selenium `webdriver-setup.md` →
  `browser-setup.md`, `screenshots-logs.md` → `troubleshooting.md`;
  rf-appium `device-capabilities.md` → `capabilities.md`, `android-specific.md`
  + `ios-specific.md` → `platform-specific.md`; rf-requests `http-methods.md`
  → `request-options.md`). Re-installing prunes the removed files. New
  `tests/test_library_skill_structure.py` enforces the layout, budget,
  references, style and example dry runs.
- **Libdoc skills merged.** `rf-libdoc-search` and `rf-libdoc-explain`
  (plugin/installed skills `libdoc-search/` and `libdoc-explain/`, slash
  commands `/rf-agentskills:libdoc-search` and `:libdoc-explain`) are
  replaced by one skill, `rf-libdoc` (plugin/installed skill `rf-libdoc/`,
  slash command `/rf-agentskills:rf-libdoc`), that covers keyword search,
  keyword explain (with search fallback) and listing a library, and says
  when to prefer `robotcode libdoc`. `rf_libdoc.py` flags and its JSON
  output contract are unchanged, and so are the `rf-tools` MCP tools
  `rf_libdoc_search` and `rf_libdoc_explain`. The script now ships as one
  regular file per channel (the symlink in the old explain skill is gone;
  `scripts/check-drift.sh` rejects symlinks in skill trees).
  **Upgrade:** re-running `rf-agentskills install` removes the old
  `libdoc-search/` and `libdoc-explain/` copies (prune-on-reinstall);
  users who copied skill folders by hand must delete the two old folders.
- **Generator skills retired.** The skills `rf-keyword-builder`,
  `rf-testcase-builder` and `rf-resource-architect` (plugin slash commands
  `/rf-agentskills:keyword-builder`, `:testcase-builder`,
  `:resource-architect`), their scripts `keyword_builder.py`,
  `testcase_builder.py` and `resource_architect.py`, and the `rf-tools` MCP
  tools `rf_keyword_builder`, `rf_testcase_builder` and
  `rf_resource_architect` are removed. The JSON → script → paste round trip
  cost more turns and tokens than writing Robot Framework directly, and the
  scripts lagged the language. Instead: write keywords, test cases and
  resource files directly, check keyword names and arguments with the
  libdoc skill (or `robotcode libdoc`), and validate with `robot --dryrun`
  (the validation hooks also check every written file). The subagents
  `rf-test-architect`, `rf-keyword-consultant` and `rf-migration-guide` now
  follow that workflow. Calling a removed MCP tool returns the normal
  unknown-tool error. To keep the old behaviour, stay on content 1.2.0 /
  `rf-agentskills` 0.6.0.
  **Upgrade:** re-running `rf-agentskills install` removes the old copies
  (see Added). Installs made before a manifest existed, and skills-tarball
  users, delete `keyword-builder/`, `testcase-builder/` and
  `resource-architect/` (tarball: `rf-keyword-builder/`,
  `rf-testcase-builder/`, `rf-resource-architect/`) from their skills
  directory by hand.
- `rf_results` / the `rf_results_analyze` MCP tool no longer emit
  `details.criticality`. Test criticality was removed in Robot Framework 4.0;
  use `details.tags` (a `critical` tag still gets its own entry there).
  The rf-results skill no longer mentions criticality.
- **One identifier per skill: `rf-<topic>` everywhere.** Skill folders now
  have the same name as their `SKILL.md` `name` in every channel, as the
  agentskills.io spec requires. Claude Code plugin skills and the folders
  this installer writes (`.claude/skills/`, `~/.agents/skills/`,
  `.cursor/skills/`, `~/.config/opencode/skills/`, …) change from the short,
  collision-prone names to the `rf-` ids, and the plugin slash commands
  change accordingly (`/rf-agentskills:browser` → `/rf-agentskills:rf-browser`):

  | Before (repo `skills/` folder) | Before (plugin / installed folder) | Now |
  |---|---|---|
  | `robotframework-browser-skill` | `browser` | `rf-browser` |
  | `robotframework-selenium-skill` | `selenium` | `rf-selenium` |
  | `robotframework-appium-skill` | `appium` | `rf-appium` |
  | `robotframework-requests-skill` | `requests` | `rf-requests` |
  | `robotframework-restinstance-skill` | `restinstance` | `rf-restinstance` |
  | `robotframework-platynui-skill` | `platynui` | `rf-platynui` |
  | `robotframework-robotcode-skill` | `robotcode` | `rf-robotcode` |
  | `robotframework-setup-skill` | `setup` | `rf-setup` |
  | `robotframework-results` | `results` | `rf-results` |
  | `rf-libdoc` (merged, see above) | `libdoc` | `rf-libdoc` |

  **Upgrade:** re-run `rf-agentskills install`; the re-install pruning
  removes the old folders it recorded (files you edited are kept and
  reported). Folders copied by hand from a release tarball are never
  deleted — `rf-agentskills doctor` lists them with an `rm -r` hint.
  Rollback: installing an older release re-creates the old names; the new
  `rf-*` folders then stay until `rf-agentskills uninstall`.

- **Skill script commands and layout.** `rf-libdoc` / `rf-results` SKILL.md
  commands are now `uv run python scripts/<name>.py …` (root/VS Code, relative
  to the skill folder) and `uv run python "${CLAUDE_SKILL_DIR}/scripts/<name>.py" …`
  (Claude Code plugin), with a single non-uv fallback line (see rf-setup).
  Scripts ship inside each skill's own `scripts/` folder in every channel; the
  flat plugin copies `plugins/rf-agentskills/scripts/rf_libdoc.py` and
  `rf_results.py` (installed as `rf-agentskills-files/scripts/*.py`) are
  removed — re-install prunes them. Commands copied from earlier releases
  (`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/…"`) no longer resolve.
- **Script exit codes:** `0` ok (also no matches / partial source failures),
  `1` internal error (`--debug` for a traceback), `2` usage, `3` Robot
  Framework missing or < 7, `4` input not found / not loadable (previously `1`
  for every failure). Diagnostics are `error:`/`warning:`/`hint:` stderr lines
  (the JSON error object on stderr and the `pip install robotframework`
  advice are gone); stdout is empty on failure.
- `scripts/check-drift.sh` also fails on `${CLAUDE_PLUGIN_ROOT}` in any
  SKILL.md, on bare `python scripts/…` commands and on any flat plugin
  `scripts/*.py`.

### Fixed
- The PostToolUse hook (and the documented `robocop` commands in rf-language,
  rf-setup and the subagents) now pass `--no-cache`, so Robocop no longer
  leaves a `.robocop_cache/` directory in the user's project.
- `rf-appium` SKILL.md had two H1 headings.
- The `lint_clean` eval grader called `robocop <path>` (not a Robocop 6+
  command); it now runs `robocop check --no-cache`.
- A `--what` subset re-install no longer drops the files and config merges
  of the unselected categories from the manifest record (they were left on
  disk untracked, so `uninstall` could not remove them).
- Library skills (browser, selenium, appium, requests) no longer teach
  nonexistent, deprecated or malformed keyword calls in `SKILL.md`,
  `references/` and `assets/examples/` (for example Browser `Fill` →
  `Fill Text`, `Wait Until Network Is Idle` → `Wait For Load State
  networkidle`; Selenium `Wait Until Element Count Is*`, `Get Window Handle`;
  Appium `Element Should Be Visible` → `Expect Element`, removed `Long Press`,
  `Click A Point`, `Zoom`, `Pinch`, `*App` keywords). `Run Keyword If` is
  replaced by native `IF`. A new CI job (`check-skill-keywords`) resolves
  every keyword call against libdoc so these cannot come back.

### Known issues
- The SessionStart environment check writes its report to stderr, which
  Claude Code likely does not add to the model's context (only stdout is
  added for SessionStart). To be addressed in a follow-up change.

## 0.6.0 — 2026-06-18

Installer onboarding + uninstall-safety overhaul. No content-bundle change
(plugin tree untouched), so this is a tooling-only release.

### Added
- **Interactive install wizard.** Bare `rf-agentskills install` in a terminal
  now shows a multi-select of known agents (detected ones pre-checked) instead
  of erroring. Built on `questionary` (optional `[interactive]` extra) with a
  dependency-free stdlib numbered-selector fallback.
- **Headless selectors.** `--agents all|none|detected|<csv>` plus `--yes` and
  `--no-input`; non-TTY stdin is treated as non-interactive automatically.
  Nothing detected + no selection in a non-interactive context exits non-zero
  with the valid-agent list. `--agent`/`--all` kept as back-compat.
- **Zero-install entry point** via PyPI: `uvx rf-agentskills install` /
  `pipx run rf-agentskills install`.

### Changed
- **Project scope is now the default** (was user). Bare installs write into the
  current directory (`./.claude/` etc.); `--scope user` opts into a global
  home-directory install. `--project` defaults to CWD.
- **Uninstall manifest follows scope** — project installs keep it in
  `<project>/.rf-agentskills/`, user installs in the global data dir — so two
  projects no longer collide on the `(agent, scope)` key.

### Fixed
- **Hooks merge no longer clobbers other tools' or the user's hooks.** The
  previous merge replaced the entire `settings.json` `hooks` key on install
  (wiping foreign/user hooks) and dropped the whole key on uninstall (or
  stranded our own when `hooks` pre-existed). Hooks are now merged granularly
  per event and removed by an install-dir ownership marker — foreign and
  user-authored hooks are preserved on both install and uninstall, re-install
  is idempotent, and no orphaned commands are left behind. (The MCP per-server
  merge was already granular.) Cursor's `hooks.json` merge gets the same fix.

## 0.5.0 — 2026-06-18

Stable 0.5.0, consolidating pre-releases rc1–rc3. Install with
`pip install rf-agentskills` (no `--pre` needed) or the attached wheel.

### Bundled content
- **rf-agentskills plugin manifest: 1.2.0** — Robot Framework validation
  hooks, the new `rf-platynui` native-desktop skill, and the overhauled
  libdoc/testcase scripts.

### Added
- **Real static + semantic validation hooks** for `.robot`/`.resource` files
  (replaces the previous no-op `get_model` check): `PostToolUse` runs
  `robocop check --threshold E` (errors fed back via exit 2) and
  `robocop format --check` (formatting drift as a suggestion); an opt-in
  `Stop` hook (`RF_AGENTSKILLS_PROJECT_VALIDATION`) runs `robot --dryrun` +
  `robotframework-find-unused`. All tiers degrade to a silent no-op when their
  optional tooling is absent (install via the `validation` extra).
- **PlatynUI library skill** (`/rf-agentskills:platynui`) — native desktop UI
  testing (Windows UIA, Linux AT-SPI2) for the `new_core` `PlatynUI.BareMetal`
  surface: pinned pre-release install guidance, the XPath/namespace locator
  model, the 24-keyword reference, the CLI/inspector loop, and platform setup.
  The context-injection hook now triggers on `platynui`.
- `rf_libdoc.py --include-library-doc` flag.
- `testcase_builder.py --full-suite` flag — wraps output in a `*** Test Cases
  ***` section so the artifact is a directly runnable suite (default remains a
  composable fragment).
- Installer README: pre-release install guidance + a troubleshooting note for
  the stale-uv-cache "no version of rf-agentskills==<rc>" failure.

### Changed
- **BREAKING (script output contract):** `rf_libdoc.py` (and the `rf-tools`
  MCP `libdoc_search`/`libdoc_explain` tools) now return a single stable shape
  — `{schema_version, mode, libraries, results, ...}` with `mode ∈
  explain|search|fallback|list` and one uniform `results` array — instead of
  the old, outcome-dependent `matches`/`keyword_matches`/`keywords` keys.
- **Bounded payloads:** a library's full prose `doc` is **no longer embedded
  by default** (it dominated 56–96% of responses); pass `--include-library-doc`
  to restore it. Per-result `library` is now a minimal `{name,type,version}`
  reference. Typical explain responses drop from ~80 KB to ~3 KB.
- **Cleaner `usage`:** arguments are exposed as `params: [{name, type, default,
  kind}]` (`kind ∈ required|optional|vararg|kwarg|named_only`); names are bare
  (no `: type`), and `defaults` is keyed by bare name.

### Fixed
- **Stop-hook infinite loop.** Both Stop hooks (`maybe_remind_robot_tests.mjs`,
  `validate_robot_project.mjs`) now short-circuit on `stop_hook_active`, and
  the reminder fires at most once per session. (Lesson documented in the hook
  README: on Stop hooks, model-facing output — `additionalContext` or exit 2 —
  re-invokes the model, so "exit 0" alone is not non-blocking.)
- Marketplace SKILL.md validation reads files as UTF-8 (was failing on Windows
  for skills containing non-ASCII characters).

## 0.5.0rc3 — 2026-06-17 (pre-release)

Third pre-release toward 0.5.0. Fixes the Stop-hook loop and overhauls the
libdoc script output. Install with `pip install --pre rf-agentskills` or the
attached wheel.

### Bundled content
- **rf-agentskills plugin manifest: 1.2.0** — Stop-hook scripts and the
  libdoc/testcase scripts updated (see below).

### Fixed
- **Stop-hook infinite loop (High; blocker for promoting any `0.5.0rc*` to
  stable).** `maybe_remind_robot_tests.mjs` emitted its "run the suite"
  reminder on every `Stop` — including continuations — with no
  `stop_hook_active` guard, so once a session wrote a `.robot`/`.resource`
  file the reminder re-fired until Claude Code force-overrode the turn (9
  blocks). Both Stop hooks (`maybe_remind_robot_tests.mjs`,
  `validate_robot_project.mjs`) now short-circuit on `stop_hook_active`, and
  the reminder fires at most once per session. (Lesson documented in the hook
  README: on Stop hooks, model-facing output — `additionalContext` or exit 2
  — re-invokes the model, so "exit 0" alone is not non-blocking.)

### Changed
- **BREAKING (script output contract):** `rf_libdoc.py` (and the `rf-tools`
  MCP `libdoc_search`/`libdoc_explain` tools) now return a single stable shape
  — `{schema_version, mode, libraries, results, ...}` with `mode ∈
  explain|search|fallback|list` and one uniform `results` array — instead of
  the old, outcome-dependent `matches`/`keyword_matches`/`keywords` keys.
- **Bounded payloads:** a library's full prose `doc` is **no longer embedded
  by default** (it dominated 56–96% of responses); pass `--include-library-doc`
  to restore it. Per-result `library` is now a minimal `{name,type,version}`
  reference. Typical explain responses drop from ~80 KB to ~3 KB.
- **Cleaner `usage`:** arguments are exposed as `params: [{name, type, default,
  kind}]` (`kind ∈ required|optional|vararg|kwarg|named_only`); names are bare
  (no `: type`), and `defaults` is keyed by bare name.

### Added
- `rf_libdoc.py --include-library-doc` flag.
- `testcase_builder.py --full-suite` flag — wraps output in a `*** Test Cases
  ***` section so the artifact is a directly runnable suite (default remains a
  composable fragment).
- Installer README: pre-release install guidance + a troubleshooting note for
  the stale-uv-cache "no version of rf-agentskills==<rc>" failure.

## 0.5.0rc2 — 2026-06-17 (pre-release)

Second pre-release toward 0.5.0. Adds the PlatynUI skill on top of 0.5.0rc1's
validation hooks. Install with `pip install --pre rf-agentskills` or the wheel.

### Bundled content
- **rf-agentskills plugin manifest: 1.2.0** — now also bundles the new
  `rf-platynui` native-desktop skill (PlatynUI.BareMetal, new_core).

### Added
- **PlatynUI library skill** (`/rf-agentskills:platynui`) — native desktop UI
  testing (Windows UIA, Linux AT-SPI2) for the `new_core` `PlatynUI.BareMetal`
  surface: install guidance (pinned pre-release wheel; the `0.9.2` footgun),
  the XPath/namespace locator model, full 24-keyword reference, CLI/inspector
  loop, and platform setup. The context-injection hook now triggers on
  `platynui`.

### Fixed
- Marketplace SKILL.md validation reads files as UTF-8 (was failing on Windows
  for skills containing non-ASCII characters).

## 0.5.0rc1 — 2026-06-17 (pre-release)

Pre-release for testing the new Robot Framework validation hooks before
a stable 0.5.0. Install with `pip install --pre rf-agentskills` or from
the attached wheel.

### Bundled content
- **rf-agentskills plugin manifest: 1.2.0** — bundles the new
  validation hook scripts (`validate_robot.mjs` rewrite +
  `validate_robot_project.mjs`).

### Added
- **Real static + semantic validation hooks** for `.robot`/`.resource`
  files (replaces the previous no-op `get_model` check):
  - `PostToolUse` — `robocop check --threshold E` (structural errors,
    no style noise) feeds errors back to the agent via exit 2;
    `robocop format --check` surfaces formatting drift as a suggestion.
  - `Stop` (opt-in via `RF_AGENTSKILLS_PROJECT_VALIDATION`) —
    `robot --dryrun` + `robotframework-find-unused` over the project.
  - All tiers degrade to a silent no-op when their (optional) tooling
    is absent. Install the tooling with the `validation` extra.

## 0.4.2 — 2026-05-13

### Bundled content
- **rf-agentskills plugin manifest: 1.2.0** — unchanged from 0.4.1.

### Fixed
- **ClaudeCode SessionStart hook error on Windows / PowerShell**:
  After installing v0.4.1, every ClaudeCode session opened on Windows
  logged

  ```
  SessionStart:startup hook error
  Failed with non-blocking status code:
  The argument '…/scripts/check_rf_environment.ps1' to the -File
  parameter does not exist.
  ```

  Root cause: v0.4.1's `transforms.rewrite_hooks_for_windows()`
  substituted `.sh` → `.ps1` in the hooks block, **but no `.ps1` files
  ever shipped in the package**. All four hook commands (SessionStart,
  PostToolUse, UserPromptSubmit, Stop) pointed at non-existent files.
  Reported in
  `docs/issues/rf-agentskills_claudecode_powershell_error.txt`; full
  analysis and alternatives considered in
  `docs/issues/claudecode-powershell-startup-fix-proposal.md`.

### Changed — hook scripts migrated to Node.js
- The four hook scripts are now `.mjs` (Node.js) instead of `.sh` (bash).
  Hook commands look like
  `node "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.mjs"`.
- Rationale (per
  [claudefa.st cross-platform-hooks guidance](https://claudefa.st/blog/tools/hooks/cross-platform-hooks)):
  Claude Code itself ships as a Node.js CLI, so `node` is on PATH for
  the vast majority of installs. One implementation runs identically
  on Linux, macOS, and Windows — no `.sh`/`.ps1` parity to maintain.
- `transforms.rewrite_hooks_for_windows()` is **removed**. The
  Windows-specific hook command rewrite is no longer needed; the same
  hooks block is now written verbatim on every OS.
- Affects every adapter that registers hooks: Claude Code, Copilot
  (inherits from Claude Code), Cursor, and Codex.

### Added — Node-availability probe + graceful fallback
- At install time, the Claude Code / Cursor / Codex adapters probe
  `shutil.which("node")`. If Node is not on PATH, the hooks merge is
  **skipped** and a clear `post_install` note explains what to do
  (e.g. `winget install OpenJS.NodeJS` on Windows). Skills, subagents,
  and MCP server install normally regardless.

### Added — install-time Python interpreter is pinned for hooks
- `validate_robot.mjs` and `check_rf_environment.mjs` need to invoke
  Python to parse Robot Framework files (`from robot.api import
  get_model`) and probe library availability. They now read
  `<plugin_dst>/scripts/python_runtime.json` — written by the
  installer from `sys.executable` — to find the **same** Python
  rf-agentskills was installed into.
- This is the only correct interpreter to use under pipx, uv tool
  install, and venv setups, where `python3` / `python` on PATH is NOT
  the env that has `robotframework` installed. Without this pinning,
  hooks would falsely report Robot Framework as missing.
- If the recorded interpreter is unreachable (user moved their venv),
  the hooks fall back to `python3` → `python` on PATH. If neither has
  `robotframework`, hooks exit silently (non-blocking by design).

### Added — regression tests
- New test: every command in the Windows install's hooks block must
  resolve to an existing file in the bundled `_assets/`. This is the
  exact test shape that would have caught v0.4.1's broken `.ps1`
  rewrite pre-release. Runs on every CI cell (POSIX + Windows).
- New tests: graceful-degrade when `node` is absent (hooks merge
  skipped, note surfaced) and positive branch (hooks merge present
  when Node is on PATH).
- New tests: `python_runtime_config_bytes()` pins `sys.executable`.
- The `tests/test_hook_scripts.py` Windows skip we added in v0.4.1 is
  **lifted** — the new Node-driven tests run on every OS.

### Compatibility
- Drop-in upgrade from 0.4.1 if Node.js is on PATH. If Node isn't
  installed, the install still succeeds; hooks are silently skipped
  with a clear note.
- Users already on v0.4.1 with broken `.ps1` references in
  `~/.claude/settings.json` should run `rf-agentskills uninstall
  --agent claude-code` then `install --agent claude-code` to refresh
  the hooks block. Or use `install --force`.

## 0.4.1 — 2026-05-13

### Bundled content
- **rf-agentskills plugin manifest: 1.2.0** — unchanged.

### Fixed
- **Windows install crash**: `rf-agentskills install --agent claude-code`
  on Windows / PowerShell terminated with
  `json.decoder.JSONDecodeError: Invalid \escape: line 9 column 27`
  during plan-build. Root cause: the installer substituted a
  backslash-separator Windows path (e.g.
  `C:\Users\x\.claude\rf-agentskills-files`) into JSON template
  text, then called `json.loads()` — and `\U`, `\r`, `\.` are not
  valid JSON escapes. Reported in
  `docs/issues/rf-agentskills_install_issues_win_powershell.txt`;
  analysis and fix design in
  `docs/issues/win-powershell-install-fix-proposal.md`.
- The same bug was latent in every adapter that consumes JSON or
  TOML after substitution: Claude Code (hooks + MCP), Copilot,
  Codex (MCP read), Cursor (hooks + MCP), OpenCode (MCP), Claude
  Desktop (MCP). Files written under `<root>/rf-agentskills-files/`
  on Windows would also have been invalid JSON on disk.

### Internals
- `transforms.to_native_path_string()` now returns **forward-slash
  paths on Windows** (e.g. `C:/Users/x/.claude/rf-agentskills-files`).
  Every supported Windows tool (Claude Code, Codex CLI, PowerShell,
  Python `pathlib`, Node `child_process`) accepts forward slashes,
  and forward slashes don't need escaping in JSON / TOML / YAML —
  so the substitute-then-parse pattern in adapters becomes safe
  regardless of OS.

### Tests
- New unit tests for `to_native_path_string`:
  - posix returns `str(path)` unchanged
  - on `sys.platform=='win32'` (monkeypatched), returns no
    backslashes; result is round-trip safe through `json.loads`.
- New per-adapter Windows-mock regression tests covering all seven
  adapters (Claude Code, Copilot, Codex, Cursor, OpenCode, Goose,
  Claude Desktop). Each test mocks the substitution target to a
  Windows-style path and asserts plan-build completes without the
  pre-fix JSON crash, and that no payload retains the unescaped
  backslash form.
- 117/117 tests pass (was 107; +10 new).

### CI
- Added `windows-latest` to the `Test (Python …)` matrix in
  `.github/workflows/ci.yml`, so future Windows regressions are
  caught automatically rather than waiting for user reports.

### Compatibility
- Drop-in upgrade from 0.4.0. No API change.

## 0.4.0 — 2026-05-13

### Bundled content
- **rf-agentskills plugin manifest: 1.2.0**
  (from `plugins/rf-agentskills/.claude-plugin/plugin.json`) —
  unchanged from 0.3.0.

### Added
- `rf-agentskills version` now prints the **bundled content version**
  alongside the installer version, e.g.:
  ```
  rf-agentskills 0.4.0
  bundled content: 1.2.0  (from rf-agentskills plugin manifest)
  ```
  Reads `_assets/.claude-plugin/plugin.json` via `importlib.resources`
  so it works under wheel install, editable install, and zipapp.
  Returns gracefully (without the bundled-content line) if the
  manifest file isn't present.

### Docs
- `RELEASING.md` (new, repo root) documents the content-vs-tooling
  versioning policy and the planned alignment at the installer's
  1.0.0 milestone.
- `installer/CHANGELOG.md` (this file) introduced.
- `vscode-extension/CHANGELOG.md` updated to cross-reference this
  package as the Copilot-companion install for richer features
  (hooks, subagents, MCP) not shipped via the `.vsix`.

### Compatibility
- Same as 0.3.0 — no breaking changes to adapter protocol, CLI
  surface, or manifest format. Drop-in upgrade.

## 0.3.0 — 2026-05-12

First packaged release of the cross-agent installer.

### Bundled content
- **rf-agentskills plugin manifest: 1.2.0**
  (from `plugins/rf-agentskills/.claude-plugin/plugin.json`)

### Added
- 7 per-agent adapters: Claude Code, GitHub Copilot (VS Code 1.108+),
  OpenAI Codex, Cursor (2.4+), OpenCode, Project Goose (1.25+), Claude
  Desktop. Each writes to the agent's documented install paths and
  registers its MCP server.
- `rf-agentskills` CLI with subcommands: `install`, `uninstall`,
  `list`, `targets`, `doctor`, `version`.
- Hash-tracked install manifest at
  `$XDG_DATA_HOME/rf-agentskills/installed.json` — uninstall only
  removes files whose hash still matches what we wrote.
- `${CLAUDE_PLUGIN_ROOT}` substitution at install time so staged
  artifacts are self-contained.
- Conflict detection: refuses to overwrite pre-existing files we don't
  own unless `--force` is set.
- `--dry-run`, `--what`, `--scope user|project`, `--prefix DIR` flags.
- 107 unit tests covering plan structure, transforms, end-to-end
  install/uninstall round-trips.
- Docker test harness (`scripts/docker-test-harness.sh`) for API-free
  validation against real npm/curl-installed agents.

### Compatibility
- Python ≥ 3.10
- Linux, macOS, Windows (file placement; bash hooks active on
  Linux/macOS today; PowerShell ports planned).
- Coexists with the Claude Code marketplace install — the installer
  warns on conflicts and `--force` is required to overwrite a
  marketplace-installed bundle.
