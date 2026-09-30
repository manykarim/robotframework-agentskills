# Failures, logging and talking to Robot Framework

How a library reports failures, writes to the log and console, handles
threads and timeouts, and reaches Robot Framework itself. Examples need RF
7.0+ unless a block says otherwise.

- [Exceptions](#exceptions)
- [Exception names and HTML messages](#exception-names-and-html-messages)
- [Logging](#logging)
- [Threads](#threads)
- [Timeouts](#timeouts)
- [Using BuiltIn from a library](#using-builtin-from-a-library)

## Exceptions

A keyword fails by raising. The exception class decides what happens next:

| Raise | Effect |
|---|---|
| `AssertionError` / `robot.api.Failure` | the test fails (verification failed) |
| `robot.api.ContinuableFailure` | the failure is recorded, the test continues and fails at the end |
| `robot.api.SkipExecution` | the test is marked SKIP |
| `robot.api.FatalError` | the test fails and all remaining tests fail without running |
| `ValueError` / `TypeError` / `robot.api.Error` | the keyword was used incorrectly (bad arguments, wrong state) |
| any other exception | the test fails with the exception's message |

`Failure` is an `AssertionError`, `Error` a `RuntimeError`; the `robot.api`
classes add HTML support and consistent names. `Run Keyword And Expect Error`
catches failures and errors, but not `SkipExecution` (the test is skipped),
`FatalError` or timeouts.

```python
# file: Checks.py
"""Failure classes from robot.api."""

from robot.api import ContinuableFailure, SkipExecution
from robot.api.deco import keyword, library


@library(scope="GLOBAL")
class Checks:
    """Verification keywords."""

    @keyword
    def values_should_match(self, actual: int, expected: int) -> None:
        """Fail unless the values are equal."""
        if actual != expected:
            raise AssertionError(f"expected {expected}, got {actual}")

    @keyword
    def soft_check(self, actual: int, expected: int) -> None:
        """Record a mismatch and let the test continue."""
        if actual != expected:
            raise ContinuableFailure(f"soft check: expected {expected}, got {actual}")

    @keyword
    def require_feature(self, enabled: bool) -> None:
        """Skip the test when the feature is disabled."""
        if not enabled:
            raise SkipExecution("feature disabled in this environment")
```

```robotframework
# file: checks.robot
*** Settings ***
Library    Checks


*** Test Cases ***
Hard Failure Message
    Run Keyword And Expect Error    expected 2, got 1    Values Should Match    1    2

Feature Gate Skips
    Require Feature    no
    Fail    not reached
```

## Exception names and HTML messages

RF shows the message alone for `AssertionError`, `RuntimeError`, `Exception`
and the `robot.api` classes; other exceptions are prefixed with their class
name (`ValueError: …`). A custom exception class hides its name with
`ROBOT_SUPPRESS_NAME = True`. A message starting with `*HTML*` is rendered as
HTML in the log and report (escape any user data you put into it).

```python
# file: Orders.py
"""Custom exception without the class name in the message."""

from robot.api.deco import keyword, library


class OrderRejected(Exception):
    ROBOT_SUPPRESS_NAME = True


@library(scope="GLOBAL")
class Orders:
    """Order keywords."""

    @keyword
    def submit_order(self, quantity: int) -> int:
        """Submit an order; quantities over 10 are rejected."""
        if quantity > 10:
            raise OrderRejected(f"order rejected: {quantity} exceeds the limit of 10")
        return quantity
```

```robotframework
# file: orders.robot
*** Settings ***
Library    Orders


*** Test Cases ***
Message Without Class Name
    Run Keyword And Expect Error    order rejected: 11 exceeds the limit of 10
    ...    Submit Order    11
```

## Logging

| Call | Level / target |
|---|---|
| `logger.trace(msg)`, `logger.debug(msg)` | TRACE / DEBUG (shown with `--loglevel DEBUG` or `TRACE`) |
| `logger.info(msg)` | INFO (default level of the log) |
| `logger.info(msg, html=True)` | INFO, rendered as HTML |
| `logger.info(msg, also_console=True)` | INFO plus the console |
| `logger.warn(msg)` / `logger.error(msg)` | WARN / ERROR; also listed in "Test Execution Errors" and on the console |
| `logger.console(msg)` | the console only (progress output) |

`from robot.api import logger`. Plain `print()` in a keyword also ends up in
the log at INFO, and `*WARN*`-prefixed prints become warnings, but the
logger is explicit and supports levels. Never log secrets: log a masked value,
or take a `Secret` argument (see conversion.md). During import and `__init__`
nothing should be logged (checker: `output_during_import`).

## Threads

Only the thread that runs the keyword can log or fail it. Messages that other
threads send through `logger` are silently dropped, and exceptions raised in
them never reach RF. Collect results in the worker thread and log or raise in
the keyword's own thread:

```python
# file: Parallel.py
"""Run work in threads, report from the keyword thread."""

from concurrent.futures import ThreadPoolExecutor

from robot.api import logger
from robot.api.deco import keyword, library


@library(scope="GLOBAL")
class Parallel:
    """Thread-safe reporting."""

    @keyword
    def square_all(self, numbers: list[int]) -> list[int]:
        """Square the numbers in parallel and log the result."""
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda n: n * n, numbers))
        logger.info(f"squares: {results}")
        return results
```

## Timeouts

A `[Timeout]` or `Test Timeout` stops a running library keyword by raising
`robot.errors.TimeoutExceeded` (RF 7.3; `robot.errors.TimeoutError` before)
inside it. Before RF 7.5 that exception derives from `Exception`, so a broad
`except Exception:` in the keyword swallows it: a retry loop keeps running
past the timeout (a 4 s loop with a 1 s timeout ran 4.4 s on RF 7.4.2 and
1.5 s on 7.5). Catch specific exceptions, or re-raise the timeout first
(checker: `broad_except`):

```python
# file: Poller.py
"""A retry loop that does not swallow Robot Framework timeouts."""

import time

from robot.api.deco import keyword, library
from robot.errors import TimeoutError as RobotTimeout  # TimeoutExceeded on RF 7.3+


@library(scope="GLOBAL")
class Poller:
    """Polling helpers."""

    @keyword
    def wait_until_ready(self, attempts: int = 3, interval: float = 0.01) -> int:
        """Retry a check; RF timeouts still stop the loop."""
        for attempt in range(1, attempts + 1):
            try:
                if attempt == attempts:
                    return attempt
                raise ConnectionError("not ready")
            except RobotTimeout:
                raise
            except ConnectionError:
                time.sleep(interval)
        raise AssertionError("never ready")
```

`robot.errors.TimeoutError` exists on every RF 7.x (an alias of
`TimeoutExceeded` from 7.3), so the import above works on 7.0+.

## Using BuiltIn from a library

`from robot.libraries.BuiltIn import BuiltIn` gives access to variables and
keywords of the running test: `BuiltIn().get_variable_value("${OUTPUT DIR}")`,
`BuiltIn().run_keyword("Log", "x")`, `BuiltIn().get_library_instance("Browser")`.
It only works while tests run: calling it in `__init__` or at import time
fails with `RobotNotRunningError` under libdoc, the checker and language
servers. Call it inside keywords.

`BuiltIn().robot_running` is false under libdoc and the checker, and
`BuiltIn().dry_run_active` (RF 6.1+) is true during `--dryrun`. Guard side
effects that must not happen outside a real run:

```python
# file: Database.py
"""Guarded side effect in __init__."""

from robot.api.deco import keyword, library
from robot.libraries.BuiltIn import BuiltIn


@library(scope="GLOBAL")
class Database:
    """Connects only during a real run."""

    def __init__(self, url: str = "sqlite:///:memory:") -> None:
        self._url = url
        self._connected = False
        if BuiltIn().robot_running and not BuiltIn().dry_run_active:
            self._connected = True  # open the real connection here

    @keyword
    def connection_should_be_open(self) -> None:
        """Fail unless the library connected."""
        if not self._connected:
            raise AssertionError(f"not connected to {self._url}")
```

Better still, connect lazily in the first keyword that needs the connection.
