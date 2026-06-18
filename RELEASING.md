# Releasing — versioning policy

The repo ships **two release scopes** that are versioned independently
today. This document captures why and when that's expected to change.

## Two scopes

| Scope | Channel | Source of truth | Current version |
|---|---|---|---|
| **Content** | Claude Code plugin · VS Code `.vsix` · skills tarballs | `plugins/rf-agentskills/.claude-plugin/plugin.json` + `vscode-extension/package.json` | **1.2.0** |
| **Tooling** | `rf-agentskills` Python installer (PyPI / GitHub release) | `installer/pyproject.toml` | **0.3.0** |

Internal-only:

| Scope | Use | Source of truth |
|---|---|---|
| `rf-skill-eval` | CI evaluation harness, tagged `Private :: Do Not Upload` | root `pyproject.toml` |

## Why independent today

The two scopes are driven by different change axes:

- **Content** changes when a `SKILL.md`, subagent prompt, hook script,
  or MCP server is edited. Every consumer that *embeds* the content
  (the plugin tarball, the vsix, the installer's staged `_assets/`)
  needs the new bundle.
- **Tooling** changes when the installer's adapter logic, CLI dispatch,
  manifest format, or transforms are edited. The content is unchanged;
  only `rf-agentskills` needs a new release.

Forcing one number across both axes means either:
- A typo fix in `skills/browser/SKILL.md` drags the installer's
  pre-1.0 version along (false signal to `pipx` users), **or**
- A fix in the installer's Codex adapter stalls until the next content
  release (unnecessary lockstep).

The installer is intentionally pre-1.0. Until its adapter protocol /
CLI surface stabilises, bumping it to 1.x to match the content channel
would falsely advertise stability and violate SemVer expectations of
`pipx`/`pip` users.

## Tag → workflow mapping

| Tag pattern | Workflow | What it produces |
|---|---|---|
| `v*` (e.g. `v1.3.0`) | `.github/workflows/release.yml` | Plugin tarball, `.vsix`, skills tarballs (Codex/Copilot/generic), GitHub release. Force-pushes `stable` and `latest` branches. |
| `rf-agentskills-v*` (e.g. `rf-agentskills-v0.4.0`) | none (manual `gh release create` + `uv publish` today) | Wheel + sdist on a GitHub release **and** on PyPI (`uvx rf-agentskills`). |

The two patterns are non-overlapping so the flows can co-trigger or
fire independently as needed.

## Cross-referencing in release notes

Each release should call out the version on the *other* axis so users
can correlate:

- **`v1.x` release notes** should include: *"compatible with
  `rf-agentskills` ≥ 0.3.0"* (or whatever the current installer version
  is). When the installer bumps in lockstep with a content change,
  call that out too.
- **`rf-agentskills-v0.x` release notes** should include: *"bundled
  content: 1.2.0"* (read from
  `plugins/rf-agentskills/.claude-plugin/plugin.json` at build time).
  The `rf-agentskills version` CLI prints this automatically:
  ```
  $ rf-agentskills version
  rf-agentskills 0.4.0
  bundled content: 1.2.0  (from rf-agentskills plugin manifest)
  ```

## Planned alignment milestone

When `rf-agentskills` reaches **1.0.0** — meaning the adapter protocol
and CLI surface are considered stable — the *first* aligned release
becomes a deliberate milestone:

1. Pick a coordinated version (e.g. `v2.0.0` for both content and
   installer) that's higher than both current numbers.
2. Tag both `v2.0.0` (triggers the content release flow) and
   `rf-agentskills-v2.0.0` (triggers the PyPI release flow once that's
   wired up).
3. From that point forward, **track major versions** when there's a
   coupled content + tooling release; minor / patch versions remain
   independent.

This buys the "psychological alignment" benefit at the moment when it
genuinely matters (API stability), without paying the lockstep cost
during the messy pre-1.0 phase.

## Release checklist (content, `v*`)

1. Bump `plugins/rf-agentskills/.claude-plugin/plugin.json` `version`
   and `.claude-plugin/marketplace.json` `version`.
2. Bump `vscode-extension/package.json` `version`.
3. Update `vscode-extension/CHANGELOG.md`.
4. Run `bash scripts/sync-skills.sh` and `bash scripts/check-drift.sh`.
5. Commit, push, tag `vX.Y.Z`, push the tag.
6. `release.yml` runs, attaches the 5 artifacts to the GitHub release,
   and updates `stable` / `latest` branches.

## Release checklist (tooling, `rf-agentskills-v*`)

1. Bump `installer/pyproject.toml` `version`.
2. Bump `installer/src/rf_agentskills/__init__.py` `__version__`.
3. Update `installer/CHANGELOG.md`.
4. `bash scripts/build-packages.sh --clean --check` (validates with
   `twine check`).
5. Commit, push.
6. `gh release create rf-agentskills-vX.Y.Z dist/rf_agentskills-*` with
   release notes referencing the bundled content version.
7. **Publish to PyPI** so `uvx rf-agentskills` / `pipx run rf-agentskills`
   resolves the new version:
   ```bash
   # API token in $PYPI_TOKEN (or a CI secret); never commit it.
   uv publish --token "$PYPI_TOKEN" dist/rf_agentskills-*
   # or: twine upload -u __token__ -p "$PYPI_TOKEN" dist/rf_agentskills-*
   ```
   Only `rf_agentskills-*` is public; the internal `rf-skill-eval` harness is
   classified `Private :: Do Not Upload` and PyPI rejects it. After upload,
   smoke-test the published artifact:
   ```bash
   uvx --refresh rf-agentskills@X.Y.Z version
   ```
