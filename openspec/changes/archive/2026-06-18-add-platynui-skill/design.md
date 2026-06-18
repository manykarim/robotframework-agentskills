## Context

Studied PlatynUI's `new_core` branch in depth (source, docs, tests, CLI). Key facts that shape the skill:

- **Only `PlatynUI.BareMetal` is usable.** The high-level `PlatynUI` library is a placeholder: a single `Dummy Keyword` and `warnings.warn("...not implemented yet...")`. The migration's Phase 5 ("Keywords + Robot-Library") is pending. Every `.robot` test in the repo imports `PlatynUI.BareMetal`.
- **BareMetal *does* have docstrings** (unlike the old PyPI `PlatynUI` 0.9.2 surface that the libdoc-search assessment found undocumented). The skill's value for `new_core` is less "supply missing docstrings" and more "teach the model the XPath UI model, the cross-platform setup, and the CLI loop the docstrings can't convey."
- **~25 keywords**, grouped: `Query` / `Set Root`; pointer (`Pointer Click`, `Pointer Multi Click`, `Pointer Press`, `Pointer Release`, `Pointer Move To`, `Get Pointer Position`); keyboard (`Keyboard Type`/`Press`/`Release`); `Focus`, `Get Attribute`, `Bring To Front`; window surface (`Activate`/`Minimize`/`Maximize`/`Restore`/`Close`/`Move`/`Resize`/`Move And Resize Window`); diagnostics (`Take Screenshot`, `Highlight`). No app-launch keyword (use `Process`); no explicit wait keyword (resolution lazily retries for ~30 s).
- **Locator model = XPath 2.0 over a normalized tree** with four namespaces: `control` (default), `item`, `app`, `native`. Elements are referenced by an XPath string (auto-converted to a `UiNodeDescriptor`) or a `UiNode` captured via `Query ... only_first=${True}`. Roles are PascalCase and cross-platform-normalized. Stable selectors prefer `@Id` over `@Name`; `app:` and `item:` must be prefixed explicitly; `Set Root` scopes relative queries.
- **Library package install (experimentally verified, 0.12.0.dev330):** the new_core RF library is published on PyPI as a **prebuilt prerelease wheel** — `robotframework-PlatynUI==0.12.0.dev330` provides `PlatynUI.BareMetal` (24 keywords, 24/24 documented) + the `PlatynUI` placeholder, identical to the branch. It pulls a prebuilt `platynui-native==0.12.0.dev330` whose wheel bundles the compiled runtime (`_native.abi3.so`) — **no git branch, no Rust toolchain.** Prerelease opt-in is mandatory: unpinned `pip install robotframework-PlatynUI` (no `--pre`) silently resolves the old stable **`0.9.2`** (the different 19-keyword, near-undocumented `PlatynUI` surface, no `BareMetal`); new_core requires `--pre` (unpinned) or an exact prerelease pin (`==0.12.0.dev330`, accepted by uv/pip without `--pre`). Python 3.12+ (PyO3 abi3-py312). A Rust 1.95+ source build is needed **only** for the optional mock provider.
- **Tooling loop:** `platynui-cli query`/`snapshot`/`highlight`/`watch` and the `platynui-inspector` GUI are how locators are developed/debugged. Install via `uv tool install --prerelease allow platynui-cli` (same prerelease rule). Prebuilt wheels need no Rust; source builds need Rust 1.95+.
- **Runtime:** Linux needs AT-SPI2 running + a session; **X11 is the complete path, Wayland is degraded** (input injection, screen-absolute coords, screenshots). A **mock provider** gives deterministic, display-less runs (`use_mock=${True}` / `Runtime.new_with_mock()`), but — **verified against the 0.12.0.dev330 wheel** — the published `platynui-native` is built *without* `mock-provider` and raises `ProviderError` on `Runtime.new_with_mock()`; using mock needs a source build with `--features mock-provider`.
- **Libdoc is display-free (verified):** `robot.libdoc` on `PlatynUI.BareMetal` succeeds with no display and no AT-SPI, because the native Runtime is lazy (instantiated on first keyword call, not at import). So a keyword-fidelity test only needs the pip wheel, not a desktop.

The existing library skills (Browser/Selenium/Appium) establish the house structure: `SKILL.md` (frontmatter `name: rf-<lib>`) → references/ → assets/examples/. `sync-skills.sh` iterates `skills/*/`, maps long→short names, transforms `python scripts/...` paths, and regenerates the plugin + VS Code channels; `check-drift.sh` guards the Python-script copies; `installer/hatch_build.py` mirrors the plugin tree into the installer wheel at build time.

## Goals / Non-Goals

**Goals:**
- A first-class PlatynUI library skill matching the Browser/Selenium/Appium pattern, pinned to `new_core` + `PlatynUI.BareMetal`.
- Teach the three things docstrings can't: the XPath/namespace locator model, the cross-platform setup (AT-SPI/X11/Wayland/mock), and the `platynui-cli`/inspector locator-development loop.
- Honest status signalling (preview, unreleased, BareMetal-only, differs from old PyPI surface).
- Tests that keep the documented keyword names true to the library without needing a live desktop in CI.
- Clean integration into both distribution channels with no drift.

**Non-Goals:**
- Documenting the high-level `PlatynUI` library (placeholder) or the older PyPI `PlatynUI`/0.9.x surface.
- Bundling or pinning PlatynUI as a package dependency.
- A live, desktop-driving RF integration test in CI (the upstream project itself has none and flags it as a gap).
- Building the Rust toolchain in CI or shipping mock-provider binaries.
- Inventing semantic keywords (`Activate`/`Select`/`Set Value`): those are upstream's *intended direction*, not shipped keywords — present them as direction, not API.

## Decisions

### D1: One skill, `new_core` + `BareMetal` only
A single `robotframework-platynui-skill` (`name: rf-platynui`), documenting `Library    PlatynUI.BareMetal`. The high-level API and semantic verbs are described in a `status-and-migration.md` reference as "direction," never as available keywords.
- *Alternative:* document both libraries — rejected; the high-level one is a non-functional placeholder and would mislead the agent.

### D2: Reference-file split mirrors the four study axes
`keywords-reference.md`, `locators-and-queries.md`, `cli-and-inspector.md`, `platform-setup.md`, `status-and-migration.md`. The locator/query reference is the centerpiece (the analog of Browser's `locators.md`) because the XPath/namespace model is the highest-leverage, least-discoverable knowledge.
- *Rationale:* progressive disclosure — SKILL.md stays scannable; deep material lives in references loaded on demand, exactly like the Browser skill's table.

### D3: Two example suites — live-desktop (primary) + mock (teaching-only)
`assets/examples/`: (1) a live example adapted from `calc.robot`/`anv.robot` (launch via `Process`, `Set Root` on the app, relative `@Id` queries, keyboard input), explicitly labelled as needing a desktop + AT-SPI/X11; and (2) a `use_mock=${True}` suite showing the mock shape. The mock example is a **teaching artifact only** — verified that the published wheel raises `ProviderError` on `Runtime.new_with_mock()`, so it runs only against a `--features mock-provider` source build. The display-less, reproducible *automated* check is the libdoc keyword-fidelity test (D4), not the mock example.
- *Open:* if the mock example risks misleading (it can't run from pip), consider dropping it and pointing to the upstream `tests/BareMetal/` suites instead.

### D4: Tests = structure (always) + keyword fidelity (real in CI, skip-if-absent as safety net)
Frontmatter/structure validation folds into the existing marketplace test (auto-discovers the new SKILL.md). A new keyword-fidelity test asserts that the keyword names the skill documents exist in `PlatynUI.BareMetal` via `robot.libdoc`. Because libdoc is display-free (verified) and the wheel is a fast prebuilt prerelease, CI installs `robotframework-PlatynUI==0.12.0.dev330` and the test runs **for real, headless, no skip** — `skipif(PlatynUI not importable)` is only a safety net for local runs without the optional dependency. (Same graceful pattern as the validation-hook tests, but here the dependency is cheap enough to actually install in CI.)
- *Alternative:* a checked-in libdoc spec (`.libspec`) of BareMetal to diff against — rejected for now (preview API churns; would need constant regen). Revisit if churn proves painful.
- *Alternative:* live desktop integration test — rejected (needs AT-SPI/X11; upstream has none).

### D5: Hook regex picks up `platynui`
Add `platynui` to `maybe_inject_rf_context.mjs`'s trigger regex and the test's positive list, so PlatynUI prompts surface the skill — consistent with how `selenium`/`browser`/`appium` already trigger.

### D6: Distribution via the existing sync, not hand-mirroring
Edit only `skills/robotframework-platynui-skill/`; add the short-name map entry; run `sync-skills.sh`. The plugin + VS Code copies and `vscode-extension/package.json` are regenerated; the installer wheel picks it up via `hatch_build.py`. No manual copies.

## Risks / Trade-offs

- **Preview API churn** — `new_core` keyword names/CLI output may change before stable. → Pin the skill to documented `new_core` behavior, date/label it "preview," and let the skip-if-absent keyword-fidelity test catch drift when a maintainer installs a newer build.
- **Two different PyPI surfaces** (`new_core` BareMetal vs released `PlatynUI` 0.9.x) → an agent could install the wrong one and find different keywords. → `status-and-migration.md` + Installation section make the `--pre`/`new_core` requirement and the BareMetal import explicit.
- **Can't run live in CI** (no desktop/AT-SPI; mock needs a Rust build) → tests stay static + skip-if-absent; live validation is a documented manual/optional step (Docker + X11 + AT-SPI, or a mock-feature native build).
- **Skill claims could drift from reality** if PlatynUI changes → keyword-fidelity test + a "verified against version X" note in the skill give a check and a paper trail.
- **Wayland users** hit degraded behavior → platform-setup.md states X11 (or XWayland) + AT-SPI as the recommended runtime and explains why.

## Open Questions

- Should the skill name be `rf-platynui` (consistent) — and the long dir `robotframework-platynui-skill` (matches `-skill` suffix of browser/selenium/appium/requests/restinstance)? (Proposed: yes to both.)
- Do we want to *optionally* validate against a live desktop now via Docker+X11+AT-SPI (the user offered), or defer that to apply-phase validation? (Leaning: do a mock/CLI smoke during apply; full desktop run optional.)
- Should we vendor a checked-in `PlatynUI.BareMetal` `.libspec` snapshot as a stable fixture for the fidelity test, accepting periodic regen? (Deferred per D4.)
- Is a short companion "platynui-inspector workflow" worth its own reference, or does it fit inside `cli-and-inspector.md`? (Proposed: one file.)
