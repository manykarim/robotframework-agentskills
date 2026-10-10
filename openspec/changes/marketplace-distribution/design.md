## Context

The current state is described in proposal.md (Why).

**Canonical plugin** (`plugins/rf-agentskills/`):
- `.claude-plugin/plugin.json`;
- 12 skills;
- 4 subagents `agents/*.md` (frontmatter `name`, `description`);
- `hooks/hooks.json` in Claude format: `PostToolUse` `Write|Edit` and `Bash`, `UserPromptSubmit`, `SessionStart`, `Stop`, each `node "${CLAUDE_PLUGIN_ROOT}/scripts/<x>.mjs"`;
- `settings.json` = `{"agent": "rf-test-architect"}`.

The hook scripts read `tool_input.file_path` (or top-level `file_path`) and answer with `hookSpecificOutput.additionalContext`. The root `.claude-plugin/marketplace.json` lists the plugin.

**Verification on 2026-10-08.** Each agent was run with an instrumented copy of the plugin: a probe hook on every event, logging the event, the environment variables and the stdin, plus an extra `*.agent.md` subagent. Isolated homes were used (`COPILOT_HOME`, `CODEX_HOME`, a separate VS Code profile, a scratch `HOME` for the Cursor CLI).

| Agent (version) | Reads our `.claude-plugin/` | Skills | Subagents | Claude-format plugin hooks | Tool names in hook input | Project scope from committed files |
|---|---|---|---|---|---|---|
| Copilot CLI 1.0.91 (live) | marketplace and plugin | 12 | 4 `*.md` (+ `*.agent.md`) | all 5 events; `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PROJECT_DIR`, `CLAUDE_PLUGIN_DATA` (+ `PLUGIN_ROOT`, `COPILOT_*`) | Claude: `Edit`, `Bash`, `Glob`, `skill`; `tool_input.file_path` | `.claude/settings.json` **or** `.github/copilot/settings.json` with `extraKnownMarketplaces` + `enabledPlugins` loads the plugin with no user install |
| VS Code 1.138 Copilot (live, `chat.pluginLocations` in a separate profile) | plugin (`.claude-plugin` auto-detected) | 12 | 4 `*.md` (+ `*.agent.md`) | all 5 events; `CLAUDE_PLUGIN_ROOT` | **native**: `create_file` (`tool_input.filePath`), `apply_patch` (`tool_input.input` = patch), `read_file`, `run_in_terminal`, `manage_todo_list`, `memory`. `Write\|Edit` fired for `create_file`; docs say matchers are ignored for Claude-format hooks | workspace recommendation via `.claude/settings.json` / `.github/copilot/settings.json` (docs); `chat.plugins.marketplaces` is user-only |
| Codex 0.153.4 (live) | marketplace via `codex plugin marketplace add`, plugin | 12, namespaced | not a plugin component; TOML `.codex/agents/` or `~/.codex/agents/` (docs) | all 5 events once the hooks are trusted (`/hooks`, or `--dangerously-bypass-hook-trust`); nothing runs before that; `CLAUDE_PLUGIN_ROOT`, `PLUGIN_ROOT` | `Bash` (`tool_input.command`), `apply_patch` (`tool_input.command` = patch); `Write\|Edit` matches `apply_patch` | **none**: a committed `.claude-plugin/` or `.agents/plugins/marketplace.json` is not picked up, and `enabled = true` needs a prior `codex plugin add` |
| Cursor CLI 2026.10.01 (static: plugin loader in `index.js`; a live run needs a Cursor account) | plugin manifest order `.cursor-plugin/plugin.json` → `.claude-plugin/plugin.json` → `plugin.json`; marketplace `.cursor-plugin/` or `.claude-plugin/marketplace.json`; `${CLAUDE_PLUGIN_ROOT}` and `${CURSOR_PLUGIN_ROOT}` substituted | yes | `agents/` | detects `"claude-code"` format in plugin hooks and converts events (`UserPromptSubmit` → `beforeSubmitPrompt` …) and tools (`Bash` → `Shell`, `Edit` → `Write`); a manifest `hooks` key replaces `hooks/hooks.json` | Cursor payloads (`file_path`, `tool_input`) (docs) | marketplaces are added by git URL and kept on the account; imports Claude Code's `~/.claude/plugins/installed_plugins.json` and `enabledPlugins` from `~/.claude/settings.json`, `.claude/settings.json` and `.claude/settings.local.json` |
| OpenCode 1.15 (docs) | no marketplace | `.opencode/skills`, `.claude/skills`, `.agents/skills` (+ `~`) | `.opencode/agents/*.md` with `mode: subagent`; does not read `.claude/agents` | JS/TS plugins only (`tool.execute.after`, `session.created`, `file.edited` …) | n/a | folders only |

**Re-check of the finished plugin on 2026-10-09 (task 6.3).** Each project was bootstrapped with `rf-agentskills install --mode plugin` and run against a snapshot of this branch, in isolated homes. The prompt asked the agent to create an invalid `.robot` file (a `FOR` without `END`) with its edit tool, and to list its skills and agents.

| Agent | Result |
|---|---|
| Copilot CLI 1.0.91 | Project scope from the committed settings, with no user install. It listed the 12 `rf-*` skills and 4 agents (`rf-agentskills:rf-test-architect` …). The model received "Tool result blocked: The edit was applied, but Robot Framework validation found errors … ERR12 Invalid for loop syntax". |
| Codex 0.161.0 (auto-updated from 0.153.4) | Set up with `codex plugin marketplace add` + `codex plugin add`, hooks trusted via `--dangerously-bypass-hook-trust`, and the 4 TOML subagents installed by `--mode plugin` in `.codex/agents/`. It listed the 12 skills and 4 subagents. The `apply_patch` validation error (ERR12) reached the model. |
| VS Code 1.138 | Not re-run: chat needs interactive approval in the GUI. Its input shapes (`create_file`, `apply_patch`, `multi_replace_string_in_file`, `run_in_terminal`) are covered by the recorded fixtures in `tests/fixtures/hook_inputs/`. |
| Cursor | Not run: needs a Cursor account. |

The installer already has `subagent_md_to_codex_toml` and an OpenCode subagent copy. `rewrite_hooks_for_cursor` exists but is no longer needed for the plugin.

## Goals / Non-Goals

**Goals:**
- One canonical Claude-format plugin. Per-agent files only where an agent cannot use it (Codex subagents, OpenCode), generated and drift-checked.
- Hook scripts that work with every agent's input, rather than per-agent copies of the hooks.
- Project scope through committed `.claude/settings.json` wherever an agent honours it; the installer fills the gaps.

**Non-Goals:**
- Gemini CLI extensions and Goose plugins. Goose and Claude Desktop keep the installer path; Gemini can follow as its own change.
- Publishing to vendor directories (Anthropic's directory, Cursor Marketplace, the OpenAI plugin directory).
- Working around Codex's per-user plugin install or its hook trust step. Those are documented, not automated, apart from the installer printing the commands.

## Decisions

### D1. Claude-format plugin only: no root `plugin.json`, no `.cursor-plugin/`
- All five plugin-capable agents read `.claude-plugin/` (table above).
- A root Agent Plugins `plugin.json` would take precedence in Copilot CLI, Codex and Cursor. In that format hooks and subagents are client-specific, so they would stop loading.
- A `.cursor-plugin/plugin.json` would win over `.claude-plugin/` in Cursor for no gain, since Cursor already converts our hooks.
- **Alternative rejected:** per-agent manifests as in robotcode's marketplace. That's duplication our tests show is unnecessary.

### D2. Normalize hook input inside the scripts
- A shared helper in `scripts/_hook_input.mjs` returns `{agent, tool, files[], command}` from any input shape: Claude, Copilot CLI (Claude-shaped), Cursor, VS Code native, and Codex/VS Code `apply_patch`.
- Patch file headers (`*** Add File:` / `*** Update File:`) are parsed like the workshop's `hookio.py`.
- `validate_robot.mjs` and `rf_error_hints.mjs` use it.
- Each script exits 0 silently when nothing applies, because VS Code ignores Claude-format matchers and runs every hook command for every tool.
- Output channels (verified live with Copilot CLI 1.0.91 on 2026-10-09):
  - Copilot CLI passes **only** `{"decision": "block", "reason": ...}` from stdout to its model. It parses this even on exit 2, and replaces the tool result with "Tool result blocked: <reason>".
  - Copilot CLI drops `additionalContext` on every event (`UserPromptSubmit`, `SessionStart`, `PostToolUse`), and shows stderr only to the user as a warning.
  - Validation errors therefore go out as exit 2 + stderr (Claude Code, Codex) **and** a `decision`/`reason` JSON whose reason starts "The edit was applied, but …", so the model doesn't assume the file is missing.
  - Advisory output (deprecations, formatting, context injection, error hints, environment report) stays `additionalContext`; Copilot CLI users don't receive it.
- **Alternative rejected:** per-agent hook files with per-agent matchers. That's more files, and VS Code would still ignore the matchers.

### D3. Codex: plugin for skills and hooks, installer for subagents, documented trust step
- `plugins/rf-agentskills/variants/codex/agents/<name>.toml` is generated with `subagent_md_to_codex_toml` and committed.
- The installer copies it to `.codex/agents/` or `~/.codex/agents/`.
- The README tells Codex users to run `/hooks` once to trust the plugin hooks.

### D4. OpenCode: generated subagents plus one JS plugin that drives the same scripts
- `variants/opencode/agents/<name>.md`: the body unchanged, frontmatter `description` + `mode: subagent`.
- `variants/opencode/plugins/rf-agentskills.js`:
  - `tool.execute.after` for edit/write tools on `*.robot`/`*.resource`: builds a Claude-shaped stdin, runs `node <scripts>/validate_robot.mjs`, and appends any `additionalContext` to the tool output, which the model reads;
  - `session.created` runs `check_rf_environment.mjs`.
- `UserPromptSubmit` context injection and the `Stop` reminder are documented as not ported, since OpenCode has no hook event that can inject text at those points.
- The installer writes these files plus the shared `scripts/` to the support folder.

### D5. Variant generator and drift check
- `scripts/build-agent-variants.py` writes `variants/codex/agents/*.toml` and `variants/opencode/{agents,plugins}`.
- `scripts/sync-skills.sh` runs it.
- `scripts/check-drift.sh` reruns it into a temporary directory and diffs the result.
- `variants/` sits inside the plugin, so marketplace installs carry it, and the installer's `_assets` mirror ships it.
- All plugin-capable agents ignore an unknown `variants/` folder: none of them scans it.

### D6. Installer `--mode plugin`
- **Claude Code / Copilot / VS Code / Cursor:** merge into `.claude/settings.json` (Copilot: also `.github/copilot/settings.json`):
  - `extraKnownMarketplaces.robotframework-agentskills = {source: {source: "github", repo: "manykarim/robotframework-agentskills", ref?}}`;
  - `enabledPlugins["rf-agentskills@robotframework-agentskills"] = true`.

  This is a `json_nested` merge per key path, recorded for uninstall.
- **Codex:** write the TOML subagents; print the two `codex plugin` commands, or run them with `--yes`, plus the `/hooks` trust note.
- **Cursor:** print how to add the marketplace by git URL to the Cursor account, or rely on the Claude Code import.
- **OpenCode, Goose, Claude Desktop:** fall back to file copy with a note.
- The default mode stays `files`.

### D7. Retire the VS Code extension
- Delete `vscode-extension/`, its CI job, the `.vsix` release asset, and the VS Code entries in sync, drift check and tests.
- VS Code users:
  - `chat.plugins.marketplaces` (user scope);
  - the workspace recommendation (project scope, written by `--mode plugin`);
  - `install --agent copilot` (files).

### D8. Remove `plugins/rf-agentskills/settings.json`
The plugin stops forcing `rf-test-architect` as Claude Code's main agent.

## Risks / Trade-offs

- [Copilot's and Cursor's support for the Claude format is observed or reverse-engineered, not a stated contract] → record the verified versions in the README; re-run the probe procedure (tasks 4.5 and 6.3) on content releases.
- [VS Code plugin and hook support is experimental or preview, and needs settings] → document `chat.plugins.enabled`, `chat.useHooks` and the approval mode; keep `install --agent copilot` as the stable path.
- [Copilot CLI ignores `additionalContext` from plugin hooks] → only validation errors reach the Copilot model (via `decision`/`reason`); context injection and advisory warnings are Claude Code/Codex/Cursor features. The README states this, and the skills still trigger on their descriptions.
- [VS Code runs every hook command for every tool] → scripts exit fast and silently when not applicable (D2); covered by tests.
- [Codex needs per-user commands and a hook trust step] → printed by plugin mode and stated in the README.
- [Cursor not run live] → the static evidence is strong (loader code). The README marks Cursor as "verified from the Cursor CLI 2026.10.01 plugin loader", and a live check can follow when an account is available.
- [OpenCode loses `UserPromptSubmit` injection and the `Stop` reminder] → documented as not ported; the skills still trigger on their descriptions.
- [Users relying on `rf-test-architect` as the default agent] → changelog entry explaining how to select it.

## Migration Plan

1. Land the hook-input normalization (D2), the variant generator and the variants (D3–D5), with the drift check in CI.
2. Add installer `--mode plugin` (installer minor release).
3. Remove the VS Code extension channel and `settings.json`; update README, RELEASING and changelogs; release as content 2.1.0 (no skill removed, so no major bump).
4. Rollback: the VS Code extension was never published, so nothing needs withdrawing; restoring `settings.json` or the channel is a revert.
