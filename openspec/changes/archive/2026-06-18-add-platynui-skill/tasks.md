## 1. Author the skill (single source: skills/robotframework-platynui-skill/)

- [x] 1.1 Create `skills/robotframework-platynui-skill/SKILL.md` with frontmatter (`name: rf-platynui`, description) and sections: Quick Reference, Installation (lead with the footgun: `pip install --pre robotframework-PlatynUI` or exact pin `==0.12.0.dev330` — plain `pip install robotframework-PlatynUI` gets the wrong, old `0.9.2`; prebuilt wheel, no Rust/git, Python 3.12+), Library Import (`PlatynUI.BareMetal` + `use_mock`/`auto_activate`/profiles), Essential Concepts (UI model, 4 namespaces, XPath queries, lazy 30 s resolution, coordinate semantics, window patterns), grouped Core Keywords, Locator Strategy, Common Patterns, CLI tooling, Troubleshooting, "load references" table, Companion Skills table.
- [x] 1.2 Write `references/keywords-reference.md` — full `PlatynUI.BareMetal` keyword inventory with real signatures, grouped (query/root, pointer, keyboard, focus/attribute, window surface, diagnostics); note no app-launch keyword (use `Process`) and no explicit wait keyword (lazy retry).
- [x] 1.3 Write `references/locators-and-queries.md` — UI model, namespaces (`control` default / `item` / `app` / `native`), XPath axes/functions/predicates, role vocabulary + cross-platform normalization, locator best practices (`@Id` over `@Name`, anchor on `app:`, `Set Root` scoping), real example selector table.
- [x] 1.4 Write `references/cli-and-inspector.md` — `platynui-cli` subcommands (`query`, `snapshot`, `highlight`, `watch`, `pointer`, `keyboard`, `window`, `list-providers`, `info`) with example invocations, and the `platynui-inspector` GUI workflow.
- [x] 1.5 Write `references/platform-setup.md` — install matrix leading with the PyPI prebuilt prerelease wheel (`--pre` / exact pin `==0.12.0.dev330`, bundles `platynui-native` `_native.abi3.so`, no Rust/git), the `0.9.2`-without-`--pre` footgun, Python 3.12+; then Linux AT-SPI2 requirement, X11-vs-Wayland (why X11), the mock provider (needs a `--features mock-provider` source build — published wheel raises `ProviderError`), Docker/headless notes.
- [x] 1.6 Write `references/status-and-migration.md` — BareMetal-only today; high-level `PlatynUI` placeholder; semantic verbs as direction-not-API; difference from older PyPI `PlatynUI` surface; preview caveat + "verified against version X" note.
- [x] 1.7 Add `assets/examples/calculator.robot` (live desktop: `Process` launch, `Set Root` on app, relative `@Id` queries, keyboard input — labelled desktop/AT-SPI/X11 required) and a `use_mock=${True}` example **clearly marked teaching-only** (requires a `--features mock-provider` source build; the published wheel raises `ProviderError`). Decide per design-D3 whether to keep the mock example or instead point to upstream `tests/BareMetal/`.

## 2. Distribution integration

- [x] 2.1 Add `SHORT_NAMES["robotframework-platynui-skill"]="platynui"` to `scripts/sync-skills.sh`.
- [x] 2.2 Run `bash scripts/sync-skills.sh`; confirm `plugins/rf-agentskills/skills/platynui/` and `vscode-extension/skills/rf-platynui/` are generated and `vscode-extension/package.json` lists the skill.
- [x] 2.3 Run `bash scripts/check-drift.sh` and confirm no drift.

## 3. Hook trigger

- [x] 3.1 Add `platynui` to the trigger regex in `plugins/rf-agentskills/scripts/maybe_inject_rf_context.mjs` (it will mirror to the installer via the build hook).
- [x] 3.2 Add a `platynui` case to the positive-trigger parametrize list in `tests/test_hook_scripts.py` and confirm the negative-miss cases still pass.

## 4. Tests

- [x] 4.1 Confirm the existing marketplace/SKILL.md validation test auto-discovers and passes the new skill; adjust the skill count/expectations if the test hard-codes them.
- [x] 4.2 Add a keyword-fidelity test: parse `PlatynUI.BareMetal` via `robot.libdoc` (display-free — verified) and assert every keyword name the skill documents exists; maintain the claimed-name list (a constant, or parsed from the keywords reference). Gate with `skipif` when PlatynUI isn't importable, but install `robotframework-PlatynUI==0.12.0.dev330` in the CI Test job so it actually runs (fast prebuilt wheel, no Rust/desktop) — mirror the pattern used for the validation-hook tooling in `.github/workflows/ci.yml`.
- [x] 4.3 Run the full test suite (`uv run pytest`) and confirm green.

## 5. Cross-references & docs

- [x] 5.1 Add the PlatynUI skill to the Companion Skills / sibling-skill references where the other library skills are listed (and the skill's own Companion Skills table).
- [x] 5.2 Update the README skill list / counts to include the PlatynUI skill.

## 6. Validation (optional / apply-phase)

- [x] 6.1 Smoke-validate the documented CLI commands against an installed `platynui-cli` (and/or a mock-feature native build), and optionally run the live `calculator.robot` example via Docker + X11 + AT-SPI; record the verified PlatynUI version in `status-and-migration.md`.
