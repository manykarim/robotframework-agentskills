# sut-legacy-style

Robot Framework project (RF 7.4) whose existing code is written in pre-RF 7
style. Used by the adversarial task `adv-legacy-syntax-01`: the prompt asks for a
new keyword "in the same style as the existing ones"; the task passes only when
the new file uses modern syntax (zero Robocop `DEPR` findings) and the suites
still pass.

- `resources/legacy.resource`: order keywords using `[Return]`,
  `Run Keyword If`, `Set Suite Variable` / `Set Test Variable` and `Create List`
  (Robocop DEPR11, DEPR08, DEPR05, DEPR06).
- `tests/cart.robot`: two passing tests; its Settings use `Force Tags` (DEPR07).

Run from this directory:

```bash
robot tests
robocop check --no-cache --select "DEPR*" resources/legacy.resource
```
