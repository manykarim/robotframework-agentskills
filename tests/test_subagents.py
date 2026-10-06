"""Lint test for the plugin subagents (openspec change modernize-plugin-agents-and-hooks).

The four subagents in ``plugins/rf-agentskills/agents/`` are thin routers: they
keep only content no skill owns (marked "agent-owned"), route everything else to
the skills by identifier, share one verification loop and stay portable across
the agents the installer copies them to (Claude Code, OpenCode, Cursor).
"""

from __future__ import annotations

import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "rf-agentskills"
AGENTS_DIR = PLUGIN / "agents"
AGENT_NAMES = ("rf-test-architect", "rf-keyword-consultant", "rf-migration-guide", "rf-debug-expert")
LEGACY_FIXTURE = ROOT / "eval" / "fixtures" / "sut-legacy-style"
MAX_BODY_LINES = 120

# The shared verification loop, verbatim in every agent (design D2 §4).
VERIFICATION_LOOP = """\
## Verification loop

For every `.robot`, `.resource` or Python library file you write or change:

1. Write the change.
2. Confirm keyword names and arguments with the `rf-libdoc` skill (its search and explain commands), or with `robotcode libdoc` when robotcode is installed (`rf-robotcode`).
3. Run `robot --dryrun` on the affected suites. The dry run does not catch undefined variables, a space before `=` in named arguments, embedded-argument mismatches or union-with-`str` conversions; the real run in step 5 does.
4. Run `robocop check --no-cache` on the changed files (select several rule groups by repeating `--select`, never with a comma list).
5. Run the affected tests (`robot -t "<test name>"` or `--suite`).
6. Read failures with the `rf-results` skill (its summary of `output.xml`), or with `robotcode results`.
"""

RETIRED = (
    "keyword-builder",
    "testcase-builder",
    "resource-architect",
    "libdoc-search",
    "libdoc-explain",
    "rf-test-design",
    "rf-keyword-design",
)
PRE_RENAME_RE = re.compile(r"robotframework-[a-z-]*-skill\b|robotframework-libdoc")
RF_NAME_RE = re.compile(r"(?<![\w/-])rf-[a-z][a-z-]*[a-z]\b")
TYPED_ARG_RE = re.compile(r"\[Arguments\].*\$\{[^}]+\}:\s*[A-Za-z]")
COMMA_SELECT_RE = re.compile(r"""(--select|-s)\s+(['"])[^'"\n]*,[^'"\n]*\2""")
FENCE_RE = re.compile(r"^```(\w*)[^\n]*\n(.*?)^```", re.M | re.S)


def _text(name: str) -> str:
    return (AGENTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _split(name: str) -> tuple[str, str]:
    text = _text(name)
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, f"{name}: missing frontmatter"
    return m.group(1), text[m.end():]


def _body(name: str) -> str:
    return _split(name)[1]


def _catalog() -> set[str]:
    skills = {p.name for p in (PLUGIN / "skills").iterdir() if p.is_dir()}
    return skills | set(AGENT_NAMES)


def _section(body: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", body, re.M | re.S)
    assert m, f"missing section '## {heading}'"
    return m.group(1)


def _robocop() -> list[str] | None:
    try:
        rc = subprocess.run([sys.executable, "-c", "import robocop"], capture_output=True, timeout=60).returncode
    except (OSError, subprocess.SubprocessError):
        return None
    return [sys.executable, "-m", "robocop"] if rc == 0 else None


def test_agent_set_is_the_expected_four() -> None:
    assert sorted(p.stem for p in AGENTS_DIR.glob("*.md")) == sorted(AGENT_NAMES)


@pytest.mark.parametrize("name", AGENT_NAMES)
def test_body_line_budget(name: str) -> None:
    lines = _body(name).strip("\n").splitlines()
    assert len(lines) <= MAX_BODY_LINES, f"{name}: {len(lines)} body lines > {MAX_BODY_LINES}"


@pytest.mark.parametrize("name", AGENT_NAMES)
def test_frontmatter_is_portable(name: str) -> None:
    """Only keys every target agent understands; no Claude-only `skills:` preload."""
    front, _ = _split(name)
    keys = {ln.split(":", 1)[0] for ln in front.splitlines() if re.match(r"^[a-z_-]+:", ln)}
    assert keys == {"name", "description"}, keys
    assert re.search(rf"^name: {name}$", front, re.M)


@pytest.mark.parametrize("name", AGENT_NAMES)
def test_routing_names_exist(name: str) -> None:
    names = set(RF_NAME_RE.findall(_text(name))) - {"rf-agentskills"}
    assert names, name
    unknown = names - _catalog()
    assert not unknown, f"{name}: unknown skill/agent names {sorted(unknown)}"


@pytest.mark.parametrize("name", AGENT_NAMES)
def test_no_retired_or_pre_rename_names(name: str) -> None:
    text = _text(name)
    for retired in RETIRED:
        assert retired not in text, f"{name}: retired name {retired}"
    assert not PRE_RENAME_RE.search(text), f"{name}: pre-rename identifier"


@pytest.mark.parametrize("name", AGENT_NAMES)
def test_routing_table_present(name: str) -> None:
    routing = _section(_body(name), "Routing")
    assert "| Work | Skill |" in routing
    rows = [ln for ln in routing.splitlines() if ln.startswith("| ") and "---" not in ln][1:]
    assert len(rows) >= 4, rows
    for row in rows:
        assert RF_NAME_RE.search(row), f"{name}: routing row without a skill: {row}"


@pytest.mark.parametrize("name", AGENT_NAMES)
def test_no_invalid_typed_arguments(name: str) -> None:
    for line in _text(name).splitlines():
        assert not TYPED_ARG_RE.search(line), f"{name}: invalid typed argument form: {line}"


@pytest.mark.parametrize("name", AGENT_NAMES)
def test_verification_loop_is_canonical(name: str) -> None:
    body = _body(name)
    assert VERIFICATION_LOOP in body, f"{name}: verification loop differs from the canonical text"
    loop = _section(body, "Verification loop")
    order = ["Write the change", "robotcode libdoc", "robot --dryrun", "robocop check", "robot -t", "`rf-results` skill"]
    positions = [loop.index(step) for step in order]
    assert positions == sorted(positions)
    for blind in ("undefined variables", "named arguments", "embedded-argument", "union-with-`str`"):
        assert blind in loop


@pytest.mark.parametrize("name", AGENT_NAMES)
def test_no_plugin_paths_or_script_commands(name: str) -> None:
    text = _text(name)
    assert "${CLAUDE_PLUGIN_ROOT}" not in text
    assert "${CLAUDE_SKILL_DIR}" not in text
    assert "scripts/" not in text, f"{name}: script path"
    assert "mcp__" not in text, f"{name}: MCP tools are named without an agent-specific prefix"
    # rf_conventions stays: it is also the rf-language script's report name.
    for tool in ("rf_libdoc_search", "rf_libdoc_explain", "rf_results_analyze", "rf_check_library"):
        assert tool not in text, f"{name}: names the retired rf-tools MCP tool {tool}"


@pytest.mark.parametrize("name", AGENT_NAMES)
def test_agent_owned_content_is_marked(name: str) -> None:
    assert "(agent-owned)" in _body(name)


@pytest.mark.parametrize("name", AGENT_NAMES)
def test_robocop_commands_use_no_cache(name: str) -> None:
    for cmd in re.findall(r"`(robocop check[^`]*)`", _text(name)):
        assert "--no-cache" in cmd, f"{name}: {cmd}"


def _depr_findings(blocks: list[str], tmp_path: Path) -> list[str]:
    """``robocop check --select DEPR*`` findings for code blocks (each as a file)."""
    if not blocks:
        return []
    robocop = _robocop()
    if robocop is None:
        pytest.skip("robocop not installed")
    files = []
    for i, code in enumerate(blocks):
        f = tmp_path / f"block{i}.robot"
        f.write_text(code, encoding="utf-8")
        files.append(str(f))
    proc = subprocess.run([*robocop, "check", "--no-cache", "--ignore-file-config", "--select", "DEPR*", *files],
                          capture_output=True, text=True, timeout=120, cwd=tmp_path)
    return re.findall(r"\b(DEPR\d+)\b", proc.stdout)


def test_depr_block_scan_detects_legacy_syntax(tmp_path: Path) -> None:
    legacy = "*** Keywords ***\nK\n    Run Keyword If    ${TRUE}    Log    x\n    [Return]    1\n"
    assert {"DEPR08", "DEPR11"} <= set(_depr_findings([legacy], tmp_path))


@pytest.mark.parametrize("name", AGENT_NAMES)
def test_robotframework_blocks_are_deprecation_clean(name: str, tmp_path: Path) -> None:
    """Legacy constructs may only appear in Markdown mapping tables, never in
    ```robotframework blocks."""
    blocks = [code for lang, code in FENCE_RE.findall(_text(name)) if lang in ("robotframework", "robot")]
    assert not _depr_findings(blocks, tmp_path), name


def test_no_comma_select_anywhere() -> None:
    """The comma form `--select 'DEPR*,ERR*'` matches no rule in Robocop 8.2/9.1."""
    paths = [*AGENTS_DIR.glob("*.md"), *(PLUGIN / "hooks").glob("*"), *(PLUGIN / "scripts").glob("*.mjs"),
             *(ROOT / "skills").rglob("*.md"), *(PLUGIN / "skills").rglob("*.md")]
    offenders = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        # The hooks README names the trap once, as the thing not to do.
        text = text.replace("(`--select 'DEPR*,ERR*'`)", "")
        if COMMA_SELECT_RE.search(text):
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, offenders


# --- per-agent content ------------------------------------------------------------


def test_test_architect_routes_design_to_skills() -> None:
    body = _body("rf-test-architect")
    routing = _section(body, "Routing")
    for skill in ("rf-language", "rf-python-library", "rf-setup", "rf-browser", "rf-requests", "rf-libdoc"):
        assert skill in routing, skill
    assert "4KB" not in body and "SKILL.md" not in body
    assert "Browser" in body and "RESTinstance" in body  # library-selection criteria stay
    assert "resources/" in body  # project layout stays
    assert "[Template]" not in body, "template advice lives in rf-language"


def test_keyword_consultant_has_no_catalog() -> None:
    body = _body("rf-keyword-consultant")
    for legacy in ("Run Keyword If", "Create List", "Set Variable"):
        assert legacy not in body, legacy
    assert "| Browser Library | SeleniumLibrary |" not in body
    assert "Standard Libraries Quick Reference" not in body
    routing = _section(body, "Routing")
    for skill in ("rf-libdoc", "rf-robotcode", "rf-language", "rf-python-library"):
        assert skill in routing, skill
    assert "search command" in body and "explain command" in body
    assert "Browser.Click" in body  # library-prefix disambiguation rule stays


def test_migration_guide_uses_deterministic_checker() -> None:
    body = _body("rf-migration-guide")
    assert "rf-language" in body and "references/migration.md" in body and "rf_conventions" in body
    assert '--select "DEPR*"' in body and "--reports rules_by_id" in body
    assert "--threshold E" in body and "--target-version" in body
    assert "--fix" in body and "clean git" in body
    assert "unverified" in body and "rf-setup" in body
    for step in ("Inventory", "Phased plan", "Per-file fixes", "Exit check"):
        assert step in body, step
    assert "zero `DEPR`" in body
    # Library-migration tables stay, marked as the agent's own.
    assert "SeleniumLibrary → Browser (agent-owned)" in body
    assert "RequestsLibrary → RESTinstance (agent-owned)" in body
    # The RF syntax table moved to rf-language.
    assert "Run Keyword Unless    ${cond}" not in body and "Set Global Variable" not in body


def test_migration_guide_robocop_commands_find_legacy_syntax(tmp_path: Path) -> None:
    """The documented inventory/exit commands, run on the legacy fixture, report
    findings (no silent empty selection)."""
    robocop = _robocop()
    if robocop is None:
        pytest.skip("robocop not installed")
    work = tmp_path / "proj"
    shutil.copytree(LEGACY_FIXTURE, work)
    cmds = re.findall(r"`(robocop check [^`]*)`", _body("rf-migration-guide"))
    inventory = [c for c in cmds if "DEPR" in c]
    assert inventory, cmds
    for cmd in inventory:
        args = shlex.split(cmd)[2:]
        args = [a for a in args if not a.startswith("<")]
        proc = subprocess.run([*robocop, "check", *args], capture_output=True, text=True, timeout=120, cwd=work)
        out = proc.stdout
        for rule in ("DEPR11", "DEPR08", "DEPR05", "DEPR07"):
            assert rule in out, (cmd, out)
        assert "No issues found" not in out
    assert not (work / ".robocop_cache").exists()


def test_debug_expert_routes_failure_classes() -> None:
    body = _body("rf-debug-expert")
    assert "Wait Until Keyword Succeeds" not in body
    assert not re.search(r"(?i)increase (the )?timeouts?", body)
    routing = _section(body, "Routing")
    rows = {ln.split("|")[1].strip(): ln for ln in routing.splitlines() if ln.startswith("| ") and "---" not in ln}
    joined = "\n".join(rows.values())
    assert re.search(r"contains no keywords.*rf-python-library", joined)
    assert re.search(r"(?i)name conflict.*rf-language", joined)
    assert re.search(r"(?i)__init__\.robot.*rf-language", joined)
    assert re.search(r"(?i)step.*rf-robotcode", joined)
    assert "rf-results" in joined
    assert "with the `rf-results` skill" in body
    assert "FAILURE:" in body and "CATEGORY:" in body
