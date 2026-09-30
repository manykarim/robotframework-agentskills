# Hidden grader suites (rf-language tasks)

These suites are **never staged into the agent's workspace** (the runner copies
only `eval/fixtures/<fixture>/`). `rf_skill_eval.scoring.custom.language`
copies a suite into the run's artifacts directory and runs it with the workspace
as the working directory and on the python-path (`--pythonpath <workspace>
--pythonpath <workspace>/libraries`), so the suites import the agent's files as
`resources/<name>.resource` and libraries by module name.

| Suite | Task | Checks |
|---|---|---|
| `teams_binding.robot` | `narrow-language-embedded-01` | `Select team <city> <team>` binds multi-word cities (Los Angeles Lakers, Golden State Warriors, New York Knicks) and one-word cities (Chicago Bulls). |
| `env_staging.robot` | `narrow-language-env-varfiles-01` | run with `--variablefile variables/staging.yaml`: staging values. |
| `env_dev.robot` | `narrow-language-env-varfiles-01` | run with `--variablefile variables/dev.yaml`: dev values. |
