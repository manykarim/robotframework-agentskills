## Context

`rf_libdoc.py` is the shared engine for `libdoc-search`, `libdoc-explain`, the `rf-tools` MCP server (`rf-tools-server.py`, which imports its functions), and the RF subagents. Reproduced measurements against the repo source (Browser 20.0.0):

- `--search "mouse click" --limit 15`: total **68,581 B**, of which `libraries[0].doc` is **38,155 B (56%)**.
- `--keyword Hover`: total **80,883 B**; library `doc` embedded **twice** (top-level + per-match) = **94%**.
- `--library Browser --library SeleniumLibrary --keyword Click`: total **109,331 B**, **96%** doc — and SeleniumLibrary's full doc is embedded despite contributing **0** matches.
- Schema keys differ per outcome: `{keyword_matches, libraries}` (found) / `{hint, matches, libraries}` (not found) / `{matches, query, libraries}` (search) / `{keywords, libraries}` (list).
- `usage` for `Click`: `required=['selector: str']`, `optional=['button: MouseButton']`, `defaults={'button: MouseButton': 'left'}`.
- `testcase_builder` artifact for one test: `'T\n    Log    hi'` — no `*** Test Cases ***` header.

Root causes in code: `_library_meta` (lines 104-113) always emits `doc`+`source`; `_find_keyword` (line 230) attaches full `_library_meta` per match while `_search_keywords` (line 211) already uses minimal `{name,type}`; `main` (line 273) emits full meta for every loaded lib and switches top-level keys by branch; `_parse_keyword_args` (lines 56-86) splits only on `=`.

Consumers in-repo: `rf-tools-server.py` rebuilds `data["matches"]/["keyword_matches"]/["hint"]` itself (lines 115-156); `libdoc-explain/SKILL.md` documents `keyword_matches`/`matches`. The scripts are single-sourced under `skills/` and synced to plugin + VS Code by `sync-skills.sh` (drift-checked).

## Goals / Non-Goals

**Goals:**
- Bound payload size: a search/explain response should be a few KB, dominated by the matched keywords — not fixed library prose.
- One stable response schema across found / not-found / search / list, branch-free for consumers.
- A `usage` breakdown a consumer can use directly (`name → default`, positional vs named-only preserved).
- Keep the (correct) data content; this is a shape/size change.
- Update all in-repo consumers (MCP server, skill docs) in lockstep; add regression tests.

**Non-Goals:**
- Changing scoring/search ranking logic (it works; report confirms).
- Touching `rf_results.py` (report: works correctly).
- Fixing the external `rf-agentskills-demo` repo (only in-repo install docs change for Issue 5).
- Preserving the old output keys as long-term aliases (all consumers are ours; a clean coordinated cut is simpler than dual-maintenance — but see D3 for a transition note).

## Decisions

### D1: Drop library `doc` by default; opt-in flag (Issues 1 & 2)
`_library_meta(lib, include_doc=False)` returns `{name, type, version, scope, doc_format, short_doc}` and only adds `doc`/`source` when `include_doc=True`, wired to a new `--include-library-doc` CLI flag (default off). `_find_keyword`'s per-match `library` becomes the minimal `{name, type, version}` reference (parity with `_search_keywords`). The top-level `libraries[]` stays (cheap once `doc` is gone) as the place to optionally surface the full meta.
- *Alternatives:* truncate `doc` to first paragraph (rejected — arbitrary, still unsolicited); drop `libraries[]` entirely (rejected — `{name,type,version}` per lib is useful and tiny).

### D2: Structured `usage` params (Issue 4)
Add `params: [{name, type, default, kind}]` where `kind ∈ {required, optional, vararg, kwarg, named_only}`. Detect `named_only` from the position after a bare `*`/vararg (Robot/Python keyword-only convention, e.g. everything after `*modifiers` in `Click With Options`). Strip `: type` into the `type` field; `default` is `null` when absent. Keep `raw` (the verbatim arg strings) for traceability and keep `required`/`optional` name lists but with **clean** names and `defaults` keyed by bare `name`.
- *Alternatives:* replace `required/optional/defaults` outright (rejected for this pass — keep them clean for back-compat, add `params` as the rich source of truth).

### D3: Stable schema with `mode` discriminator (Issue 3) — the breaking one
Every invocation returns `{mode, libraries, results, ...}`:
- `mode`: `"explain"` (exact keyword found), `"search"`, `"fallback"` (explain miss → search), `"list"` (no query).
- `results`: a single array; each item `{library, keyword, usage|null, score|null, reasons|null}`. Explain/fallback items carry `usage`; search items carry `score`+`reasons`; all carry the minimal `library` ref + `keyword`.
- Keep `query` (echo) and `hint` (when empty) and `errors` as optional top-level fields.
- **Transition:** all consumers are in-repo. Update `rf-tools-server.py` and the skill docs in the same change. Do NOT keep the old `matches`/`keyword_matches` keys (dual-shape is the bug). Call it out as a breaking output-contract change in the changelog; bump nothing package-wise (scripts aren't versioned independently).
- *Alternatives:* additive (`results` alongside old keys) — rejected; perpetuates the divergent shapes the report flags. A `--legacy-output` flag — rejected as scope creep unless a real external consumer surfaces.

### D4: `testcase_builder --full-suite` (Issue 6)
Add `--full-suite` (wraps body in `*** Test Cases ***`; future-friendly toward also emitting `*** Settings ***`/`*** Keywords ***` when present) — default off to preserve the composable fragment behavior. Document fragment-vs-suite in `testcase-builder`'s SKILL.md.

### D5: Install-docs note for stale prerelease cache (Issue 5)
Add a short troubleshooting note where pre-release installs are already documented (e.g. the PlatynUI `platform-setup.md` and/or the installer/README install section): if `uv add` reports "no version of rf-agentskills==<rc>", run `uv cache clean rf-agentskills` or `--refresh`; mention `[tool.uv] prerelease = "allow"`. Pure docs.

### D6: Single source + lockstep consumers
Edit only `skills/.../scripts/*.py`; run `sync-skills.sh`; update `rf-tools-server.py` and skill docs in the same change; `check-drift.sh` guards the script copies.

## Risks / Trade-offs

- **Breaking output contract (D3/D1)** → Mitigation: all consumers are in-repo and updated together; regression tests pin the new schema; changelog calls it out. Risk limited to any user who scripted the raw CLI JSON.
- **MCP server drift** → the MCP server reimplements the shape; if only the script is updated, the MCP tool would still emit the old keys. Mitigation: explicit task to refactor `rf-tools-server.py` to consume/emit the unified shape (ideally call a shared builder in `rf_libdoc.py` rather than re-deriving).
- **`named_only` detection heuristic** (D2) → libdoc arg strings may not always mark the `*` boundary uniformly across RF versions. Mitigation: derive from the presence of a bare `*`/vararg sentinel; fall back to `optional` when ambiguous; test against Browser's `Click With Options` (`*modifiers` then named-only).
- **Losing `library.doc` someone relied on** → Mitigation: `--include-library-doc` restores it explicitly; the per-keyword `keyword.doc` (the actually-relevant prose) is unchanged.
- **Scope spread across 2 scripts + MCP + docs + tests** → Mitigation: sequence by leverage (1/2 → 4 → 3 → 5/6); each tier independently shippable.

## Open Questions

- Should `libraries[]` be omitted entirely when `len(libs)==1` and the single lib is implied by `results[].library`? (Leaning: keep it; it's tiny and stable.)
- For `mode:"fallback"`, is a distinct value worth it vs reusing `"search"` with a `fellBackFrom` field? (Leaning: keep `"fallback"` explicit — clearer for consumers.)
- Should `--full-suite` also emit a `*** Settings ***` stub (Library imports) when the input names libraries? (Defer; `--full-suite` minimal first.)
- Do we want a top-level `schema_version` integer to make future contract changes detectable? (Cheap insurance; lean yes.)
