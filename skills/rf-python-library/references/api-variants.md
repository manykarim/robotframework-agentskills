# Library API variants

How Robot Framework turns a Python module or class into keywords, and the
alternatives to the default static class library. Examples need RF 7.0+
unless a block says otherwise.

- [Module or class library](#module-or-class-library)
- [Which class RF picks](#which-class-rf-picks)
- [Library scope](#library-scope)
- [Init arguments and AS](#init-arguments-and-as)
- [Embedded-argument keywords](#embedded-argument-keywords)
- [Async keywords](#async-keywords)
- [Hybrid API](#hybrid-api)
- [Dynamic API](#dynamic-api)
- [PythonLibCore](#pythonlibcore)
- [Remote libraries](#remote-libraries)

## Module or class library

A module library exposes its public functions. Everything public counts,
including functions it imports, so `from os.path import join` adds a `Join`
keyword (checker: `leaked_keyword`). Keep module libraries small and turn
automatic discovery off:

```python
# file: textutils.py
"""Module library: only @keyword functions are keywords."""

import re

from robot.api.deco import keyword

ROBOT_AUTO_KEYWORDS = False


@keyword
def normalise_whitespace(text: str) -> str:
    """Collapse runs of whitespace to one space."""
    return re.sub(r"\s+", " ", text).strip()
```

`__all__ = ["normalise_whitespace"]` also limits the keywords. A class library
(the template in SKILL.md) is the default for anything with state, init
arguments, converters or a listener. Module libraries always have `GLOBAL`
scope.

## Which class RF picks

`Library    Name` imports module `Name` and uses its class `Name` when one
exists. From RF 7.2 a module without a same-named class may contain exactly
one `@library`-decorated class, and RF uses that. `Library    pkg.module.Class`
names the class explicitly on every version. Otherwise the module itself is
the library, and a class-only module reports "contains no keywords".

## Library scope

Source: Robot Framework User Guide, "Creating test libraries" → "Library
scope". The only library scopes are `TEST` (alias `TASK`), `SUITE` and
`GLOBAL`; `SUITES` is a `VAR` scope for variables, not a library scope.

- `TEST` (default without a setting): a new instance for every test; suite
  setup and teardown share another instance. Tests stay independent.
- `SUITE`: one instance per suite, shared by its tests.
- `GLOBAL`: one instance for the whole run. Module libraries are global.
- A library imported with different arguments gets a new instance for each
  argument set, whatever the scope.
- A `SUITE` or `GLOBAL` library that keeps state should offer a cleanup
  keyword for a suite setup or teardown; SeleniumLibrary is `GLOBAL` and
  offers `Close All Browsers`.

Set the scope with `@library(scope="SUITE")` or the class attribute
`ROBOT_LIBRARY_SCOPE = "SUITE"`. `__init__` runs when an instance is created:
for every test in `TEST` scope, and also during libdoc and `--dryrun`.

```python
# file: Counter.py
"""SUITE scope: the tests of one suite share the count."""

from robot.api.deco import keyword, library


@library(scope="SUITE")
class Counter:
    """Counts calls across the tests of a suite."""

    def __init__(self) -> None:
        self._count = 0

    @keyword
    def increment(self) -> int:
        """Add one and return the count."""
        self._count += 1
        return self._count

    @keyword
    def reset_counter(self) -> None:
        """Cleanup keyword for a suite setup or teardown."""
        self._count = 0
```

```robotframework
# file: counter.robot
*** Settings ***
Library           Counter
Suite Setup       Reset Counter


*** Test Cases ***
First Test
    ${count}=    Increment
    Should Be Equal    ${count}    ${1}

Second Test Sees The Same Instance
    ${count}=    Increment
    Should Be Equal    ${count}    ${2}
```

With `scope="TEST"` the second test would get `1`, and the checker would warn
with `state_in_test_scope`.

## Init arguments and AS

`__init__` arguments are import arguments and use the same type conversion as
keywords. Named import arguments work too.

```robotframework
*** Settings ***
Library    Client    https://dev.example.com    timeout=10    AS    DevClient
Library    Client    https://staging.example.com               AS    StagingClient
```

Call the keywords as `DevClient.Get Status` and `StagingClient.Get Status`.
Without `AS`, the second import of the same library with different arguments
is ignored with a warning. For the checker, pass init arguments with
`--init-arg VALUE` (repeatable, one library per run).

## Embedded-argument keywords

`@keyword("Add ${quantity} items of ${product}")` embeds arguments in the
name; put the types on the Python arguments. An inline type in the name
(`${quantity: int}`) is rejected on RF 7.3+ and the library then contains no
keywords (checker: `keyword_creation_failed`, `no_keywords`); before 7.3 the
`: int` part is read as a regular expression, so the keyword never matches.
From RF 7.0 an embedded keyword can also take normal arguments after the name.
Custom patterns use `${name:regex}` without a space after the colon.

```python
# file: Basket.py
"""Embedded arguments with Python type hints."""

from robot.api.deco import keyword, library


@library(scope="SUITE")
class Basket:
    """A basket of products."""

    def __init__(self) -> None:
        self._items: dict[str, int] = {}

    @keyword("Add ${quantity:\\d+} items of ${product}")
    def add_items(self, quantity: int, product: str, note: str = "") -> int:
        """Add items; ``note`` is a normal argument after the embedded ones (RF 7.0+)."""
        self._items[product] = self._items.get(product, 0) + quantity
        return self._items[product]
```

```robotframework
# file: basket.robot
*** Settings ***
Library    Basket


*** Test Cases ***
Embedded And Normal Arguments
    ${count}=    Add 3 items of apple
    Should Be Equal    ${count}    ${3}
    ${count}=    Add 2 items of apple    note=gift
    Should Be Equal    ${count}    ${5}
```

## Async keywords

An `async def` keyword (RF 6.1+) is awaited by Robot Framework on its own
event loop; do not start one yourself with `asyncio.run`.

```python
# file: Waiter.py
"""Async keyword."""

import asyncio

from robot.api.deco import keyword, library


@library(scope="GLOBAL")
class Waiter:
    """Async waits."""

    @keyword
    async def wait_and_return(self, value: str, seconds: float = 0.01) -> str:
        """Wait ``seconds`` and return ``value``."""
        await asyncio.sleep(seconds)
        return value
```

## Hybrid API

`get_keyword_names()` returns the keyword names; RF then looks up each name as
a method or attribute, so arguments, types and docs still come from real
callables. Use it when the set of keywords is computed at import time (for
example one keyword per configured endpoint).

## Dynamic API

A dynamic library implements `get_keyword_names()` and
`run_keyword(name, args, kwargs)`, plus optional `get_keyword_arguments`,
`get_keyword_types`, `get_keyword_documentation`, `get_keyword_tags` and
`get_keyword_source`. Without `get_keyword_arguments` every keyword takes
`*varargs, **kwargs` (checker: `signature_lost`) and nothing is converted.
Use it for proxies to another tool or process. `get_keyword_documentation`
with `"__intro__"` / `"__init__"` returns the library and init docs.

```python
# file: Commands.py
"""Dynamic library that proxies a command table."""

from robot.api.deco import library

COMMANDS = {
    "Double Value": (lambda value: value * 2, ["value"], {"value": int}, "Return ``value`` times two."),
    "Join Words": (lambda *words: " ".join(words), ["*words"], {}, "Join words with spaces."),
}


@library(scope="GLOBAL")
class Commands:
    """Keywords generated from the COMMANDS table."""

    def get_keyword_names(self) -> list[str]:
        return list(COMMANDS)

    def run_keyword(self, name: str, args: list, kwargs: dict):
        return COMMANDS[name][0](*args, **kwargs)

    def get_keyword_arguments(self, name: str) -> list[str]:
        return COMMANDS[name][1]

    def get_keyword_types(self, name: str) -> dict:
        return COMMANDS[name][2]

    def get_keyword_documentation(self, name: str) -> str:
        if name in ("__intro__", "__init__"):
            return "Keywords generated from the COMMANDS table." if name == "__intro__" else ""
        return COMMANDS[name][3]
```

```robotframework
# file: commands.robot
*** Settings ***
Library    Commands


*** Test Cases ***
Dynamic Keywords Run With Converted Arguments
    ${result}=    Double Value    21
    Should Be Equal    ${result}    ${42}
    ${text}=    Join Words    a    b    c
    Should Be Equal    ${text}    a b c
```

List the keywords: `uv run python -m robot.libdoc Commands list` (with the
module on the python-path), `robotcode libdoc Commands list`, or the checker.
The checker skips its method-based checks (`public_method_not_keyword`,
`state_in_test_scope`) for hybrid and dynamic libraries.

## PythonLibCore

`robotframework-pythonlibcore` (`from robotlibcore import DynamicCore,
keyword`) builds a dynamic library from several component classes; Browser
and SeleniumLibrary use it. Reach for it when a library grows beyond one
class. Add it to the project with `uv add robotframework-pythonlibcore` (see
rf-setup); it is not needed for ordinary libraries.

## Remote libraries

The Remote library (`Library    Remote    http://host:8270`) calls keywords of
a library that runs in another process or machine over XML-RPC, served by a
remote server such as `robotremoteserver`. The library code itself is written
the same way; only the server wraps it. Prefer a local library unless the
code must run elsewhere.
