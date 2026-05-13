# Changelog — rf-agentskills installer

The `rf-agentskills` package is versioned independently from the
content bundle (Claude Code plugin, VS Code extension, skills
tarballs). See `RELEASING.md` at the repo root for the policy.

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
