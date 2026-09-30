---
name: rf-python-library
description: "Use first, before exploring or answering, to write or fix Robot Framework keyword libraries or listeners in Python."
license: Apache-2.0
compatibility: "Requires Python 3.10+ with robotframework>=7 in the project environment for the bundled check_library script; guidance is version-gated from RF 6.1 to 7.5 and the examples need RF 7.0+."
metadata:
  author: manykarim
  version: "2.0.0"
---

# Robot Framework Python Library

Writing and fixing keyword libraries and listeners in Python: the default library shape, scope, argument conversion, failures, logging and the checks that catch Robot Framework-specific defects before a test runs.
Tests, user keywords and `.resource` files belong to rf-language; using an existing library (Browser, RequestsLibrary, …) belongs to that library's skill.
Rule of thumb: logic goes into Python, composition of existing keywords into a user keyword.

## When to use

Load this skill first, before exploring the project, reading or creating .py files, or answering from memory, when Robot Framework keywords, libraries or listeners are written in Python:

- a new keyword library (around an API, database or device client), `@keyword` and `@library` decorators;
- `ROBOT_LIBRARY_SCOPE` and state kept between tests (a library that loses its state, a connection scope);
- argument conversion from type hints (Enum, Literal, custom converters), failures and logging via `robot.api`, libdoc docs;
- a library that "contains no keywords";
- a listener that reacts to or reports results (chat, dashboards).

Not this skill: keywords in .robot/.resource files use `rf-language`; using an existing library such as Browser or RequestsLibrary uses its library skill.

## Quick reference and version gate

Check the version in the project environment first (`robot --version` exits 251 even on success):

```bash
uv run python -c "import robot; print(robot.__version__)"
```

| Feature | Min RF |
|---|---|
| `async def` keywords, `BuiltIn().dry_run_active` | 6.1 |
| `Literal` conversion, embedded plus normal arguments in one library keyword, listener API v3 as the default | 7.0 |
| `ROBOT_LISTENER_PRIORITY` | 7.1 |
| `@library` selects the decorated class in a module whose name differs | 7.2 |
| `robot.errors.TimeoutExceeded` (named `TimeoutError` before 7.3) | 7.3 |
| `Secret` (`robot.api.types`) and `object` type hints | 7.4 |
| Markdown doc format (`doc_format="MARKDOWN"`); RF timeouts no longer derive from `Exception` | 7.5 |

## Default library template

Save it as `libraries/<Name>.py`; the class name equals the file name.

```python
# file: MyLibrary.py
"""Keywords for <what the library does>."""

from enum import Enum

from robot.api import logger
from robot.api.deco import keyword, library


class Mode(Enum):
    ON = "ON"
    OFF = "OFF"


# scope: pick it by how long the library state must live (scope table below).
@library(scope="TEST", version="0.1.0")
class MyLibrary:
    """One-line summary: libdoc shows it as the library introduction.

    Import: ``Library    MyLibrary    timeout=5``.
    """

    def __init__(self, timeout: float = 5.0) -> None:
        self._timeout = timeout  # state is set here only

    @keyword
    def set_mode(self, mode: Mode) -> str:
        """Switch the mode; ``on`` and ``off`` are accepted case-insensitively.

        Args:
            mode: ``ON`` or ``OFF``.
        """
        logger.info(f"mode {mode.name}, timeout {self._timeout}")
        return mode.name

    @keyword
    def value_should_be(self, actual: int, expected: int) -> None:
        """Fail unless ``actual`` equals ``expected``."""
        if actual != expected:
            raise AssertionError(f"expected {expected}, got {actual}")
```

Why each part: `@library` turns off automatic discovery, so only `@keyword` methods become keywords; type hints drive argument conversion and libdoc; the docstring's first line is the short doc; `AssertionError` marks a verification failure; `robot.api.logger` writes to the log.

## Decisions

**Module or class**

| Library needs | Use |
|---|---|
| A few stateless functions | Module library; set `ROBOT_AUTO_KEYWORDS = False` and decorate keywords with `@keyword`, so imported names do not become keywords |
| State, init arguments, converters or a listener | Class library with `@library` (the template) |

**Library scope** (Robot Framework User Guide, "Creating test libraries" → "Library scope"). Choose by how long the state must live:

| State must live … | Scope | Note |
|---|---|---|
| per test, or must not leak between tests | `TEST` (default) | a new instance for every test keeps tests independent; suite setup and teardown share another instance |
| across the tests of one suite (client, connection, accumulated data) | `SUITE` | a new instance per suite; add a cleanup keyword (`Clear …`) for a suite setup or teardown |
| across suites for the whole run (one browser or session) | `GLOBAL` | one instance for the run; add a cleanup keyword (`Close All …`); module libraries are always global |
| no state at all | any; `GLOBAL` avoids needless instances | a stateless library does not need new instances |

Importing the same library with different arguments creates a new instance regardless of scope; give each import a name with `AS`.

**Static, hybrid or dynamic API**

| Situation | API |
|---|---|
| Normal library | Static: methods are keywords (the template) |
| Keyword names computed at runtime, implementations are real methods | Hybrid: `get_keyword_names` |
| Proxy to another tool or process, or keywords generated from a spec | Dynamic: `get_keyword_names` + `run_keyword`; PythonLibCore helps compose large libraries |

**Failures and logging**

| Want | Use |
|---|---|
| Verification failed | `AssertionError` (or `robot.api.Failure`) |
| Fail but continue the test | `robot.api.ContinuableFailure` |
| Mark the test skipped | `robot.api.SkipExecution` |
| Stop the whole run | `robot.api.FatalError` |
| Keyword used incorrectly | `ValueError` / `robot.api.Error` |
| Log for the report | `logger.info` / `logger.debug`; `html=True` for HTML; `logger.warn` for warnings |
| Show progress on the console | `logger.console` |

## Placement and import

Project libraries live in `libraries/` on the python-path that rf-setup's project layout defines, and are imported by name:

```toml
# robot.toml
python-path = ["resources", "libraries"]
```

```robotframework
*** Settings ***
Library    MyLibrary    timeout=10
Library    MyLibrary    timeout=60    AS    SlowLibrary
```

Plain `robot` needs `--pythonpath libraries`. Import by name, not by a relative `../libraries/X.py` path, so the same import works from every suite. Add third-party runtime dependencies with the project's tool (`uv add <package>`; see rf-setup).

## Agent workflow

1. Check the version: `uv run python -c "import robot; print(robot.__version__)"`, then use only features from the gate table.
2. Write or edit `libraries/<Name>.py` from the template; pick the scope from the scope table.
3. Run the checker and fix every `error` and `warning` finding (or state why one stays). It runs the library's import and `__init__` code, so use it on your own project libraries only:

   ```bash
   uv run python scripts/check_library.py libraries/<Name>.py
   ```

4. List the keyword names the tests will call: `robotcode libdoc libraries/<Name>.py list`, or the rf-libdoc skill.
5. Pure Python logic with branches gets pytest unit tests.
6. `uv run robot --dryrun --pythonpath libraries tests/`. Dry run misses variables, named-argument typos, embedded-argument mismatches and `str` in unions.
7. `uv run robot --pythonpath libraries --outputdir results tests/`; on failure rerun with `--loglevel DEBUG` for tracebacks and read the results with rf-robotcode (`robotcode results`) or rf-results.
8. Fix and go back to step 3.

The script path is relative to this skill's directory; library paths are relative to the project root. More checker calls:

```bash
uv run python scripts/check_library.py libraries/*.py --pretty
uv run python scripts/check_library.py Client --init-arg https://staging.example.com --pythonpath libraries
uv run python scripts/check_library.py libraries/Inventory.py --json-out results/check_library.json
```

Not using uv? Run the same commands with `.venv/bin/python` or `poetry run python` instead of `uv run python`; see rf-setup.

The JSON lists per library the scope, API style and keywords with arguments, plus findings (`id`, `severity`, `keyword`, `message`, `hint`), errors first. Exit 0 means checked (findings do not change it); 4 means the input is outside the project root or no library loaded (stderr has the error line and a hint); 3 means Robot Framework is missing from the interpreter.

## Gotchas

- `@library` disables automatic keyword discovery: a public method without `@keyword` is silently not a keyword (→ `public_method_not_keyword`); mark helpers `@not_keyword` or prefix them with `_`.
- Functions imported into a module library, and public base-class methods, become keywords: `from os.path import join` adds `Join` (→ `leaked_keyword`). Import modules (`import os`) or use `ROBOT_AUTO_KEYWORDS = False`.
- The default `TEST` scope creates a new instance for every test, by design, so tests stay independent: a counter or cache set in one test is gone in the next (→ `state_in_test_scope`). State that must span tests needs `SUITE` or `GLOBAL` plus a cleanup keyword. `__init__` also runs during libdoc and `--dryrun`, so it must not connect anywhere unguarded (→ `output_during_import`).
- An inline type in a library embedded-argument name, `@keyword("Take ${qty: int} pears")`, makes RF 7.3+ reject the keyword, and the library then "contains no keywords" (→ `keyword_creation_failed`, `no_keywords`; before 7.3, `: int` is read as a regex and the keyword never matches). Put the type on the Python argument: `def take(self, qty: int)`.
- A union that contains `str`, such as `int | str`, never converts a string argument: `"10"` stays a string (→ `union_with_str`). Drop `str` or convert explicitly.
- Implicit typing from defaults is lenient: `def kw(n=3)` passes `abc` through as a string (not detected). Use real type hints.
- `bool` conversion passes unknown strings through: `flag: bool` with `maybe` gives the string `maybe` (not detected). Use `Literal` or an `Enum` when only fixed values are valid.
- Positional-only arguments (`def kw(a, /)`) cannot be passed by name: `a=1` arrives as the string `a=1` (→ `positional_only_argument`).
- A broad `except Exception:` swallows Robot Framework timeouts before RF 7.5 (they derive from `Exception` until then) (→ `broad_except`). Catch specific exceptions, or re-raise `robot.errors.TimeoutExceeded`.
- Logging or raising from a non-main thread is silently dropped from the log (not detected). Collect results in the thread and log them from the keyword's own thread.
- A decorator without `functools.wraps` hides the signature: the keyword takes only `*args, **kwargs` and loses conversion (→ `signature_lost`). Add `@functools.wraps(func)` to the wrapper.
- Listener methods (`end_test`, `close`, …) on a class that is also a library become keywords unless the class uses `@library(listener="SELF")` (→ `listener_method_exposed`).
- Importing the same library twice with different arguments needs `AS` names, otherwise the second import is ignored with a warning (not detected; it lives in `.robot` data).

## When to read the references

| Read | When |
|---|---|
| `references/conversion.md` | Choosing argument types: built-ins, Enum, Literal, TypedDict, containers, unions, `Secret`, custom converters |
| `references/api-variants.md` | Module vs class details, scope and init arguments, embedded arguments, async, hybrid and dynamic APIs, PythonLibCore, Remote |
| `references/listeners.md` | Writing a listener (API v3), a library that is also a listener, listener priority, changing results |
| `references/communication.md` | Exceptions, HTML messages, logging levels, threads, timeouts, calling BuiltIn from a library |
| `references/packaging-and-docs.md` | libdoc output, doc formats, versioning, packaging a library with resources, tests for a library |

The runnable examples in `assets/examples/` (`ExampleLibrary.py`, `converters.py`, `ResultListener.py` and their suites) pass with `uv run robot --pythonpath assets/examples --listener ResultListener assets/examples`.

## Companion Skills

| Need | Skill |
|------|-------|
| Write tests, suites, user keywords, resources and variables in Robot Framework syntax | `rf-language` |
| Install Robot Framework or a library, fix the environment | `rf-setup` |
| Look up keyword names, arguments and docs | `rf-libdoc` (or `rf-robotcode`: `robotcode libdoc`) |
| Analyze output.xml results | `rf-results` (or `rf-robotcode`: `robotcode results`) |
| Discover, run, debug and statically check with the robotcode CLI | `rf-robotcode` |
