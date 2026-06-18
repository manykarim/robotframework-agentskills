# Design — improve-installer

## Context

Two baselines were studied firsthand (OpenSpec cloned + run; rf-agentskills
installed + exercised in a sandbox).

**OpenSpec model** (`core/config.ts`, `core/available-tools.ts`, `core/init.ts`):
a flat declarative `AI_TOOLS[]` registry, **project-scoped** detection
("does `<projectDir>/<skillsDir>` exist?"), and an init decision tree —
`--tools all|none|csv` for headless, TTY multi-select otherwise,
non-TTY falling back to detected tools with a helpful error when none.

**rf-agentskills model**: Python, 7 adapter classes, **machine-scoped**
detection (`shutil.which` + `~/.claude`), argparse-only (no wizard),
manifest-tracked uninstall, config-merges across JSON/TOML/YAML.

## Decisions

### D1. Keep the Python toolstack; adopt only OpenSpec's *approach*
rf-agentskills ships a Python MCP server + Python skill scripts and has a
manifest-based precise uninstall that OpenSpec lacks. A Node rewrite would
lose both. We port the UX *shape* (wizard + headless flags + smart
defaults), not the runtime.

### D2. Prompt library = questionary (optional extra) + stdlib fallback
- **questionary 2.1.1** (Aug 2025, requires-python ≥3.9, single dep
  `prompt_toolkit`) — actively maintained, the de-facto Python multiselect.
- Rejected: **InquirerPy** (0.3.4, last release Jun 2022, "Pre-Alpha");
  **python-inquirer** (older UI, heavier input stack).
- The installer "reaches into $HOME", so base deps stay minimal:
  `questionary` lives in a `[interactive]` extra. When it is absent (or the
  session is non-TTY), the wizard degrades to a numbered stdlib `input()`
  selector. Either way, explicit flags bypass prompting entirely.

### D3. Selection & interactivity decision tree (mirrors OpenSpec)
```
install
  ├─ explicit selection? (--agents all|none|detected|csv, --agent, --all)
  │     └─ yes → use it, no prompt
  └─ no selection
        ├─ interactive? (stdin.isatty() and not --yes and not --no-input)
        │     └─ yes → multi-select wizard, detected agents pre-checked,
        │              then scope confirm
        └─ no  → fall back to DETECTED agents
                  └─ none detected → exit 2 + print valid agents + flag hint
```
- `--yes` ⇒ accept the detection-driven default with no prompt (CI).
- Exit codes: 0 ok, 1 nothing-detected-and-none-selected, 2 usage.

### D4. Project scope is the default
Default `scope="project"`, `project_dir` defaults to CWD; `--scope user`
opts into the global `~/.<agent>` install. The wizard shows and confirms
the resolved target directory before writing. Existing `--scope`/`--project`
flags are unchanged in meaning, only the default flips.

### D5. Granular, ownership-aware hooks merge (the core fix)
Claude Code `settings.json` hooks are `hooks.<Event> = [ {matcher, hooks:[{type,command}]} , ... ]`.
The current merge does `data["hooks"] = ours` (whole-key replace) and
reverts by deleting `hooks` — unsafe both ways (see proposal experiment).

New approach, parallel to the already-correct MCP per-server merge:

- **Ownership marker.** Every rf-agentskills hook command references the
  install dir (`…/rf-agentskills-files/…`). That substring is the stable
  ownership marker — no schema-polluting sentinel field needed, and it is
  the exact absolute path already recorded in the manifest.
- **Apply (idempotent).** For each event in our `hooks.json`: ensure
  `settings.hooks[event]` is a list; append our matcher-groups *only if* an
  equivalent rf-agentskills-owned group (same marker) is not already
  present. Never touch groups lacking our marker.
- **Manifest.** New `ConfigMerge.kind = "json_hooks"` records the ownership
  marker (the install dir) and the events touched — enough to reconstruct
  removal out-of-process.
- **Uninstall.** For each recorded event, drop only matcher-groups whose
  commands contain the marker; if an event list becomes empty, remove the
  event; if `hooks` becomes empty, remove it; if `settings.json` becomes
  `{}`, remove the file. All other events, groups, and top-level keys
  (`model`, foreign tools' hooks) are preserved.
- A new `transforms.merge_hooks_block` / `remove_owned_hook_entries` pair
  implements this; `claude_code._hooks_merge_op` switches to it. The MCP
  merge is unchanged (already granular).

### D6. Uninstall test strategy
Tests run fully sandboxed (`HOME=<tmp>`, no real user dirs), seeding a
`settings.json` with a foreign `PostToolUse` group + a user `Notification`
group, and a `.mcp.json` with a foreign server. Assertions:
1. after install: ours present **and** foreign/user entries intact;
2. after uninstall: ours gone, foreign/user entries intact, no orphaned
   rf-agentskills commands, file not deleted while foreign keys remain;
3. re-install is idempotent (no duplicate groups);
4. user-modified installed files are skipped (existing manifest hash gate).

### D7. Per-project manifest (decided during apply)
Flipping the default to project scope exposed a manifest-keying hazard: the
manifest is keyed by `(agent, scope)` in **one global file**, so a second
project's `(claude-code, project)` install would `upsert`-replace the first's
record and strand its files from uninstall. Decision: **the manifest location
follows scope** —
- **project scope** → `<project_or_cwd>/.rf-agentskills/installed.json` (local
  to the repo; `uninstall` from within the repo needs no `--project`), and
- **user scope** → today's global `$XDG_DATA_HOME/rf-agentskills/installed.json`.

`manifest.manifest_path_for(scope, project_dir)` resolves it; `cmd_install`,
`cmd_uninstall`, and `_is_already_owned` thread the resolved path. `list`
shows the global manifest plus the CWD project manifest when present. This
keeps two concurrent projects fully isolated and uninstall a no-argument
operation from inside a repo.

## Risks / open questions
- **Default-scope flip** is a visible behavior change; mitigated by clear
  CHANGELOG/README notes and unchanged flags. Confirm we want bare
  `install` to write into CWD by default (matches OpenSpec).
- **questionary UX parity**: no built-in fuzzy search like OpenSpec's; the
  flat agent list (7 items) doesn't need it.
- **PyPI publish** is partly process (token/CI), tracked as its own task
  group; the UX work does not block on it.
