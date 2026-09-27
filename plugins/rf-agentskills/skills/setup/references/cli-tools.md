# Standalone CLI Tools: `uv tool`, `uvx`, `pipx`

`uv tool install`, `uvx` and `pipx` put a command-line tool into **its own isolated environment** and link the command onto PATH. That is right for tools that don't need to import your test libraries, and wrong for everything `robot` needs at run time.

| Use a tool environment for | Keep in the project environment |
|---|---|
| `rf-agentskills` (this skill bundle's installer) | `robotframework` |
| `uv` itself (`pipx install uv`) | Every test library (Browser, SeleniumLibrary, RequestsLibrary, …) |
| `platynui-cli`, `platynui-inspector` (optional PlatynUI tools) | `robotcode` (it imports your libraries for `libdoc`, `discover`, `analyze`) |
| One-off commands: `uvx rf-agentskills install` | `robocop` when it should use the project's RF version (recommended) |

Why: a library installed with `pipx install robotframework-browser` lives in `~/.local/pipx/venvs/robotframework-browser/`. Your project's `robot` can't import it, so you get `No module named 'Browser'` or `Importing library 'Browser' failed`.

## Commands

```bash
# uv
uv tool install rf-agentskills          # persistent, on PATH
uvx rf-agentskills install              # run once without installing
uv tool upgrade rf-agentskills
uv tool list

# pipx
pipx install rf-agentskills
pipx run rf-agentskills install
pipx upgrade rf-agentskills
```

Pre-release tools need an opt-in: `uv tool install --prerelease allow platynui-cli`, `pipx install --pip-args=--pre <tool>`.

## Hooks and the rf-agentskills installer

The rf-agentskills hooks (validation, environment check) run Python. The installer records the interpreter it was installed with in `python_runtime.json`, and the hooks prefer it. If hooks report "robotframework not installed" although the project has it, the hooks are using a different interpreter than the project. Install rf-agentskills (or at least `robotframework-robocop`) into the project env, or rerun the installer from inside the project env: `uv run rf-agentskills install` after `uv add --dev rf-agentskills`.
