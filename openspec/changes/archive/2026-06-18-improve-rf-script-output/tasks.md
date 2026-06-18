## 1. Payload size — strip library doc (Issues 1 & 2, highest leverage)

- [x] 1.1 In `skills/robotframework-libdoc-search/scripts/rf_libdoc.py`, change `_library_meta(lib, include_doc=False)` to omit `doc`/`source` by default and emit `{name, type, version, scope, doc_format, short_doc}`; add `doc`/`source` only when `include_doc=True`.
- [x] 1.2 Add a `--include-library-doc` CLI flag (default off) and thread it into the top-level `libraries[]` construction in `main()`.
- [x] 1.3 In `_find_keyword()`, replace the per-match full `_library_meta(lib)` with a minimal `{name, type, version}` reference (parity with `_search_keywords`).
- [x] 1.4 Measure before/after with Browser: assert explain payload drops from ~80 KB to a few KB and search from ~69 KB to a few KB.

## 2. Clean structured usage breakdown (Issue 4)

- [x] 2.1 Rewrite `_parse_keyword_args()` to produce `params: [{name, type, default, kind}]` with `kind ∈ {required, optional, vararg, kwarg, named_only}`; strip `: type` into `type`; `default=null` when absent.
- [x] 2.2 Detect `named_only` from the position after a bare `*`/vararg sentinel; fall back to `optional` when ambiguous.
- [x] 2.3 Keep `raw` and the `required`/`optional` name lists but with clean (annotation-free) names, and key `defaults` by bare `name`.
- [x] 2.4 Verify against `Click` (`selector`, `button=left`) and `Click With Options` (`*modifiers` then named-only args).

## 3. Stable schema with mode discriminator (Issue 3 — breaking)

- [x] 3.1 Refactor `main()` to always emit `{mode, libraries, results, query?, hint?, errors?}` with `mode ∈ explain|search|fallback|list` and a single `results` array (items `{library, keyword, usage|null, score|null, reasons|null}`). Consider a top-level `schema_version`.
- [x] 3.2 Extract a shared result-builder in `rf_libdoc.py` so the CLI and MCP server emit the identical shape (avoid re-derivation).
- [x] 3.3 Update `plugins/rf-agentskills/servers/rf-tools-server.py` to build/return the unified `mode`/`results` schema (it currently hand-rolls `matches`/`keyword_matches`/`hint`).
- [x] 3.4 Update `libdoc-explain/SKILL.md` (and `libdoc-search/SKILL.md` if it documents shape) to describe the `mode`/`results` contract and the `--include-library-doc` flag.

## 4. testcase_builder runnable suite (Issue 6)

- [x] 4.1 Add `--full-suite` to `skills/robotframework-testcase-builder/scripts/testcase_builder.py` that wraps bodies in a `*** Test Cases ***` section (default off preserves the fragment).
- [x] 4.2 Document fragment-vs-suite (and `--full-suite`) in `testcase-builder`'s SKILL.md.

## 5. Onboarding docs — stale prerelease cache (Issue 5, docs-only)

- [x] 5.1 Add a troubleshooting note where pre-release installs are documented (PlatynUI `platform-setup.md` and/or installer/README): the `uv add` "no version of rf-agentskills==<rc>" failure → `uv cache clean rf-agentskills` / `--refresh`; mention `[tool.uv] prerelease = "allow"`.

## 6. Sync, consistency & tests

- [x] 6.1 Run `bash scripts/sync-skills.sh` to propagate the script changes to plugin + VS Code channels; run `bash scripts/check-drift.sh` and confirm no drift.
- [x] 6.2 Add regression tests: payload-size bound for `--search`/`--keyword` (with and without `--include-library-doc`); single-keyword explain `library` ref has no `doc`; non-matching library not embedded.
- [x] 6.3 Add schema tests: `--keyword <found>`, `--keyword <missing>`, `--search <q>` all return the same top-level keys with the correct `mode`; result items carry the right optional fields.
- [x] 6.4 Add usage tests: `button` → `{name:"button", type:"MouseButton", default:"left"}`; named-only args after `*modifiers` have `kind:"named_only"`; `defaults` keyed by bare name.
- [x] 6.5 Add a `testcase_builder --full-suite` test: artifact contains `*** Test Cases ***` and parses (via `get_model`/`--dryrun`).
- [x] 6.6 Gate library-dependent tests with `skipif`/install of `robotframework-browser` as needed (mirror the PlatynUI fidelity-test pattern); run the full suite (`uv run pytest tests/ --ignore=tests/eval`) green.

## 7. Changelog

- [x] 7.1 Note the breaking output-contract change (mode/results schema; `library.doc` now opt-in) and the new flags in `installer/CHANGELOG.md`.
