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
from ..mcp.config_builder import write_mcp_config

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
        cleanup_violations: bool = True,
        plugin_root: Path | None = None,
    ) -> None:
        self._claude = claude_binary
        self._default_max_turns = default_max_turns
        self._grace_seconds = grace_seconds
        self._fixtures_root = fixtures_root
        self._repo_root = (repo_root or Path.cwd()).resolve()
        self._cleanup_violations = cleanup_violations
        self._plugin_root = (
            plugin_root.resolve()
            if plugin_root is not None
            else (self._repo_root / "plugins" / "rf-agentskills").resolve()
        )

    # --- port --------------------------------------------------------------

    def execute(self, task: Task, profile: Profile, output_dir: Path) -> Run:
        run_id = f"{task.id}-{profile.name}-{uuid.uuid4().hex[:8]}"
        artifacts_dir = output_dir / run_id
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        config_dir = artifacts_dir / "claude_config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Provision an isolated workspace from the fixture (if declared).
        # This is the agent's CWD; graders resolve expected_files relative to it.
        workspace_dir = self._provision_workspace(task, artifacts_dir)

        # Stage the full plugin once when treatment profile is active.
        # The downstream provisioners (skills, agents, hooks, extra MCP) all
        # read from this single canonical copy with ${CLAUDE_PLUGIN_ROOT}
        # already substituted, so every component sees a consistent path.
        plugin_dst = (
            self._stage_plugin(config_dir) if profile.enabled_skills else None
        )

        # Isolated MCP config for this run, augmented with any servers the
        # plugin defines (e.g., rf-tools alongside the default rf-mcp).
        extra_mcp = self._extra_mcp_servers(plugin_dst) if plugin_dst else None
        write_mcp_config(config_dir, extra_servers=extra_mcp)

        if plugin_dst is not None:
            self._provision_skills(plugin_dst, config_dir, workspace_dir)
            self._provision_agents(plugin_dst, config_dir, workspace_dir)

        hooks_section = (
            self._extract_hooks(plugin_dst) if plugin_dst is not None else None
        )

        # Write a Claude Code settings.json into the config dir that denies
        # Write/Edit outside the workspace. Defense-in-depth alongside the
        # prompt preamble and the post-run integrity check below. When the
        # plugin is staged, also wire its hooks in here.
        self._write_settings(config_dir, workspace_dir, hooks=hooks_section)

        env = self._build_env(config_dir)
        cmd = self._build_cmd(task, workspace_dir)

        stdout_path = artifacts_dir / "stdout.stream.jsonl"
        stderr_path = artifacts_dir / "stderr.log"

        # Snapshot the project root before the run so the post-run integrity
        # check can detect files created outside the workspace.
        pre_snapshot = _snapshot_repo_root(self._repo_root, workspace_dir)

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

        # Post-run integrity check: detect writes outside the workspace.
        violations = _detect_workspace_violations(
            self._repo_root, workspace_dir, pre_snapshot
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

        return Run(
            id=run_id,
            task_id=task.id,
            profile_name=profile.name,
            started_at=started_at,
            finished_at=finished_at,
            exit_code=exit_code,
            session_jsonl_path=session_jsonl,
            artifacts_dir=artifacts_dir,
            workspace_dir=workspace_dir if workspace_dir != artifacts_dir else None,
            model=task.model,
            timed_out=timed_out,
        )

    # --- helpers -----------------------------------------------------------

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
        workspace = artifacts_dir / "workspace"
        # shutil.copytree refuses an existing target; artifacts_dir is fresh.
        shutil.copytree(
            fixture_src,
            workspace,
            ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.pyc", "output.xml",
                                          "log.html", "report.html"),
        )
        return workspace

    def _stage_plugin(self, config_dir: Path) -> Path | None:
        """Copy the rf-agentskills plugin into the run's config dir.

        ``${CLAUDE_PLUGIN_ROOT}`` is rewritten to the absolute path of the
        staged copy throughout — that token does not expand in
        personal/project skill bash blocks or in hooks (Claude Code issue
        #9354), so this substitution is what makes script paths resolve.

        Returns the staged plugin path, or ``None`` if the plugin source
        could not be located.
        """
        if not self._plugin_root.is_dir():
            _log.warning(
                "plugin root not found at %s; skipping plugin staging",
                self._plugin_root,
            )
            return None

        plugin_dst = config_dir / "rf-agentskills"
        if not plugin_dst.exists():
            shutil.copytree(
                self._plugin_root,
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

        Used to merge plugin-defined MCP servers (e.g., rf-tools) into the
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
        """Substitute ``${CLAUDE_PLUGIN_ROOT}`` across the staged plugin tree."""
        token = "${CLAUDE_PLUGIN_ROOT}"
        for path in plugin_dst.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".md", ".sh", ".py", ".txt", ".json"}:
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

    def _build_env(self, config_dir: Path) -> dict[str, str]:
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config_dir)
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

    def _build_cmd(self, task: Task, workspace_dir: Path | None = None) -> list[str]:
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

    def _record_violations(
        self,
        artifacts_dir: Path,
        violations: list[Path],
    ) -> None:
        """Write a violations report and optionally clean up the offending files."""
        report = artifacts_dir / "workspace_violations.json"
        report.write_text(
            json.dumps(
                {
                    "count": len(violations),
                    "files": [str(p) for p in violations],
                    "cleaned_up": self._cleanup_violations,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        if not self._cleanup_violations:
            return
        for p in violations:
            try:
                if p.is_file() or p.is_symlink():
                    p.unlink()
                    # Best-effort parent-dir cleanup if empty.
                    parent = p.parent
                    while parent != self._repo_root and parent.exists():
                        try:
                            parent.rmdir()
                        except OSError:
                            break
                        parent = parent.parent
            except OSError as exc:
                _log.warning("Failed to clean up violating file %s: %s", p, exc)


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


def _snapshot_repo_root(repo_root: Path, workspace_dir: Path) -> set[Path]:
    """Return the set of files present under ``repo_root`` before the run.

    Excludes the workspace itself, eval output dirs, VCS and build caches.
    """
    workspace_resolved = workspace_dir.resolve()
    snapshot: set[Path] = set()
    for p in repo_root.rglob("*"):
        if not p.is_file():
            continue
        p_resolved = p.resolve()
        try:
            p_resolved.relative_to(workspace_resolved)
            continue  # inside workspace — ignore
        except ValueError:
            pass
        if _is_excluded_path(p_resolved, repo_root):
            continue
        snapshot.add(p_resolved)
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
    "raise_on_timeout",
    "run_concurrency_limit",
)
