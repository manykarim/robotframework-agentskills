## 1. Spike and verification against robotcode 2.7.0

- [x] 1.1 In a scratch uv project with `robotcode[all]==2.7.0`, run `robotcode analyze code` (text and `--format json`) on a fixture with a missing keyword, an undefined variable and a wrong argument count, plus one case with an uninstalled library; record the exit codes, diagnostic codes and `-mi`/`-me` effect in the scratch notes. Verify: notes list the observed exit code for each fixture
- [x] 1.2 Capture `--help` for root, `discover *`, `libdoc`, `repl`, `robot-debug`, `results *`, `analyze code`, `config *`, `profiles *` and keep the output as the reference for the claim list in 4.2. Verify: every flag the report's cheat sheet uses appears in the captured help

## 2. Skill content

- [x] 2.1 Create `skills/robotframework-robotcode-skill/SKILL.md` with frontmatter `name: rf-robotcode`, then: availability check, agent-safety rule (pipe/`--plain`, `.exit`), decision table, agent workflow, four inline traps, cheat sheet, companion skills with the fallbacks. Verify: ≤ 200 lines and every linked reference path resolves
- [x] 2.2 Write `references/setup-and-config.md` (install `robotcode[all]` in the project env, `uv run robotcode`, `robot.toml`, profiles, `config show/root/files`, `profiles list/show`, `discover info`). Verify: commands match captured help from 1.2
- [x] 2.3 Write `references/discover.md` (all/tests/suites/tags/files/info, tag patterns, `--search` matching keyword calls, `-bl`, `--format json` + jq). Verify: commands match captured help
- [x] 2.4 Write `references/run-and-wrapper.md` (`robot`/`run`, `-p`, `--wrapper`, profile `wrapper`, `--no-wrapper`, `ROBOTCODE_WRAPPER`, `xvfb-run -a`, `--dry` and missing-wrapper exit-code traps). Verify: commands match captured help
- [x] 2.5 Write `references/libdoc.md` (`version`/`list`/`show`, resource files, `--format JSON` spec, REPL `.imports`/`.kw`/`.doc`, RequestsLibrary `*args` caveat). Verify: commands match captured help
- [x] 2.6 Write `references/repl.md` (piped/heredoc/file input, `-V`/`-v`/`-d`/`-o`/`-l`, `--inspect`, `-k`, blocks, `${_}`, `.vars --user`, `.save -t "Name"`, create the output dir first, exit code 0, secrets in output). Verify: manual smoke run of `explore-api.robotrepl` succeeds on 2.7.0
- [x] 2.7 Write `references/debug.md` (default stop at failure, `--break` keyword/file:line, `--stop-on-entry`, `.where/.vars/.pp/.whatis/.print`, live keywords, `.s/.n/.r/.l`, conditions at the call site, logpoints via `.commands`, `.display`, embedded `Breakpoint`, `.set` limits, `.abort` exit 253, EOF resumes, `--break-on-failed-test` caveat). Verify: manual smoke run of `debug-at-failure.rdb` stops at the failure and exits
- [x] 2.8 Write `references/results.md` (summary/show/log/stats/diff, `-o` and auto-discovery scope, `--sort elapsed`, `--extract` + Browser screenshot condition, output.json, `diff` exit 0 + jq CI gate). Verify: commands match captured help
- [x] 2.9 Write `references/analyze.md` from the spike notes (1.1): usage, bitmask exit codes, modifiers, JSON output, when to use it vs robocop. Verify: every example was run in 1.1
- [x] 2.10 Write `references/agent-mode.md` (detection env vars, force/disable overrides, pipe vs PTY table, secrets handling). Verify: override variable names match the report
- [x] 2.11 Write `references/gotchas.md` as a version-stamped table of the report's 14 limitations with effect and workaround, library-behaviour items labelled. Verify: 14 entries, header states robotcode 2.7.0
- [x] 2.12 Add `assets/examples/robot.toml`, `explore-api.robotrepl`, `explore-browser.robotrepl`, `debug-at-failure.rdb` (plus a tiny target suite if the `.rdb` example needs one). Verify: `robotcode profiles list` reads the toml; the smoke runs in 2.6/2.7 use these files

## 3. Cross-links and triggers

- [x] 3.1 Add one line pointing to `rf-robotcode` to `skills/robotframework-results/SKILL.md`, `skills/robotframework-libdoc-search/SKILL.md` and `skills/robotframework-libdoc-explain/SKILL.md`, leaving existing instructions unchanged. Verify: `git diff` shows only additions in these three files
- [x] 3.2 Extend `RF_REGEX` in `plugins/rf-agentskills/scripts/maybe_inject_rf_context.mjs` with `robotcode`, `robot-debug`, `robot.toml`, and add `robotcode` to the injected skills list and the libdoc hint. Verify: task 3.3 tests pass
- [x] 3.3 Add positive-trigger prompts for the three terms to `tests/test_hook_scripts.py` and assert the injected text names `robotcode`. Verify: `uv run pytest tests/test_hook_scripts.py` passes, including the existing negative cases

## 4. Tests

- [x] 4.1 Create `tests/test_robotcode_skill.py` structural layer: directory, frontmatter `rf-robotcode`, the ten reference files, non-empty `assets/examples/`, SKILL.md links resolve, gotchas version stamp, the four inline traps, the companion fallbacks, and the three cross-links. Verify: `uv run pytest tests/test_robotcode_skill.py` passes
- [x] 4.2 Add the fidelity layer with a `DOCUMENTED_CLI` claim list (subcommands + long options, root-level globals checked against root help) skipped when `shutil.which("robotcode")` is None. Verify: passes with robotcode 2.7.0 installed and reports skipped without it
- [x] 4.3 Add a fail-soft CI step `pip install "robotcode[all]==2.7.0" || echo ...` to `.github/workflows/ci.yml`. Verify: workflow YAML is valid and the step does not fail the job when the install fails

## 5. Distribution

- [x] 5.1 Add `["robotframework-robotcode-skill"]="robotcode"` to `SHORT_NAMES` in `scripts/sync-skills.sh` and run it. Verify: `plugins/rf-agentskills/skills/robotcode/SKILL.md` has `name: robotcode`, `vscode-extension/skills/rf-robotcode/` exists and `vscode-extension/package.json` lists it
- [x] 5.2 Run `scripts/check-drift.sh` and the full test suite. Verify: no drift and `uv run pytest` passes (marketplace validation included)
- [x] 5.3 Add the skill to the README skills table and the installer CHANGELOG's unreleased section. Verify: README table lists `rf-robotcode` with a one-line description
