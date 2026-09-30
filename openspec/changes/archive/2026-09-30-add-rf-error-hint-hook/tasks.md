## 1. Hook

- [x] 1.1 Add `plugins/rf-agentskills/scripts/rf_error_hints.mjs` (D1–D3) and register it in `hooks/hooks.json` under PostToolUse with matcher `Bash`, timeout 10. Update the hooks README. Verify: `node --check`; tests in 1.2.
- [x] 1.2 Add tests to `tests/test_hook_scripts.py`: embedded hint for "No keyword with name", each other kind, once per session, unrelated output, malformed stdin, and the 400-character bound. Verify: `uv run pytest -q tests/test_hook_scripts.py`.

## 2. Distribution and measurement

- [x] 2.1 Sync, drift check, `uv build installer/`, CHANGELOG entries, and both test suites. Verify: all pass.
- [x] 2.2 Re-measure `narrow-language-embedded-01` locally with at least 9 treatment runs, and record the pass rate and skill loads in design.md. Verify: at least 8 of 9 pass. Result: 4/9 at 14 turns, and **9/9 at 25 turns** with 5/9 for the no-plugin baseline (design.md Evidence).
- [x] 2.3 Set the task to `max_turns: 25` and `timeout_seconds: 600`, and refresh its entry in `eval/baselines/narrow.json` from the 9-run 25-turn bench. Verify: the gate passes against that run.
