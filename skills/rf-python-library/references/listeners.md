# Listeners

A listener is a Python class or module whose methods Robot Framework calls
while a run progresses. Listener API version 3 (the default from RF 7.0)
passes the running data and result model objects, so a listener can read and
change them. Examples need RF 7.0+ unless a block says otherwise.

- [Listener API v3 methods](#listener-api-v3-methods)
- [Registering a listener](#registering-a-listener)
- [A library that is also a listener](#a-library-that-is-also-a-listener)
- [Priority](#priority)
- [Changing results](#changing-results)
- [Rules of thumb](#rules-of-thumb)

## Listener API v3 methods

| Method | Called |
|---|---|
| `start_suite(data, result)` / `end_suite(data, result)` | around each suite; `start_suite` may modify `data` (add or filter tests) |
| `start_test(data, result)` / `end_test(data, result)` | around each test; `end_test` may change `result.status` and `result.message` |
| `start_keyword(data, result)` / `end_keyword(data, result)` | around every keyword and control structure (RF 7.0+; also `start_library_keyword`, `start_user_keyword`, `start_for`, …) |
| `log_message(message)` / `message(message)` | a log message / a system message |
| `library_import`, `resource_import`, `variables_import` | after an import |
| `output_file(path)`, `log_file`, `report_file`, `xunit_file`, `debug_file` | when an output file is written |
| `close()` | once at the end (for a library listener: when the library goes out of scope) |

Every method is optional; implement only the ones you need. Version 2
listeners (name and attribute-dict arguments) still work with
`ROBOT_LISTENER_API_VERSION = 2`, but new code uses version 3.

## Registering a listener

On the command line, by module or class name on the python-path (or a file
path). Arguments follow after colons and reach `__init__` as strings:

```bash
uv run robot --pythonpath libraries --listener ResultListener tests/
uv run robot --pythonpath libraries --listener ResultListener:summary.json tests/
```

In `robot.toml` the same goes into `listeners = ["ResultListener:summary.json"]`.
`assets/examples/ResultListener.py` is a complete listener that writes a JSON
summary into the output directory at `close`.

## A library that is also a listener

`@library(listener="SELF")` (or `ROBOT_LIBRARY_LISTENER = self` in `__init__`)
makes the library instance a listener for the suites that import it. With
`@library`, listener methods such as `end_test` do not become keywords, and
the checker does not flag them. Without `@library` they are keywords (checker:
`listener_method_exposed`).

```python
# file: Timing.py
"""Library listener: records test durations of the importing suite."""

from robot.api.deco import keyword, library


@library(scope="SUITE", listener="SELF")
class Timing:
    """Collects the duration of each finished test."""

    def __init__(self) -> None:
        self._durations: dict[str, float] = {}

    def end_test(self, data, result) -> None:
        self._durations[result.name] = result.elapsed_time.total_seconds()

    @keyword
    def finished_test_count(self) -> int:
        """Number of tests of this suite that have finished so far."""
        return len(self._durations)
```

```robotframework
# file: timing.robot
*** Settings ***
Library    Timing


*** Test Cases ***
First
    No Operation

Second Sees The First As Finished
    ${count}=    Finished Test Count
    Should Be Equal    ${count}    ${1}
```

## Priority

With several listeners, `ROBOT_LISTENER_PRIORITY = <number>` (RF 7.1+) orders
them: higher numbers are called first for every event. Without it, listeners
run in the order they were registered.

## Changing results

In `end_test`, set `result.status` to `"PASS"`, `"FAIL"` or `"SKIP"` and
adjust `result.message`; the change reaches `output.xml`, the log, the report
and the exit code (skipped tests do not fail the run). Keep such rules narrow
and explicit, for example driven by a tag, and say in the message why the
status changed.

```python
# file: KnownIssues.py
# check: skip (a listener, not a library)
"""Listener: failing tests tagged known-issue are reported as SKIP."""


class KnownIssues:
    """Turns failures of tests tagged ``known-issue`` into skips."""

    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self, tag: str = "known-issue") -> None:
        self._tag = tag

    def end_test(self, data, result) -> None:
        if result.failed and self._tag in result.tags:
            result.message = f"Skipped by KnownIssues ({self._tag}): {result.message}"
            result.status = "SKIP"
```

```robotframework
# file: known_issues.robot
# run: --listener KnownIssues
*** Test Cases ***
Tracked Bug
    [Tags]    known-issue
    Fail    Ticket 123 is not fixed yet

Healthy Feature
    Should Be Equal    ${{ 2 * 2 }}    ${4}
```

With the listener the run exits 0 (1 passed, 1 skipped); without it, 1.
`KnownIssues` is a listener, not a library: its listener methods would be
keywords if it were imported with `Library`.

## Rules of thumb

- Keep listener methods fast; they run for every test or keyword.
- Do not raise from a listener: RF reports the error and continues, but the
  change you wanted is lost.
- Use `robot.api.logger` from listener methods only in the main thread.
- `start_keyword` / `end_keyword` fire for every keyword, including BuiltIn
  ones; filter on `data.name` or `data.owner` early.
- A listener that posts to chat or a webhook reads the URL and token from
  environment variables, never from the repository.
