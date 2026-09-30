# Argument conversion from type hints

Robot Framework passes every argument from `.robot` data as a string unless it
is a variable holding another object. A type hint on the Python argument makes
RF convert the string before the keyword runs and documents the type in libdoc.
Examples need RF 7.0+ unless a block says otherwise.

- [Built-in types](#built-in-types)
- [Enum and Literal](#enum-and-literal)
- [Containers and TypedDict](#containers-and-typeddict)
- [None, unions and their order](#none-unions-and-their-order)
- [Implicit typing and bool](#implicit-typing-and-bool)
- [Secret and object (RF 7.4)](#secret-and-object-rf-74)
- [Custom converters](#custom-converters)
- [Types without annotations: `types=`](#types-without-annotations-types)

## Built-in types

| Hint | Accepts (strings) | Notes |
|---|---|---|
| `int` | `42`, `-1`, `0x2A`, `1 000` | spaces and underscores allowed |
| `float` / `Decimal` | `3.14`, `1e3` | use `Decimal` for money |
| `bool` | `True`/`yes`/`on`/`1`, `False`/`no`/`off`/`0`/`none`/empty | other strings pass through unchanged |
| `str` | anything | no conversion |
| `bytes` | `abc` (Latin-1) | |
| `datetime` / `date` | `2026-09-28 12:00:00`, epoch seconds | |
| `timedelta` | `1 minute 30 s`, `90`, `1:30` | RF time format |
| `Path` | `results/out.json` | |
| `None` | `None` (case-insensitive) | usually inside a union |

```python
# file: Types.py
"""Built-in conversions."""

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from robot.api.deco import keyword, library


@library(scope="GLOBAL")
class Types:
    """Show converted values."""

    @keyword
    def describe(self, count: int, price: Decimal, wait: timedelta, target: Path, enabled: bool) -> str:
        """Return the converted values as one string."""
        return f"{count + 1}|{price * 2}|{wait.total_seconds()}|{target.name}|{enabled}"
```

```robotframework
# file: types.robot
*** Settings ***
Library    Types


*** Test Cases ***
Strings Become Typed Values
    ${text}=    Describe    41    1.25    1 minute 30 s    results/out.json    yes
    Should Be Equal    ${text}    42|2.50|90.0|out.json|True

Bad Integer Fails Before The Keyword Runs
    Run Keyword And Expect Error    *cannot be converted to integer*
    ...    Describe    many    1    1s    x    no
```

## Enum and Literal

Both restrict an argument to fixed values and match case-insensitively
(`on` → `ON`). `Literal` (RF 7.0) keeps the plain value; an `Enum` gives the
member and documents the allowed values once for several keywords. A wrong
value fails and names the allowed values (`Literal`: "… cannot be converted
to 'ON' or 'OFF'"; `Enum`: "… Available: 'FAST' and 'SLOW'").

```python
# file: Modes.py
"""Enum and Literal arguments."""

from enum import Enum
from typing import Literal

from robot.api.deco import keyword, library


class Speed(Enum):
    SLOW = 1
    FAST = 2


@library(scope="GLOBAL")
class Modes:
    """Fixed-value arguments."""

    @keyword
    def set_power(self, state: Literal["ON", "OFF"]) -> str:
        """Return the normalised power state."""
        return state

    @keyword
    def set_speed(self, speed: Speed) -> int:
        """Return the numeric value of the speed."""
        return speed.value
```

```robotframework
# file: modes.robot
*** Settings ***
Library    Modes


*** Test Cases ***
Values Match Case-Insensitively
    ${state}=    Set Power    on
    Should Be Equal    ${state}    ON
    ${speed}=    Set Speed    fast
    Should Be Equal    ${speed}    ${2}

Unknown Value Lists The Allowed Ones
    Run Keyword And Expect Error    *'ON' or 'OFF'*    Set Power    maybe
    Run Keyword And Expect Error    *Available: 'FAST' and 'SLOW'*    Set Speed    medium
```

## Containers and TypedDict

`list[int]`, `dict[str, int]`, `tuple[int, ...]` and `set[str]` convert
Python-literal strings (`[1, 2]`) and also convert the items of a list or
dictionary variable. `TypedDict` checks the keys and converts each value;
missing required keys fail.

```python
# file: Orders.py
"""Parametrised containers and TypedDict."""

from typing import TypedDict

from robot.api.deco import keyword, library


class Item(TypedDict):
    name: str
    qty: int


@library(scope="GLOBAL")
class Orders:
    """Container arguments."""

    @keyword
    def total_quantity(self, quantities: list[int]) -> int:
        """Sum the quantities."""
        return sum(quantities)

    @keyword
    def item_label(self, item: Item) -> str:
        """Return ``<qty> x <name>``."""
        return f"{item['qty']} x {item['name']}"
```

```robotframework
# file: orders.robot
*** Settings ***
Library    Orders


*** Test Cases ***
Literal String And List Variable Are Converted
    ${total}=    Total Quantity    [1, 2, 3]
    Should Be Equal    ${total}    ${6}
    VAR    @{strings}    4    5
    ${total}=    Total Quantity    ${strings}
    Should Be Equal    ${total}    ${9}

TypedDict Converts Values
    ${label}=    Item Label    {'name': 'apple', 'qty': '3'}
    Should Be Equal    ${label}    3 x apple
```

## None, unions and their order

`int | None = None` accepts `None` or an integer. RF tries the union members
from left to right and stops at the first that works; if the argument already
has one of the member types, it is passed unchanged. So a union with `str`
never converts a string: every argument from `.robot` data already is one.
The checker reports this as `union_with_str`.

```python
# file: Unions.py
# Wrong: union_with_str
"""A union with str never converts strings."""

from robot.api.deco import keyword, library


@library(scope="GLOBAL")
class Unions:
    """Union order."""

    @keyword
    def add_one(self, value: int | str) -> str:
        """Returns the type name: ``10`` stays a string."""
        return type(value).__name__
```

Put the converting types only (`int | float`), order them from the most to the
least specific, and keep `str | None` for "text or nothing" (the checker does
not flag it).

## Implicit typing and bool

Without a hint, a default value implies the type, but leniently: `def kw(n=3)`
converts `5` to `5` and passes `abc` through as the string `abc`. `bool`
conversion also passes unknown strings through (`maybe` stays `maybe`). Neither
is detected by the checker. Use real hints, and `Literal`/`Enum` when only a
few values are valid.

## Secret and object (RF 7.4)

`Secret` (`from robot.api.types import Secret`) marks an argument that only
accepts `Secret` objects, so the value does not appear in logs. A plain string
fails ("… must have type 'Secret', got string"). The data creates one from an
environment variable in the Variables section; read `.value` in the keyword.

```python
# file: Vault.py
# RF 7.4+
"""Secret arguments."""

from robot.api.deco import keyword, library
from robot.api.types import Secret


@library(scope="GLOBAL")
class Vault:
    """Uses a secret without logging it."""

    @keyword
    def password_length(self, password: Secret) -> int:
        """Return the length of the secret value."""
        return len(password.value)
```

```robotframework
# file: vault.robot
# RF 7.4+
*** Settings ***
Library    Vault


*** Variables ***
${PASSWORD: Secret}    %{APP_PASSWORD=s3cret}


*** Test Cases ***
Secret From Environment
    ${length}=    Password Length    ${PASSWORD}
    Should Be True    ${length} > 0

Plain String Is Rejected
    Run Keyword And Expect Error    *must have type 'Secret'*    Password Length    s3cret
```

`object` as a hint (RF 7.4) states "any value, no conversion" explicitly.

## Custom converters

For a domain type, register a converter function on the library. RF calls it
only when the argument is not already of that type; it must raise `ValueError`
on bad input, and RF turns that into a failure naming the argument. Register it
with `@library(converters={Type: function})` or, in a module library,
`ROBOT_LIBRARY_CONVERTERS = {Type: function}`.

```python
# file: Shop.py
"""Custom converter registered with @library(converters=...)."""

from dataclasses import dataclass

from robot.api.deco import keyword, library


@dataclass(frozen=True)
class Sku:
    """A stock-keeping unit such as ``AB-1234``."""

    prefix: str
    number: int


def parse_sku(value: str) -> Sku:
    """Convert ``AB-1234``; raise ValueError on anything else."""
    prefix, _, number = value.partition("-")
    if len(prefix) != 2 or not prefix.isalpha() or not number.isdigit():
        raise ValueError(f"expected an SKU like 'AB-1234', got '{value}'")
    return Sku(prefix.upper(), int(number))


@library(scope="GLOBAL", converters={Sku: parse_sku})
class Shop:
    """Keywords that take SKUs."""

    @keyword
    def sku_number(self, sku: Sku) -> int:
        """Return the numeric part of ``sku``."""
        return sku.number
```

```robotframework
# file: shop.robot
*** Settings ***
Library    Shop


*** Test Cases ***
String Becomes Sku
    ${number}=    Sku Number    ab-1234
    Should Be Equal    ${number}    ${1234}

Converter Error Names The Argument
    Run Keyword And Expect Error    *'sku'*expected an SKU like 'AB-1234'*    Sku Number    1234
```

`assets/examples/converters.py` shows the module-library form
(`ROBOT_LIBRARY_CONVERTERS`) with a `Money` type.

## Types without annotations: `types=`

`@keyword(types={"count": int})` (or a list in argument order) sets types when
annotations are not possible, for example on generated functions. Annotations
are preferred.

```python
# file: Legacy.py
"""Types given through the keyword decorator."""

from robot.api.deco import keyword, library


@library(scope="GLOBAL")
class Legacy:
    """Old-style keyword."""

    @keyword(types={"count": int})
    def repeat_word(self, word, count):
        """Repeat ``word`` ``count`` times."""
        return word * count
```
