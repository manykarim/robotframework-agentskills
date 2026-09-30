# sut-platynui

Spec-only PlatynUI fixture (desktop automation over Windows UIA / Linux
AT-SPI2). The CI runner has no desktop session, so tasks on this fixture are
graded **statically** with `keywords_resolve` against the committed libdoc spec
`specs/PlatynUI.BareMetal.json` (PlatynUI 0.12.0.dev330).

## Application under test: Calculator

The standard desktop calculator (Windows Calculator / GNOME Calculator).

| Element | XPath (PlatynUI desktop tree) |
|---|---|
| Main window | `//control:Window[@Name='Calculator']` |
| Digit buttons | `//control:Button[@Name='One']` … `//control:Button[@Name='Nine']` |
| Plus / Equals | `//control:Button[@Name='Plus']`, `//control:Button[@Name='Equals']` |
| Result display | `//control:Text[@AutomationId='CalculatorResults']` |

`tests/example.robot` is a stub that resolves cleanly. Real execution stays a
manual, local activity on a desktop machine.

## Refreshing the spec

```bash
uv run python -m robot.libdoc PlatynUI.BareMetal eval/fixtures/sut-platynui/specs/PlatynUI.BareMetal.json
```
