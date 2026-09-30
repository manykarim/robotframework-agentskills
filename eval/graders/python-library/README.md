# Hidden grader suites (rf-python-library tasks)

These suites are **never staged into the agent's workspace** (the runner copies
only `eval/fixtures/<fixture>/`). `rf_skill_eval.scoring.custom.python_library`
copies a suite into the run's artifacts directory and runs it with the
workspace as the working directory and `--pythonpath <workspace>/libraries`, so
the suites import the agent's library by module name.

| Suite | Task | Checks |
|---|---|---|
| `inventory.robot` | `narrow-python-library-inventory-scope-01` | `Add Item` state survives across three tests of one suite (fails with the default `TEST` scope), a wrong count fails, `Clear Inventory` empties the stock. |
| `mode.robot` | `narrow-python-library-mode-literal-01` | `Set Mode` accepts `on` / `OFF` / `Off` and returns `ON`/`OFF`; `maybe` fails with a message naming `ON`. |
| `flaky.robot` | `narrow-python-library-flaky-listener-01` | with `--listener FlakySkip`: the failing `flaky` test is SKIP, the other test PASS, exit code 0. |
| `flaky_real_failure.robot` | `narrow-python-library-flaky-listener-01` | with `--listener FlakySkip`: a failing test without the tag stays FAIL (exit code 1), a passing flaky test stays PASS. |
