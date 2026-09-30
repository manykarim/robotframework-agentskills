# PlatynUI Locators & Queries

PlatynUI's analog of Browser Library's "locators" is an **XPath-2.0 query engine over a normalized desktop UI tree**. Selectors are XPath strings; node names are roles; namespaces scope the query.

## The UI model

Every application's accessibility tree is normalized into one model rooted at the **Desktop** document node. Each node exposes:

- `role()` — normalized PascalCase role (`Window`, `Button`, `Edit`, `ListItem`…). The original native role is preserved under `native:Role`.
- `Name` — display name (`@Name`).
- `Id` — developer-set stable id (`@Id`): UIA AutomationId / AT-SPI accessible_id / macOS AXIdentifier.
- typed attributes — `Bounds`, `IsVisible`, `IsEnabled`, `IsFocused`, `IsSelected`, `Value`, `Text`, `ActivationPoint`, `ToggleState`, … Structured values auto-expose component aliases: `Bounds.X`, `Bounds.Width`, `ActivationPoint.Y`.

Top-level controls appear both directly under the desktop (flat) and under `app:Application` nodes (grouped) — so `app:Application[@Name='Studio']//control:Window` works.

## Namespaces (scope selector)

| Prefix | Scope | Examples | Default? |
|--------|-------|----------|----------|
| `control` | UI controls | `Window`, `Button`, `Edit`, `Menu`, `Tree`, `Table` | **Yes** |
| `item` | container children | `ListItem`, `TreeItem`, `TabItem`, `Cell`, `Row` | No |
| `app` | application/process | `Application` | No |
| `native` | raw platform attrs | `native:HWND`, `native:Role`, `native:Accessible.*` | No |

**The single most important rule:** an unprefixed query matches `control:` only. `//Button` ≡ `//control:Button`. To match container items you MUST write `//item:ListItem` — `//ListItem` finds nothing. Always prefix `app:` and `item:`.

## Supported XPath syntax

The engine implements XPath 2.0 over live UI trees (not XML files).

**Axes:** `child` (default), `descendant` (`//`), `descendant-or-self`, `self` (`.`), `parent` (`..`), `ancestor`, `ancestor-or-self`, `following`, `following-sibling`, `preceding`, `preceding-sibling`, `attribute` (`@`), `namespace`.

**Node tests:** name tests, `*` wildcard, `node()`, `text()`, `comment()`.

**Predicates `[...]`:**
- equality: `[@Name='OK']`, `[@Id="num5Button"]`
- boolean: `[@Name='Calculator' or @Name='Rechner']`, `and`
- positional: `[1]`, `[position()=2]`, `last()`
- functions: `contains()`, `matches()` (regex), `starts-with()`, `count()`, `normalize-space()`, `string()`
- all-attribute wildcard: `[contains(@*, 'Close')]`

**Value expressions** (returned by `Query` as computed values, not nodes): `count(//control:Button)`.

Not supported: schema awareness, `fn:unparsed-text*`, static typing.

## Example selectors (from real PlatynUI tests)

| Selector | Matches | Notes |
|----------|---------|-------|
| `//control:Button[@Name="OK"]` | a button named OK | `control:` optional |
| `//Button[@Name="New File"]` | same as above unprefixed | default namespace = control |
| `app:Application[@Name="Notepad"]//Document` | a Document anywhere under Notepad | grouped `app:` view |
| `app:Application[@Name="ApplicationFrameHost"]/control:Window[@Name="Calculator" or @Name="Rechner"]` | the Calc/Rechner window | direct child `/`, locale-tolerant |
| `.//control:Button[@Id="num5Button"]` | digit button relative to root | use after `Set Root`; `@Id` stable |
| `app:Application[@Name='kalk']/Frame//item:TabItem` | a tab item | **`item:` required** |
| `…/Label[@Name='5']/parent::Button` | the button owning a label | reverse axis |
| `//*[contains(@Name,'Checked')]` | any node with "Checked" in name | `*` widens past control |
| `app:Application[@Name='…']//*[contains(@*, 'Close')]` | any node whose any attribute has "Close" | `@*` all-attribute search |
| `count(//control:Button)` | number of buttons | value expression |
| `.` | the current root node | with `Query .` |

## Role vocabulary

Common normalized roles usable as node names in queries:

- **control:** `Window`, `Frame`, `Dialog`, `Button`, `CheckBox`, `ComboBox`, `Edit`, `Text`, `List`, `Tree`, `Table`, `Menu`, `MenuBar`, `MenuItem`, `TabList`, `Document`, `Label`, `Control`.
- **item:** `ListItem`, `TreeItem`, `TabItem`, `Cell`, `EditableCell`, `Row`.
- **app:** `Application`.
- **special:** `Desktop` (root).

Cross-platform normalization (originals under `native:Role`):

| PlatynUI | UIA | AT-SPI2 | macOS AX |
|----------|-----|---------|----------|
| Button | Button | PUSH_BUTTON | AXButton |
| Edit | Edit | ENTRY/TEXT | AXTextField |
| List / ListItem | List / ListItem | LIST / LIST_ITEM | AXList / AXStaticText |
| Tree / TreeItem | Tree / TreeItem | TREE / TABLE_ROW | AXOutline / AXRow |
| Menu / MenuItem | Menu / MenuItem | MENU / MENU_ITEM | AXMenu / AXMenuItem |
| TabList / TabItem | Tab / TabItem | PAGE_TAB_LIST / PAGE_TAB | AXTabGroup / AXRadioButton |
| Window | Window | FRAME / WINDOW | AXWindow |

## Locator strategy (best practices)

1. **`control` is default** — only add `control:` for clarity.
2. **Always prefix `app:` and `item:`** — the #1 "element not found" cause.
3. **Prefer `@Id` over `@Name`** — language-independent and stable; `@Name` only when no Id.
4. **Anchor on the app, then descend** — `app:Application[@Name='…']//control:Window//control:Button[@Id='…']`, or `Set Root` once and use `.//…`.
5. **`/` vs `//` deliberately** — `/` direct child (precise/fast), `//` any descendant (broad/slower).
6. **Localization → `or`** — `[@Name='Calculator' or @Name='Rechner']`.
7. **Fuzzy → functions** — `contains(@Name,'…')`, `matches(@X,'regex')`, `[contains(@*,'…')]`.
8. **Structure → axes** — `…/Label[@Name='5']/parent::Button`.
9. **Positional `[1]` is a last resort** — brittle; prefer attribute predicates.
10. **Don't `Sleep`** — descriptor resolution retries ~30 s; write the right selector and let it wait.
11. **Develop selectors with the CLI/inspector** — `platynui-cli query "…"`, `platynui-cli highlight "…"`, or the inspector GUI (see `cli-and-inspector.md`).
