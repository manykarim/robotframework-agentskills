"""Adapter for Project Goose.

Goose (v1.25+ Summon extension) loads Agent Skills from
``~/.agents/skills/``; it has no subagents or hooks. We install:

* skills → ``~/.agents/skills/<name>/`` (verbatim SKILL.md trees);
* a short persona-style hint file composed from each subagent's
  frontmatter ``description`` and a list of available skills, written
  to ``~/.goosehints`` (the file lives directly in ``$HOME``, not
  inside the Goose config dir).

Subagents and hooks are *not* installable; the plan adds notes when the
user asked for those categories.

If ``--prefix`` is provided, ``.goosehints`` lands inside the prefix
dir — that's the "sandbox" tests rely on.
"""

from __future__ import annotations

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
            project = opts.project_dir if opts.project_dir is not None else Path.cwd()
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
            project = opts.project_dir if opts.project_dir is not None else Path.cwd()
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
                            payload=self.render_skill_dir(
                                self._read_with_substitution(f, plugin_root_abs),
                                f, skills_root / rel.parts[0],
                            ),
                            transform_name="plugin_root_substitution",
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
            "Skills were installed to ~/.agents/skills (loaded by Goose's Summon "
            "extension); subagents are summarised in .goosehints. Goose has no "
            "hooks, so none were installed.",
            "Restart your Goose session to pick up the skills.",
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
