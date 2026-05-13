"""Adapter for Project Goose.

Goose has a very limited extension surface — only **MCP servers** and
the ``~/.goosehints`` text file. We honestly translate what we can:

* MCP servers from the bundle's ``.mcp.json`` are translated into
  Goose's YAML extension shape and merged under ``extensions.<name>``
  in ``~/.config/goose/config.yaml`` (or the platform-specific path on
  Windows).
* A short persona-style hint file is composed from each subagent's
  frontmatter ``description`` and a list of available skills, written
  to ``~/.goosehints`` (the file lives directly in ``$HOME``, not
  inside the Goose config dir).
* **Skills, subagents, hooks** are *not* installable: Goose has no
  native equivalents. The plan adds notes when the user asked for
  those categories, and ``post_install`` prints a clear honest
  reminder.

If ``--prefix`` is provided, both ``config.yaml`` and ``.goosehints``
land inside the prefix dir — that's the "sandbox" tests rely on.
"""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from .. import _assets
from .. import transforms as _x
from ._base import AdapterBase, ConfigMergeOp, InstallOptions, InstallPlan, InstallTarget


EXTENSIONS_KEY = "extensions"
GOOSEHINTS_FILENAME = ".goosehints"
CONFIG_FILENAME = "config.yaml"


@dataclass
class GooseAdapter(AdapterBase):
    name: str = "goose"
    pretty: str = "Project Goose"
    user_root_subpath: tuple[str, ...] = (".config", "goose")
    project_root_subpath: tuple[str, ...] = (".goose",)

    # ------------------------------------------------------------------
    # detect
    # ------------------------------------------------------------------

    def detect(self) -> bool:
        """True if the ``goose`` CLI is on PATH or any Goose dotfile exists."""
        if shutil.which("goose") is not None:
            return True
        home = Path.home()
        if (home / ".config" / "goose").is_dir():
            return True
        if (home / GOOSEHINTS_FILENAME).is_file():
            return True
        return False

    # ------------------------------------------------------------------
    # install_root overrides — Windows uses %APPDATA%/Block/goose/config
    # ------------------------------------------------------------------

    def install_root(self, opts: InstallOptions) -> Path:
        if opts.prefix is not None:
            return opts.prefix
        if opts.scope == "project":
            project = opts.project_dir
            if project is None:
                raise ValueError("--project required when --scope project")
            return project.joinpath(*self.project_root_subpath)
        if sys.platform == "win32":
            # Goose on Windows: %APPDATA%\Block\goose\config\config.yaml
            import os
            appdata = os.environ.get("APPDATA")
            if appdata:
                return Path(appdata) / "Block" / "goose" / "config"
            # Fallback: the POSIX layout under HOME (rarely used on Windows
            # but keeps tests deterministic when APPDATA is unset).
            return Path.home() / ".config" / "goose"
        return Path.home() / ".config" / "goose"

    def _goosehints_path(self, opts: InstallOptions) -> Path:
        """Goose reads ``~/.goosehints`` directly from $HOME — *not* inside
        the config dir. With ``--prefix`` we co-locate it there for the
        sandbox-friendly install layout the tests assume."""
        if opts.prefix is not None:
            return opts.prefix / GOOSEHINTS_FILENAME
        if opts.scope == "project":
            project = opts.project_dir
            assert project is not None
            return project / GOOSEHINTS_FILENAME
        return Path.home() / GOOSEHINTS_FILENAME

    def _skills_root(self, opts: InstallOptions) -> Path:
        """Goose v1.25+ reads skills from ``~/.agents/skills/`` (global) or
        ``<project>/.agents/skills/`` (project). The Summon extension
        auto-discovers them at startup — no registration needed.

        ``--prefix`` co-locates skills at ``<prefix>/agents/skills/`` so the
        sandbox tests don't need to assume a writable ``$HOME/.agents/``.
        """
        if opts.prefix is not None:
            return opts.prefix / "agents" / "skills"
        if opts.scope == "project":
            project = opts.project_dir
            assert project is not None
            return project / ".agents" / "skills"
        return Path.home() / ".agents" / "skills"

    # ------------------------------------------------------------------
    # plan
    # ------------------------------------------------------------------

    def plan(self, opts: InstallOptions) -> InstallPlan:
        root = self.install_root(opts)
        skills_root = self._skills_root(opts)
        targets: list[InstallTarget] = []
        merges: list[ConfigMergeOp] = []
        notes: list[str] = []

        with _assets.asset_root_path() as src_root:
            # 1. Skills → ~/.agents/skills/<name>/ (Goose v1.25+ Summon
            #    extension auto-discovers them). SKILL.md format is
            #    identical to Anthropic's — verbatim copy plus
            #    ${CLAUDE_PLUGIN_ROOT} substitution. The skill body's
            #    references / scripts / assets subdirs come along too.
            #    Goose has no plugin-root env var of its own (per
            #    docs.goose-docs.ai/.../using-skills/), so the
            #    install-time substitution is what makes the skill's
            #    bash blocks resolvable.
            if "skills" in opts.what:
                skills_src = src_root / "skills"
                if skills_src.is_dir():
                    plugin_root_abs = _x.to_native_path_string(
                        (root / "rf-agentskills-files").resolve()
                    )
                    for f in sorted(skills_src.rglob("*")):
                        if not f.is_file():
                            continue
                        rel = f.relative_to(skills_src)
                        targets.append(InstallTarget(
                            dst=skills_root / rel,
                            payload=self._read_with_substitution(f, plugin_root_abs),
                            transform_name="plugin_root_substitution",
                        ))
                    # Co-locate scripts/servers under <root>/rf-agentskills-files/
                    # so substituted paths in skill bodies resolve.
                    for category in ("scripts", "servers"):
                        cat_src = src_root / category
                        if not cat_src.is_dir():
                            continue
                        for f in sorted(cat_src.rglob("*")):
                            if not f.is_file():
                                continue
                            rel = f.relative_to(src_root)
                            targets.append(InstallTarget(
                                dst=root / "rf-agentskills-files" / rel,
                                payload=self._read_with_substitution(f, plugin_root_abs),
                                transform_name="plugin_root_substitution",
                                executable=f.suffix in (".sh", ".ps1"),
                            ))
                    # Pin the install-time Python interpreter so hook
                    # .mjs scripts can find the env with robotframework
                    # if a user manually wires them up. Goose itself
                    # doesn't register hooks, but the script files are
                    # still shipped — keep the runtime config uniform.
                    targets.append(InstallTarget(
                        dst=root / "rf-agentskills-files" / "scripts" / "python_runtime.json",
                        payload=_x.python_runtime_config_bytes(),
                        transform_name="python_runtime_pin",
                    ))

            # 2. Goosehints — Goose has no subagent primitive, so we fold
            #    subagent descriptions plus a skill index into the hints
            #    file. This ALSO helps users discover the skills installed
            #    in step 1 by giving them a single high-level summary.
            if {"skills", "agents"} & opts.what:
                hints_text = self._compose_goosehints(src_root)
                targets.append(InstallTarget(
                    dst=self._goosehints_path(opts),
                    payload=hints_text.encode("utf-8"),
                    transform_name="goosehints_persona",
                ))

            # 3. MCP → extensions block in config.yaml
            if "mcp" in opts.what:
                plugin_mcp = src_root / ".mcp.json"
                if plugin_mcp.is_file():
                    merges.append(self._mcp_merge_op(
                        plugin_mcp=plugin_mcp,
                        target=root / CONFIG_FILENAME,
                    ))

        # 4. Honest skip-notes for the categories Goose still lacks.
        if "agents" in opts.what:
            notes.append(
                "Goose has no native subagent primitive — subagent "
                "descriptions are folded into .goosehints instead."
            )
        if "hooks" in opts.what:
            notes.append(
                "Goose has no hooks system — hooks were skipped."
            )

        return InstallPlan(
            targets=tuple(targets),
            merges=tuple(merges),
            notes=tuple(notes),
        )

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    @staticmethod
    def _read_with_substitution(src: Path, plugin_root_abs: str) -> bytes:
        data = src.read_bytes()
        if _x.is_substitution_candidate(src):
            return _x.substitute_plugin_root_bytes(data, plugin_root_abs)
        return data

    # ------------------------------------------------------------------
    # post_install
    # ------------------------------------------------------------------

    def post_install(self, opts: InstallOptions) -> list[str]:
        return [
            "Goose only supports MCP servers and goosehints from this bundle. "
            "Skills, subagents, and hooks are not installed (Goose has no "
            "native equivalent).",
            "Restart your Goose session for the new extension to be picked up.",
        ]

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _compose_goosehints(self, src_root: Path) -> str:
        """Build a short persona-style hint text from agents + skills.

        Format:

            # rf-agentskills available
            When working with Robot Framework:
            - <agent-name>: <description>
            - ...
            - Skills: <comma-separated list of skill dirs>
        """
        lines: list[str] = [
            "# rf-agentskills available",
            "When working with Robot Framework:",
        ]
        agents_dir = src_root / "agents"
        if agents_dir.is_dir():
            for agent_md in sorted(agents_dir.glob("*.md")):
                doc = _x.parse_frontmatter(agent_md.read_text(encoding="utf-8"))
                agent_name = str(doc.frontmatter.get("name") or agent_md.stem)
                description = str(doc.frontmatter.get("description") or "").strip()
                if description:
                    lines.append(f"- {agent_name}: {description}")
                else:
                    lines.append(f"- {agent_name}")

        skills_dir = src_root / "skills"
        if skills_dir.is_dir():
            skill_names = sorted(
                p.name for p in skills_dir.iterdir() if p.is_dir()
            )
            if skill_names:
                lines.append(f"- Skills: {', '.join(skill_names)}")

        return "\n".join(lines) + "\n"

    def _mcp_merge_op(
        self,
        *,
        plugin_mcp: Path,
        target: Path,
    ) -> ConfigMergeOp:
        """Translate the bundle's ``.mcp.json`` into Goose's YAML extension shape.

        Each ``mcpServers.<name>`` entry becomes::

            extensions:
              <name>:
                type: stdio
                cmd: <command>
                args: [<args>]
                enabled: true
                timeout: 300
        """
        # Note: we do NOT substitute ${CLAUDE_PLUGIN_ROOT} here. Goose has
        # no notion of plugin root, and we have no co-located scripts/
        # tree under the install. The user is expected to point Goose at
        # the same on-disk install of rf-tools that the Claude Code
        # adapter would have created — or to install both adapters,
        # which is the common case. Documenting this in post_install.
        plugin_servers = json.loads(plugin_mcp.read_text(encoding="utf-8")).get(
            "mcpServers", {}
        )
        extensions = {
            name: _server_to_goose_extension(spec)
            for name, spec in plugin_servers.items()
        }

        def apply() -> list[str]:
            _x.merge_yaml_block(target, EXTENSIONS_KEY, extensions)
            # Track the server names we added inside the `extensions:`
            # block — *not* the top-level "extensions" key itself.
            # Uninstall walks into key_path=("extensions",) and removes
            # these entries, so the user's other extensions are kept.
            return list(extensions)

        def revert() -> None:
            _x.remove_yaml_keys(
                target, list(extensions), parent_key=EXTENSIONS_KEY,
            )

        return ConfigMergeOp(
            path=target,
            description=f"merge MCP extensions into {target}",
            apply=apply,
            revert=revert,
            kind="yaml_block",
            key_path=(EXTENSIONS_KEY,),
        )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _server_to_goose_extension(spec: dict) -> dict:
    """Translate one ``.mcp.json`` server entry to Goose's extension shape."""
    return {
        "type": "stdio",
        "cmd": spec.get("command", ""),
        "args": list(spec.get("args", [])),
        "enabled": True,
        "timeout": 300,
    }
