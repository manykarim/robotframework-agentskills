# sut-appium

Spec-only AppiumLibrary fixture. There is no device, emulator or Appium server
on the CI runner, so tasks on this fixture are graded **statically** with the
`keywords_resolve` check: the produced suite must parse and every keyword must
resolve against the committed libdoc spec `specs/AppiumLibrary.json` (plus the
suite's own user keywords and standard libraries).

- `app/SCREENS.md` — the Demo Login app contract (accessibility ids, activity).
- `tests/example.robot` — a stub that resolves cleanly.
- `specs/AppiumLibrary.json` — libdoc spec (AppiumLibrary 3.2.1).

Real execution against an emulator stays a manual, local activity.

## Refreshing the spec

```bash
uv run python -m robot.libdoc AppiumLibrary eval/fixtures/sut-appium/specs/AppiumLibrary.json
```

Refreshing the spec changes the fixture hash, so the affected baseline entries
report `rebaseline-needed` until the next weekly baseline is promoted.
