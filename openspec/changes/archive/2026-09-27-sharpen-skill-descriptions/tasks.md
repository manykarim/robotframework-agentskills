## 0. Preconditions

- [x] 0.1 Confirm `retire-generator-skills`, `merge-libdoc-skills` and `align-skill-names-with-spec` are merged. Verify: `ls skills/` shows exactly the 10 `rf-*` skills including `rf-libdoc`, and `python scripts/validate-skills.py --channel all` passes
- [x] 0.2 Check whether `strengthen-skill-eval-harness` has landed the `trigger` command and seeded any `eval/triggers/*.yaml`. Verify: `uv run rf-skill-eval trigger --help` works; list the existing trigger files (extend them instead of recreating them)

## 1. Trigger query sets

- [x] 1.1 Author `eval/triggers/rf-browser.yaml` and `rf-selenium.yaml` per design D5: ≥ 8 per polarity (aim 10–12), about 60/40 train/validation stratified, ≥ 3 sibling and ≥ 2 non-RF near-misses, ≥ 2 should-trigger queries that don't name the library, no shared-ambiguity negatives. Verify: the harness loader (or `tests/test_skill_descriptions.py` once written) accepts both files
- [x] 1.2 Author `rf-requests.yaml` and `rf-restinstance.yaml` with the same rules, each using the other as sibling near-misses. Verify: loader accepts both; each contains ≥ 3 queries whose `note` names the sibling
- [x] 1.3 Author `rf-appium.yaml` and `rf-platynui.yaml`. Verify: loader accepts both
- [x] 1.4 Author `rf-robotcode.yaml`, `rf-results.yaml` and `rf-libdoc.yaml`. Generic output.xml/keyword-lookup queries are positives for the script skills and are not used as negatives for rf-robotcode. Verify: loader accepts all three; `grep -n output.xml eval/triggers/rf-robotcode.yaml` shows no `should_trigger: false` entry without an explicit robotcode-free rationale in `note`
- [x] 1.5 Author `rf-setup.yaml` (install/env-error positives; test-writing and `robot.toml`-usage negatives). Verify: loader accepts it
- [x] 1.6 Peer-read all 10 sets for realism (phrased like users, including typos and pasted errors) and for queries that leak the answer (do not name the skill id). Verify: `grep -n "rf-" eval/triggers/*.yaml | grep "query:"` returns nothing

## 2. Pre-change baseline

- [ ] 2.1 Run `uv run rf-skill-eval trigger --skills <all 10> --split train,validation --runs 3 --max-cost-usd <cap>` on the current (old) descriptions and store the result as the pre-change trigger baseline. Verify: `eval/baselines/triggers.json` (or the harness equivalent) contains per-skill precision/recall/accuracy for both splits and is committed. If the harness is not ready, record this task as blocked and continue with group 3 (DEFERRED: live eval run — tracked in follow-up)

## 3. Descriptions and companion tables

- [x] 3.1 Write `tests/test_skill_descriptions.py` per design D7 (description rules, sibling boundaries, companion catalogue rows and required rows, no retired names, trigger-set shape). Verify: it fails on the current tree for the expected reasons (meta-phrasing, missing boundaries)
- [x] 3.2 Replace the `description` in the 10 root `SKILL.md` files with the design D3 drafts, as double-quoted YAML scalars. Check every quoted keyword/CLI name against libdoc or `--help` (for example `Get Text` with `==`, `Integer    response status`, `robotcode analyze code`). Verify: `python scripts/validate-skills.py --channel root` passes and `python -c "import yaml…"` parses each frontmatter
- [x] 3.3 Rewrite each `## Companion Skills` section from the D4 catalogue with the per-skill required rows. Keep rf-robotcode's three-column form. Verify: `uv run pytest tests/test_skill_descriptions.py tests/test_robotcode_skill.py tests/test_setup_skill.py` passes (robotcode/setup specs still satisfied)
- [x] 3.4 Align secondary description surfaces: the `README.md` skill table one-liners and the skill list in `plugins/rf-agentskills/scripts/maybe_inject_rf_context.mjs` (same boundaries, no contradicting text). Verify: `uv run pytest tests/test_hook_scripts.py` passes; README table lists the same 10 skills
- [x] 3.5 Run `bash scripts/sync-skills.sh` and `bash scripts/check-drift.sh`. Verify: drift check passes, and `python scripts/validate-skills.py --channel all` passes

## 4. Tune and accept

- [ ] 4.1 Run trigger evals on the **train** split for all 10 skills and revise descriptions where a query fails. Look at which other skill loaded for failing queries (confusion list) and strengthen both sides of that boundary. Verify: train recall ≥ 0.80 and should-not-trigger accuracy ≥ 0.90 per skill, or the remaining failures are documented (DEFERRED: live eval run — tracked in follow-up)
- [ ] 4.2 Run the **validation** split (3 runs, threshold 0.5, Haiku). Verify: per skill, validation recall ≥ 0.80, should-not-trigger accuracy ≥ 0.90, and neither is below the pre-change baseline from 2.1. Re-run borderline skills once before deciding. Do not edit validation queries (DEFERRED: live eval run — tracked in follow-up)
- [ ] 4.3 Commit the accepted trigger baseline and add a results table (skill × old/new recall and specificity) to the PR description. Verify: the baseline file is updated in the PR, and the PR's CI trigger job (from the harness change) is green (DEFERRED: live eval run — tracked in follow-up)
- [ ] 4.4 Re-sync after any tuning edits and re-run the static tests. Verify: `bash scripts/sync-skills.sh && bash scripts/check-drift.sh && uv run pytest tests/test_skill_descriptions.py` all succeed (DEFERRED: live eval run — tracked in follow-up; runs after the 4.1 tuning edits)

## Implementation Notes

- **Adapted to the tree after 7 earlier changes.** 10 skills at `skills/rf-<topic>/` (validator: `name`/`description`
  stay frontmatter lines 2–3, description ≤ 1024 and tag-free; `license`/`compatibility`/`metadata` untouched, so
  `tests/test_skill_commands.py`'s compatibility ↔ `requires-python` tie is unaffected). Plugin/VS Code copies are plain
  synced copies (no short-name rewrite), so backticked skill names in Companion tables are identical in all channels.
- **0.2 / group 1:** `strengthen-skill-eval-harness` already seeded all 10 `eval/triggers/<skill>.yaml` (10 + 10,
  6/4 train/validation, D5 queries incl. the rf-browser example verbatim) and the `trigger` runner. Tasks 1.1–1.5 were
  done as a review against D5/spec (sibling + non-RF near-miss counts, rf-requests ↔ rf-restinstance ≥ 3 sibling notes
  each, no shared-ambiguity negatives, no `output.xml` negative in rf-robotcode, generic output.xml / keyword lookups
  are positives for rf-results / rf-libdoc). No existing query was changed (validation queries untouched). For 1.6
  (realism incl. typos) each set gained one **train** positive `<p>-t07` with typos / chat phrasing (note
  `typos, user phrasing`), giving 11 + 10 per set (7/4 train/validation positives, still inside the 0.5–0.7 ratio
  enforced by `tests/eval/test_trigger_sets.py`).
- **1.6 verify:** the literal `grep -n "rf-" … | grep "query:"` also matches the `note: "sibling rf-x"` field on the
  same line; the equivalent check on the query text (`grep 'query: "[^"]*rf-'`) returns nothing, and
  `tests/test_skill_descriptions.py::test_trigger_set_exists_with_shape` now enforces "no skill id in a query".
- **2.1 deferred** (live model runs are not executed in this implementation cycle). Because the descriptions had to be
  rewritten in the same pass, the exact pre-change texts were saved to `pre-change-descriptions.yaml` in this change
  directory; the follow-up restores them in a scratch copy, runs `rf-skill-eval trigger --split train,validation`
  there and stores that as the "before" result, then runs the new texts (4.1–4.3). `eval/baselines/` still holds only
  its README.
- **3.2 final texts vs D3 drafts** (all verified: keyword names via libdoc — Browser `New Browser`/`New Context`/
  `New Page`/`Get Text` (assertion_operator), `>>>` frame selector (Browser library doc "iFrames"); SeleniumLibrary
  `Open Browser`, `Wait Until …`, **`Execute Javascript`** (draft said `Execute JavaScript`; libdoc name is
  `Execute Javascript`); AppiumLibrary `Open Application`, `Switch To Context`; RequestsLibrary `GET On Session`
  documents `expected_status`; RESTinstance `Integer`/`String`/`Object`/`Array`, `Expect Response Body`,
  `Output Schema`; robotcode 2.x `analyze code`, `robot-debug`, `libdoc`, `results` via `robotcode --help`):
  - all written as one double-quoted YAML scalar on line 3 (no `"`/`\` inside, so no escapes needed); both the PyYAML
    and the stdlib fallback parser of `scripts/validate-skills.py` accept them;
  - rf-browser: states the confirmed default ("or wants a web test with no library chosen yet"), mirroring rf-requests'
    "without naming a library"; rf-selenium's boundary adds "or new web tests with no library chosen, use rf-browser";
  - rf-platynui: the draft's "Not for web browsers or mobile apps." became a named boundary ("For mobile apps use
    rf-appium; for web browsers use rf-browser or rf-selenium"), matching rf-appium's boundary to rf-platynui (proposal:
    every description ends with the sibling to use instead);
  - rf-setup: "Use for installing…" became "Use when installing…" (the spec requires a literal `Use when`);
  - rf-libdoc: "signatures (arguments, types, defaults)" keeps the words `tests/test_libdoc_skill.py` requires;
  - rf-restinstance names `Expect Response Body` / `Output Schema`; small trims elsewhere to stay near 500.
  - Lengths: appium 499, browser 528, libdoc 467, platynui 492, requests 482, restinstance 487, results 474,
    robotcode 508, selenium 491, setup 572 — the three > 500 raise the D7 warning only (spec-mandated terms / default
    clause); the train-split tuning (4.1) may trim them.
- **3.3 companion tables:** rows are the D4 catalogue verbatim; order = sibling(s) first, then setup, libdoc, results,
  robotcode. rf-libdoc and rf-results had no `## Companion Skills` section — added at the end. Optional rows used:
  rf-appium ↔ rf-platynui (the D2 disjoint-domain pair, so each table links the description's boundary skill).
  rf-robotcode keeps `Need | With robotcode | Without robotcode`; the combined "Browser / Requests library usage" row
  was split into the catalogue's browser and requests rows. `tests/test_library_install_guidance.py`
  (`## Companion Skills` + `` `rf-setup` ``), `tests/test_setup_skill.py`, `tests/test_robotcode_skill.py` stay green.
- **3.1 test (`tests/test_skill_descriptions.py`):** failed on the pre-change tree for the expected reasons (meta-phrasing,
  missing boundaries, catalogue rows, missing rf-libdoc/rf-results sections), passes now. Beyond D7 it also checks:
  every `rf-*` token in a description or companion table is shipped and not the skill itself, the boundary text
  appears **after** `Use when`, the two confirmed default clauses (rf-browser / rf-requests), per-skill required
  trigger terms (incl. the robotcode/setup/libdoc spec words), every row's `Need` is a catalogue entry, the two-column
  skill cell equals the catalogue cell, `eval/triggers/*.yaml` == shipped skills. `CATALOGUE`, `REQUIRED_ROWS`,
  `SIBLINGS` are module-level dicts: `add-rf-language-skill` / `add-rf-python-library-skill` add their `language` /
  `python-library` keys and rows there (and `test_every_shipped_skill_is_covered_by_the_contract` fails until they do).
- **3.4 secondary surfaces:** README skill table one-liners rewritten to the same boundaries/defaults; the plugin hook
  `maybe_inject_rf_context.mjs` gained one line "Pick by import: `Library    Browser` -> rf-browser (default for new
  web tests), `SeleniumLibrary` -> rf-selenium; `RequestsLibrary` -> rf-requests (default for API tests), `REST` /
  JSON Schema -> rf-restinstance; installing or environment errors -> rf-setup", with
  `tests/test_hook_scripts.py::test_injected_context_states_skill_boundaries`. The existing name-list lines are
  unchanged (their parser test still passes).
- **CHANGELOG:** entries under installer `0.7.0 — Unreleased` → `### Changed` and VS Code `2.0.0 (unreleased)`; no
  version bump.
- **4.4** left unchecked: it re-syncs after the (deferred) 4.1 tuning edits. Its commands already pass on the
  untuned texts (sync, drift, `tests/test_skill_descriptions.py`).
