# Control Structures

- [Where control structures belong](#where-control-structures-belong)
- [IF and inline IF](#if-and-inline-if)
- [FOR loops](#for-loops)
- [WHILE loops](#while-loops)
- [BREAK, CONTINUE and RETURN](#break-continue-and-return)
- [TRY and EXCEPT](#try-and-except)
- [GROUP](#group)
- [Nesting, retries and timeouts](#nesting-retries-and-timeouts)

Markers (`IF`, `ELSE IF`, `ELSE`, `FOR`, `WHILE`, `TRY`, `EXCEPT`, `FINALLY`, `GROUP`, `END`) are upper case and case-sensitive. Code blocks are complete files.

## Where control structures belong

Keep `FOR`, `WHILE`, `IF` and `TRY` out of test case bodies: a test case reads as a sequence of steps, and the logic goes into a user keyword whose name says what it does. The one exception is a templated test, where `FOR` or `IF` feeds data rows to the template (see the templates reference).

## IF and inline IF

```robotframework
*** Test Cases ***
Conditions
    Classify    ${5}
    Classify    ${50}

*** Keywords ***
Classify
    [Arguments]    ${n}
    IF    $n > 10
        Log    big
    ELSE IF    $n > 3
        Log    medium
    ELSE
        Log    small
    END
    IF    $n == 50    Log    fifty
    ${size}=    IF    $n > 10    Set Variable    big    ELSE    Set Variable    small
    Should Not Be Equal    ${size}    ${None}
```

- An inline IF with no matching branch assigns `None`: `${v}=    IF    $n > 10    Set Variable    big` leaves `${v}` as `None` when `$n` is 5. Add an `ELSE` branch.
- Keep an inline IF on one line (robocop MISC11); use a block when it gets long.
- `Run Keyword If`/`Run Keyword Unless` are legacy (robocop DEPR08).
- Conditions are Python expressions; use `$var` (see the variables reference).

## FOR loops

```robotframework
*** Test Cases ***
Loops
    Loop Variants

*** Keywords ***
Loop Variants
    VAR    @{names}    alice    bob
    VAR    @{ages}    30    40
    VAR    &{roles}    alice=admin    bob=user
    FOR    ${name}    IN    @{names}
        Log    ${name}
    END
    FOR    ${i}    IN RANGE    1    4
        Log    ${i}
    END
    FOR    ${index}    ${name}    IN ENUMERATE    @{names}    start=1
        Log    ${index}: ${name}
    END
    FOR    ${name}    ${age}    IN ZIP    ${names}    ${ages}    mode=STRICT
        Log    ${name} is ${age}
    END
    FOR    ${name}    ${role}    IN    &{roles}
        Log    ${name} has ${role}
    END
```

- `IN ZIP` takes lists as `${lists}`, not `@{lists}`. Set `mode=STRICT`, `SHORTEST` or `LONGEST` (with `fill=`) explicitly; the default may change.
- Iterating a dictionary with `IN    &{dict}` yields key and value pairs.
- Loop variables are typed on RF 7.3+: `FOR    ${i: int}    IN    1    2`.

## WHILE loops

```robotframework
*** Test Cases ***
While Loop
    Count Down

*** Keywords ***
Count Down
    VAR    ${n}    ${3}
    WHILE    $n > 0    limit=10
        ${n}=    Evaluate    $n - 1
    END
    WHILE    True    limit=3    on_limit=pass
        Log    polling
    END
```

- The default limit is 10 000 iterations; set `limit=` to a count (`10`, `10x`) or a time (`30s`), or `NONE`.
- `on_limit=pass` (RF 6.1+) ends the loop without failing; `on_limit_message=` customises the failure.

## BREAK, CONTINUE and RETURN

- `BREAK` and `CONTINUE` work only directly inside a `FOR` or `WHILE` body. In a keyword called from the loop they fail with "BREAK is not allowed in this context" (robocop MISC08). Return a value and test it in the loop instead.
- `RETURN` inside a loop leaves the whole keyword. In a test case body `RETURN` is an error (robocop ERR14).
- `Exit For Loop`, `Continue For Loop` and their `If` variants are legacy (robocop DEPR09).

```robotframework
*** Test Cases ***
First Even
    ${found}=    Find First Even    3    5    8    9
    Should Be Equal    ${found}    8

*** Keywords ***
Find First Even
    [Arguments]    @{numbers}
    FOR    ${n}    IN    @{numbers}
        IF    int($n) % 2    CONTINUE
        RETURN    ${n}
    END
    Fail    no even number
```

## TRY and EXCEPT

```robotframework
*** Test Cases ***
Handling Errors
    Handle Errors

*** Keywords ***
Handle Errors
    TRY
        Fail    Connection refused: port 8080
    EXCEPT    Connection refused*    type=GLOB    AS    ${error}
        Log    retrying after: ${error}
    EXCEPT    Timeout    Invalid*    type=GLOB
        Log    other known error
    ELSE
        Log    no error
    FINALLY
        Log    cleanup
    END
```

- Messages match exactly by default; `type=GLOB`, `type=REGEXP` or `type=START` change that. Backslashes in a `REGEXP` pattern are doubled.
- `AS    ${error}` stores the message.
- Syntax errors and fatal errors cannot be caught.
- `TRY` replaces `Run Keyword And Ignore Error`, `Run Keyword And Return Status` and `Run Keyword And Expect Error` when they only control flow.
- Do not wrap templated rows in `TRY`; templated tests already continue on failure.

## GROUP

`GROUP` (RF 7.2+) labels a block in the log and shares the surrounding variable scope. Prefer a user keyword when the block is reused or has a name worth calling.

```robotframework
# RF 7.2+
*** Test Cases ***
Grouped Steps
    Prepare And Check

*** Keywords ***
Prepare And Check
    GROUP    Prepare data
        VAR    ${value}    42
    END
    GROUP    Check data
        Should Be Equal    ${value}    42
    END
```

## Nesting, retries and timeouts

- Keep nesting to at most four levels. Deeper logic, parsing and computation belong in a Python keyword library.
- For a flaky step, first use the library's own waiting or retrying assertion (for example Browser's assertion operators with a timeout, SeleniumLibrary's `Wait Until …` keywords). Use `Wait Until Keyword Succeeds    3x    1s    Keyword` only around keywords that do not wait themselves; retrying a waiting keyword multiplies the timeouts.
- `WHILE … limit=` is an alternative when the retry needs custom logic.
- A keyword `[Timeout]` has no default. A test timeout does not interrupt the test teardown; a keyword timeout inside the teardown does.
