# Embedded Arguments

- [Matching rules](#matching-rules)
- [The shortest-match trap](#the-shortest-match-trap)
- [Custom patterns](#custom-patterns)
- [Mixing embedded and normal arguments](#mixing-embedded-and-normal-arguments)
- [Conflicts between keywords](#conflicts-between-keywords)
- [BDD step definitions](#bdd-step-definitions)

A keyword name can contain arguments: `Select Team "${city}" "${team}"` is called as `Select Team "Los Angeles" "Lakers"`. Code blocks are complete files; `assets/examples/resources/embedded.resource` holds the reference versions.

## Matching rules

- Matching ignores case: `select fruit apple` calls `Select Fruit ${name}`.
- Spaces and underscores are significant: `Select_fruit apple` does not match `Select Fruit ${name}`.
- Embedded arguments cannot have defaults and cannot be varargs.
- By default an embedded argument matches any text (`.*?`), including other words of the call.
- A value passed as a variable (`Select Fruit ${fruit}`) is not checked against the pattern.
- Keep literal words between arguments; `${year}-${month}` needs patterns to be unambiguous.

## The shortest-match trap

With default patterns, adjacent embedded arguments split the call at the first possible place. A dry run passes, because some keyword matched; only a real run shows the wrong values.

```robotframework
# Wrong: `city` receives "Los" and `team` receives "Angeles Lakers".
*** Keywords ***
Select Team ${city} ${team}
    Log    city=${city} team=${team}
```

Two fixes, both in `embedded.resource` and exercised by `tests/05__embedded.robot`:

```robotframework
*** Test Cases ***
Multi-Word Cities Bind Correctly
    Select Team "Los Angeles" "Lakers"
    Should Be Equal    ${CITY}    Los Angeles
    Pick Team Golden State Warriors
    Should Be Equal    ${CITY}    Golden State

*** Keywords ***
Select Team "${city}" "${team}"
    [Documentation]    Quotes delimit each value.
    VAR    ${CITY}    ${city}    scope=TEST

Pick Team ${city} ${team:\S+}
    [Documentation]    The team is one word, so the city takes the rest.
    VAR    ${CITY}    ${city}    scope=TEST
```

- Quoting is the clearest fix when you control the call sites.
- A pattern on the last argument fixes existing unquoted calls such as `Select Team Los Angeles Lakers`, as long as the team name is one word.
- On RF 7.3+ the fix combines with a type: `${count: int:\d+}`.
- After writing embedded keywords, run at least one test that uses them and check the logged values.

## Custom patterns

`${name:regex}` restricts what an argument matches. The regex is Python syntax inside Robot Framework data, so backslashes are written once (`\d`, `\S`).

```robotframework
*** Test Cases ***
Patterns
    Wait 5 Seconds
    Choose Animal CAT
    Book For 2026-10-01

*** Keywords ***
Wait ${count:\d+} Seconds
    Should Be True    ${count} == 5

Choose Animal ${animal:(?i)cat|dog}
    Should Be Equal    ${animal}    CAT

Book For ${date:\d{4}-\d{2}-\d{2}}
    Should Match Regexp    ${date}    ^2026-
```

- Lone braces in a pattern are escaped (`\{`, `\}`); counted braces such as `\d{4}` work as written.
- `(?i)` makes one pattern case-insensitive (RF 7.2+).
- Alternatives need no group: `${animal:cat|dog}` matches either word.
- A pattern that should match a leading space needs `\ ` or `\s`.
- Types with patterns (RF 7.3+): `${count: int:\d+}` or `${when: date:\d{4}-\d{2}-\d{2}}`.

## Mixing embedded and normal arguments

From RF 6.1 a user keyword may have embedded arguments and an `[Arguments]` list:

```robotframework
*** Test Cases ***
Mixed
    Order 3 Apples    express=${True}

*** Keywords ***
Order ${count:\d+} Apples
    [Arguments]    ${express}=${False}
    Should Be True    ${count} == 3 and ${express}
```

## Conflicts between keywords

When several keywords match one call:
- a keyword in the same file wins over imported ones;
- a normal keyword wins over an embedded-argument keyword with the same text;
- among embedded keywords, one wins when the other also matches its name but not the other way round: `Select ${x} Team` beats `Select ${x}` for `Select Lakers Team` (RF 6.0+); a stricter pattern alone (`${n:\d+}` versus `${n}`) does not make a keyword win;
- if no keyword wins, the call fails with "Multiple keywords with name '…' found".

Pairs such as `${type} Framework` and `Robot ${action}` both match `Robot Framework` and cannot be resolved automatically: rename one or narrow a pattern. For the same name defined in two resource files, see the resources reference (qualified calls, robocop KW06).

## BDD step definitions

Steps are called with `Given`, `When`, `Then`, `And` or `But`; Robot Framework removes the prefix and looks up the rest. Define step keywords without the prefix:

```robotframework
*** Test Cases ***
Checkout Scenario
    Given The Cart Contains 2 "Blue Mug"
    When The User Checks Out
    Then The Order Total Is 2 Items

*** Keywords ***
The Cart Contains ${count:\d+} "${product}"
    VAR    ${ITEMS}    ${count}    scope=TEST

The User Checks Out
    Log    checking out ${ITEMS} items

The Order Total Is ${count:\d+} Items
    Should Be Equal As Integers    ${ITEMS}    ${count}
```

- A keyword defined as `Given The App Is Open` is found only through that exact prefix; `When The App Is Open` fails with "No keyword with name".
- From RF 7.1 a prefix is also stripped when the keyword starts with an embedded argument (`Given ${user} Logs In`).
- Keep one step keyword per sentence; share implementation through normal keywords that the steps call.
- Quote or pattern-restrict every embedded value in a step, because steps often place values next to each other.
