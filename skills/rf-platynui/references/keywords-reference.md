# PlatynUI.BareMetal — Keyword Reference

Complete keyword surface of `Library    PlatynUI.BareMetal` (verified against `robotframework-PlatynUI==0.12.0.dev330`, library version `0.12.0-dev.330`, scope `SUITE`, doc format `ROBOT`). **24 keywords, all documented.**

> The high-level `PlatynUI` library is a placeholder (`Dummy Keyword` only). Use `BareMetal`.

## Import

```robotframework
Library    PlatynUI.BareMetal
...    keyboard_profile=${None}     # KeyboardProfileLike | dict | None
...    pointer_settings=${None}     # PointerSettingsLike | dict | None
...    pointer_profile=${None}      # PointerProfileLike  | dict | None
...    use_mock=${False}            # mock provider (needs --features mock-provider build)
...    auto_activate=${True}        # foreground target window before pointer/keyboard
```

All import args are keyword-only and optional.

## Element references

Most keywords take a `descriptor: UiNodeDescriptor` — pass either:
- a **PlatynUI XPath string** (e.g. `//control:Button[@Name="OK"]`) — auto-converted, lazily resolved with retry (~30 s) until the node appears or `ElementNotFoundError` is raised, or
- a **`UiNode`** captured from `Query ... only_first=${True}`.

Where the signature shows `descriptor: ... | None`, passing `${None}` means "no element" (act on raw coordinates, or type into whatever currently has focus).

## Query & scope

| Keyword | Arguments | Returns | Notes |
|---------|-----------|---------|-------|
| `Query` | `expression: str`, `root: UiNode \| None = None`, `only_first: bool = False` | node / list / value | Evaluate an XPath expression. `only_first=${True}` → first `UiNode` or `${None}`. Value expressions (`count(...)`) return the computed value. Read-only. |
| `Set Root` | `descriptor: UiNodeDescriptor \| None` | previous root | Scope subsequent queries to a subtree. `${None}` resets to the desktop. |

## Pointer / mouse

Shared optional args (keyword-only `*`): `button: PointerButtonLike = LEFT` (`LEFT`/`MIDDLE`/`RIGHT` or `1`/`2`/`3`), `x`/`y: float | None`, `overrides: PointerOverridesLike | None`, `activate: bool | None` (defaults to library `auto_activate`). See coordinate rules in SKILL.md.

| Keyword | Arguments | Short doc |
|---------|-----------|-----------|
| `Pointer Click` | `descriptor=None`, `*`, `button=LEFT`, `x=None`, `y=None`, `overrides=None`, `activate=None` | Click at absolute or element-relative screen coordinates. |
| `Pointer Multi Click` | …above… `+ clicks: int = 2` | Multiple clicks (double=`${2}`, triple=`${3}`). |
| `Pointer Press` | same as Pointer Click | Press (and hold) a mouse button. |
| `Pointer Release` | same as Pointer Click | Release a mouse button at current or specified coordinates. |
| `Pointer Move To` | `descriptor=None`, `*`, `x=None`, `y=None`, `overrides=None`, `activate=None` | Move the pointer (no `button`). |
| `Get Pointer Position` | `assertion_operator=None`, `assertion_expected=None`, `assertion_message=None` | Current pointer position (assertable). |

## Keyboard

| Keyword | Arguments | Short doc |
|---------|-----------|-----------|
| `Keyboard Type` | `descriptor: UiNodeDescriptor \| None`, `text: str`, `*`, `overrides: KeyboardOverridesLike \| None = None` | Type a sequence of characters and/or keys (full press→release). |
| `Keyboard Press` | `descriptor \| None`, `text: str`, `*`, `overrides=None` | Press (and hold) keys. |
| `Keyboard Release` | `descriptor \| None`, `text: str`, `*`, `overrides=None` | Release keys. |

`descriptor` is positional but may be `${None}` (skip focusing). Key syntax: `<Ctrl+A>`, `<Return>`, `<ESC>`, `<Shift+Tab>`, plain text, `${\n}`. List valid key names: `platynui-cli keyboard list`.

## Focus & attributes

| Keyword | Arguments | Short doc |
|---------|-----------|-----------|
| `Focus` | `descriptor: UiNodeDescriptor` | Set input focus to the element (brings to front + focuses). |
| `Bring To Front` | `descriptor: UiNodeDescriptor` | Bring the node to the front (no focus). |
| `Get Attribute` | `descriptor`, `attribute_name: str`, `assertion_operator=None`, `assertion_expected=None`, `assertion_message=None` | Read an attribute (assertable). `ns:Name` selects a namespace. |

`Get Attribute` is **assertable** — `Get Attribute  //control:Button[@Name="OK"]  Name  ==  OK`. Typed/structured attributes expose component aliases (`Bounds.X`, `Bounds.Width`, `ActivationPoint.Y`).

## Window surface

All take `descriptor: UiNodeDescriptor` and require a window node (else `PatternError`).

| Keyword | Extra args | Short doc |
|---------|-----------|-----------|
| `Activate Window` | — | Activate (bring to front and focus) a window. |
| `Bring To Front` | — | (listed above — front without focus) |
| `Minimize Window` | — | Minimize a window. |
| `Maximize Window` | — | Maximize a window. |
| `Restore Window` | — | Restore from minimized/maximized. |
| `Close Window` | — | Close a window. |
| `Move Window` | `x: float`, `y: float` | Move top-left to screen coordinates. |
| `Resize Window` | `width: float`, `height: float` | Resize. |
| `Move And Resize Window` | `x`, `y`, `width`, `height` (float) | Move + resize in one operation. |

## Diagnostics

| Keyword | Arguments | Short doc |
|---------|-----------|-----------|
| `Take Screenshot` | `descriptor=None`, `filename='platynui-screenshot-{index}.png'`, `rect: RectLike \| None = None` | Full screen, an element (its bounds), or a rect. `filename=EMBED` embeds base64 PNG in the log; files go to `${OUTPUT DIR}`; `{index}` auto-increments. |
| `Highlight` | `descriptor: ... \| list \| None = None`, `*`, `rect: RectLike \| list \| None = None`, `duration: float = 1.0` | Draw an overlay around one/many elements or rect(s) for `duration` seconds. Needs at least one of descriptor/rect. |

## Not present (know the gaps)

- **No application launch/attach keyword** — launch with `Library Process` (`Start Process    calc.exe`) and locate via `app:Application[...]`.
- **No explicit wait/retry keyword** — resolution waits automatically (~30 s). There is no runtime keyword to change that timeout.
- **No semantic action keywords** (`Activate`, `Select`, `Set Value`, `Check`) — these are the *intended direction* of the high-level library, not shipped. Compose `Pointer Click` / `Keyboard Type` / `Query` instead. See `status-and-migration.md`.

## Types referenced

- `PointerButtonLike` = `PointerButton` enum (`LEFT=1`, `MIDDLE=2`, `RIGHT=3`) or `int`.
- `RectLike` = `Rect` | `(x, y, width, height)` tuple | `{x, y, width, height}` dict.
- `*OverridesLike` / `*ProfileLike` / `*SettingsLike` = native object or a `&{dict}` (keys like `press_delay_ms`, `between_keys_delay_ms`, `acceleration_profile`, `motion`, `jitter_amplitude`, `multi_click_delay_ms`).
- Exceptions: `BareMetalError` → `ElementNotFoundError`, `ResultTypeError`, `NoQueryError`; native `PlatynUiError` → `PatternError`, `PointerError`, `KeyboardError`, `ProviderError`, …
