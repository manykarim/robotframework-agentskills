"""Subprocess-based Claude Code runner (ADR-003).

Each call to :meth:`ClaudeCodeRunner.execute` spawns exactly one
``claude -p`` subprocess with:

- isolated ``CLAUDE_CONFIG_DIR`` (per-run tmp dir — no pollution of
  ``~/.claude``);
- an ``.mcp.json`` registering the skill-relevant MCP servers;
- ``--output-format stream-json`` for structured capture;
- ``--max-turns`` and wall-clock timeout bounding cost.

The runner is intentionally the *only* place that shells out to the
``claude`` binary; the rest of the codebase sees only ``Run`` values.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ...domain.profile import Profile
from ...domain.run import Run
from ...domain.task import Task
from ...errors import AuthConfigError, RunnerTimeout, SkillRunnerError
from ..mcp.config_builder import MCP_SERVER_REGISTRY, write_mcp_config
from ..telemetry.session_parser import parse_result_usage
from ..telemetry.skill_listing import LISTING_BUDGET_ENV
from ..telemetry.skill_loads import detect_skill_loads_in_file, skill_dir_map

_log = logging.getLogger(__name__)


class ClaudeCodeRunner:
    """Subprocess adapter that satisfies the :class:`SkillRunner` port."""

    def __init__(
        self,
        *,
        claude_binary: str = "claude",
        default_max_turns: int = 40,
        grace_seconds: int = 10,
        fixtures_root: Path = Path("eval/fixtures"),
        repo_root: Path | None = None,
        plugin_root: Path | None = None,
    ) -> None:
        self._claude = claude_binary
        self._default_max_turns = default_max_turns
        self._grace_seconds = grace_seconds
        self._fixtures_root = fixtures_root
        self._repo_root = (repo_root or Path.cwd()).resolve()
        self._warned_inside_repo = False
        self._plugin_root = (
            plugin_root.resolve()
            if plugin_root is not None
            else (self._repo_root / "plugins" / "rf-agentskills").resolve()
        )

    # --- port --------------------------------------------------------------

    def execute(
        self,
        task: Task,
        profile: Profile,
        output_dir: Path,
        *,
        replicate: int = 0,
    ) -> Run:
        run_id = f"{task.id}-{profile.name}-{uuid.uuid4().hex[:8]}"
        artifacts_dir = output_dir / run_id
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        config_dir = artifacts_dir / "claude_config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Provision an isolated workspace from the fixture (if declared).
        # This is the agent's CWD; graders resolve expected_files relative to it.
        # Every replicate gets its own fresh copy (new run_id -> new dir).
        workspace_dir = self._workspace_for(task, profile, artifacts_dir)

        # Treatment arm: stage the full plugin once. The downstream
        # provisioners (skills, agents, hooks, plugin MCP) all read from this
        # single canonical copy; ${CLAUDE_PLUGIN_ROOT} is substituted in its
        # JSON configs (hooks, MCP) only — SKILL.md script commands use
        # ${CLAUDE_SKILL_DIR}, expanded by Claude Code itself.
        # Baseline arm: nothing from the plugin is staged (design D1).
        plugin_dst = (
            self._stage_plugin(config_dir, profile.plugin_root) if profile.stage_plugin else None
        )

        write_mcp_config(config_dir, extra_servers=self._mcp_servers(task, plugin_dst))

        if plugin_dst is not None:
            self._provision_skills(plugin_dst, config_dir, workspace_dir)
            self._provision_agents(plugin_dst, config_dir, workspace_dir)

        hooks_section = (
            self._extract_hooks(plugin_dst)
            if plugin_dst is not None and profile.hooks_enabled
            else None
        )

        # Write a Claude Code settings.json into the config dir that denies
        # Write/Edit outside the workspace. Defense-in-depth alongside the
        # prompt preamble and the post-run integrity check below. When the
        # plugin is staged, also wire its hooks in here.
        self._write_settings(config_dir, workspace_dir, hooks=hooks_section)

        run_kwargs: dict[str, Any] = {
            "id": run_id,
            "task_id": task.id,
            "profile_name": profile.name,
            "artifacts_dir": artifacts_dir,
            "workspace_dir": workspace_dir if workspace_dir != artifacts_dir else None,
            "model": task.model,
            "arm": profile.arm,
            "replicate": replicate,
        }

        leaked = self._pre_run_isolation(profile, config_dir, workspace_dir, run_kwargs)
        if leaked is not None:
            return leaked

        env = self._build_env(config_dir, listing_budget=profile.listing_budget)
        cmd = self._build_cmd(task, workspace_dir, restrict_tools=profile.restrict_tools)

        stdout_path = artifacts_dir / "stdout.stream.jsonl"
        stderr_path = artifacts_dir / "stderr.log"

        # Snapshot the project root before the run so the post-run integrity
        # check can detect files created outside the workspace. Sessions that
        # have no write-capable tool (trigger profiles) skip it (design D15).
        pre_snapshot = (
            _snapshot_repo_root(self._repo_root, workspace_dir)
            if needs_isolation_check(task, profile)
            else None
        )

        _log.info("Invoking: %s", " ".join(cmd))
        started_at = datetime.now(UTC)
        t0 = time.monotonic()
        timed_out = False
        exit_code: int | None = None

        try:
            with stdout_path.open("wb") as out_fh, stderr_path.open("wb") as err_fh:
                completed = subprocess.run(
                    cmd,
                    env=env,
                    stdout=out_fh,
                    stderr=err_fh,
                    timeout=task.timeout_seconds,
                    check=False,
                    cwd=workspace_dir,
                )
            exit_code = completed.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            _log.warning(
                "claude subprocess timed out after %ss (task=%s)",
                task.timeout_seconds,
                task.id,
            )
        except FileNotFoundError as exc:
            raise SkillRunnerError(f"claude binary '{self._claude}' not found on PATH") from exc

        finished_at = datetime.now(UTC)
        elapsed = time.monotonic() - t0
        _log.info(
            "Run %s finished in %.2fs (exit=%s timed_out=%s)",
            run_id,
            elapsed,
            exit_code,
            timed_out,
        )

        session_jsonl = self._capture_session_jsonl(config_dir, artifacts_dir)

        # Post-run integrity check: detect writes outside the workspace. The
        # files are reported, never deleted: another process (a developer, an
        # editor) may have created them (design D15).
        violations = (
            _detect_workspace_violations(self._repo_root, workspace_dir, pre_snapshot)
            if pre_snapshot is not None
            else []
        )
        if violations:
            _log.warning(
                "Workspace-integrity violation: %d file(s) written outside workspace",
                len(violations),
            )
            self._record_violations(artifacts_dir, violations)

        if timed_out and exit_code is None:
            # Normalise: the exit code slot signals 'no clean exit'.
            exit_code = -1

        usage = parse_result_usage(stdout_path)
        error: str | None = None
        if not profile.stage_plugin:
            leaks = baseline_transcript_leaks(stdout_path, self._known_skill_dirs())
            if leaks:
                error = "arm-leak: baseline transcript loaded " + ", ".join(leaks)
                _log.error("%s (run %s)", error, run_id)
        if violations:
            isolation = isolation_error(self._repo_root, violations)
            error = f"{error}; {isolation}" if error else isolation

        return Run(
            started_at=started_at,
            finished_at=finished_at,
            exit_code=exit_code,
            session_jsonl_path=session_jsonl,
            timed_out=timed_out,
            usage=usage,
            error=error,
            **run_kwargs,
        )

    # --- helpers -----------------------------------------------------------

    @staticmethod
    def _mcp_servers(task: Task, plugin_dst: Path | None) -> dict[str, dict[str, Any]]:
        """Per-task servers (e.g. rf-mcp) in both arms; plugin servers in treatment."""
        servers: dict[str, dict[str, Any]] = {
            name: dict(MCP_SERVER_REGISTRY[name]) for name in task.mcp_servers
        }
        if plugin_dst is not None:
            servers.update(ClaudeCodeRunner._extra_mcp_servers(plugin_dst) or {})
        return servers

    def _pre_run_isolation(
        self,
        profile: Profile,
        config_dir: Path,
        workspace_dir: Path,
        run_kwargs: dict[str, Any],
    ) -> Run | None:
        """Baseline arm: refuse to launch when plugin parts are discoverable."""
        if profile.stage_plugin:
            return None
        problems = baseline_isolation_problems(config_dir, workspace_dir, self._plugin_root)
        if not problems:
            return None
        _log.error("baseline arm isolation violated: %s", problems)
        now = datetime.now(UTC)
        return Run(
            started_at=now,
            finished_at=now,
            error="arm-leak: " + "; ".join(problems),
            **run_kwargs,
        )

    def _known_skill_dirs(self) -> dict[str, str]:
        """rf-agentskills skill name -> dir, from repo skills/ and the plugin."""
        known = skill_dir_map(self._plugin_root / "skills")
        known.update(skill_dir_map(self._repo_root / "skills"))
        return known

    def _warn_if_inside_repo(self, artifacts_dir: Path) -> None:
        """Runs under the repo checkout see it as "our project" (and may edit it)."""
        if self._warned_inside_repo or not artifacts_dir.resolve().is_relative_to(self._repo_root):
            return
        self._warned_inside_repo = True
        _log.warning(
            "run artifacts %s are inside the repository %s: the agent sees the repo as its "
            "project, which skews triggering and tokens; pass an --output outside the repo",
            artifacts_dir,
            self._repo_root,
        )

    def _workspace_for(self, task: Task, profile: Profile, artifacts_dir: Path) -> Path:
        """Task fixture, else the profile's fixture, else an empty dir (if isolated)."""
        self._warn_if_inside_repo(artifacts_dir)
        workspace_dir = self._provision_workspace(task, artifacts_dir)
        if workspace_dir != artifacts_dir:
            return workspace_dir
        if profile.workspace_fixture is not None:
            return self._copy_fixture(profile.workspace_fixture, artifacts_dir)
        if profile.isolated_workspace:
            workspace_dir = artifacts_dir / "workspace"
            workspace_dir.mkdir(parents=True, exist_ok=True)
        return workspace_dir

    def _provision_workspace(self, task: Task, artifacts_dir: Path) -> Path:
        """Stage ``eval/fixtures/<task.fixture>/`` into ``artifacts_dir/workspace/``.

        Returns the workspace path that should be used as the subprocess CWD.
        When no fixture is declared, returns ``artifacts_dir`` unchanged (the
        agent then runs in an empty dir but still rooted at a disposable path).
        """
        if not task.fixture:
            return artifacts_dir
        fixture_src = self._fixtures_root / task.fixture
        if not fixture_src.is_dir():
            raise SkillRunnerError(
                f"fixture '{task.fixture}' not found under {self._fixtures_root}"
            )
        return self._copy_fixture(fixture_src, artifacts_dir)

    @staticmethod
    def _copy_fixture(fixture_src: Path, artifacts_dir: Path) -> Path:
        """Fresh copy of ``fixture_src`` at ``artifacts_dir/workspace``."""
        if not fixture_src.is_dir():
            raise SkillRunnerError(f"workspace fixture not found: {fixture_src}")
        workspace = artifacts_dir / "workspace"
        # shutil.copytree refuses an existing target; artifacts_dir is fresh.
        shutil.copytree(
            fixture_src,
            workspace,
            ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.pyc", "output.xml",
                                          "log.html", "report.html"),
        )
        return workspace

    def _stage_plugin(self, config_dir: Path, plugin_root: Path | None = None) -> Path | None:
        """Copy the rf-agentskills plugin into the run's config dir.

        ``${CLAUDE_PLUGIN_ROOT}`` is rewritten to the absolute path of the
        staged copy in the JSON configs (hooks, MCP) only — those are merged
        into personal/project settings where the token does not expand.
        SKILL.md files are staged unchanged: their script commands use
        ``${CLAUDE_SKILL_DIR}``, which Claude Code expands for personal and
        project skills too.

        ``plugin_root`` overrides the runner's default source (variant roots).

        Returns the staged plugin path, or ``None`` if the plugin source
        could not be located.
        """
        source = plugin_root.resolve() if plugin_root is not None else self._plugin_root
        if not source.is_dir():
            _log.warning(
                "plugin root not found at %s; skipping plugin staging",
                source,
            )
            return None

        plugin_dst = config_dir / "rf-agentskills"
        if not plugin_dst.exists():
            shutil.copytree(
                source,
                plugin_dst,
                ignore=shutil.ignore_patterns(
                    "__pycache__", "*.pyc", ".venv", "node_modules"
                ),
            )

        plugin_root_abs = str(plugin_dst.resolve())
        self._rewrite_plugin_root(plugin_dst, plugin_root_abs)
        return plugin_dst

    def _provision_skills(
        self,
        plugin_dst: Path,
        config_dir: Path,
        workspace_dir: Path,
    ) -> None:
        """Stage every skill in the plugin into Claude Code's discovery paths.

        Two locations are populated for resilience:

        * ``<config_dir>/skills/<name>/`` — Claude Code's per-user skills dir
          (resolved via ``CLAUDE_CONFIG_DIR``).
        * ``<workspace>/.claude/skills/<name>/`` — project-scoped fallback
          picked up via the agent's CWD.
        """
        plugin_skills_src = plugin_dst / "skills"
        if not plugin_skills_src.is_dir():
            return

        targets = [
            config_dir / "skills",
            workspace_dir / ".claude" / "skills",
        ]
        for parent in targets:
            parent.mkdir(parents=True, exist_ok=True)

        for skill_src in plugin_skills_src.iterdir():
            if not skill_src.is_dir():
                continue
            for parent in targets:
                skill_dst = parent / skill_src.name
                if skill_dst.exists():
                    shutil.rmtree(skill_dst)
                shutil.copytree(skill_src, skill_dst)

    def _provision_agents(
        self,
        plugin_dst: Path,
        config_dir: Path,
        workspace_dir: Path,
    ) -> None:
        """Stage subagents (``agents/<name>.md``) so Claude Code can dispatch.

        Same dual-location strategy as skills.
        """
        plugin_agents_src = plugin_dst / "agents"
        if not plugin_agents_src.is_dir():
            return

        targets = [
            config_dir / "agents",
            workspace_dir / ".claude" / "agents",
        ]
        for parent in targets:
            parent.mkdir(parents=True, exist_ok=True)

        for agent_md in plugin_agents_src.iterdir():
            if not agent_md.is_file() or agent_md.suffix.lower() != ".md":
                continue
            for parent in targets:
                shutil.copy2(agent_md, parent / agent_md.name)

    @staticmethod
    def _extra_mcp_servers(plugin_dst: Path) -> dict[str, dict[str, Any]] | None:
        """Read the plugin's ``.mcp.json`` and return its ``mcpServers`` dict.

        Used to merge plugin-defined MCP servers (if the plugin ships any) into the
        run's ``.mcp.json`` alongside the harness defaults (rf-mcp).
        """
        plugin_mcp = plugin_dst / ".mcp.json"
        if not plugin_mcp.is_file():
            return None
        try:
            data = json.loads(plugin_mcp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _log.warning("failed to read plugin .mcp.json: %s", exc)
            return None
        servers = data.get("mcpServers")
        if not isinstance(servers, dict):
            return None
        return servers

    @staticmethod
    def _extract_hooks(plugin_dst: Path) -> dict[str, Any] | None:
        """Return the plugin's ``hooks/hooks.json`` ``hooks`` section, if present.

        ``${CLAUDE_PLUGIN_ROOT}`` substitution has already happened on the
        staged copy, so commands in the returned structure resolve to real
        paths.
        """
        plugin_hooks = plugin_dst / "hooks" / "hooks.json"
        if not plugin_hooks.is_file():
            return None
        try:
            data = json.loads(plugin_hooks.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _log.warning("failed to read plugin hooks.json: %s", exc)
            return None
        hooks = data.get("hooks")
        if not isinstance(hooks, dict):
            return None
        return hooks

    @staticmethod
    def _rewrite_plugin_root(plugin_dst: Path, plugin_root_abs: str) -> None:
        """Substitute ``${CLAUDE_PLUGIN_ROOT}`` in the staged JSON configs only.

        Only hook and MCP configs (``hooks/hooks.json``, ``.mcp.json``) are
        rewritten: they are merged into the run's settings as plain
        personal/project config, where the token is not expanded. SKILL.md
        and agent bodies are left exactly as users receive them (skills use
        ``${CLAUDE_SKILL_DIR}``, which Claude Code expands itself), so evals
        exercise the real script-path resolution instead of papering over it.
        """
        token = "${CLAUDE_PLUGIN_ROOT}"
        for path in plugin_dst.rglob("*.json"):
            if not path.is_file():
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if token not in content:
                continue
            path.write_text(
                content.replace(token, plugin_root_abs), encoding="utf-8"
            )

    def _build_env(
        self, config_dir: Path, *, listing_budget: int | None = None
    ) -> dict[str, str]:
        env = os.environ.copy()
        # `uv run rf-skill-eval` exports the harness venv; an agent's
        # `uv pip install ...` in its workspace would then install into it.
        for var in _HARNESS_VENV_VARS:
            env.pop(var, None)
        env["CLAUDE_CONFIG_DIR"] = str(config_dir)
        if listing_budget is not None:
            # Skill-listing budget (design D14); only set when requested.
            env[LISTING_BUDGET_ENV] = str(listing_budget)
        if not (env.get("CLAUDE_CODE_OAUTH_TOKEN") or env.get("ANTHROPIC_API_KEY")):
            raise AuthConfigError(
                "Neither CLAUDE_CODE_OAUTH_TOKEN nor ANTHROPIC_API_KEY is set. "
                "Populate .env (see .env.example) or export the token before running."
            )
        return env

    _WORKSPACE_PREAMBLE_TEMPLATE = (
        "You are running in an isolated workspace at the absolute path:\n"
        "    {workspace}\n\n"
        "Your current working directory IS already this path. "
        "All file operations (Read, Write, Edit, MultiEdit, Bash) MUST resolve "
        "to paths **inside** this workspace — either relative paths like "
        "``resources/foo.resource`` or absolute paths that begin with:\n"
        "    {workspace}\n\n"
        "Do NOT write or edit files outside this workspace. Do NOT use absolute "
        "paths that point elsewhere (even if you think you know the 'real' project "
        "location — this is a sandboxed eval). Writes outside the workspace are "
        "blocked by the runtime and will cause the task to fail.\n\n"
        "The task follows:\n\n"
    )

    def _build_cmd(
        self,
        task: Task,
        workspace_dir: Path | None = None,
        *,
        restrict_tools: bool = False,
    ) -> list[str]:
        if task.fixture and workspace_dir is not None:
            preamble = self._WORKSPACE_PREAMBLE_TEMPLATE.format(
                workspace=workspace_dir.resolve()
            )
            prompt = preamble + task.prompt
        else:
            prompt = task.prompt
        args: list[str] = [
            self._claude,
            "-p",
            prompt,
            "--output-format",
            "stream-json",
            "--verbose",
            "--max-turns",
            str(task.max_turns or self._default_max_turns),
            "--model",
            task.model,
            # Bypass interactive approval prompts that block plugin hooks and
            # "trust this project" gates in headless runs. The workspace
            # boundary is still enforced by the prompt preamble plus the
            # post-run snapshot diff in _detect_workspace_violations, so
            # this does not weaken the eval sandbox.
            "--permission-mode",
            "bypassPermissions",
        ]
        if task.allowed_tools:
            args += ["--allowedTools", ",".join(task.allowed_tools)]
            if restrict_tools:
                # In bypassPermissions mode --allowedTools only pre-approves;
                # --tools makes these the only built-in tools that exist in
                # the session (Skill must be listed or skills are not offered).
                args += ["--tools", ",".join(task.allowed_tools)]
        return args

    def _capture_session_jsonl(
        self,
        config_dir: Path,
        artifacts_dir: Path,
    ) -> Path | None:
        """Copy the session JSONL emitted by Claude Code into artifacts.

        Claude Code writes sessions under
        ``$CLAUDE_CONFIG_DIR/projects/<slug>/<session_id>.jsonl``. We
        capture *all* JSONL files present, concatenated into a single
        file for convenience; ADR-003 warns against "newest file in dir"
        heuristics so we prefer completeness over guessing.
        """

        projects_dir = config_dir / "projects"
        if not projects_dir.exists():
            return None
        target = artifacts_dir / "session.jsonl"
        written = False
        with target.open("wb") as sink:
            for jsonl in sorted(projects_dir.rglob("*.jsonl")):
                try:
                    with jsonl.open("rb") as src:
                        shutil.copyfileobj(src, sink)
                        written = True
                except OSError as exc:
                    _log.warning("Failed to copy %s: %s", jsonl, exc)
        return target if written else None

    def _write_settings(
        self,
        config_dir: Path,
        workspace_dir: Path,
        *,
        hooks: dict[str, Any] | None = None,
    ) -> None:
        """Write Claude Code ``settings.json`` for permissions and hooks.

        The user-scope file at ``<config_dir>/settings.json`` carries the
        ``permissions`` block (workspace allow + system-write deny) — Claude
        Code 2.1 honours that block reliably from ``${CLAUDE_CONFIG_DIR}``.

        Hooks, by contrast, only fire when configured at project scope:
        Claude Code in headless ``-p`` mode silently skips the ``hooks``
        block from ``${CLAUDE_CONFIG_DIR}/settings.json`` even with
        ``--permission-mode bypassPermissions``. So when ``hooks`` are
        provided, we additionally write ``<workspace>/.claude/settings.json``
        — that one IS read and, with bypassPermissions, fires without a
        trust prompt.
        """
        workspace_abs = str(workspace_dir.resolve())
        permissions = {
            "allow": [
                f"Read({workspace_abs}/**)",
                f"Write({workspace_abs}/**)",
                f"Edit({workspace_abs}/**)",
                f"MultiEdit({workspace_abs}/**)",
                "Bash(*)",
                "Glob(*)",
                "Grep(*)",
            ],
            "deny": [
                "Write(/home/**)",
                "Edit(/home/**)",
                "MultiEdit(/home/**)",
                "Write(/etc/**)",
                "Write(/usr/**)",
                "Write(/var/**)",
            ],
        }

        user_settings: dict[str, Any] = {"permissions": permissions}
        if hooks:
            user_settings["hooks"] = hooks
        (config_dir / "settings.json").write_text(
            json.dumps(user_settings, indent=2), encoding="utf-8"
        )

        if hooks:
            project_dir = workspace_dir / ".claude"
            project_dir.mkdir(parents=True, exist_ok=True)
            (project_dir / "settings.json").write_text(
                json.dumps({"hooks": hooks}, indent=2), encoding="utf-8"
            )

    @staticmethod
    def _record_violations(artifacts_dir: Path, violations: list[Path]) -> None:
        """Write ``workspace_violations.json``; the files themselves are left alone.

        They may belong to someone else (a developer editing the repository
        while runs are active), so nothing outside the run's own workspace
        and artifacts directory is ever deleted (design D15).
        """
        report = artifacts_dir / "workspace_violations.json"
        report.write_text(
            json.dumps(
                {
                    "count": len(violations),
                    "files": [str(p) for p in violations],
                    "deleted": False,
                },
                indent=2,
            ),
            encoding="utf-8",
        )


# --- module-level helpers -----------------------------------------------------


# Directories inside the repo root that are expected to change during a run
# and MUST be excluded from the integrity snapshot.
_SNAPSHOT_EXCLUDE_DIRS = frozenset(
    {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache",
     ".ruff_cache", "eval/runs", "eval/reports", "dist", "build"}
)


def _is_excluded_path(path: Path, repo_root: Path) -> bool:
    """True if ``path`` sits under any excluded subdir of ``repo_root``."""
    try:
        rel = path.resolve().relative_to(repo_root)
    except ValueError:
        return True  # outside repo root → not interesting
    parts = rel.parts
    for i in range(1, len(parts) + 1):
        prefix = "/".join(parts[:i])
        if prefix in _SNAPSHOT_EXCLUDE_DIRS:
            return True
    return False


def _walkable_dirs(
    current: Path, rel: str, dirnames: list[str], workspace: Path, excluded_names: set[str]
) -> list[str]:
    """Subdirectories of ``current`` the integrity snapshot descends into."""
    kept = []
    for name in dirnames:
        child_rel = name if rel == "." else f"{rel}/{name}"
        child = current / name
        if name in excluded_names or child_rel in _SNAPSHOT_EXCLUDE_DIRS:
            continue
        if child == workspace or child.is_symlink():
            continue
        kept.append(name)
    return kept


def _resolved_symlink(p: Path, workspace: Path, root: Path) -> Path | None:
    """Target of a file symlink worth snapshotting, else ``None``."""
    try:
        if not p.is_file():
            return None
        target = p.resolve()
    except OSError:
        return None
    if target.is_relative_to(workspace) or _is_excluded_path(target, root):
        return None
    return target


#: Built-in tools that can create files. A session whose tool set is
#: restricted (``claude --tools``) to none of these cannot write outside its
#: workspace, so it skips the repository snapshot (design D15).
WRITE_CAPABLE_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit", "Bash"})
#: Violating paths named in a run's error text (the JSON report has all).
_MAX_NAMED_VIOLATIONS = 10


def needs_isolation_check(task: Task, profile: Profile) -> bool:
    """False only for sessions restricted to tools that cannot write files."""
    if not (profile.restrict_tools and task.allowed_tools):
        return True
    return bool(WRITE_CAPABLE_TOOLS & set(task.allowed_tools))


def isolation_error(repo_root: Path, violations: list[Path]) -> str:
    """``isolation-violation: …`` run error naming the files (repo-relative)."""
    names: list[str] = []
    for p in violations[:_MAX_NAMED_VIOLATIONS]:
        try:
            names.append(p.relative_to(repo_root).as_posix())
        except ValueError:
            names.append(str(p))
    more = len(violations) - len(names)
    tail = f" (+{more} more)" if more > 0 else ""
    return (
        f"isolation-violation: {len(violations)} file(s) created outside the workspace "
        f"during the run: {', '.join(names)}{tail}"
    )


#: Variables that point an agent's Python tooling at the harness venv.
_HARNESS_VENV_VARS = ("VIRTUAL_ENV", "VIRTUAL_ENV_PROMPT", "UV_PROJECT_ENVIRONMENT")


def _snapshot_repo_root(repo_root: Path, workspace_dir: Path) -> set[Path]:
    """Return the set of files present under ``repo_root`` before the run.

    Excludes the workspace itself, eval output dirs, VCS and build caches.
    Excluded dirs are pruned *before* descending: walking .venv /
    node_modules and filtering per file made every run spend minutes here.
    """
    root = repo_root.resolve()
    workspace = workspace_dir.resolve()
    excluded_names = {d for d in _SNAPSHOT_EXCLUDE_DIRS if "/" not in d}
    snapshot: set[Path] = set()
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        rel = current.relative_to(root).as_posix()
        dirnames[:] = _walkable_dirs(current, rel, dirnames, workspace, excluded_names)
        for name in filenames:
            p = current / name
            if not p.is_symlink():
                # root is resolved and dir symlinks are not followed, so
                # ``p`` is already canonical and outside excluded dirs.
                snapshot.add(p)
                continue
            target = _resolved_symlink(p, workspace, root)
            if target is not None:
                snapshot.add(target)
    return snapshot


def _detect_workspace_violations(
    repo_root: Path,
    workspace_dir: Path,
    pre_snapshot: set[Path],
) -> list[Path]:
    """Return files under ``repo_root`` that were created during the run."""
    post_snapshot = _snapshot_repo_root(repo_root, workspace_dir)
    new_files = post_snapshot - pre_snapshot
    return sorted(new_files)


def _json_mapping(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _server_names(path: Path) -> set[str]:
    servers = _json_mapping(path).get("mcpServers") if path.is_file() else None
    return set(servers) if isinstance(servers, dict) else set()


def baseline_isolation_problems(
    config_dir: Path, workspace_dir: Path, plugin_root: Path
) -> list[str]:
    """Pre-run assertion for the baseline arm (design risk "arm isolation").

    The baseline config dir and workspace must contain no skills, subagents,
    plugin hooks or plugin MCP servers.
    """
    problems = [
        f"{base / part} exists"
        for base in (config_dir, workspace_dir / ".claude")
        for part in ("skills", "agents", "plugins", "rf-agentskills")
        if (base / part).exists()
    ]
    problems += [
        f"{settings} defines hooks"
        for settings in (config_dir / "settings.json", workspace_dir / ".claude" / "settings.json")
        if settings.is_file() and _json_mapping(settings).get("hooks")
    ]
    plugin_servers = _server_names(plugin_root / ".mcp.json")
    for mcp in (config_dir / ".mcp.json", workspace_dir / ".mcp.json"):
        leaked = sorted(_server_names(mcp) & plugin_servers)
        if leaked:
            problems.append(f"{mcp} registers plugin MCP servers {leaked}")
    return problems


def baseline_transcript_leaks(transcript: Path, known: dict[str, str]) -> list[str]:
    """Names of rf-agentskills skills *successfully* loaded in a transcript."""
    return sorted(
        {load.skill for load in detect_skill_loads_in_file(transcript, known) if load.successful}
    )


def raise_on_timeout(run: Run) -> None:
    """Helper for callers that want an exception on a timed-out run."""

    if run.timed_out:
        raise RunnerTimeout(f"run {run.id} timed out")


def run_concurrency_limit(
    requested: int,
    *,
    oauth_present: bool,
    max_under_oauth: int = 2,
    max_under_api_key: int = 8,
) -> int:
    """Return a safe concurrency cap, respecting OAuth rate windows.

    Per ADR-002 §3.1, subscription-based OAuth shares a 5-hour rate
    window with interactive use; we cap at 1–2 concurrent sessions.
    API-key auth allows higher parallelism.
    """

    upper = max_under_oauth if oauth_present else max_under_api_key
    return max(1, min(requested, upper))


__all__: Sequence[str] = (
    "ClaudeCodeRunner",
    "baseline_isolation_problems",
    "baseline_transcript_leaks",
    "raise_on_timeout",
    "run_concurrency_limit",
)
