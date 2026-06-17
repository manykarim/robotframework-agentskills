# rf-agentskills — Issue Report

**Prepared for:** rf-agentskills maintainer
**Date:** 2026-06-17
**Reporter context:** Hit while using the skills end-to-end in `rf-agentskills-demo` (libdoc-search → libdoc-explain → testcase-builder → browser).

## Environment

| Component | Version |
|---|---|
| rf-agentskills | `0.5.0rc2` (published 2026-06-17T12:57:29Z) |
| uv | 0.9.26 |
| Python | 3.13.11 |
| robotframework | 7.4.2 |
| robotframework-browser | 20.0.0 |
| Scripts under test | `~/.claude/rf-agentskills-files/scripts/rf_libdoc.py` (322 LOC), `testcase_builder.py`, `rf_results.py` |

Every claim below was reproduced with a runnable command and measured. Where my initial in-session assumption turned out to be **wrong**, I say so explicitly (see #5).

---

## Summary of findings

| # | Severity | Area | Issue |
|---|----------|------|-------|
| 1 | **High** | `rf_libdoc.py` | Full library `doc` (~38 KB for Browser) embedded in `libraries[]` on *every* invocation — 55% of a search payload |
| 2 | **High** | `rf_libdoc.py` | Library meta (incl. the full `doc`) is **re-embedded per `keyword_match`** — a single-keyword explain is 95% library doc; output routinely exceeds tool display limits |
| 3 | Medium | `rf_libdoc.py` | Output schema is inconsistent for the same flag (`keyword_matches` vs `matches`+`hint`), and the item shapes differ |
| 4 | Medium | `rf_libdoc.py` | `usage` arg breakdown keeps `: type` annotations inside arg names and as `defaults` keys, so consumers can't map a clean param name → default |
| 5 | Low / Docs | demo repo + onboarding | `uv add` fails confusingly against the prerelease pin. **Root cause is a stale uv cache, not the prerelease policy** (assumption corrected by experiment) |
| 6 | Minor | `testcase_builder.py` | Artifact omits the `*** Test Cases ***` header, so it is a fragment, not a runnable file (undocumented) |
| — | ✅ Positive | `rf_results.py`, skills, hooks | Worked correctly; see notes |

---

## Issue 1 — Library `doc` bloats every libdoc payload (High)

**What happens.** `_library_meta()` (rf_libdoc.py:104-113) always includes `lib.doc`, and `main()` puts a `_library_meta` for every loaded library into the top-level `libraries[]` (rf_libdoc.py:272-274) — even on `--search`, where nobody asked for the library's prose intro. For Browser Library that intro is ~38 KB.

**Reproduce:**
```bash
S=~/.claude/rf-agentskills-files/scripts/rf_libdoc.py
python3 "$S" --library Browser --search "mouse click" --limit 15 > /tmp/e.json
python3 - <<'PY'
import json; d=json.load(open('/tmp/e.json')); t=len(json.dumps(d))
print("total:", t, "libraries[0].doc:", len(d['libraries'][0]['doc']),
      f"({100*len(d['libraries'][0]['doc'])/t:.0f}% of payload)")
PY
```

**Measured:** `total: 68985  libraries[0].doc: 38095 (55% of payload)`.

**Consequence.** `--limit` cannot bound payload size, because the dominant cost is fixed library-doc overhead, not the matches. In this session the very first `libdoc-search` call returned **71.3 KB** and had to be spilled to a temp file before it could be read.

**Suggested fix.** In `_library_meta`, drop `doc` (or replace with `short_doc` / a truncated first paragraph), or add a `--include-library-doc` opt-in that defaults off. A search response only needs `{name, type, version}` per library.

---

## Issue 2 — Library doc is re-embedded per match (High)

**What happens.** `_find_keyword()` (rf_libdoc.py:221-234) attaches a full `_library_meta(lib)` — including the 38 KB `doc` — to **each** `keyword_matches` entry, *in addition to* the top-level `libraries[]` copy.

**Reproduce (single keyword):**
```bash
python3 "$S" --library Browser --keyword Hover > /tmp/k.json
python3 - <<'PY'
import json; d=json.load(open('/tmp/k.json')); t=len(json.dumps(d))
km=d['keyword_matches'][0]
print("total:", t, "| top libraries[0].doc:", len(d['libraries'][0]['doc']),
      "| keyword_matches[0].library.doc:", len(km['library']['doc']))
PY
```
**Measured:** `total: 80850 | top libraries[0].doc: 38095 | keyword_matches[0].library.doc: 38095` → **94% of the payload is the library doc, embedded twice**, for one keyword whose own doc is ~1 KB.

**Reproduce (scales with #libraries):**
```bash
python3 "$S" --library Browser --library SeleniumLibrary --keyword Click > /tmp/m.json
```
**Measured:** `total: 109327`, of which **95.7%** is embedded library `doc` fields — and `SeleniumLibrary`'s full doc is included even though it contributed **zero** matches (it has `Click Element`, not `Click`). So adding libraries to widen a search multiplies the bloat super-linearly.

**Suggested fix.** Per-match `library` should be a minimal reference (`{name, type, version}`); the full meta, if wanted at all, belongs once at top level (and per Issue 1, without `doc`).

---

## Issue 3 — Inconsistent output schema for the same flag (Medium)

The `--keyword` flag returns a different top-level key depending on whether the keyword was found, and `--search` returns yet another shape:

```bash
python3 "$S" --library Browser --keyword Hover  | jq -c 'keys'   # ["keyword_matches","libraries"]
python3 "$S" --library Browser --keyword Hoverr | jq -c 'keys'   # ["hint","libraries","matches"]
python3 "$S" --library Browser --search  hover  | jq -c 'keys'   # ["libraries","matches","query"]
```

(measured with a stdin reader; `jq` shown for brevity). Beyond the key name, the **item shapes differ**:

- `keyword_matches[i]` = `{library: <full meta>, keyword, usage}` — no score.
- `matches[i]` = `{library: {name,type}, keyword, score, reasons}` — no `usage`.

So a programmatic consumer driving `--keyword` must branch on two top-level keys *and* two item schemas for one logical operation. This is the kind of thing the skills' own "Output JSON only" contract should make stable.

**Suggested fix.** Always return a single `results` array with a stable item schema; include `usage` and `score` as optional fields (null when N/A), and a top-level `mode: "explain"|"search"|"fallback"` discriminator instead of changing key names.

---

## Issue 4 — `usage` arg breakdown keeps type annotations in names (Medium)

`_parse_keyword_args()` (rf_libdoc.py:56-86) splits each raw arg only on `=`, so the annotation stays glued to the parameter name, and `defaults` is keyed by the annotated string:

```bash
python3 "$S" --library Browser --keyword Click | python3 -c "
import json,sys; u=json.load(sys.stdin)['keyword_matches'][0]['usage']
print('required:', u['required']); print('optional:', u['optional']); print('defaults:', u['defaults'])"
```
**Measured:**
```
required: ['selector: str']
optional: ['button: MouseButton']
defaults: {'button: MouseButton': 'left'}
```

A consumer that wants "default of `button`" has to re-parse `'button: MouseButton'`. Keyword-only args (everything after `*modifiers` in `Click With Options`) are also flattened into `optional`, losing the positional-vs-named distinction that the docs explicitly call out.

**Suggested fix.** Split each arg into `{name, type, default, kind}` where `kind ∈ {required, optional, vararg, kwarg, named_only}`; key `defaults` by bare `name`.

---

## Issue 5 — `uv add` onboarding failure (Low / Docs) — *assumption corrected by experiment*

**Symptom (this session).** With the demo repo pinning the prerelease `rf-agentskills==0.5.0rc2`, `uv add robotframework …` failed:
```
× No solution found when resolving dependencies:
╰─▶ Because there is no version of rf-agentskills==0.5.0rc2 and your project
    depends on rf-agentskills==0.5.0rc2, we can conclude that ... unsatisfiable.
```
My in-session assumption was *"uv won't consider prereleases by default."* **Experiment shows that was wrong.**

**Experiment.** Fresh throwaway project, same pin, **warm** cache, no flags:
```bash
mkdir /tmp/uvtest && cd /tmp/uvtest
printf '[project]\nname="t"\nversion="0.1.0"\nrequires-python=">=3.13"\ndependencies=["rf-agentskills==0.5.0rc2"]\n' > pyproject.toml
uv add robotframework      # SUCCEEDS — rc2 resolves fine
```
It succeeds, because an exact `==` pin is honored under uv's default `if-necessary-or-explicit` prerelease mode. The only difference between the failing call and the succeeding `--refresh` call in this session was the cache. **Root cause: a stale uv index cache** — `rf-agentskills 0.5.0rc2` was published **2026-06-17T12:57Z, the same day** as this session, so a pre-existing cached index for the package didn't list rc2 yet. `uv add --refresh …` re-fetched the index and resolved immediately.

**Recommendations for the maintainer (low effort, high onboarding value):**
- Document the failure mode in the demo README: if `uv add` reports "no version of rf-agentskills==<rc>", run `uv cache clean rf-agentskills` or add `--refresh` (stale index for a freshly published prerelease).
- Consider not pinning a **prerelease** in the demo's `pyproject.toml`, or add an explicit `[tool.uv]\nprerelease = "allow"` so intent is self-documenting. (Verified: adding that block lets a plain `uv add` resolve and is harmless.)

---

## Issue 6 — `testcase_builder` artifact is a fragment, not a suite (Minor)

```bash
echo '{"style":"keyword-driven","tests":[{"name":"T","steps":[{"keyword":"Log","args":["hi"]}]}]}' \
 | python3 ~/.claude/rf-agentskills-files/scripts/testcase_builder.py \
 | python3 -c "import json,sys;a=json.load(sys.stdin)['artifact'];print(repr(a[:30]));print('*** Test Cases ***' in a)"
# 'T\n    Log    hi'   False
```
The `artifact` has no `*** Test Cases ***` header, so it can't be saved and run directly — it must be embedded into a suite (as I did manually in `mouse_interactions.robot`). This is reasonable as a composable fragment, but it isn't documented in the skill, and a `--full-suite` / `--with-section-header` option would remove a manual step. Worth a one-line note in the skill at minimum.

---

## What worked well (positive signal)

- **`rf_results.py`** parsed `output.xml` cleanly: `--sections summary` returned correct totals (8 passed / 0 failed) in well-structured JSON.
- **libdoc-search / libdoc-explain** returned accurate keyword data for Browser 20.0.0; the scoring/`reasons` were sensible.
- **Skill + subagent + hook wiring** all fired correctly (UserPromptSubmit RF-context injection, Stop-hook next-step hints, skill loading).
- The data *content* is good throughout — the issues above are about **payload shape/size and schema stability**, which mostly hurt automated/LLM consumers that have to page through or branch on the output.

---

## Suggested priority order

1. **Issue 2** then **Issue 1** — strip/avoid embedding library `doc`. Single highest-leverage fix; turns 80–110 KB responses into ~2–5 KB and removes the truncation-to-tempfile workaround.
2. **Issue 4** — clean `usage` arg breakdown (`{name,type,default,kind}`).
3. **Issue 3** — stable single-shape response with a `mode` discriminator.
4. **Issue 5 / 6** — docs-only quick wins.

### Appendix: one-paragraph patch sketch for #1/#2
In `_library_meta`, gate `doc`/`source` behind a flag (default off) or replace `doc` with `short_doc`. In `_find_keyword`, replace `"library": _library_meta(lib)` with `"library": {"name": lib.name, "type": lib.type, "version": lib.version}`. No consumer needs the full intro prose on a per-keyword lookup.
