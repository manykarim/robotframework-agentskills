# Setup and Configuration

## Install robotcode into the project environment

robotcode must run in the **same** Python environment as Robot Framework and the test libraries. Otherwise `libdoc`, `discover` and `analyze` see different library versions, or none.

```bash
# uv project (preferred)
uv add --dev "robotcode[all]"
uv run robotcode --version

# venv + pip
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install "robotcode[all]"

# poetry
poetry add --group dev "robotcode[all]"
poetry run robotcode --version
```

`[all]` pulls in the REPL, debugger, analyzer and runner plugins. Check what will actually be used:

```bash
robotcode discover info
```

```text
- _Robot Framework:_ 7.5
- _RobotCode:_ 2.7.0
- _Python:_ 3.13.11
- _Executable:_ .venv/bin/python
```

If `Executable` is not the project's venv, you are running the wrong robotcode.

## robot.toml

`robot.toml` in the project root is read by **every** robotcode command: `robot`, `robot-debug`, `repl`, `discover`, `libdoc`, `results`, `analyze`. It replaces long `robot` command lines and argument files. `pyproject.toml` with `[tool.robot]` works as well. Files are merged in this order (later wins): the user default `~/.config/robotcode/robot.toml`, `pyproject.toml`, `robot.toml`, and a personal, untracked `.robot.toml`. `robotcode config files` shows which were found.

Minimal example (full version: `assets/examples/robot.toml`):

```toml
output-dir = "results/latest"
python-path = ["resources", "libraries"]
paths = ["tests"]                       # lets `discover` / `robot` run without path arguments

[variables]
HEADLESS = "true"

[profiles.headed]
description = "Run browsers with a visible window"
variables = { HEADLESS = "false" }

[profiles.ci]
description = "CI run: virtual display, separate output folder"
output-dir = "results/ci"
wrapper = ["xvfb-run", "-a"]
```

- Keys are `robot` long options in kebab-case (`output-dir`, `python-path`, `variables`, `include`, `exclude`, …).
- `extend-*` variants (`extend-variables`, `extend-python-path`, …) add to the inherited value instead of replacing it. Use them in profiles.
- `[variables]` is also loaded by the REPL and the debugger (they show up in `.vars`).
- Without `paths` in `robot.toml`, `discover` and `robot` need path arguments. Otherwise they fail with `Expected at least 1 argument, got 0.`

## Profiles

```bash
robotcode profiles list                 # names and descriptions
robotcode profiles show headed          # one profile's settings
robotcode -p headed robot               # use a profile (global option, before the subcommand)
robotcode -p ci -p headed robot         # combine profiles
```

Profiles apply to every command: `robotcode -p baseline discover tests`, `robotcode -p headed repl`, `robotcode -p ci results summary` (reads that profile's `output-dir`).

`default-profiles = ["dev"]` in `robot.toml` selects profiles when no `-p` is given. The env var `ROBOTCODE_PROFILES` does the same.

## Inspecting configuration

| Command | Shows |
|---|---|
| `robotcode config show` | The merged configuration from all config files |
| `robotcode config files` | Which config files were found and used |
| `robotcode config root` | The detected project root |
| `robotcode config info list` | Every supported `robot.toml` key |
| `robotcode config info desc <key>` | Documentation for one key, e.g. `wrapper` |

Useful global options (before the subcommand):

| Option | Env var | Meaning |
|---|---|---|
| `-p, --profile` | `ROBOTCODE_PROFILES` | Select profile(s) |
| `-c, --config PATH` | `ROBOTCODE_CONFIG_FILES` | Use a specific config file |
| `-r, --root DIR` | `ROBOTCODE_ROOT` | Override the project root |
| `-f, --format toml\|json\|json_indent\|text` | — | Output format for discover/results/config |
| `-d, --dry` | `ROBOTCODE_DRY` | Print what would run, don't run it (see gotchas: wrappers still run) |
| `--no-color`, `--no-pager` | `ROBOTCODE_COLOR`, `ROBOTCODE_PAGER` | Plain output (automatic in agent terminals) |

## Git hygiene

robotcode creates `.robotcode_cache/` in the project root (analysis and library cache). Add it and the output directory to `.gitignore`:

```gitignore
.robotcode_cache/
results/
```
