## 1. Plugin clean-up and manifests

- [x] 1.1 Remove `plugins/rf-agentskills/settings.json`. Add a test asserting the plugin ships no `settings.json` and no `settings.agent` key in `.claude-plugin/plugin.json`. Verify with pytest and `claude plugin validate plugins/rf-agentskills`.
- [x] 1.2 Add a manifest-consistency test. The marketplace entry and `.claude-plugin/plugin.json` must agree on name and version, and no root `plugin.json` or `.cursor-plugin/` may exist. Verify the test passes and fails when a version is edited by hand.

## 2. Hook input for every agent

- [x] 2.1 Add `plugins/rf-agentskills/scripts/_hook_input.mjs`. It returns the agent, tool, edited files and command from any of these input shapes:
  - Claude/Copilot CLI: `tool_input.file_path`;
  - Cursor: `file_path`;
  - VS Code: `tool_input.filePath`;
  - Codex and VS Code `apply_patch`: patch in `tool_input.command` or `tool_input.input`, taking every `*** Add File:` / `*** Update File:` path.

  Verify with Node tests using payloads recorded in the 2026-10-08 probes (one per agent and shape).
- [x] 2.2 Use the helper in `validate_robot.mjs` and `rf_error_hints.mjs`. Exit 0 silently for tools and files they don't handle, because VS Code ignores Claude-format matchers. Verify with hook-script tests:
  - a Codex `apply_patch` adding a broken `.robot` file and a VS Code `create_file` of one both get the validation error as `additionalContext`;
  - `read_file` and `run_in_terminal` inputs produce no output and finish under 200 ms.

## 3. Codex and OpenCode variants

- [x] 3.1 Add `scripts/build-agent-variants.py`, generating `plugins/rf-agentskills/variants/codex/agents/<name>.toml` for the 4 subagents (via `subagent_md_to_codex_toml`). Verify that a test parses each file with `tomllib` and finds `name`, `description` and a non-empty `developer_instructions`.
- [x] 3.2 Generate `variants/opencode/agents/<name>.md` (frontmatter `description`, `mode: subagent`, body unchanged). Verify with a test of the frontmatter and that the body matches the canonical agent's.
- [x] 3.3 Add the OpenCode plugin template, generated to `variants/opencode/plugins/rf-agentskills.js`:
  - `tool.execute.after` runs `validate_robot.mjs` for `.robot`/`.resource` edits and appends `additionalContext` to the tool output;
  - `session.created` runs `check_rf_environment.mjs`.

  Verify with a Node test that loads the plugin with stubbed `input`/`output` objects and checks that the validation text is appended for a broken `.robot` file.
- [x] 3.4 Run the generator from `scripts/sync-skills.sh`, and make `scripts/check-drift.sh` regenerate into a temp dir and diff against the committed variants. Verify that the drift check passes after sync and fails after a hand edit of a variant file.

## 4. Installer

- [x] 4.1 Codex adapter: install the committed `variants/codex/agents/*.toml` to `.codex/agents/` (project) or `~/.codex/agents/` (user) instead of converting at install time. Verify with adapter tests for both scopes.
- [x] 4.2 OpenCode adapter: install `variants/opencode/agents/*.md` to `agents/`, the plugin to `plugins/rf-agentskills.js`, and the shared hook `scripts/` to the support folder that the plugin references. Verify with adapter tests and an e2e install/uninstall round trip.
- [x] 4.3 Add `--mode plugin|files` (default `files`), and give `--mode plugin` a `--ref` option. For Claude Code, Copilot and Cursor, merge `extraKnownMarketplaces` + `enabledPlugins` into `.claude/settings.json` (Copilot: also `.github/copilot/settings.json`) and record the merges for uninstall. Verify with tests showing that existing keys survive, uninstall removes only the two entries, and `--ref` pins the source.
- [x] 4.4 Plugin mode for the remaining agents:
  - Codex: TOML subagents, plus the two `codex plugin` commands and the `/hooks` trust note, printed, or the commands run with `--yes`;
  - Cursor: printed git-URL marketplace steps;
  - OpenCode, Goose, Claude Desktop: fall back to file copy with a note.

  Verify with CLI tests of the printed output and that no command runs without `--yes`.
- [x] 4.5 Live check with Copilot CLI in a throwaway `COPILOT_HOME`: a project bootstrapped with `--mode plugin` (pointing at a local checkout via a test-only marketplace source) loads the plugin's skills, subagents and hooks without a user-level install, and the validation hook reports an error for a broken `.robot` edit. Record the CLI version in the README.

## 5. Retire the VS Code extension

- [x] 5.1 Delete `vscode-extension/` and remove the VS Code channel from `scripts/sync-skills.sh`, `scripts/check-drift.sh`, `scripts/validate-skills.py` and the tests that reference it. Verify with the full test suite, `check-drift.sh` and `validate-skills.py --channel all`.
- [ ] 5.2 Remove the `Build VS Code extension` CI job and the `.vsix` steps and asset from `release.yml`. Add the manifest-consistency test and `build-agent-variants.py --check` to CI. Verify that the workflows parse and a PR run is green.
- [x] 5.3 Update `RELEASING.md`: content scope = plugin + marketplace manifest, the version rule, and `v<version>` tags as pinnable marketplace refs. Verify that the doc names no `vscode-extension` path.

## 6. Documentation and release notes

- [x] 6.1 Rewrite the README install section as a matrix per agent covering:
  - adding the marketplace and installing;
  - user and project scope, including the committed file;
  - pinning to a tag;
  - which components work there;
  - one-time steps (Codex `/hooks` trust; VS Code `chat.plugins.enabled`, `chat.useHooks`, approval mode);
  - the verified agent versions;
  - the installer for OpenCode, Goose and Claude Desktop.

  Verify that it covers Claude Code, Copilot CLI, VS Code, Codex, Cursor, OpenCode, Goose and Claude Desktop.
- [x] 6.2 Add CHANGELOG entries: content (VS Code extension retired, default agent removed, hook input for all agents, generated variants) and installer (`--mode plugin`, Codex/OpenCode variants). Verify that each entry names the replacement for removed behaviour.
- [ ] 6.3 Re-run the 2026-10-08 probe procedure against the finished plugin:
  - Copilot CLI and Codex in isolated homes;
  - VS Code in a separate profile;
  - Cursor if an account is available.

  Record the results in the change's design.md. Then run `openspec validate marketplace-distribution --strict`, the full test suite and `check-drift.sh`; all pass.
