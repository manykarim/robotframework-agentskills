## Why

`docs/RF_AGENTSKILLS_ISSUE_REPORT.md` documents — and I reproduced against the repo source — that `rf_libdoc.py` (the engine behind `libdoc-search`/`libdoc-explain`, the `rf-tools` MCP server, and the agent subagents) emits payloads dominated by fixed overhead rather than the requested data:

- A `--search` response is **56%** the library's prose `doc` (~38 KB for Browser), embedded even though a search never asked for it.
- A single-keyword `--keyword` (explain) response is **94%** library `doc`, embedded **twice** (top-level + per match); adding a second library to widen a search pushes it to **96%** and embeds docs for libraries that contributed **zero** matches. The first real `libdoc-search` call in the reporter's session returned **71 KB** and had to be spilled to a temp file before it could be read — so `--limit` can't bound payload size.

Two further consumer-hostile shapes: the output schema **changes keys** for one logical operation (`keyword_matches` when found, `matches`+`hint` when not, `matches`+`query` for search), and the `usage` arg breakdown keeps `: type` annotations glued into parameter names and `defaults` keys (`{'button: MouseButton': 'left'}`), so a consumer can't cleanly map a param to its default. Plus two minor papercuts: `testcase_builder` emits a header-less fragment (not a runnable suite), and a freshly-published prerelease trips a stale-uv-cache resolution error during onboarding.

These hurt exactly the automated/LLM consumers these skills exist for. The data *content* is correct; the *shape and size* are the problem.

## What Changes

- **Stop embedding library prose `doc` by default (Issues 1 & 2 — highest leverage).**
  - `_library_meta()` drops `doc` (and `source`) from its default output; expose them only behind a new opt-in `--include-library-doc` flag (default off). A library entry becomes `{name, type, version, scope, doc_format}` (+`short_doc`).
  - `_find_keyword()` (explain) per-match `library` becomes a minimal `{name, type, version}` reference — matching what `_search_keywords` already does — instead of a full re-embedded meta.
  - Net: explain payload ~80 KB → ~2 KB; search ~69 KB → ~5 KB.
- **Clean, structured `usage` arg breakdown (Issue 4).** Parse each arg into `{name, type, default, kind}` with `kind ∈ {required, optional, vararg, kwarg, named_only}`; strip `: type` from `name`; key `defaults` by bare `name`. Preserve `raw` for traceability and keep `required`/`optional` lists but with clean names.
- **Stable single-shape response with a `mode` discriminator (Issue 3).** Replace the divergent top-level keys with a stable contract: a `mode: "explain"|"search"|"fallback"|"list"` field and a single `results` array whose items share one schema (`{library, keyword, usage?, score?, reasons?}`, optional fields `null` when N/A). Update every in-repo consumer in lockstep (the MCP server reimplements the old keys; the `libdoc-explain` skill documents them).
- **`testcase_builder` runnable-suite option (Issue 6).** Add a `--full-suite` (and/or `--with-section-header`) flag that wraps the body in a `*** Test Cases ***` section so the artifact is directly saveable/runnable; document the fragment-vs-suite behavior in the skill.
- **Onboarding docs for the stale-prerelease-cache failure (Issue 5).** Document the `uv add` "no version of rf-agentskills==<rc>" failure mode and the `--refresh` / `uv cache clean` remedy in the install docs; note the `[tool.uv] prerelease = "allow"` option. (The demo repo itself is external; only the in-repo install guidance changes.)
- **Propagate + test.** Apply via the single-source script, re-sync channels (`sync-skills.sh`/`check-drift.sh`), keep the MCP server consistent, and add regression tests asserting payload bounds, the stable schema, and the clean `usage` shape.

## Capabilities

### New Capabilities
- `rf-script-output`: The output contract of the rf-agentskills helper scripts (`rf_libdoc.py`, `testcase_builder.py`) and their MCP wrapper — bounded payloads (no unsolicited library prose), a stable single-shape schema with a `mode` discriminator, a clean structured `usage` breakdown, and a runnable-suite option — so automated/LLM consumers get small, predictable, branch-free output.

### Modified Capabilities
<!-- No existing OpenSpec specs to modify (openspec/specs/ holds rf-validation-hooks, platynui-skill). -->

## Impact

- **Single-source scripts:** `skills/robotframework-libdoc-search/scripts/rf_libdoc.py` (`_library_meta`, `_find_keyword`, `_parse_keyword_args`, `main`); `skills/robotframework-testcase-builder/scripts/testcase_builder.py`. Synced to `plugins/rf-agentskills/scripts/` (drift-checked) and `vscode-extension/`.
- **MCP server:** `plugins/rf-agentskills/servers/rf-tools-server.py` reimplements the `matches`/`keyword_matches`/`hint` shape and calls `_search_keywords`/`_find_keyword` directly — must be updated in lockstep for the schema (Issue 3) and benefits automatically from the shared-function fixes (Issues 1/2/4).
- **Skill docs:** `libdoc-explain/SKILL.md` (and `libdoc-search/SKILL.md` if it documents shape) describe the output keys — update to the `mode`/`results` contract and the `--include-library-doc` / `--full-suite` flags.
- **BREAKING (output contract):** Issue 3 changes top-level keys; Issues 1/2 remove `library.doc` from default output. All consumers are in-repo/ours, so this is a coordinated update, not an external break — but anyone scripting against the old keys must adapt. Document in the changelog.
- **Tests:** `tests/` gains regression coverage (payload-size bounds with/without `--include-library-doc`, stable `mode`/`results` schema across found/not-found/search, clean `usage` shape, `testcase_builder --full-suite` produces a parseable suite). Existing drift + marketplace tests still apply.
- **No new dependencies.** Behavior/shape change only.
