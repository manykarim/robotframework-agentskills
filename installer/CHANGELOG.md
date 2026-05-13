# Changelog — rf-agentskills installer

The `rf-agentskills` package is versioned independently from the
content bundle (Claude Code plugin, VS Code extension, skills
tarballs). See `RELEASING.md` at the repo root for the policy.

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
