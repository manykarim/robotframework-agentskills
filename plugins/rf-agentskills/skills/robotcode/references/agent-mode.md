# AI-Agent Mode, Pipes and Terminals

## Detection

robotcode checks for environment variables that AI agents set and, when it finds one, switches to agent-friendly defaults: no colour, no pager, and the **plain line-by-line REPL/debugger backend**. Variables it checks (robotcode 2.7.0) include:

`AI_AGENT`, `AGENT`, `CLAUDECODE`, `CLAUDE_CODE`, `CURSOR_AGENT`, `CODEX_CI`, `CODEX_THREAD_ID`, `GEMINI_CLI`, `COPILOT_AGENT`, `COPILOT_AGENT_SESSION_ID`, `VSCODE_AGENT`, `OPENCODE`, `AUGMENT_AGENT`, `CLINE_ACTIVE`, and a few others.

A variable counts when it is set to anything other than empty or `0`.

Overrides:

| Variable | Effect |
|---|---|
| `ROBOTCODE_FORCE_AI_AGENT=1` | Force agent mode on (wins over everything). Use it when your agent's marker isn't recognised. |
| `ROBOTCODE_NO_AI_AGENT=1` | Force agent mode off (loses only to `ROBOTCODE_FORCE_AI_AGENT`) |

## Pipe vs terminal (PTY)

| How robotcode is started | Backend | Result |
|---|---|---|
| Input from a pipe / file (`printf … \|`, `<`) | plain | Works, line by line. Same output with agent mode on or off. |
| Real terminal (PTY), agent mode **on** | plain | Works; `.exit` ends the session. |
| Real terminal (PTY), agent mode **off** | prompt-toolkit | ❌ Piped lines are taken as **one pasted multi-line block** (`...` prompts), nothing runs, and the REPL waits until killed. |
| Any, with `--plain` | plain | Works |

Rules for agents and scripts:

1. Always feed `repl` and `robot-debug` from a pipe or file.
2. Always pass `--plain` (and `--no-history`). It costs nothing and protects against the PTY case.
3. End REPL input with `.exit`.
4. Put a `timeout` around the call when you run it from a script: `timeout 300 robotcode robot-debug --plain … < cmds.rdb`.
5. For the debugger, EOF while paused resumes the run, so a short command list is safe.

On **Windows**, set `PYTHONUTF8=1` for robotcode commands whose output is piped or captured. Otherwise text output with ❌/✅ or `→` can crash with `UnicodeEncodeError` under the cp1252 console encoding. `--format json` output is not affected.

`discover`, `libdoc`, `results` and `analyze` are not interactive. Agent mode only removes colour and the pager there, so their output is the same.

## Secrets in output

- RequestsLibrary (and other HTTP libraries) log full request and response bodies at INFO level. In REPL and debugger output, **passwords and tokens appear in plain text**, for example `&{creds} = { username=admin | password=password123 }`.
- The same data ends up in `output.xml` / `log.html`, and in `robotcode results log` output.
- Don't paste raw REPL, debugger or `results log` output into commits, issues or reports without checking it. Prefer showing selected values with `Log To Console`. For tests, use the library's secret handling (for example Browser's `Fill Secret`) and `Set Log Level` around sensitive steps.
