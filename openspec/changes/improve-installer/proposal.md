## Why

The `rf-agentskills` installer is **fully scriptable but not easy**, and its
**hooks config-merge is unsafe** for shared config files. Both gaps were
confirmed by experiment against OpenSpec (`@fission-ai/openspec`), whose
init flow is the comparison baseline.

1. **No easy path.** A bare `rf-agentskills install` errors — argparse
   requires a mutually-exclusive `--agent` or `--all`. There is no
   interactive wizard and no detection-driven default. (Experiment: bare
   `install` prints a usage error.)

2. **User scope is the default.** Installs default to `~/.claude` etc.; the
   per-repo, reviewable, project-local install is opt-in via
   `--scope project --project <dir>`.

3. **The hooks merge clobbers other tools' and the user's hooks, and
   leaks its own on uninstall.** Proven in a sandboxed install/uninstall:

   - **Install** replaced the entire `settings.json` `hooks` key — a
     pre-existing foreign `PostToolUse` matcher *and* the user's own
     `Notification` hook were **wiped out**.
   - **Uninstall** removed **nothing** from `hooks` (because `hooks`
     pre-existed, the add-diff recorded zero keys), leaving
     rf-agentskills' own hook entries behind — now pointing at the
     just-deleted `rf-agentskills-files/` scripts, i.e. broken commands.

   The **MCP merge is already correct** (granular per-server add/remove:
   the sibling `some-other-server` survived both install and uninstall).
   Hooks must reach the same standard.

4. **Not on PyPI** → no `uvx rf-agentskills` / `pipx run` one-liner, so
   the zero-install ease that `npx openspec init` enjoys is missing.

OpenSpec itself stays a **comparison only**, not a dependency: it ships
markdown and can be Node/npm; rf-agentskills ships a Python MCP server
and Python skill scripts, so the Python toolstack and the
manifest-tracked uninstall are load-bearing and are kept.

## What Changes

- **Interactive wizard** (TTY + no explicit selection): a multi-select of
  known agents, pre-checking those detected on the machine, then a scope
  confirmation. Built on **questionary** (active, single-dep) shipped as
  an optional `[interactive]` extra, with a **stdlib `input()` fallback**
  so the wizard works even without the extra and the base stays lean.
- **Non-interactive parity & determinism**: add `--agents all|none|detected|<csv>`
  (keeping `--agent`/`--all` as back-compat aliases) and `--yes`. Treat a
  non-TTY stdin as non-interactive automatically; never block on input.
  Nothing selected + non-interactive + no flag ⇒ non-zero exit with the
  valid-agent list (OpenSpec's behavior).
- **Project scope becomes the default**; `--scope user` is the opt-in for a
  global install. `--project` defaults to the current directory.
- **Granular, ownership-aware hooks merge**: append rf-agentskills' hook
  matcher-groups to each `settings.json` event without replacing siblings;
  identify ownership by the install-dir marker in the hook command;
  idempotent on re-install; uninstall removes only rf-agentskills-owned
  entries and never leaves orphans, pruning empty events/`hooks`.
- **Uninstall correctness test suite** covering foreign-hook preservation,
  foreign-MCP preservation, our-own removal, idempotent re-install, and
  user-modified-file skip.
- **PyPI publish** wired so `uvx rf-agentskills install` works (the
  remaining "easy" lever; see RELEASING.md "future follow-up").

## Capabilities

### New Capabilities
- `installer-onboarding` — wizard, non-interactive flags, scope default,
  detection-driven selection, zero-install entry point.
- `installer-uninstall-safety` — granular ownership-aware config merges and
  manifest-accurate uninstall that coexists with other tools.

### Modified Capabilities
- None (no existing installer capability spec; these are the first).

## Impact

- **Behavior change**: default scope flips user→project; bare `install`
  becomes interactive instead of erroring. Documented in `installer/README.md`
  and `installer/CHANGELOG.md`; existing flags keep working.
- **Dependency**: optional `[interactive]` extra adds `questionary`
  (→ `prompt_toolkit`); base install unchanged.
- **Files**: `installer/src/rf_agentskills/{cli.py,transforms.py,adapters/claude_code.py}`,
  new `tests/installer/test_uninstall_safety.py` + wizard tests, docs.
- **No content-bundle change** (the plugin tree is untouched), so the
  installer (`rf-agentskills`) version bumps, not the content `1.2.0`.
