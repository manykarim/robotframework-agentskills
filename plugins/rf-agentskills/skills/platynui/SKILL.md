---
name: platynui
description: Guide AI agents in creating native desktop UI tests with PlatynUI (new_core) using the PlatynUI.BareMetal library — cross-platform desktop automation over Windows UIA and Linux AT-SPI2 with an XPath query model. Use when asked to automate desktop applications (windows, buttons, menus, text fields), locate native UI elements by XPath, or write Robot Framework tests with PlatynUI.
---

# PlatynUI Library Skill (new_core / BareMetal)

## Quick Reference

PlatynUI is cross-platform **native desktop** UI automation for Robot Framework. It normalizes Windows UIA, Linux AT-SPI2 (and planned macOS AX) into one desktop UI model that you query with **XPath-2.0-style selectors**.

> ⚠️ **Preview / pre-release.** This skill targets the `new_core` rewrite. The only usable keyword library today is **`PlatynUI.BareMetal`**; the high-level `PlatynUI` library is a not-yet-implemented placeholder. Keywords, CLI output, and behavior may change.

## Installation

**Get the version with the right pin — this is the #1 mistake:**

```bash
# ✅ new_core (PlatynUI.BareMetal, documented keywords) — pin OR use --pre:
pip install robotframework-PlatynUI==0.12.0.dev330
pip install --pre robotframework-PlatynUI          # latest pre-release

# ❌ WRONG — installs old 0.9.2 (a different library, NO BareMetal):
pip install robotframework-PlatynUI                # no --pre, no pin → 0.9.2
```

- A plain `pip install robotframework-PlatynUI` resolves the **old stable `0.9.2`**, whose surface is a different, near-undocumented `PlatynUI` library with **no `BareMetal`**. You only get `new_core` by opting into the pre-release (`--pre`) or pinning an exact dev version.
- The wheel is **prebuilt** — it bundles the compiled `platynui-native` runtime (`_native.abi3.so`). **No Rust toolchain and no git checkout required.** Python **3.12+** only.
- Optional CLI / inspector tools (for locator development — see below):
  ```bash
  uv tool install --prerelease allow platynui-cli
  uv tool install --prerelease allow platynui-inspector
  ```
- **Linux** additionally needs a running **AT-SPI2** accessibility bus and (recommended) an **X11** session — see `references/platform-setup.md`.

## Library Import

```robotframework
*** Settings ***
Library    PlatynUI.BareMetal
```

Import arguments (all keyword-only, all optional):

| Argument | Default | Purpose |
|----------|---------|---------|
| `auto_activate` | `True` | Bring the target element's window to the foreground before pointer/keyboard actions. Override per-call with `activate=`. |
| `use_mock` | `False` | Use the Rust mock provider (deterministic, no desktop). **Note:** the published wheel is built *without* mock support and raises `ProviderError`; needs a `--features mock-provider` source build. |
| `keyboard_profile` / `pointer_profile` / `pointer_settings` | `None` | Tune input timing/motion realism. Accept a native object **or** a plain `&{dict}` (e.g. `press_delay_ms`, `acceleration_profile`, `motion`). |

```robotframework
Library    PlatynUI.BareMetal    auto_activate=${True}    pointer_profile=${POINTER_PROFILE}

*** Variables ***
&{POINTER_PROFILE}    acceleration_profile=EASE_OUT    motion=JITTER    jitter_amplitude=100.0
```

Library scope is **SUITE**. The native runtime is created lazily on first keyword use (so `libdoc` and import work without a desktop).

## Essential Concepts

### The normalized desktop UI model

PlatynUI exposes every application's accessibility tree as one queryable model rooted at the **Desktop**. Each node has a normalized PascalCase **role** (`Window`, `Button`, `Edit`, `ListItem`…), a `Name`, an optional developer `Id`, and typed attributes (`Bounds`, `IsEnabled`, `Value`…). Native roles are normalized cross-platform (UIA `Button` / AT-SPI `PUSH_BUTTON` → `Button`); the original stays under `native:Role`.

### Four query namespaces

```
control:  UI controls (Window, Button, Edit, …)   ← DEFAULT (unprefixed = control:)
item:     container children (ListItem, TreeItem, TabItem, Cell, Row)
app:      Application/process nodes
native:   raw platform attributes (native:HWND, native:Role, …)
```

**Critical rule:** an unprefixed query matches `control:` **only**. You MUST prefix `app:` and `item:` explicitly — `//ListItem` finds nothing; `//item:ListItem` works.

### XPath query language

Elements are referenced by an **XPath string** passed directly as a keyword argument (auto-converted to an element descriptor), or by a `UiNode` captured from `Query ... only_first=${True}`.

```robotframework
Pointer Click    //control:Button[@Name="OK"]
Pointer Click    app:Application[@Name="Calculator"]//Button[@Id="num5Button"]
${count}=        Query    count(//control:Button)        # value expression
${node}=         Query    //control:Edit[@Name="Search"]    only_first=${True}
```

Supports the full XPath-2.0 axis/function set: `//` (descendant), `..`/`parent::`, `following-sibling::`, predicates (`[@Name='OK']`, `[1]`), and functions (`contains()`, `matches()`, `count()`, `starts-with()`). See `references/locators-and-queries.md`.

### Lazy resolution with built-in wait

There is **no explicit "wait for element" keyword.** When a descriptor is first used, PlatynUI polls the query (default **~30 s**, retrying ~0.1 s) until the element resolves or it raises `ElementNotFoundError`. Write the correct selector and let the runtime wait — don't add `Sleep`.

### Coordinate semantics (pointer keywords)

| You pass | Behavior |
|----------|----------|
| descriptor, no x/y | acts at the element's `ActivationPoint` (else bounds center) |
| descriptor **+** x/y | x/y are **offsets** from the element's top-left bounds |
| no descriptor, x/y | x/y are **absolute screen** coordinates |
| only one of x/y | `ValueError` — pass both together |

### Window keywords need a window node

`Activate/Minimize/Maximize/Restore/Close/Move/Resize Window` operate on a node that supports the window surface — target a `Window` node, not an arbitrary control, or they raise `PatternError`.

## Core Keywords Quick Reference

### Query & scope

```robotframework
${node}=    Query      //control:Button[@Name="OK"]    only_first=${True}
${all}=     Query      //item:ListItem                              # list of nodes
${n}=       Query      count(//control:Button)                      # computed value
Set Root    app:Application[@Name="Calculator"]//control:Window     # scope later queries
Set Root    ${None}                                                 # reset to desktop
```

### Pointer / mouse

```robotframework
Pointer Click          //control:Button[@Name="OK"]
Pointer Click          //control:Button[@Name="OK"]    button=RIGHT    activate=${False}
Pointer Multi Click    //item:ListItem[@Name="file.txt"]    clicks=${2}
Pointer Move To        ${None}    x=${100}    y=${200}              # absolute screen
Pointer Press          //control:Slider
Pointer Release        ${None}
${pos}=                Get Pointer Position
```

### Keyboard

```robotframework
Keyboard Type    //control:Edit[@Name="Search"]    Hello <Ctrl+A> world${\n}
Keyboard Type    ${None}    <Ctrl+A><Delete>        # type into whatever has focus
Keyboard Press   ${None}    <Shift>
Keyboard Release    ${None}    <Shift>
```
Key syntax: `<Ctrl+A>`, `<Return>`, `<ESC>`, `<Shift+Tab>`, plain text, `${\n}`. Pass `${None}` as the descriptor to skip focusing. Discover valid key names with `platynui-cli keyboard list`.

### Focus, attributes, windows

```robotframework
Focus            //control:Button[@Name="New File"]
${bounds}=       Get Attribute    //control:Window[@Name="Calc"]    Bounds
Get Attribute    //control:Button[@Name="OK"]    Name    ==    OK     # built-in assertion
Bring To Front   //control:Window[@Name="Calc"]
Activate Window    //control:Window[@Name="Calc"]
Maximize Window    //control:Window[@Name="Calc"]
Move And Resize Window    //control:Window[@Name="Calc"]    ${0}    ${0}    ${800}    ${600}
```

### Diagnostics

```robotframework
Take Screenshot                                              # full screen → ${OUTPUT DIR}
Take Screenshot    //control:Window[@Name="Calc"]            # just the element
Take Screenshot    filename=EMBED                            # inline base64 in the log
Highlight    //control:Button[@Name="OK"]    duration=${2}   # draw an overlay (debug)
```

## Locator Strategy

1. **Default namespace is `control`** — `//Button` ≡ `//control:Button`. Add `control:` only for clarity.
2. **Always prefix `app:` and `item:`** — applications and container items are NOT in the default namespace. Forgetting this is the most common cause of "element not found."
3. **Prefer `@Id` over `@Name`** — `[@Id="num5Button"]` is language-independent and stable (UIA AutomationId / AT-SPI accessible_id / AX AXIdentifier). Use `@Name` only when no Id exists.
4. **Anchor on the application, then descend** — `app:Application[@Name='…']//control:Window//control:Button[@Id='…']`. Or `Set Root` once on the app/window and use short relative queries (`.//Button[@Id='…']`).
5. **Handle localization with `or`** — `[@Name='Calculator' or @Name='Rechner']`.
6. **Fuzzy match with functions** — `contains(@Name,'Save')`, `matches(@Name,'.*Save.*')`, `[contains(@*,'Close')]` (search across all attributes).
7. **Step axes when structure beats identity** — `…/Label[@Name='5']/parent::Button`.
8. **Let resolution wait** — don't `Sleep`; the descriptor retries for ~30 s.

## Common Patterns

### Launch an app, scope to it, act

```robotframework
*** Settings ***
Library      PlatynUI.BareMetal
Library      Process
Test Setup   Start Calculator

*** Keywords ***
Start Calculator
    Start Process    calc.exe
    # Prefer letting the next Query wait over a fixed Sleep.

Enter Digit
    [Arguments]    ${d}
    Set Root       app:Application[@Name="ApplicationFrameHost"]/control:Window[@Name="Calculator" or @Name="Rechner"]
    Pointer Click    .//control:Button[@Id="num${d}Button"]
```

### Type into a field and assert

```robotframework
Keyboard Type    //control:Edit[@Name="Search"]    robot framework${\n}
Get Attribute    //control:Edit[@Name="Search"]    Value    ==    robot framework
```

### Verify targeting before automating

```robotframework
${node}=    Query        //control:Button[@Name="Submit"]    only_first=${True}
Highlight    ${node}     duration=${2}      # visually confirm you matched the right node
Pointer Click    ${node}
```

## CLI Tooling (locator development loop)

Develop and debug selectors with `platynui-cli` before baking them into tests:

```bash
platynui-cli list-providers                          # confirm a provider is active
platynui-cli query "//control:Button[@Name='OK']"    # test a selector live
platynui-cli snapshot "//control:Window" --pretty    # dump a UI subtree
platynui-cli highlight "//control:Button[@Name='OK']"  # visually confirm on screen
```

`platynui-inspector` is a GUI that shows the live UI tree, lets you test XPath interactively, and highlights matches. See `references/cli-and-inspector.md`.

## Troubleshooting

- **`pip install robotframework-PlatynUI` gives a library with no `BareMetal`** → you got `0.9.2`; reinstall with `--pre` or pin `==0.12.0.dev330`.
- **Linux: queries return nothing / empty tree** → AT-SPI2 not running, or accessibility not enabled. See `references/platform-setup.md` (`platynui-cli list-providers` should show the `atspi` provider active).
- **Wayland: clicks land wrong / screenshots fail** → use an X11 (or XWayland) session; Wayland is degraded for input injection and screen coordinates.
- **`ElementNotFoundError`** → check the namespace prefix (`item:`/`app:`), prefer `@Id`, and verify the selector with `platynui-cli query`.
- **`ProviderError: requires building with feature 'mock-provider'`** → `use_mock=${True}` needs a source build; the published wheel has no mock provider.

## When to Load Additional References

| Need | Reference File |
|------|----------------|
| Full keyword signatures, args, return types | `references/keywords-reference.md` |
| XPath syntax, namespaces, roles, axes, locator best practices | `references/locators-and-queries.md` |
| `platynui-cli` subcommands + the inspector | `references/cli-and-inspector.md` |
| Install matrix, Linux AT-SPI/X11/Wayland, mock, Docker | `references/platform-setup.md` |
| BareMetal-vs-high-level status, version footgun, migration | `references/status-and-migration.md` |

## Companion Skills

| Need | Skill |
|------|-------|
| Search for keywords across libraries | `libdoc-search` |
| Explain keyword arguments in detail | `libdoc-explain` |
| Generate user keywords | `keyword-builder` |
| Generate test cases | `testcase-builder` |
| Design resource file layout | `resource-architect` |
| Parse test results from output.xml | `results` |
