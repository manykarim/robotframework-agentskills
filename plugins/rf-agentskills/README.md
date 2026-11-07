# rf-agentskills plugin

Robot Framework skills, subagents and validation hooks for coding agents. Install instructions for every agent are in the [repository README](https://github.com/manykarim/robotframework-agentskills#install).

## Requires robotcode

Install `robotcode[all]>=2.8` in the project's Python environment, next to Robot Framework. Don't use `uvx`, `pipx` or `uv tool` for it: an isolated robotcode cannot see the project's libraries.

```bash
uv add --dev "robotcode[all]>=2.8"                 # uv
poetry add --group dev "robotcode[all]>=2.8"       # Poetry
pip install "robotcode[all]>=2.8"                  # venv + pip (venv active)
```

The `all` extra is needed because it is the only one that brings everything the skills and hooks run: `runner` (`robot`, `discover`, `results`, `libdoc`), `analyze` (`analyze code`), `repl` (`doc`, `repl`, `robot-debug`) and Robocop. A CI job that only runs tests can use `robotcode[runner]`. The `rf-setup` skill installs it for you.

## Recommended companion: the robotcode plugin

The RobotCode project publishes `robotcode@robotframework-agent-plugins`, which teaches agents to drive the robotcode CLI. Install it next to this plugin:

```bash
claude plugin marketplace add robotcodedev/robotframework-agent-plugins
claude plugin install robotcode@robotframework-agent-plugins
```

(`copilot plugin …` and `codex plugin marketplace add … / codex plugin add …` work the same way. The RobotCode VS Code extension already bundles it for Copilot Chat.) This plugin does not declare a dependency on it, so it loads either way.

| The robotcode plugin owns | rf-agentskills owns |
|---|---|
| running, discovery, keyword documentation, result analysis, static analysis, `robot.toml` configuration, the REPL and the debugger | Robot Framework syntax (`rf-language`), Python keyword libraries (`rf-python-library`), the test-library skills, environment setup (`rf-setup`), the validation hooks, and the `rf-test-architect`, `rf-debug-expert` and `rf-migration-guide` subagents |
