## Context

See proposal.md (Why). The current state that shapes the approach:

- **Upstream.** `robotcodedev/robotframework-agent-plugins` (checked at commit `86a8641`, 2026-10-15) ships one plugin, `robotcode` 2.8.0. Its single skill has about 300 lines of SKILL.md plus 9 references. Releases are tagged `robotcode--v<version>`, and the plugin has no hooks and no subagents. Its README plans Browser, Requests and "general Robot Framework patterns" plugins.
- **robotcode 2.8.0 extras** (package metadata and https://robotcode.io/reference/cli/):

  | Extra | Provides |
  |---|---|
  | `runner` | `robot`, `rebot`, `libdoc`, `testdoc`, `discover`, `results` |
  | `analyze` | `analyze code`, `analyze cache` |
  | `repl` | `repl`, `robot-debug`, `doc` |
  | `debugger` | DAP server |
  | `languageserver` | LSP server |
  | `replserver` | REPL server |
  | `lint` | `robotframework-robocop>=2` |
  | `yaml`, `rest` | YAML variable files, reST docs |
  | `all` | everything above, with `robotframework-robocop>=6.0.0` |

  The core package alone gives only `config` and `profiles`. `python -m robotcode` does not work: there is no `__main__`.
- **Measured** on robotcode 2.8.0, RF 7.5.1, with a broken 11-line file. `robotcode analyze code` reported:
  - `KeywordNotFound`;
  - an argument-count `DataError`;
  - `ModelError` "FOR loop must have closing END.";
  - `VariableNotFound`.

  It exited 1. A cold run took 4.0 s and a warm one 0.8 s, and it left `.robotcode_cache/` in the project. Robocop at error severity, which the current hook uses, reports only the `FOR` error. robotcode did not flag `Run Keyword If`; Robocop `DEPR08` does.
- Current hooks resolve a Python interpreter (`_python_env.mjs`) and run Robocop through it. The pending-error record (`_pending_errors.mjs`) and the Stop re-check (`report_pending_errors.mjs`) already exist.
- The installer mirrors `plugins/rf-agentskills/` into `_assets/` at build time. Skill directories it installs carry an ownership marker.

## Goals / Non-Goals

**Goals:**
- After this change no file in this repo teaches robotcode CLI mechanics that the upstream skill already owns. What remains is inline commands at the point of use.
- The blocking hook check gets stronger (semantic errors) without adding false blocks while the agent is mid-edit.
- Every remaining component works the same with or without the robotcode plugin installed.

**Non-Goals:**
- Changing the robotcode plugin repo beyond filing issues or PRs for traps that still reproduce.
- Moving the library skills upstream. That waits on agreement with the RobotCode maintainers about their planned Browser/Requests plugins.
- Raising the 160-character description limit. The 3 freed listing slots are measured first, and a limit change would be its own change.
- Replacing Robocop for deprecation and formatting advice.

## Decisions

### D1. Require `robotcode[all]>=2.8`, documented only

- **Why `[all]`:** the skills need `runner` (run, discover, results), `repl` (`doc`, `robot-debug`) and `analyze`, and the hooks need Robocop. Only `[all]` bundles all four with one install line and a modern Robocop (`>=6`, where `lint` allows `>=2`). The extra LSP/DAP packages are small and pure-Python.
- **Why `>=2.8`:** `robotcode doc` first appears in 2.8, so it is the floor.
- **Alternatives:**
  - `[runner,analyze,repl,lint]`, upstream's minimum plus lint. Rejected: it is four extras to get right in every install line, and `lint` only allows Robocop `>=2`, which predates the `DEPR` rule IDs we classify on.
  - A plugin `dependencies` entry in Claude Code. Rejected by the user: a missing marketplace would make our plugin fail to load, and no other agent supports it.
- **CI note:** `robotcode[runner]` is enough for jobs that only execute tests.
- **Conflict to state:** upstream's `install.md` asks the user about scope and extras and suggests `[runner,analyze,repl]`. rf-setup installs `[all]` as a dev dependency, because the rest of this plugin assumes it. rf-setup says so explicitly, so the two skills don't look contradictory.

### D2. Inline commands, no skill-to-skill dependency

- **Approach:** skills and subagents write the full robotcode command where it is used (`robotcode doc keyword Browser "Click"`). They name the upstream `robotcode` skill only in prose, never as a Companion Skills row, because those rows are validated against shipped directories.
- **Alternative:** a stub `rf-robotcode` skill that just says "see the robotcode plugin". Rejected: it costs a listing slot and competes for triggering, the problem we are removing.

### D3. Per-file error check: robotcode for errors, Robocop for advice

- **Tier 1 (blocking or advisory):** `robotcode --format json analyze code <file>`, run from the project root with a 20 s timeout. Classification by code:

  | Diagnostic | Result |
  |---|---|
  | error-severity, not `KeywordNotFound`/`VariableNotFound` | blocking, exit 2 |
  | `KeywordNotFound` / `VariableNotFound` | advisory on edit; recorded as pending |
  | warning / info / hint | dropped |

  JSON was chosen over text output because the text format can change and severity is a field in the JSON.
- **Tiers 2 and 3:** unchanged Robocop deprecation and formatting tiers, still advisory.
- **Executable resolution:** the same environment order as now (VIRTUAL_ENV, `.venv`, installer interpreter, PATH), but the hook looks for the `robotcode` executable in the environment's `bin/` or `Scripts\`, then `robotcode` on PATH. `-m` invocation is impossible.
- **Pending record:** a file with an unresolved name is recorded with `{kind: "unresolved"}`. At Stop, `report_pending_errors.mjs` re-validates it, so a keyword that is still missing then blocks. The once-per-content-version rule stays.
- **Cache:** `.robotcode_cache/` is accepted. It is robotcode's normal cache, which the VS Code extension also creates, and the rf-setup `gitignore.txt` already lists it. The hooks README states it. Disabling the cache would turn 0.8 s into about 4 s per edit.
- **Alternatives:**
  - Block on `KeywordNotFound` too. Rejected: it gives false blocks while the agent writes a keyword in a second file.
  - Use `robot --dryrun`. Rejected: it imports libraries (side effects) and doesn't read `robot.toml`.
  - Keep Robocop as the blocker. Rejected: it misses arguments, keywords and variables.
- **Latency:** the budget moves from "+150 ms over Robocop" to a 1.5 s median when the cache is warm. The hook timeout rises to 60 s: 20 s for robotcode, 10 s for Robocop and 20 s for the opt-in dry run, plus margin.

### D4. Project tier: `robotcode analyze code --collect-unused`

One tool replaces `robot --dryrun` + `robotframework-find-unused`. It reads `robot.toml`, and its exit code is a bitmask. The hook masks out warnings, info and hints and parses the JSON. It stays opt-in, because analysis loads libraries (for keyword lists) and scales with project size.

### D5. Subagents

- **`rf-keyword-consultant`:** removed. `robotcode doc keywords`/`keyword` and REPL `.kw` do its job.
- **`rf-debug-expert`:** keeps its taxonomy, flakiness table, report format and rules (see spec). Its method delegates mechanics to the upstream workflows: B, investigate one failing test; E, fix a whole failing run with a pinned output file.
  - Claude frontmatter: `tools: Read, Grep, Glob, Bash`.
  - OpenCode variant: `permission: {edit: deny, bash: allow}`.
  - Codex TOML: no restriction field. Read-only is stated in the instructions.
- **`model`:** left unset. Inheriting the caller's model avoids pinning an alias that ages.
- **Generator:** `build-agent-variants.py` learns to map `tools` to OpenCode `permission`.
- **Alternative:** a read-write `rf-debug-expert` that applies fixes. Rejected: the user chose a read-only diagnostician, and keeping analysis apart from editing matches the owner's site guidance.

### D6. Upstreaming traps before deletion

These `rf-robotcode/references/gotchas.md` rows are not in the upstream skill: 1 (REPL output dir), 2 (`.save` keeps failed lines), 3 (quoted `.break`), 4 (breakpoint condition scope), 5 (`--break-on-failed-test` `IndexError`), 7 (bare `${var}` / `[Tags]` in REPL), 8 (`--dry` runs the wrapper), 9 (secrets in INFO logs) and 13 (PTY paste). Also the `--wrapper "xvfb-run -a"` recipe.

Row 6 (REPL always exits 0) is superseded: 2.8 exits 1 for piped input. Rows 10, 11 and 14 are already documented upstream.

Each remaining row gets a scripted re-check on robotcode 2.8.0. The result is recorded in the table below during implementation, and then an issue or PR is filed. Several rows had already been filed (robotcode #662–#670, 2026-10-09) and fixed in 2.8.0; the new reports (#683–#685, agent-plugins #1, filed 2026-11-04) follow robotcode's `AI_POLICY.md` (human-reviewed text, disclosure) and were re-verified on 2.9.0.dev87. Row 1 (Browser) moves to `rf-browser` Gotchas if it still reproduces (see the spec's library-specific exception).

Re-checked on 2026-11-04 with robotcode 2.8.0, Robot Framework 7.5.1, Python 3.12, Browser 21.0.0 (BrowserBatteries) and RequestsLibrary 0.9.7, all with piped input under agent detection (`CLAUDECODE=1`). Row 13 is the exception: it ran under a PTY with detection off. The scripts are in the session scratchpad (`traps/`).

| Row | Trap | 2.8.0 result | Action / upstream link |
|---|---|---|---|
| 1 | REPL output dir not created (Browser `FileNotFoundError`) | **fixed**: `-d nodir/out` is created and `New Browser` works | none (was [#662](https://github.com/robotcodedev/robotcode/issues/662), closed as not planned: a Browser bug, fixed in MarketSquare/robotframework-browser#5313) |
| 2 | `.save` keeps failed lines | **fixed**: "1 failed input left out, see --keep-failed" | none (fixed via [#663](https://github.com/robotcodedev/robotcode/issues/663)) |
| 3 | quoted `.break "Name"` at `(rdb)` never matches | **reproduces**: registers `keyword '"Add Price"'` and never stops; unquoted works | none: [#668](https://github.com/robotcodedev/robotcode/issues/668) was closed as not planned (intended: at `(rdb)` the text is taken literally); upstream fixed its skill to show `.break <Keyword>` |
| 4 | condition with unknown variable stops at every hit | **changed**: now prints "condition error: Variable '${nope}' not found" and still stops; documented upstream (debugging.md: "if the expression itself raises, the debugger stops anyway") | none ([#669](https://github.com/robotcodedev/robotcode/issues/669)) |
| 5 | `IndexError` when running a keyword at a `--break-on-failed-test` stop | **fixed**: the keyword runs | none (fixed via [#664](https://github.com/robotcodedev/robotcode/issues/664)) |
| 7 | bare `${var}` line / `[Tags]` in REPL | **partly reproduces**: `${x}` alone fails with "Keyword name cannot be empty."; `[Tags]` now fails clearly ("Setting 'Tags' is not allowed in the REPL.") | `[Tags]` fixed via [#667](https://github.com/robotcodedev/robotcode/issues/667); bare variable: [#684](https://github.com/robotcodedev/robotcode/issues/684) |
| 8 | `--dry` runs the wrapper; missing wrapper exits 1 | **fixed**: `--dry` does not run the wrapper (exit 251); missing wrapper exits 252 with "Failed to execute wrapper command" | none (fixed via [#665](https://github.com/robotcodedev/robotcode/issues/665), [#666](https://github.com/robotcodedev/robotcode/issues/666)) |
| 9 | credentials in INFO output | **reproduces**, library behaviour: password, `Basic …` header and token header logged | moved to `rf-requests` Gotchas (library-specific) |
| 13 | piped lines under a PTY taken as one paste | **not a bug**: the first re-check sent LF, which prompt_toolkit treats as "insert newline". With a real Enter (CR), typed and burst input run and `.exit` works on 2.8.0 and 2.9.0.dev87; only a bracketed paste stays in the multi-line buffer until submitted, which is normal | none |
| extra | `results diff` exits 0 with new failures | **reproduces** (exit 0, "1 new failures") | robotcode CLI enhancement (opt-in exit code): [#685](https://github.com/robotcodedev/robotcode/issues/685) |
| extra | non-ASCII output crashes under cp1252 (`PYTHONIOENCODING=cp1252`) | **reproduces**: `UnicodeEncodeError … '❌'` from `results summary` | robotcode CLI bug: [#683](https://github.com/robotcodedev/robotcode/issues/683) |
| extra | `analyze code` without paths from a subfolder analyzes the whole project | **reproduces** (3 files from `tests/`, root file included) | none: intended and documented (`analyze code --help`: "If no PATHS are provided, the whole project is analyzed"; upstream `analyze.md` says the same) |
| extra | `discover` without `paths` and without arguments | unchanged: "Expected at least 1 argument, got 0." The message is clear, so this is not reported | none |
| — | `xvfb-run` wrapper recipe | verified on 2.9.0.dev87 (`DISPLAY=:99` under the wrapper); robotcode's wrapper guide covers it, the skill doesn't link it | agent-plugins issue (not a PR: their PRs need signed commits and eval runs): [robotframework-agent-plugins#1](https://github.com/robotcodedev/robotframework-agent-plugins/issues/1) |

### D7. Versioning

- **Content:** 3.0.0 (major, retirements).
- **Installer:** 0.8.0. It gains the cleanup of retired directories and drops the archives.
- **Tags:** follow the existing `RELEASING.md`.

### D8. Co-installed trigger measurement (task 10.2, 2026-11-04)

Setup:
- Claude Code 2.1.316, `claude-haiku-4-5-20251001`.
- Train, validation and holdout3 splits, 3 runs per query, 293 queries.
- Four arms, 879 sessions each, no incomplete runs:
  - `solo`: only this plugin;
  - `co`: plus the upstream `robotcode` skill from tag `robotcode--v2.8.0` (86a8641), staged next to ours;
  - each of the two again with a 40000-character listing budget (`solo40k`, `co40k`).
- The harness stages the skills as personal skills. A real `--plugin-dir` install of both plugins produced the same listing (`rf-agentskills:rf-*` first, then `robotcode:robotcode`).

**The robotcode description is not shown under the default budget.**
- With both plugins, the default listing is 7879 of about 8000 characters. The `robotcode` line needs 1035 (its description is 1022 characters), so it is listed by name only, in 879 of 879 `co` sessions.
- Our 9 description lines take 1017 characters; Claude Code's bundled skills take most of the rest.
- With only the robotcode plugin installed, the listing is 7896 characters and the description is shown, with about 100 characters to spare.
- So installing this plugin is what hides the robotcode description on 200k-context models. Any other plugin with a few descriptions would do the same.
- Shortening our descriptions cannot fix this: freeing about 900 characters means dropping nearly all of them. The lever is the length of the upstream description.

**Default budget (`co` vs `solo`):**
- robotcode loads in 0 runs on any rf-* should-trigger query. Its only loads are 4 of 45 on rf-setup's should-not-trigger queries, by name only.
- Validation per skill differs from `solo` by at most one query, in either direction:
  - rf-python-library 4/4 → 3/4 (pylib-t09);
  - rf-restinstance 3/4 → 4/4 (ri-v01).
- Validation should-not-trigger accuracy is 1.00 for every skill in every arm.
- The robotcode near-misses still go to our skills (holdout3):
  - rf-language: 1 of 4 correct;
  - rf-requests: 2 of 3 correct.
- **Shortfall:** the skill-triggering scenario "list all tests tagged smoke" fails. rf-language loads in 2 of 3 runs (3/3 in `solo`). Cause: the model only sees `robotcode`'s name.

**40000 budget (`co40k`, reported, not gating):**
- robotcode's description is shown in 879 of 879 sessions, and it wins its near-misses:
  - all 7 holdout3 queries are correct;
  - "list all tests tagged smoke": rf-language 0/3;
  - the BuiltIn argument questions (lang-h07, lang-r04) go to robotcode.
- Cost: rf-language train recall goes from 12/13 (`solo`) / 10/13 (`solo40k`) to 9/13. robotcode takes lang-t04 ("run only tests tagged smoke but not slow"), lang-t06 ("Multiple keywords with name"), lang-h05 and lang-t11. Of these, lang-t04 plausibly belongs to both skills.
- Validation:
  - rf-language unchanged at 4/6;
  - rf-browser 3/4 (br-v04, robotcode and rf-setup loaded);
  - rf-python-library 2/4. pylib-t07 and pylib-t09 loaded no other skill, so this is our own description's variance, not robotcode.
- The mitigation in Risks ("When to use" cue when a library skill drops below threshold) is not triggered: no library skill falls below threshold because of robotcode. rf-language's validation recall, 0.67, is the existing recorded shortfall, the same in all four arms.

Pre-existing shortfalls are unchanged: rf-language validation recall 0.67 (lang-t12, lang-t14).

The results are in `eval/baselines/triggers.json`:
- `skills`: the gating `solo` baseline;
- `co_installed`: the `co` results;
- `budget_40000`: `solo40k` and `co40k`.

## Risks / Trade-offs

- **[Upstream's greedy description wins prompts our skills should get]** ("DO NOT answer Robot Framework … USE THIS SKILL FIRST") → Mitigation: the co-installed trigger measurement (skill-triggering). If a library skill's recall drops below threshold with both installed, its "When to use" block gets a cue, measured on the train split.
- **[robotcode missing → no blocking check at all]** → Mitigation: SessionStart says so loudly. Robocop advice still runs. rf-setup installs robotcode in every setup path.
- **[robotcode output format changes in a later release]** → Mitigation: parse JSON and treat unparsable output as no finding. A hook test pins a fixture captured from 2.8.0, and a CI job runs the hook against the latest robotcode.
- **[Claude Desktop archives tell the model to run robotcode, which the Desktop sandbox lacks]** → Mitigation: archives are still built for the 9 skills. The README notes that robotcode commands only work where the project environment is reachable, and the guidance itself still applies.
- **[Users relied on `rf_results.py` without robotcode, e.g. for CI artifacts]** → Mitigation: the CHANGELOG migration note gives `uvx --from "robotcode[runner]" --with robotframework robotcode results summary -o output.xml` (verified on 2.8.0; without `--with robotframework` it cannot load). That is acceptable for a standalone artifact with no project libraries; it is the one case where an isolated run is fine, and it is stated as such.
- **[Upstream Browser/Requests plugins later duplicate our library skills]** → Mitigation: out of scope here. Raise it with the maintainers when filing the trap issues.
- **[`.robotcode_cache/` appears in projects that never used robotcode]** → Mitigation: documented. It only appears once robotcode is installed, which the user chose.

## Migration Plan

1. Re-check the traps (D6) and file them upstream, while `rf-robotcode` still exists to read from.
2. Content edits: remove skills and the subagent, rewrite the remaining skills, subagents and hooks.
3. Regenerate the sync, the variants and the installer assets. Run the tests, then the eval re-baseline (co-installed).
4. Release content 3.0.0 + installer 0.8.0.
   - Plugin users get the removal on `plugin update`.
   - Installer users get the managed directories cleaned up on upgrade.
   - Hand-copied folders get a note.

Rollback: revert the release commit and re-tag 2.x. Users who need the old skills can pin the marketplace to the last 2.x tag.

## Open Questions

- Whether upstream accepts the trap reports as skill text, or wants CLI fixes instead. This doesn't change what this repo ships.
