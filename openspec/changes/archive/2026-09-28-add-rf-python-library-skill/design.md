## Context

See proposal.md (Why). Facts that shape the design:

- **Research.** `rf-guide-research.md` A4 (practices and 13 gotchas, 5 marked [verified] on RF 7.4.2) and B3 (skill outline, description draft, script idea, evals, trigger queries). The prototype libraries used there (`DecoLib`, `ModLib`, `StateLib`, `TypedEmb`) were reused for the checker spike below.
- **Checker spike (2026-09-27, RF 7.4.2, scratchpad `checklib/`).** A 230-line prototype built on `robot.libdocpkg.LibraryDocumentation` ran against 17 fixture libraries. Results:

  | Detection | Mechanism | Spike result |
  |---|---|---|
  | keyword list, scope, version | `LibraryDocumentation(path)` → `.keywords`, `.scope`, `.version` | works (module libs report `GLOBAL`, classes `TEST` unless set) |
  | `import_failed` | `DataError` from libdoc: import error ("ModuleNotFoundError: No module named …") and init error ("Initializing library 'Raises' with no arguments failed: cannot connect") | works; `BuiltIn().get_library_instance()` in `__init__` fails here with `RobotNotRunningError` (a real trap, now a hint) |
  | `keyword_creation_failed` + `no_keywords` | ERROR log message "Adding keyword 'Take ${qty: int} pears' failed: Library keywords do not support type information with embedded arguments" and 0 keywords | works, needs a logger registered with `robot.output.LOGGER` |
  | `leaked_keyword` | `kw.source` ≠ library file (`Join` → `<frozen posixpath>`) | works; `kw.source` is a `Path`, compare resolved paths |
  | `public_method_not_keyword` | import module, pick the library class, `ROBOT_AUTO_KEYWORDS is False`, public callables without `robot_name` and without `robot_not_keyword` | works (`forgot_decorator`, `helper`) |
  | `listener_method_exposed` | keyword name normalised ∈ listener v3 method names | works (`End Test` in a class with `ROBOT_LIBRARY_LISTENER = self`) |
  | `signature_lost` | args kinds exactly `[VAR_POSITIONAL, VAR_NAMED]` | works for a decorator without `functools.wraps` |
  | `union_with_str` | `arg.type.is_union` and `str` in `arg.type.nested` | works (`int \| str`) |
  | `untyped_argument` | `not arg.type` (a `TypeInfo` is always present; falsy when untyped) and `arg.required` | works after fixing a first attempt that tested `is None` |
  | `positional_only_argument` | kind `POSITIONAL_ONLY` (skip `POSITIONAL_ONLY_MARKER`) | works |
  | `output_during_import` | `print()` in `__init__` is captured by RF and emitted as an INFO message; `*WARN*` as WARN; `robot.api.logger.warn` outside a run writes straight to the real stderr | works with a registered logger, **except** the direct stderr write leaked onto the checker's stderr → drives D2 (child process) |
  | guard check | libdoc does not set `BuiltIn().robot_running`; guarded `print` never ran | confirmed |
  | `state_in_test_scope` | `ast` walk: `self.<attr>` assignments/augmented assignments in methods other than `__init__`, only when scope is `TEST` | works (`StateLib.incr`) |
  | dynamic API | `get_keyword_names`/`run_keyword` library loads, keywords listed; source may be unknown | works; method checks must be skipped |
  | async keyword | `async def` module function listed normally | works |

  The prototype output for a library with 4 findings was about 1.3 KB.
  - RF `LOGGER` replays cached messages to a newly registered logger. The checker registers once, per process, and reads messages from an index taken after registration. Running each library in its own child process (D2) avoids the issue altogether.
- **Eval spike.** Fixture suites were run on RF 7.4.2:
  - An `Inventory` library with `@library(scope="SUITE")` passes a 3-test suite with shared state. The same library with plain `@library` fails the third test.
  - `Literal["ON","OFF"]` accepts `on`. An `Enum` also accepts `on`, and `maybe` fails with "…Available: 'OFF' and 'ON'".
  - A v3 listener setting `result.status = "SKIP"` for failed `flaky` tests gives `robot` exit 0; without it the exit is 1.
- **Conventions this change must follow.**
  - Directory name = `name` = `rf-python-library` (`align-skill-names-with-spec`).
  - Script contract (`harden-skill-script-execution` D1–D6): `uv run python`, PEP 723, exit codes 0/1/2/3/4, `error:`/`hint:` stderr, bounded output, `--json-out`. MCP subprocess strategy and project-interpreter detection (D7).
  - Description template and companion catalogue (`sharpen-skill-descriptions` D1/D4).
  - Trigger-set format and task graders (`strengthen-skill-eval-harness` D6/D8).
  - JSON conventions from `rf-script-output`: one stable shape, keys present as `null` rather than absent, lean payloads.
- **RF User Guide on library scope** ("Creating test libraries" → "Library scope", read from the `master` sources on 2026-09-27). The UG says:
  - RF tries to keep tests independent, so by default (`ROBOT_LIBRARY_SCOPE` not set) it creates a new instance for every test (`TEST`); a suite setup/teardown shares yet another instance;
  - this is "not always desirable": tests sometimes need to share state, and stateless libraries do not need new instances at all;
  - `SUITE` creates one instance per suite; `GLOBAL` one instance for the whole run; module libraries are always global;
  - a library imported several times with different arguments gets a new instance each time, regardless of scope;
  - libraries with state in `SUITE` or `GLOBAL` scope should have a cleanup keyword for a suite setup/teardown (SeleniumLibrary: `GLOBAL` + `Close All Browsers`).
  - The UG lists only `TEST` (alias `TASK`), `SUITE` and `GLOBAL`. `SUITES` is a `VAR` scope (RF 7.1), not a library scope; the earlier draft of this change listed it as a library scope, which is corrected here.

## Goals / Non-Goals

**Goals:**
- One default way to write a library, with the escape hatches in references.
- Catch the silent RF-specific defects with a deterministic tool, so the agent does not depend on remembering the gotchas.
- Keep the skill small (≤ 300 lines in SKILL.md). The model already knows Python, so the text spends tokens only on RF behaviour.

**Non-Goals:**
- Remote libraries (XML-RPC server side): one paragraph in `api-variants.md`, no example.
- Generating library code from a spec, or scaffolding packages (no cookiecutter).
- Checking third-party installed libraries (rf-libdoc/robotcode libdoc already list their keywords).
- A linter for listener modules that are not libraries; the checker checks libraries only (a listener class used with `--listener` can still be loaded, see D4).
- Replacing Robocop or `robotcode analyze`. Both work on `.robot` data, not Python.

## Decisions

### D1. SKILL.md skeleton

```
---
name: rf-python-library
description: <D7>
compatibility: Python >= 3.10, robotframework>=7 in the project environment; uv recommended.
license / metadata: per align-skill-names-with-spec
---
# Robot Framework Python Library Skill
<3 lines: scope; boundary to rf-language and library skills>
## Quick reference and version gate      (python -c robot.__version__, not robot --version which exits 251; feature → min RF table)
## Default library template              (~35-line class: @library(scope=<from the scope table>, version=…), 2 @keyword methods,
                                          Enum/Literal hint, docstring, logger.info, AssertionError; state set in __init__ only)
## Decisions                             (module vs class | scope by state lifetime | static/hybrid/dynamic |
                                          which exception | which log call)
## Placement and import                  (libraries/ + python-path, Library Name, AS, deps via rf-setup)
## Agent workflow                        (numbered, D5)
## Gotchas                               (13 bullets, each "→ finding id" or "(not detected)")
## When to read the references           (Read | When)
## Companion Skills
```

Scope follows the RF User Guide (user decision 3, 2026-09-27; see Context). The template does **not** force `SUITE`. It writes the scope explicitly, as `scope="TEST"` (the UG default that keeps tests independent) with an inline comment "pick by state lifetime — see the scope table", so the decision stays visible. The template keeps state only in `__init__`, so it checks clean in any scope. The scope table, taken from the UG, is:

| State must live … | Scope | Note |
|---|---|---|
| per test, or must not leak between tests | `TEST` (default) | new instance per test; suite setup/teardown share another |
| across the tests of one suite (client, connection, accumulated data) | `SUITE` | add a cleanup keyword for suite setup/teardown |
| across suites for the whole run (one browser/session) | `GLOBAL` | add a cleanup keyword; module libraries are always global |
| no state at all | any; `GLOBAL` avoids needless instances | the UG notes stateless libraries do not need new instances |

Plus the UG note that importing a library with different arguments creates a new instance regardless of scope (`AS` for the names). The agent picks the row that matches how long the library's state must live. The eval-1 bug class (state lost between tests because the default `TEST` scope was kept) is covered by this table and by the `state_in_test_scope` finding, not by a forced default.

- *Alternative:* default template with `SUITE` (the earlier draft). Rejected by the user: it contradicts the UG's default of test independence and makes every library share state even when it should not.
- *Alternative:* a template without an explicit scope. Rejected, because it hides the decision.

Section names differ slightly from `restructure-library-skills` D1 ("Import and defaults" → "Default library template"). This skill teaches authoring, not using a library. The Gotchas, workflow, reference table and Companion Skills headings are the same, so shared tests can check them.

### D2. Checker loads each library in a child process

`check_library.py` is both the front end and the worker. The parent validates arguments, then for each input runs `subprocess.run([sys.executable, __file__, "--_worker", <input>, …], capture_output=True, timeout=--timeout)`. The worker writes its JSON result to a temp file, and the parent treats all raw worker stdout/stderr as `output_during_import` text.
- Why: the spike showed that `robot.api.logger.warn` outside a run writes directly to the real stderr, which would break the "diagnostics only as `error:/warning:/hint:`" rule. A hung `__init__` (network connect) would hang the agent's Bash call. A crash (`os._exit`, segfault in a native extension) would kill the checker. The child process isolates all three and gives a portable timeout (no `signal.alarm`, which is POSIX-only).
- Each child is a fresh interpreter, so `LOGGER` message replay, `sys.modules` caching and `sys.path` changes never leak between libraries.
- Cost: about 150–300 ms interpreter plus RF import per library. That is acceptable for a checker run a few times per task.
- *Alternative:* in-process with `contextlib.redirect_stdout` → misses direct writes and gives no timeout. *Alternative:* `multiprocessing` → pickling and spawn differences across platforms; plain subprocess is simpler.

### D3. Inputs, python-path and project root

- Positional inputs: a `.py` file, a package directory, or a dotted import name (`Inventory`, `mylibs.client.Client`). Paths use libdoc's own `Name::arg1::arg2` syntax internally; the CLI takes `--init-arg VALUE` (repeatable, applies to a single input) so shell quoting stays simple.
- `--pythonpath DIR` (repeatable). Default: `libraries/` and `resources/` if they exist, plus the input file's directory. This matches rf-setup's `python-path = ["resources", "libraries"]`.
- `--project-root` (default CWD). Every input path, resolved import origin (via `importlib.util.find_spec` in the worker **before** executing the module) and python-path entry must be inside it; otherwise exit 4 without importing. Why: the tool exists for the user's own library code; refusing paths elsewhere keeps an agent from "checking" (executing) arbitrary downloaded files, and keeps site-packages out of scope (rf-libdoc covers those).
- Name inputs that resolve to site-packages are refused with a hint to use rf-libdoc.

### D4. Detection details

- Findings table and ids: see spec ("Library checker detects library defects"). Ids are part of the contract; messages are not.
- **API style**: `dynamic` if the library object has `get_keyword_names` and `run_keyword`; `hybrid` if only `get_keyword_names`; otherwise `static`. The object is the class for class libraries and the module for module libraries.
- **Library class selection** mirrors RF: a class with the module's name, otherwise (RF ≥ 7.2) the single `@library`-decorated class in the module. Module libraries skip the class-based checks.
- **Listener awareness**: method names of listener API v3 (`start_suite`, `end_suite`, `start_test`, `end_test`, `start_keyword`, `end_keyword`, the `start_/end_` body-item methods, `log_message`, `message`, `library_import`, `resource_import`, `variables_import`, `output_file`, `log_file`, `report_file`, `xunit_file`, `debug_file`, `close`). If the class declares a listener (`@library(listener=…)` or `ROBOT_LIBRARY_LISTENER`), public listener methods are excluded from `public_method_not_keyword`. If such a method *is* a keyword, `listener_method_exposed` fires.
- **`state_in_test_scope`** is a heuristic (AST, no execution). Assignments in `__init__` or in helpers named `_…` are ignored; one finding per method. False positives (a method that intentionally keeps per-test state) are acceptable at `warning`. The hint states the UG rule: if the state must survive between tests choose `SUITE` or `GLOBAL` with a cleanup keyword; if per-test state is intended, set `scope="TEST"` explicitly to silence this. (As implemented, the explicit scope does not silence it; see Implementation Notes.)
- **`broad_except`**: an `except`/`except Exception`/`except BaseException` handler in a keyword method or function whose body has no `raise`. Severity `info`, because it is legitimate when the handler re-raises through a helper. The hint names `robot.errors.TimeoutExceeded` (RF ≥ 7.3; `TimeoutError` before).
- **`output_during_import`**: the worker registers a logger on `robot.output.LOGGER`. It counts non-internal messages (anything not starting with RF's "Imported library", "Created keyword", "In library", "Error in library") at INFO or above, plus raw stdout/stderr captured by the parent. Text is truncated to 300 chars per finding and at most 5 findings.
- Not detected (documented as such in Gotchas): lenient implicit typing (6), `bool` pass-through (7), thread logging (10), duplicate imports with different arguments (13, lives in `.robot` data).

### D5. Agent workflow text

1. `uv run python -c "import robot; print(robot.__version__)"` (not `robot --version`, which exits 251 even on success) → pick features from the gate table.
2. Write the library in `libraries/<Name>.py` from the template.
3. `uv run python scripts/check_library.py libraries/<Name>.py` → fix every `error`/`warning`, or state why it stays. (Safety line: "runs the library's import and `__init__`; use it on project code only.")
4. `robotcode libdoc libraries/<Name>.py list` (or rf-libdoc) → the keyword names the tests will call.
5. pytest for pure logic (optional, when the library has non-trivial Python logic).
6. `uv run robot --dryrun --pythonpath libraries tests/…` (dry-run blind spots listed).
7. `uv run robot --pythonpath libraries --outputdir results tests/…`; on failure add `--loglevel DEBUG` for tracebacks and read results with rf-robotcode/rf-results.
8. Fix → back to 3.

Paths are written in the root form (`scripts/…`, relative to the skill directory) and rewritten per channel by sync, as `harden-skill-script-execution` D2 defines.

### D6. JSON schema (schema_version 1)

```json
{
  "schema_version": 1,
  "robot_version": "7.4.2",
  "libraries": [
    {
      "input": "libraries/Inventory.py",
      "library": {"name": "Inventory", "source": "/abs/libraries/Inventory.py", "scope": "SUITE",
                  "version": "1.0", "doc_format": "ROBOT", "api": "static", "has_doc": true,
                  "keyword_count": 2, "init_args": []},
      "keywords": [{"name": "Add Item", "args": ["name: str", "qty: int"], "lineno": 12, "has_doc": true}],
      "findings": [{"id": "state_in_test_scope", "severity": "warning", "keyword": "add_item",
                    "message": "…", "hint": "…"}],
      "omitted": {"keywords": 0, "findings": 0}
    }
  ],
  "summary": {"libraries": 1, "loaded": 1, "error": 0, "warning": 1, "info": 0}
}
```

- `library` is `null` when loading failed, with `keywords: []` and the `import_failed` finding.
- `hint` is always present (it may be `null`); `keyword` is `null` for library-level findings.
- `args` use RF's own string form (`qty: int`, `n=3`, `*args`), which is what libdoc shows the user.
- Bounds: `--max-keywords` 100 and `--max-findings` 50 per library, messages ≤ 300 characters. With 10 libraries the worst case is ~40 KB; a typical run is 1–3 KB (spike).
- Exit codes: see spec. Import failures of *some* inputs keep exit 0, consistent with "partial source failures" in harden D4, and the JSON carries them. Exit 4 when *all* inputs failed, again as rf_libdoc does.

### D7. Description (draft, ~560 chars)

"Creates and reviews Robot Framework keyword libraries and listeners in Python: module vs class libraries, @library/@keyword/@not_keyword, scope (TEST/SUITE/GLOBAL) and init arguments, type-hint conversion (Enum, Literal, TypedDict, custom converters), embedded-argument keywords, failures and logging with robot.api, async, dynamic/hybrid APIs, listener v3 and libdoc docs. Use when writing or fixing a Python library or listener, or when a library 'contains no keywords' or state resets between tests. For .robot/.resource keywords and tests use rf-language; for using an existing library use its skill."

Tuned against the train split under `sharpen-skill-descriptions` D6 rules (≤ 1024 chars, warn > 500). If rf-language is not shipped when this lands, the boundary sentence reads "For keywords in .robot/.resource files, write them directly (no Python needed)" and task 7.3 updates it.

Companion Skills rows (catalogue keys from sharpen D4, plus one new key this change contributes):

| Key | Need | Skill |
|---|---|---|
| python-library (new) | Write or fix a Python keyword library or listener | `rf-python-library` |

Required rows for rf-python-library: setup, libdoc, results, robotcode, and `language` (the catalogue key added by `add-rf-language-skill`). rf-setup gains the `python-library` row as optional.

### D8. MCP tool `rf_check_library`

> As implemented, the server falls back to its own interpreter (still a subprocess) when no project environment is found; see Implementation Notes.

- Input schema: `libraries: string[]` (required), `init_args: string[]`, `pythonpath: string[]`, `max_keywords`, `max_findings`, `timeout`.
- Always runs as a subprocess, using the project-interpreter detection from harden D7 (uv → `.venv` → `$VIRTUAL_ENV`). There is **no** in-process path. The rf_libdoc tools import installed third-party packages, whereas this tool executes code the agent is editing right now. Importing it into the long-lived server would cache stale modules after each edit, pollute `sys.path` and run side effects inside the server.
- Project root = the server CWD (Claude Code starts it in the project root).
- Why expose it at all: the plugin's subagents (`rf-keyword-consultant`, `rf-debug-expert`) use MCP tools instead of script paths (harden D2). Without the tool they could not run the checker.
- *Alternative:* no MCP tool, script only. Rejected for the subagent reason; the added code is ~40 lines on the existing subprocess path.

### D9. Examples and CI

`assets/examples/`:
- `ExampleLibrary.py`: the template in use for a counter/inventory whose state the example suite's tests share, so, per the scope table, it uses `SUITE` scope with a cleanup keyword (the UG's own `ExampleLibrary` pattern), plus `Literal` mode and `robot.api.logger`.
- `converters.py`: a `Money` type with a `ValueError`-raising converter and a keyword that takes it.
- `ResultListener.py`: a listener v3 that records failed tests and writes a summary JSON at `close`. It writes to `${OUTPUT DIR}`, so no network or Slack is needed. A comment explains how to swap in a webhook.
- `example_library.robot`, `converters.robot`, `listener.robot`: they run offline in < 5 s.

CI step (in the existing `test` job, RF already installed): `robot --pythonpath skills/rf-python-library/assets/examples --outputdir $RUNNER_TEMP/pylib skills/rf-python-library/assets/examples/*.robot`, then the checker on the three `.py` files with a jq-free pytest assertion (`tests/test_python_library_skill.py::test_examples_clean`). Listener suite runs with `--listener ResultListener`.

### D10. Tests

- `tests/test_python_library_skill.py`, structural:
  - frontmatter, `compatibility` and size;
  - section order;
  - 13 Gotchas bullets and finding ids that exist in the checker's id list;
  - the reference table matches `references/*`;
  - Companion Skills names resolve;
  - the hook names the skill;
  - the channel copies exist and are regular files;
  - the examples run (`robot` via `subprocess`) and are clean under the checker.
- `tests/test_check_library.py`, behavioural:
  - one fixture library per finding id under `tests/fixtures/python_library/` (the spike's 17 libs, curated);
  - exit codes 0/2/3/4, with 3 tested via a throwaway venv without RF, as harden D9 does;
  - empty stdout on failure;
  - the outside-root refusal;
  - a timeout with a sleeping `__init__` and `--timeout 2`;
  - no raw library output on the checker's stdout or stderr;
  - bounds and `omitted`;
  - `--json-out`;
  - `--help` ends with examples;
  - PEP 723 block present.
- MCP: `tests/test_mcp_server.py` (or the existing server tests) calls `rf_check_library` on a fixture, asserts equality with the script output, and asserts that the fixture module is not in `sys.modules`.

### D11. Eval tasks and fixture

> As implemented, the grading suites are hidden (`eval/graders/python-library/`) and the reference solutions are golden overlays in `tests/eval/golden/`; see Implementation Notes.

- Fixture `eval/fixtures/sut-pylib/`: `pyproject.toml` (`robotframework>=7`), `robot.toml` with `python-path = ["libraries"]`, an empty `libraries/`, a `grading/` folder with the three grading suites, and a README. The graders run `robot --pythonpath libraries grading/<suite>.robot`. The grading suites are visible to the agent. That is acceptable because they state the required behaviour (state survives, `on` is accepted, flaky becomes SKIP) without revealing the fix (scope, `Literal`/`Enum`, listener API). Each prompt names the file to create (`libraries/Inventory.py`, `libraries/Modes.py`, `libraries/FlakySkip.py`) so the graders can import it.
- Tasks (narrow tier, so Haiku by the harness D7 default):
  1. `narrow-python-library-inventory-scope-01`: gating `robot_pass` on `grading/inventory.robot` (3 tests, shared state). Non-gating: `file_contains` regex `scope\s*=\s*["'](SUITE|GLOBAL)|ROBOT_LIBRARY_SCOPE` (either `SUITE` or `GLOBAL` is a correct choice by state lifetime; the task tests that the agent leaves the default `TEST` scope when state must span tests), and a `command_json` / script check that `check_library.py` reports no `leaked_keyword`. If the harness has no generic command check, the check is a `file_not_contains` `^from \w+ import` regex fallback. This is an open item for the harness change (see Open Questions).
  2. `narrow-python-library-mode-literal-01`: gating `robot_pass` on `grading/mode.robot` (`Set Mode    on` passes and returns `ON`; `Run Keyword And Expect Error    *ON*    Set Mode    maybe`). Non-gating: `file_contains` regex `Literal\[|\(Enum\)|Enum\b`.
  3. `narrow-python-library-flaky-listener-01`: gating `robot_pass` on `robot --pythonpath libraries --listener FlakySkip grading/flaky.robot` (exit 0 only when the flaky failure became SKIP). Non-gating: an `output_xml` status check (flaky test SKIP, other PASS) if the harness supports it, else `file_contains` on `output.xml` `status="SKIP"`, plus `file_contains` regex `def end_test\(self,\s*data,\s*result`.
- Prompts do not name the scope, `Literal` or listener API version, so the tasks measure the skill and not the prompt. Baseline arm (no plugin) runs are expected to fail task 1 often (the spike shows the default fails).

### D12. Trigger set (draft)

Should-trigger (train): "write a python keyword library for our REST client"; "my library imports but Robot says it contains no keywords"; "how do I make a keyword argument an enum in my Robot library"; "the counter in my Python library resets every test"; "create a robot framework listener that posts results to Slack". Validation: "add @keyword decorators to libraries/db_helpers.py so Robot can use them"; "Join shows up as a keyword from my library, why?"; "write libdoc docs for our custom Robot library and version it".
Should-not-trigger (train): "write a keyword in a .resource file that logs in" (rf-language); "use RequestsLibrary to call an API" (rf-requests); "install robotframework-browser" (rf-setup); "write a pytest fixture that yields a database connection" (non-RF); "call a Python expression inline in my test" (rf-language: `${{ }}`/Evaluate). Validation: "debug a failing test at the breakpoint" (rf-robotcode); "what arguments does Browser's Click take" (rf-libdoc); "write a Flask route that returns JSON" (non-RF).
The final set has ≥ 8 of each polarity, as the spec requires. Queries that fit both this skill and rf-language (for example "should this be a Python keyword or a user keyword?") are not used as should-not-trigger for either.

## Risks / Trade-offs

- [The checker executes user code] → it runs in a child process with a timeout, only on inputs inside the project root, and makes no network calls of its own. The skill text states this. Libdoc leaves `robot_running` false, so guarded side effects stay off. Unguarded ones (a DB connect in `__init__`) do run; that is the same exposure as `robot --dryrun` or `libdoc`, which the user already runs.
- [Heuristic false positives (`state_in_test_scope`, `broad_except`)] → severities are warning/info, the hints explain how to silence them, and exit codes never depend on findings.
- [RF internals (`LOGGER.register_logger`, `TypeInfo.is_union`) change between versions] → the worker uses only libdoc's public model plus `robot.output.LOGGER`. The tests run on the RF version in CI. A `ROBOT_VERSION` gate turns an AttributeError into an `internal` finding instead of a crash.
- [Boundary with rf-language is fuzzy ("Python or user keyword?")] → the ambiguity rule in D12, plus one sentence in both skills: "logic → Python library, composition of existing keywords → user keyword".
- [Sibling changes not merged yet] → Ordering in proposal. The rf-language name is guarded by D7's fallback sentence.
- [Child-process overhead on many libraries] → linear, ~0.3 s per library. Checking `libraries/*.py` in a large project with 30 libraries costs ~10 s, which is acceptable for an explicit check step.

## Migration Plan

Additive. Land after the ordering prerequisites in proposal.md. Rollback removes `skills/rf-python-library/` and re-runs sync; the MCP tool and hook entry are removed in the same revert. Installer users get the skill on the next `install`, and uninstall removes it through the manifest.

## Open Questions

- Does the eval harness get a generic "command exit/JSON" check type for task 1's "no `leaked_keyword`" assertion, or does this change keep the regex fallback? This does not change the gating check (robot_pass) and can be settled when `strengthen-skill-eval-harness` is implemented.
- Should the checker later accept `--listener`-only classes (not libraries) with a listener-specific finding set? Deferred; the current example listener is also loadable as a library for docs.

## Implementation Notes

- **Adapted to the ten archived changes.** Paths are `skills/rf-python-library/` in every channel (dir = `name`); the plugin rewrites `uv run python scripts/check_library.py` to `"${CLAUDE_SKILL_DIR}/scripts/check_library.py"` (harden D2); frontmatter carries `license`, `compatibility` ("Python 3.10+ … robotframework>=7", equal to the script's `requires-python = ">=3.10"`) and `metadata.version "2.0.0"`; the Companion Skills rows are the catalogue rows verbatim. The script-skill tables in `tests/test_skill_commands.py` (`SCRIPT_SKILLS`, `RF_CODE_SKILLS`) and `tests/test_script_execution.py` (`SCRIPTS`, `VALID_ARGS`) include the new script; `test_skill_commands.FENCE` now pairs every fenced block (```python/```toml blocks used to shift the pairing) and counts only shell blocks.
- **Scope follows the RF User Guide (user decision 3).** The template writes `@library(scope="TEST", version=…)` with a "pick it by how long the library state must live (scope table below)" comment; state only in `__init__`, so it checks clean. The scope table lists TEST/SUITE/GLOBAL only and names the cleanup-keyword rule; the example library is `SUITE` with `Clear Inventory` because its suite shares state.
- **D4 change: an explicit `scope="TEST"` does not silence `state_in_test_scope`.** D4 proposed silencing the heuristic when TEST is set explicitly, but D1 makes the template write `scope="TEST"` explicitly, so every template-derived library would have lost the warning that catches the eval-1 bug class. The warning stays (severity warning, heuristic); its hint says to keep TEST and say so when per-test state is intended, as the workflow step "fix every error/warning, or state why it stays" allows. The heuristic also counts item assignments (`self._stock[name] = …`, the naive Inventory) and skips `_private` helpers; mutating method calls (`self.items.append`) are not detected.
- **Checker details decided during implementation.**
  - Names are resolved in the parent with `importlib.machinery.PathFinder` over the `--pythonpath` entries only (no parent-package import), so a refused name never executes code; names found only outside the root (stdlib, site-packages) exit 4 with an rf-libdoc hint.
  - libdoc substitutes "Documentation for library ``X``." when a library has no docstring; `has_doc`/`library_doc_missing` detect that placeholder.
  - `union_with_str` ignores `str | None` (a "text or nothing" argument), and fires only when another converting type is in the union.
  - `leaked_keyword` for hybrid/dynamic libraries fires only when the keyword source is known and outside the project root (PythonLibCore components live in other project files); static libraries compare against the library file, or the package directory for package libraries.
  - `summary` counts every finding found, including those cut by `--max-findings` (`omitted` says how many are not listed). An extra id `internal` (info) records a check that failed on an RF API difference instead of crashing.
  - `--pretty` was added (as in rf_conventions); default output is compact JSON. Messages are ASCII-truncated (`...`) so Windows consoles never see a non-cp1252 character.
  - The child runs with `PYTHONDONTWRITEBYTECODE=1`, so checking a library leaves no `__pycache__` (tested: the project tree is unchanged after a run).
- **Spike re-run (task 1.2) on RF 7.0.1/7.1.1/7.2.2/7.3.2/7.4.2/7.5.** Same findings on every version except: `Take ${qty: int} pears` is rejected (→ `keyword_creation_failed` + `no_keywords`) only on RF 7.3+; on 7.0–7.2 the keyword loads but `: int` is read as an embedded regex (" int"), so `Take 3 pears` never matches (verified with a suite on 7.2.2). Gotcha 4 and api-variants.md say so. `@library` class selection in a module with another name needs 7.2 (on 7.1.1 the suite warns "contains no keywords"); the checker mirrors that gate.
- **Verified facts used in the text** (RF 7.4.2 unless noted): implicit typing `def kw(n=3)` passes `abc` through; `flag: bool` passes `maybe` through; `logger` calls from another thread are dropped; `a=1` to a positional-only `a` arrives as the string `a=1`; a second import with other arguments is ignored with "has already imported library … with different arguments. This import is ignored."; `Run Keyword And Expect Error` does not catch `SkipExecution`; exception names are hidden for AssertionError/RuntimeError/Exception and shown for others; a listener exception is reported ("Calling method 'end_test' of listener … failed") and the run continues; `robot.errors.TimeoutExceeded` exists from 7.3 (`TimeoutError` alias; before 7.3 `TimeoutError` only) and derives from `BaseException` only from 7.5 — a swallowing retry loop ran 4.4 s with a 1 s timeout on 7.4.2 and 1.5 s on 7.5; `Secret` lives in `robot.api.types` from 7.4 and a literal string is rejected, `${X: Secret}    %{ENV}` works; `object` hints (7.4) mean "no conversion"; the MARKDOWN doc format is rejected by 7.4.2 and needs the `markdown` package on 7.5; `ROBOT_LISTENER_PRIORITY` exists from 7.1; `dry_run_active` exists in 6.1.
- **Code blocks are complete files.** Every ```python block in SKILL.md and the references starts with `# file: <Name>.py` and loads clean under the checker, or produces exactly the ids on its `# Wrong: …` line; `# check: skip` marks the listener-only and pytest modules; ```robotframework blocks with `# file:` run with `robot` next to the Python blocks of the same document (`# run: --listener X` adds options; `# RF 7.4+` blocks skip on older RF). `tests/test_python_library_skill.py` enforces this.
- **Examples (D9).** `ResultListener.py` is a listener v3 used with `--listener ResultListener` that is also a clean library (`@library(scope="GLOBAL", listener="SELF")` with a `Result Summary` keyword), so the checker can load all three example files without `listener_method_exposed` (resolves D4's open question for the example). `converters.py` is a module library with `ROBOT_AUTO_KEYWORDS = False` so `dataclass`/`Decimal` do not leak. The suites pass on RF 7.0.1, 7.4.2 and 7.5.
- **MCP (D8).** `rf_check_library` always runs the checker as a subprocess with the project interpreter (uv → `.venv` → `$VIRTUAL_ENV`); when none is found but the server's own interpreter has RF ≥ 7, that interpreter runs it — still as a subprocess, never in-process. The subprocess budget is `timeout × libraries + 30 s` (at least 120 s).
- **Evals adapted to the harness conventions (D11).** The grading suites are hidden (`eval/graders/python-library/`, never staged), not visible `grading/` files in the fixture, and the reference/naive solutions live as golden overlays in `tests/eval/golden/<task>/{good,bad}` instead of `eval/fixtures/sut-pylib/.reference/`, exactly as `add-rf-language-skill` did. The custom module is `rf_skill_eval.scoring.custom.python_library` (`hidden_suite`: `listener`, `expected_rc`, `expected_statuses`, `expected_tests`; `checker_findings_absent`). This also settles the Open Question: the "no `leaked_keyword`" check is `checker_findings_absent` (non-gating; also `state_in_test_scope`, `no_keywords`). The inventory grader has five tests (three that share state, a wrong count, `Clear Inventory`); the listener task has a second gating run (`flaky_real_failure.robot`: an untagged failure stays FAIL, exit 1) so a listener that hides every failure fails; the `end_test` file check also accepts a module-level `def end_test(data, result)`.
- **Hook.** New line "Python libraries: rf-python-library (…)"; regex terms `@keyword`, `robot.api.deco`, `ROBOT_LIBRARY_*`/`ROBOT_LISTENER_*`, "contains no keywords", "robot listener", "listener API". Bare "listener" is not a trigger (negative case "Add an event listener in JavaScript …").
- **Cross-links.** rf-language's description and intro name rf-python-library and its Companion table has the `python-library` row (kept at 300 lines by merging one dry-run bullet); rf-setup gets an optional row and the `project-layout.md` pointer; rf-keyword-consultant, rf-debug-expert (and a routing row in rf-test-architect) mention `rf_check_library`.
- **Deferred (live runs):** 6.4 — not run per the release-cycle rules.
