# Debugging: `robotcode robot-debug`

Runs real suites, with the same options, `robot.toml` and profiles as `robotcode robot`, and pauses at breakpoints, at the first keyword, or at failures. At the `(rdb)` prompt you can look at the stack and variables, step, and **run any keyword** in the paused context. Alias: `robotcode run-debug`.

**When to use it:** whenever a test already exists and fails or behaves strangely. It is faster and more precise than re-running with extra `Log` lines.

## Scripted session (the agent pattern)

Always pipe the `(rdb)` commands in and pass `--plain`:

```bash
printf '.where\n.print ${total}\n.continue\n' \
  | robotcode robot-debug --plain --no-history -t "Sum Prices" tests/debug_target.robot

# or keep the commands in a file
robotcode robot-debug --plain --no-history tests/debug_target.robot < debug-at-failure.rdb
```

`assets/examples/debug-at-failure.rdb` together with `assets/examples/debug_target.robot` gives this (robotcode 2.7.0):

```text
* exception  BuiltIn.Should Be Equal As Integers  (tests/debug_target.robot:14)  — Keyword failed: Total is 60, expected 100: 60 != 100
(rdb) > #0  BuiltIn.Should Be Equal As Integers  tests/debug_target.robot:14
  #1  Sum Prices                           tests/debug_target.robot:9
  #2  Debug Target                         tests/debug_target.robot
(rdb) ${total} = 60
(rdb) ['10', '20', '30']
(rdb) [ INFO ] ${count} = 3
=> 3
(rdb) live keyword at the prompt: 3 prices
=> None
(rdb) | FAIL |
```

- If stdin ends (EOF) while paused, the run **resumes and finishes**. A short command list never hangs the run.
- The exit code is the normal robot exit code (failed test count). `.abort` exits with **253**.

## Where it stops

| Option | Stops |
|---|---|
| *(none)* | At an **uncaught failure, before it unwinds**, with the failing values still in scope (`--break-on-exception` is on by default) |
| `--break "Keyword Name"` | At every call of that keyword (repeatable) |
| `--break file.robot:42` | At that line |
| `--stop-on-entry` | At the very first keyword |
| `--break-on-all-exceptions` | Also at failures caught by `TRY/EXCEPT` or `Run Keyword And …` |
| `--break-on-failed-test` / `--break-on-failed-suite` | At the end of a failed test / suite. ⚠️ Running keywords at this stop fails with `IndexError`; prefer the default exception stop. |
| `--no-break-on-exception` | Don't stop at failures (only breakpoints) |
| `Breakpoint` keyword in the test | See "Embedded breakpoints" below |

Test selection works as for `robot`: `-t`, `-s`, `-i`, `-e`, `-bl`, profiles (`robotcode -p baseline robot-debug -i expected-fail …`).

## Browser failures: drive the live page

This is the most useful feature. When a Browser keyword fails, the debugger stops **with the browser still open**, so you can query the real page:

```bash
printf 'Get Url\n${n}=    Get Element Count    .inventory_item\nTake Screenshot    debug-state\n.c\n' \
  | robotcode robot-debug --plain --no-history -t "Problem User Sorts By Price" tests/
```

```text
(rdb) => 'https://www.saucedemo.com/inventory.html'
(rdb) [ INFO ] ${n} = 6
=> 6
(rdb) => '/…/results/browser/screenshot/debug-state.png'
```

Use `Get Url`, `Get Text`, `Get Element Count`, `Get Element States` and `Take Screenshot` to test a fix for a locator before editing the test.

## `(rdb)` commands

**Inspect**

| Command | Use |
|---|---|
| `.where` (`.w`) | Call stack (`#0` = innermost, `>` = selected frame) |
| `.vars [--user]` (`.v`) | Variables by scope (Local, Test, Suite, Global) |
| `.print <expr>` (`.p`) | Evaluate: `.print ${product}[price] * 2` |
| `.pprint <expr>` (`.pp`) | Pretty-print a dict / list / response |
| `.whatis <expr>` | Type of a value (`dict`, `str`, …) |
| `.list` (`.l`) | Source around the stop, `->` marks the line |
| `.source <Keyword>` | Source of a resource keyword (not for keywords defined in the suite file; use `.list`) |
| `.up` / `.down` / `.frame <n>` | Select another frame for `.print` / `.vars` |
| `<any keyword call>` | Runs in the paused context and prints `=> value`. Assignments (`${x}=    Get Text    h1`) stay available. |

**Move**

| Command | Use |
|---|---|
| `.continue` (`.c`) | Run to the next stop |
| `.step` (`.s`) | Step into the next keyword |
| `.next` (`.n`) | Step over |
| `.return` (`.r`) | Run until the current keyword returns (at test level: to the end of the test) |
| `.until` | Run to a later line in this frame (past loops) |
| `.detach` | Let the run finish without pausing again |
| `.abort` | Stop the run ("Execution stopped by user.", exit 253) |

**Breakpoints at the prompt**

| Command | Use |
|---|---|
| `.break Keyword Name` / `.break file.robot:42` | Add a breakpoint. ⚠️ **No quotes** around the keyword name. |
| `.break Add Price, ${index} == 2` | Conditional breakpoint |
| `.tbreak …` | One-shot breakpoint |
| `.breakpoints` (`.bp`) | List (numbered) |
| `.condition <n> <expr>`, `.ignore <n> <count>` | Change condition / skip the next N hits |
| `.disable` / `.enable` / `.delete [n]` | Manage breakpoints |
| `.display ${x}` / `.undisplay` | Print a value at every stop |
| `.catch uncaught\|all\|test\|suite\|off` | Change exception stops at runtime |
| `.commands <n>` … `end` | Commands replayed at each hit (logpoints) |

## Breakpoint semantics that matter

- **A keyword breakpoint stops at the call site**, in the caller, before the keyword starts. The keyword's own arguments are not in scope yet (`${price}` is "not found"), but the caller's variables (`${index}`) are. Use `.s` to step into the keyword and see its arguments.
- **Conditions are evaluated at the call site too.** Write them with the caller's variables. A condition that references an unknown variable does not fail: the breakpoint then stops at **every** hit.
- **Quotes at `(rdb)`:** `.break "Add Price"` becomes a breakpoint on the name `"Add Price"` including the quotes and never matches (observed on 2.7.0). On the shell command line, `--break "Add Price"` is fine.

Verified example (stop once, in the second loop iteration, step in, read the argument):

```bash
printf '.break Add Price, ${index} == 1\n.c\n.print ${index}\n.s\n.print ${price}\n.detach\n' \
  | robotcode robot-debug --plain --no-history --stop-on-entry --no-break-on-exception tests/debug_target.robot
```

```text
(rdb) breakpoint 1 at keyword 'Add Price' if ${index} == 1
* breakpoint  Add Price  (tests/debug_target.robot:12)
(rdb) ${index} = 1
* step  RETURN  (tests/debug_target.robot:19)
(rdb) ${price} = '20'
(rdb) debugger: detached
```

## Logpoints: print without stopping

```text
.break Process Product
.commands 1
silent
.print ${index}
.continue
end
.continue
```

Each hit prints `${index} = …` and continues.

## Embedded breakpoints

```robotframework
*** Settings ***
Library    robotcode.repl.Repl

*** Test Cases ***
Investigate
    ${total}=    Calculate Total
    Breakpoint                       # pauses under robot-debug, no-op under robot
```

`Breakpoint` also pauses with `--no-break-on-exception`. Remove it before committing.

## Changing values

`.set ${total} 1000` only works for **existing** scalar variables, and stores the **string** `'1000'`. To create a variable or set a typed value, run a keyword at the prompt:

```text
${total}=    Set Variable    ${1000}
```

No graphical view (gutter breakpoints, variables pane) is available in the CLI; use the RobotCode VS Code extension for that.
