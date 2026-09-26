## Context

- Source material is `docs/robotcodereports/robotcode-cli-report.md` (robotcode 2.7.0, RF 7.5, 121 experiments). Its evidence logs and the experiment project are not in this repo, so the report is the reference. Where the skill states behaviour the report did not test, that behaviour has to be checked again here.
- `robotcode --help` on 2.7.0 also lists `analyze code`, `config`, `profiles`, `rebot` and `testdoc`, which the report did not cover. `debug`, `repl-server` and `language-server` are for IDEs.
- The latest library skill (`rf-platynui`) sets the house pattern: `SKILL.md` + `references/` + `assets/examples/`, a structural + fidelity test that skips when the tool is missing, a trigger-regex entry in `maybe_inject_rf_context.mjs`, a `SHORT_NAMES` entry in `scripts/sync-skills.sh`, and an optional fail-soft install step in CI.
- Channels: root `skills/` → `plugins/rf-agentskills/skills/<short>` (sync rewrites `name:`) → `vscode-extension/skills/rf-*` and `package.json` (sync) → installer `_assets/` (hatch build mirrors the plugin). The trigger script lives in the plugin and is mirrored into the installer at build time.

## Goals / Non-Goals

**Goals:**
- An agent that loads only `SKILL.md` can pick the right command and avoid the traps that hang or mislead it. The references are depth, not prerequisites.
- Every command and flag in the skill is backed by either the report or a check in this repo.

**Non-Goals:**
- No new scripts or MCP tools; robotcode is the tool. The skill contains only Markdown and example files.
- No changes to the validation hooks (`validate_robot*.mjs`) or to `check_rf_environment.mjs`.
- The IDE-only commands (`debug`, `repl-server`, `language-server`) are named once as out of scope, not documented.

## Decisions

### D1: Router SKILL.md, references split by task
`SKILL.md` (target ≤ 200 lines) holds: when to use, availability check, the agent-safety rule, the decision table, the agent workflow, the top traps, a compact cheat sheet and companion skills. Everything else goes in `references/`, one file per task. The alternative, one file per robotcode command, was rejected: `robot`/`--wrapper`/profiles belong together, and `libdoc` and REPL `.kw` answer the same question, so a task split gives fewer hops. `libdoc.md` covers both `robotcode libdoc` and the REPL lookup commands (`.kw`, `.doc`, `.imports`); `repl.md` links there.

### D2: Complement through an availability check, not code
`SKILL.md` tells the agent to run `robotcode --version` once per session (use `uv run robotcode` inside a uv project) and pick a path. If robotcode is missing, the agent uses `rf-results` / `rf-libdoc-*`, or installs `robotcode[all]` into the project environment when the user agrees. The three script skills get one line each in their existing companion or intro area. No hook or MCP detection: that would change behaviour in shipped scripts, which is out of scope, and an agent can check this with one command.

### D3: Gotchas in one version-stamped file, top traps repeated inline
`gotchas.md` is a table: #, area, issue, effect, workaround, "observed on 2.7.0". `SKILL.md` repeats only the four traps that cause hangs or false results (output dir, `.save`, quoted `.break`, REPL exit code 0). Each topic reference repeats the traps for its own topic in one line and links to `gotchas.md`. The alternative, spreading traps only across the topic files, makes them hard to review again when upstream releases a fix. Report items that are library behaviour, not robotcode behaviour (RequestsLibrary `*args` signatures, INFO logs showing secrets), are kept but labelled as library behaviour.

### D4: CLI-fidelity test from an explicit claim list
`tests/test_robotcode_skill.py` follows `test_platynui_skill.py`: a structural layer that always runs, and a fidelity layer that runs when `robotcode` is on PATH (`shutil.which`). The fidelity layer uses a hand-kept `DOCUMENTED_CLI = {("results", "diff"): {"--only", ...}, ...}` that is the skill's claim. For each entry it runs `robotcode <cmd...> --help` and checks the subcommand and the long options. The alternative, parsing every code block in the Markdown for flags, is brittle (wrapper flags, `robot` pass-through options, `(rdb)` dot-commands), so it was rejected. REPL/`(rdb)` dot-commands are not checked by `--help`; they are only checked by the manual smoke run (D6). CI gets a fail-soft `pip install "robotcode[all]==2.7.0"` step, as done for PlatynUI.

Global options such as `--format` and `-p` live on the root command. The test checks them against `robotcode --help`, not the subcommand's help.

### D5: Examples are runnable and neutral
`assets/examples/` contains `robot.toml` (output-dir plus `headed`/`baseline`/`wrapped` profiles), `explore-api.robotrepl` (RequestsLibrary against a public demo API), `explore-browser.robotrepl` (Browser, with the output directory created first) and `debug-at-failure.rdb` (a command list for `printf`/`<` into `robot-debug --plain`). Demo credentials that the report found printed in public demo UIs can be used; nothing else that looks like a secret goes into the files.

### D6: analyze spike, then write
Before `analyze.md` is written: run `robotcode analyze code` (text and `--format json`) on a small fixture with a missing keyword, a missing variable and a wrong argument count. Record the exit codes (bitmask) and the diagnostic codes for `-mi`/`-me`. Also check how `analyze code` handles a project whose libraries are not installed. The results decide the wording of `analyze.md` and one row of the decision table only; they don't change the structure. The same session does a manual smoke run of the REPL and `robot-debug` examples against 2.7.0.

### D7: Triggers
Add `\brobotcode\b`, `\brobot-debug\b` and `\brobot\.toml\b` to `RF_REGEX` (edited in the plugin script; the installer copy is mirrored at build), and add `robotcode` to the injected skills list. The injected text keeps "Prefer libdoc-search / libdoc-explain" and adds "or `robotcode libdoc` when robotcode is installed". Bare `repl` or `debug` alone are too generic and would cause false positives, so they are not added.

## Risks / Trade-offs

- [Upstream fixes a gotcha and the skill tells agents to avoid something that now works] → version stamp; the fidelity test pins 2.7.0 in CI; bumping the pin is a point to review `gotchas.md` again.
- [robotcode releases often, so flags change] → the fidelity test fails on removed flags when the pin is bumped; that is the signal we want.
- [Agents run `robotcode` from the wrong interpreter (global vs project venv) and get the wrong library versions] → `setup-and-config.md` and the availability check tell agents to use `uv run robotcode` / the project venv and to check with `robotcode discover info`.
- [Two ways to do the same thing (robotcode vs script skills) confuse agent choice] → one explicit rule in both directions (D2); the script skills stay the documented fallback.
- [Section 9 PTY hang is hard to test automatically] → documented as a rule, not tested; the piped path is the one the examples use.

## Migration Plan

Additive only. Release with the next installer version; rollback is removing the skill directory, the name-map entry and the regex terms, then running sync again.

## Open Questions

- Whether `analyze code` output is useful enough to mention in the validation-hook docs later. This belongs to a follow-up, not this change.
