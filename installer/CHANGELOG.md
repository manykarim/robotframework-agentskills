# Changelog — rf-agentskills installer

The `rf-agentskills` package is versioned independently from the
content bundle (Claude Code plugin, VS Code extension, skills
tarballs). See `RELEASING.md` at the repo root for the policy.

## Unreleased

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
