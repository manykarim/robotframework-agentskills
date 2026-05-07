# `rf-agentskills` package + installer — proposal

**Status:** Proposal — no code changes yet. Reviewing for direction before implementation.
**Branch:** `feature/installer` (off `main` at PR #3 merge).
**Date:** 2026-05-07.

## TL;DR

Ship a single Python package, `rf-agentskills`, distributable via PyPI and `pipx`. It bundles the existing rf-agentskills tree (11 skills, 4 subagents, hook scripts, helper scripts, MCP server) and exposes a CLI:

```bash
pipx install rf-agentskills
rf-agentskills install --agent claude-code   # also: codex, copilot, cursor, goose, opencode, claude-desktop
```

Acts as a vendor-neutral alternative to the Claude Code marketplace, fanning out the same source-of-truth bundle to **seven different coding agents'** expected install paths. Manifest-tracked uninstall, doctor, list, dry-run.

The big insight from the cross-agent research: **Anthropic's `.claude/` filesystem layout is becoming the de facto standard.** Claude Code, Codex, *and* GitHub Copilot in VS Code 1.108+ all read from it natively — no transformation needed. Cursor, OpenCode, and Goose require some adaptation.

## Goals

1. **Single source of truth.** One bundle (the rf-agentskills tree we already maintain), distributed unchanged to every supported agent.
2. **One-command install.** `rf-agentskills install --agent X` does everything the user needs (write files, register MCP, optionally toggle preview flags).
3. **Reversible.** `rf-agentskills uninstall --agent X` removes only what we installed (manifest-tracked, hash-verified — never clobber user edits silently).
4. **Cross-platform.** Linux, macOS, Windows. Path separators, executable bits, and config-dir conventions handled correctly.
5. **No marketplace lock-in.** Works offline-after-install; doesn't depend on Anthropic's marketplace API or any registry beyond PyPI itself.
6. **Diagnosable.** `rf-agentskills doctor` shows what's installed, where, what's missing, and what each target agent will and won't pick up.

## Non-goals

- **Not** replacing the Claude Code marketplace — users who prefer `claude plugin install` should keep using it.
- **Not** building a new file format. We bundle exactly what we already maintain; only the *destination* layout changes per agent.
- **Not** a mid-flight transformer for skills with complex assets (references/, scripts/). The plugin's `${CLAUDE_PLUGIN_ROOT}` substitution we already do is the only transform we perform.
- **Not** managing the user's own customizations. We touch only paths we created (manifest tracks them).

## Compatibility matrix

What each target agent natively supports today, and the install shape per asset class:

| Agent | Skills (`SKILL.md`) | Subagents (`.md`) | Hooks (`hooks.json`) | MCP servers | Plugin manifest |
|---|---|---|---|---|---|
| **Claude Code** ≥ 2.1 | `~/.claude/skills/<name>/` (native) | `~/.claude/agents/<name>.md` (native) | `~/.claude/settings.json` `hooks` block (native) | `~/.mcp.json` or project `<repo>/.mcp.json` (native) | `.claude-plugin/plugin.json` (already shipped) |
| **GitHub Copilot** in VS Code ≥ 1.108 | `.claude/skills/` *honored as-is* | `.claude/agents/` *honored as-is* | `.claude/settings.json` *honored, but matcher value silently ignored* | `.vscode/mcp.json` (`servers` key, **NOT** `mcpServers`) | `.claude-plugin/plugin.json` *honored as-is* |
| **OpenAI Codex CLI** | `~/.codex/skills/<name>/` (same SKILL.md format) | `~/.codex/agents/<name>.toml` *(transform from .md required)* | `~/.codex/hooks.json`, gated by `[features] codex_hooks=true` *(experimental)* | `[mcp_servers.<name>]` block in `~/.codex/config.toml` (TOML merge) | `.codex-plugin/plugin.json` (parallel to Claude's, optional) |
| **Cursor** ≥ 1.7 | Transform → `~/.cursor/rules/<name>.mdc` (Markdown w/ frontmatter, no native SKILL.md loader) | No clean target; fold into rules | `.cursor/hooks.json` with namespaced matchers (`Shell`, `Read`, `Write`, `MCP:<name>`) | `~/.cursor/mcp.json` (MCP-standard JSON) | n/a |
| **OpenCode** | No skill primitive — map → `~/.config/opencode/commands/<name>.md` (slash command) | `~/.config/opencode/agents/<name>.md` *(direct copy)* | JS plugin module at `~/.config/opencode/plugins/rf-hooks.js` (event subscriptions, **not** bash) | `mcp.<name>` entry merged into `~/.config/opencode/opencode.json` | n/a |
| **Project Goose** | No skill primitive — concatenate into `~/.goosehints` | Recipe YAML (experimental); no canonical agents dir | **No hooks system** | `extensions.<name>` block in `~/.config/goose/config.yaml` (YAML merge) | n/a |
| **Claude Desktop** | No skill primitive | No subagents | No hooks | `claude_desktop_config.json` (per-OS path) — **MCP-only target** | n/a |

**Three takeaways**:

1. **Claude Code, Codex, and Copilot are nearly drop-in identical.** All three read SKILL.md unchanged; Copilot even reads Claude's filesystem paths verbatim. Our installer's adapters for those three are essentially "copy this tree to that location, adjust one keyname for MCP."
2. **Cursor, OpenCode, Goose, Claude Desktop need transforms.** Subagents → rules / personas / Markdown; SKILL.md → MDC / commands / hints. We accept that not every asset reaches every target — the doctor command must report this honestly.
3. **The full plugin can only be reproduced on Claude Code, Copilot, and (with caveats) Codex.** For other targets, we install what we can and `doctor` lists what's missing. This is honest about the ecosystem state rather than pretending parity.

## Package architecture

### Layout

```
rf-agentskills/                          # repo root (existing)
├── pyproject.toml                       # package metadata + build config
├── README.md
├── plugins/rf-agentskills/              # source of truth (existing)
│   ├── .claude-plugin/plugin.json
│   ├── skills/<name>/SKILL.md ...
│   ├── agents/<name>.md
│   ├── hooks/hooks.json
│   ├── scripts/*.{py,sh}
│   └── servers/rf-tools-server.py
├── src/rf_agentskills/                  # NEW Python package
│   ├── __init__.py
│   ├── cli.py                           # argparse / typer dispatch
│   ├── manifest.py                      # ~/.local/share manifest tracking
│   ├── transforms.py                    # SKILL.md → MDC, .md subagent → .toml
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── _base.py                     # Adapter protocol
│   │   ├── claude_code.py
│   │   ├── claude_desktop.py
│   │   ├── codex.py
│   │   ├── copilot.py
│   │   ├── cursor.py
│   │   ├── goose.py
│   │   └── opencode.py
│   └── _assets/                         # bundled tree (mirror of plugins/rf-agentskills/)
│       ├── skills/.../SKILL.md
│       ├── agents/*.md
│       ├── hooks/hooks.json
│       ├── scripts/*.{py,sh}
│       └── servers/rf-tools-server.py
└── tests/
    └── installer/
        ├── test_adapters.py
        ├── test_manifest.py
        └── test_transforms.py
```

`_assets/` is **inside** the Python package (not a sibling `assets/`) so it ships in the wheel by default and survives PEP 660 editable installs without `force-include` gymnastics. A small build-time hook (or a pre-build script) will mirror `plugins/rf-agentskills/` into `src/rf_agentskills/_assets/` so we don't maintain two copies.

### Build backend: hatchling

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "rf-agentskills"
version = "1.3.0"
description = "Robot Framework agent skills installer for Claude Code, Codex, Copilot, Cursor, Goose, OpenCode"
readme = "README.md"
license = { text = "Apache-2.0" }
requires-python = ">=3.10"
authors = [{ name = "manykarim" }]
classifiers = [
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Topic :: Software Development :: Testing",
]
dependencies = [
    # Keep dependencies tiny — installer reaches user $HOME, the fewer
    # transitive packages, the lower the supply-chain surface.
    "tomli; python_version<'3.11'",   # TOML read for Codex config.toml on 3.10
    "pyyaml >=6.0",                   # YAML round-trip for Goose config
]

[project.optional-dependencies]
dev = ["pytest", "pytest-cov", "ruff"]

[project.scripts]
rf-agentskills = "rf_agentskills.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/rf_agentskills"]

[tool.hatch.build.hooks.custom]
# Mirror plugins/rf-agentskills/ → src/rf_agentskills/_assets/ before build.
path = "scripts/sync_assets.py"
```

### Runtime asset access

Use `importlib.resources.files()` (3.9+, stable in 3.12). Works under wheel install, PEP 660 editable, pipx, zipapp, PyInstaller frozen.

```python
# src/rf_agentskills/_assets.py
from importlib.resources import as_file, files
from contextlib import contextmanager
from pathlib import Path

_ROOT = files(__package__).joinpath("_assets")

def asset_path(*parts: str) -> "Traversable":
    return _ROOT.joinpath(*parts)

@contextmanager
def asset_dir():
    """Yield the bundled tree as a real `Path`, extracting from zip if needed."""
    with as_file(_ROOT) as p:
        yield Path(p)
```

## CLI design

A small `argparse`-driven CLI (typer is overkill for ~6 subcommands, and `argparse` is stdlib).

```bash
rf-agentskills install --agent <name>     # write files for one agent
rf-agentskills install --all              # write files for every detected agent
rf-agentskills uninstall --agent <name>   # remove what we wrote, leave user edits alone
rf-agentskills list                       # what's installed where, per the manifest
rf-agentskills targets                    # which agents are detected on this machine
rf-agentskills doctor                     # what works, what doesn't, what needs user action
rf-agentskills version                    # bundle version + bundled-asset hash
```

### Common flags

- `--agent claude-code|claude-desktop|codex|copilot|cursor|goose|opencode` — required for `install`/`uninstall` unless `--all`.
- `--scope user|project [--project DIR]` — write to user-home (default) or to a specific project's `.claude/` etc. directory.
- `--prefix DIR` — override the install root entirely (used by tests; lets you install into a tempdir).
- `--dry-run` — print what would be written; touch nothing.
- `--what skills,agents,hooks,mcp` — install only a subset (default: everything the agent supports).
- `--force` — overwrite even when the destination has user edits (default: refuse and report).

### Adapter protocol

```python
# src/rf_agentskills/adapters/_base.py
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

@dataclass(frozen=True)
class InstallTarget:
    """One file we plan to install: source asset path → destination path."""
    src: Path           # path inside the staged _assets/ tree
    dst: Path           # absolute destination on the user's filesystem
    executable: bool    # chmod +x after copy (Unix only)
    transform: str | None  # name of transform fn in transforms.py, or None

class Adapter(Protocol):
    name: str           # "claude-code", "codex", etc.
    pretty: str         # "Claude Code"

    def detect(self) -> bool: ...
    def plan(self, opts: "InstallOptions") -> list[InstallTarget]: ...
    def post_install(self, opts: "InstallOptions") -> list[str]: ...
        # Returns warnings / next-step messages (e.g. "enable chat.hooks.enabled
        # in VS Code settings", "first MCP run requires trust prompt").
```

`detect()` looks for the agent's binary on PATH or its config directory. `plan()` returns a list of file copies (no I/O). The dispatcher executes plans, records each write to the manifest, and prints `post_install()` warnings.

This pattern keeps adapters pure — the install/uninstall/dry-run/manifest logic lives once in the dispatcher, and adding a future agent (e.g. Aider, Cline) is one new file under `adapters/` plus one row in the compat matrix.

### Per-agent install recipes (summary)

**`claude-code`** (most native): copy `_assets/skills/` → `~/.claude/skills/`, `_assets/agents/` → `~/.claude/agents/`, `_assets/hooks/hooks.json` content merged into `~/.claude/settings.json` `hooks` block, `_assets/.mcp.json` content merged into `~/.mcp.json`. `${CLAUDE_PLUGIN_ROOT}` rewritten to a stable staged location under `~/.claude/plugins/rf-agentskills-files/` (mirrors what the eval harness already does). Post-install: nothing — Claude Code picks everything up on next session.

**`copilot`** (essentially same): use Claude Code's recipe at workspace scope — Copilot reads `.claude/skills/` and friends. Plus `code --add-mcp '<json>'` to register MCP at user scope (`.vscode/mcp.json` is workspace-only). Post-install: print "Enable preview features `chat.agent.plugins.enabled`, `chat.skills.enabled`, `chat.hooks.enabled` in VS Code settings" — these flags are user-toggled in 1.108. Hooks scripts handle camelCase / snake_case field names (already a guard we should add).

**`codex`**: copy SKILL.md verbatim to `~/.codex/skills/<name>/`. Subagents transformed `.md` → `.toml` (extract `name`, `description` from frontmatter, dump body into `developer_instructions`). MCP server merged into `~/.codex/config.toml` (TOML round-trip via `tomlkit`). Hooks behind `[features] codex_hooks = true` flag — installer offers to enable but doesn't force.

**`cursor`**: SKILL.md transformed to `~/.cursor/rules/<name>.mdc` (frontmatter mapping: `description` preserved, add `globs: ["**/*.robot", "**/*.resource"]` and `alwaysApply: false`). MCP merged into `~/.cursor/mcp.json`. Hooks rewritten to Cursor's namespaced matcher syntax (`Write` → `Write`, `mcp__rf-mcp__.*` → `MCP:rf-mcp`). Subagents folded into rules with explicit `description`. Print one-click MCP install link as fallback (`cursor://anysphere.cursor-deeplink/mcp/install?...`).

**`opencode`**: subagents direct-copied to `~/.config/opencode/agents/<name>.md`. Skills mapped → slash commands at `~/.config/opencode/commands/<name>.md` (frontmatter rewrite). MCP merged into `~/.config/opencode/opencode.json` (deep JSON merge). Hooks **skipped** — bash hooks don't translate to OpenCode's JS plugin model; doctor flags this as known limitation. Print a hint about the JS plugin path for future support.

**`goose`**: only MCP gets a real install — extension entry merged into `~/.config/goose/config.yaml` (round-trip YAML). Persona text composed from skill descriptions written to `~/.goosehints`. Skills, subagents, hooks all skipped — doctor explicitly says "Goose has no native equivalent for these"; user gets a one-line summary of what each rf-agentskills component would have provided.

**`claude-desktop`**: MCP-only target (`claude_desktop_config.json` at the per-OS path). Doctor warns that skills/agents/hooks are not installable here.

## Manifest & uninstall

Every successful install writes a manifest entry at:

```
${XDG_DATA_HOME:-~/.local/share}/rf-agentskills/installed.json
```

Format:

```json
{
  "version": 1,
  "bundle_version": "1.3.0",
  "installations": [
    {
      "agent": "claude-code",
      "scope": "user",
      "installed_at": "2026-05-07T18:30:00Z",
      "files": [
        {"path": "/home/many/.claude/skills/libdoc-search/SKILL.md",
         "sha256": "ab1c...",
         "transform": null},
        {"path": "/home/many/.claude/agents/rf-test-architect.md",
         "sha256": "9d4e...",
         "transform": null}
      ],
      "config_merges": [
        {"path": "/home/many/.claude/settings.json",
         "key": "hooks",
         "added_keys": ["PostToolUse", "UserPromptSubmit", "SessionStart", "Stop"]}
      ]
    }
  ]
}
```

**Uninstall semantics:**

- For each tracked file: re-hash. If the hash still matches what we recorded → delete it. If it differs → leave it, report "user-modified, preserving" in stdout, and remove the manifest entry only.
- For each tracked config merge (settings.json hooks, opencode.json mcp, goose config.yaml extensions): parse the current file, remove only the keys we added, write back. Never blow away the whole file.
- Empty parent directories created by us (`~/.claude/skills/<name>/`) get pruned bottom-up.

This pattern is borrowed from `pre-commit install/uninstall`, `jupyter labextension install/uninstall`, and `playwright install` — every robust external-file installer in the Python ecosystem uses the same "install logs what it wrote; uninstall removes only those things" approach.

## Test strategy

Three layers, all run in CI:

1. **Unit tests for adapters** — `tests/installer/test_adapters.py` constructs each adapter with a `tmp_path` prefix, calls `plan()`, asserts on the produced `InstallTarget` list (paths, transforms, exec bits). No filesystem I/O beyond the tempdir.
2. **End-to-end install/uninstall** — `tests/installer/test_e2e.py` actually runs the dispatcher against a tempdir with `monkeypatch.setenv("HOME", tmp_path)`. Walks the tempdir afterwards, asserts on the file tree. Then runs uninstall, asserts the tempdir is empty modulo the manifest file.
3. **Cross-platform CI matrix** — `.github/workflows/installer.yml`: `ubuntu-latest`, `macos-latest`, `windows-latest` × Python 3.10/3.12/3.13. Same unit + e2e tests, with platform-specific assertions for path separators and Windows skipping bash-hook executable bits.

Per-agent integration tests are out of scope — we don't have CI access to a Cursor or Goose binary that lets us assert "skills appear in the agent UI." Instead we validate the *file-level* contract: did we write the right bytes to the right paths, and would those bytes be parseable by the target agent? For Claude Code we already have the `rf-skill-eval` harness that drives a real agent — extending that to do "install via `rf-agentskills`, then run a narrow eval task" gives us an actual end-to-end signal for the Claude Code adapter.

## Distribution

- **Primary**: PyPI. `pip install rf-agentskills`, `pipx install rf-agentskills`. CI builds wheel + sdist on tag push and uploads via OIDC trusted publishing (no API token).
- **Secondary**: GitHub Releases attach the same wheel + sdist for offline installs.
- **Tertiary (optional)**: a Homebrew tap formula that wraps `pipx install rf-agentskills`. Cross-platform installers like Scoop / Chocolatey are deferred until there's demand.
- The Claude Code marketplace publication continues independently — they're complementary, not competitive.

## Risks and open questions

1. **Build-time asset mirroring** — keeping `src/rf_agentskills/_assets/` in sync with `plugins/rf-agentskills/` requires a build hook (`hatch_build.py`). If the user runs `pip install -e .` (editable), what happens? Need to verify the hook fires; if not, fall back to a symlink or a `make assets` step in development.
2. **`${CLAUDE_PLUGIN_ROOT}` substitution at install-time** — the rf-skill-eval harness rewrites this token at runtime. The installer needs to do the same when copying scripts that reference it. Decision: substitute at install time using the destination directory as the resolved path; record the substitution in the manifest so uninstall knows what it wrote.
3. **Codex hooks experimental flag** — `[features] codex_hooks = true` is opt-in. Should the installer auto-enable it? Lean toward "no, but offer with `--enable-codex-hooks` flag" — flipping experimental flags without consent is a footgun.
4. **OpenCode JS hooks port** — out of scope for v1. Track as future work; doctor reports the gap.
5. **Field name shim for Copilot hooks** — Copilot's hook scripts receive camelCase JSON (`filePath`) where Claude Code uses snake_case (`file_path`). Our hook scripts (`maybe_inject_rf_context.sh`, etc.) currently extract via jq. Need to add a both-or pattern — `jq -r '.prompt // .Prompt // ""'` style — or fall through cleanly. Belongs in a small follow-up to the hooks PR.
6. **MCP trust dialog** — first-run trust is mandatory in VS Code Copilot and Claude Desktop. Installer can't bypass. Doctor needs to explicitly tell the user "you'll see one prompt the first time you start <agent>".
7. **Conflict with existing marketplace install** — if a user has already done `claude plugin install rf-agentskills@robotframework-agentskills`, our installer would write to the same paths. Detect this in `plan()` and warn / refuse to overwrite without `--force`. Doctor surfaces both installs.
8. **Windows bash hooks** — our hook scripts are bash. On Windows they're useless. Plan: skip hook installation on Windows, log a warning, ship `.ps1` equivalents in a follow-up.

## Implementation phases

Sized for the team but ordered for fastest user value:

**Phase 1 — Package skeleton + Claude Code + Copilot (highest-value pair)**
- pyproject.toml + hatchling + asset-mirroring build hook
- `cli.py`, `manifest.py`, `adapters/_base.py`, `adapters/claude_code.py`, `adapters/copilot.py`
- Unit tests + e2e install/uninstall via tempdir
- README install section
- Estimate: 1–2 weeks. Ships as v0.1 to PyPI.

**Phase 2 — Codex + Cursor adapters**
- TOML and YAML round-trip helpers (`tomlkit`, `pyyaml`)
- `adapters/codex.py`, `adapters/cursor.py`
- SKILL.md → MDC transform
- Subagent .md → TOML transform
- Hook matcher rewriter for Cursor's namespaced syntax
- Estimate: 1 week. Ships as v0.2.

**Phase 3 — Goose + OpenCode + Claude Desktop**
- Limited adapters that install only what each agent supports
- Doctor honestly reports the gaps
- `claude_desktop_config.json` per-OS path resolution
- Estimate: 4–5 days. Ships as v0.3.

**Phase 4 — Polish**
- `--all` aggregate install
- `doctor` rich output (which agents detected, install state, missing things)
- Windows path / bash-hook conditional handling
- Real-world Claude Code adapter validation: rf-skill-eval task that uses the installer's output instead of the harness's own staging
- Estimate: 1 week. v1.0.

## What this proposal is NOT proposing

- **Not** changing the existing plugin tree at `plugins/rf-agentskills/`. The package wraps it, doesn't replace it.
- **Not** breaking the Claude Code marketplace path. `claude plugin install rf-agentskills@robotframework-agentskills` continues to work as before.
- **Not** changing the rf-skill-eval harness's own staging logic. The harness installs into its own per-run sandbox; the installer installs into the user's permanent home. They serve different purposes.
- **Not** introducing a new hook schema, skill format, or marketplace concept. We use exactly what each target agent already understands.

## Appendix A — Exact source paths cited (for verification)

| Claim | Source |
|---|---|
| Claude Code skills, agents, hooks paths | https://code.claude.com/docs/en/skills.md, sub-agents.md, settings.md (April 2026) |
| `claude plugin install` and `--plugin-dir` flags | `claude --help` and `claude plugin --help` (verified locally on 2.1.121) |
| Codex skill install path | `~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py` (verified locally — uses `os.environ.get("CODEX_HOME", os.path.expanduser("~/.codex"))`) |
| Codex SKILL.md format identical to Claude | `~/.codex/skills/.system/imagegen/SKILL.md` frontmatter inspected locally |
| Cursor 1.7+ hooks schema, MDC rules | https://cursor.com/docs/agent/hooks, https://cursor.com/docs/context/mcp/install-links |
| GitHub Copilot agent skills + hooks (Preview, VS Code 1.108) | https://code.visualstudio.com/docs/copilot/customization/{agent-skills,agent-plugins,hooks,custom-agents}, changelog 2025-12-18 |
| Copilot reads `.claude/skills/` and `.claude/agents/` natively | https://code.visualstudio.com/docs/copilot/customization/agent-skills (cited under "supported locations") |
| OpenCode plugin/agent format | https://opencode.ai/docs/{config,agents,plugins,mcp-servers}/ |
| Goose config + extensions | https://block.github.io/goose/docs/guides/config-file/ |
| Claude Desktop config path per OS | https://github.com/anthropics/claude-code/issues/26073, https://support.claude.com/en/articles/12611117-deploy-claude-desktop-for-macos |
| Python packaging best practices | https://packaging.python.org, https://hatch.pypa.io/latest/, PEP 427 / 517 / 660, https://docs.python.org/3/library/importlib.resources.html |

## Appendix B — Compatibility matrix (one-liner per agent, for the README)

> **Claude Code** ✅ full • **Copilot (VS Code)** ✅ full (preview flags req'd) • **Codex** ✅ skills/MCP, ⚠ subagents transformed, ⚠ hooks experimental • **Cursor** ⚠ skills→rules, hooks adapted • **OpenCode** ⚠ subagents/MCP only, ⚠ skills→commands, ✗ hooks • **Goose** ⚠ MCP + persona only • **Claude Desktop** ⚠ MCP only

## Decision points for the reviewer

1. **Scope of v1**: ship Phase 1 (Claude Code + Copilot only) as v0.1 to get the package on PyPI and gather feedback, or hold for the full Phase 3 set?
2. **`${CLAUDE_PLUGIN_ROOT}` strategy**: substitute at install time (cleaner, harder to relocate later) vs leave the placeholder and require an env var at runtime (more flexible, more failure modes)?
3. **Marketplace coexistence**: when our installer detects a prior marketplace install, what's the default behavior — refuse, warn, or take over?
4. **Hooks on Windows**: skip silently with doctor notice, or invest in `.ps1` equivalents for v1?
5. **Asset mirroring**: build-hook (clean separation) or symlink (simpler, but breaks on Windows without admin)?
