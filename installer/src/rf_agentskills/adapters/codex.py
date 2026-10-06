"""Adapter for OpenAI Codex CLI.

Per the proposal (docs/installer/proposal.md, Phase 2) — adjusted
2026-05-07 against developers.openai.com/codex/skills, which lists
``$HOME/.agents/skills`` as the canonical USER-scope path (the
cross-vendor "agentskills.io" convention also honoured by Cursor 2.4+
and Goose v1.25+ Summon). Codex *also* reads ``~/.codex/skills`` (where
its bundled `.system` skills live) but the public spec is ``.agents``:

* skills      → ``~/.agents/skills/<name>/`` (USER) or
                ``<project>/.agents/skills/<name>/`` (PROJECT).
                SKILL.md format identical to Claude Code; verbatim copy
                modulo ``${CLAUDE_PLUGIN_ROOT}`` substitution.
* subagents   → ``~/.codex/agents/<name>.toml``, transformed from the
                Claude ``.md`` via :func:`transforms.subagent_md_to_codex_toml`.
* hooks       → ``~/.codex/hooks.json``. Codex hooks are **experimental**
                and gated by ``[features] codex_hooks = true`` in
                ``config.toml``. We do *not* flip that flag automatically;
                ``post_install`` tells the user how.

Plus a co-located copy of the plugin's ``scripts/`` (hook scripts) and
the skills' scripts under ``<root>/rf-agentskills-files/`` — same staging
strategy as the Claude Code adapter — so ``${CLAUDE_PLUGIN_ROOT}``
references in hook commands resolve to a stable, post-substitution path.

Substitution happens *at install time*, per the proposal's
decision-point #2: the ``${CLAUDE_PLUGIN_ROOT}`` token is rewritten to
the absolute path of the staged copy, so the resulting files are
self-contained and don't require the env var to be set at runtime.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .. import _assets
from .. import transforms as _x
from ._base import AdapterBase, InstallOptions, InstallPlan, InstallTarget, skill_script_files


PLUGIN_FILES_SUBDIR = "rf-agentskills-files"
CONFIG_TOML_FILENAME = "config.toml"
HOOKS_JSON_FILENAME = "hooks.json"


@dataclass
class CodexAdapter(AdapterBase):
    name: str = "codex"
    pretty: str = "OpenAI Codex CLI"
    user_root_subpath: tuple[str, ...] = (".codex",)
    project_root_subpath: tuple[str, ...] = (".codex",)

    # ------------------------------------------------------------------
    # detect
    # ------------------------------------------------------------------

    def detect(self) -> bool:
        """True if the ``codex`` CLI is on PATH or ``~/.codex`` exists."""
        if shutil.which("codex") is not None:
            return True
        return (Path.home() / ".codex").is_dir()

    # ------------------------------------------------------------------
    # plan
    # ------------------------------------------------------------------

    def _skills_root(self, opts: InstallOptions) -> Path:
        """Codex docs canonical user-scope skills path is ``$HOME/.agents/skills``
        (cross-vendor universal). With ``--prefix`` we keep the layout
        consistent with Goose's adapter: ``<prefix>/agents/skills/``.
        """
        if opts.prefix is not None:
            return opts.prefix / "agents" / "skills"
        if opts.scope == "project":
            project = opts.project_dir if opts.project_dir is not None else Path.cwd()
            return project / ".agents" / "skills"
        return Path.home() / ".agents" / "skills"

    def plan(self, opts: InstallOptions) -> InstallPlan:
        root = self.install_root(opts)
        plugin_dst = root / PLUGIN_FILES_SUBDIR
        plugin_root_abs = _x.to_native_path_string(plugin_dst.resolve())

        # Codex hooks invoke `node "<…>.mjs"`. If Node isn't on PATH at
        # install time, skip writing hooks.json entirely and surface a
        # post_install note (the file would be inert anyway).
        register_hooks = "hooks" in opts.what and _x.node_available()

        with _assets.asset_root_path() as src_root:
            targets = list(self._collect_targets(
                src_root=src_root,
                root=root,
                skills_root=self._skills_root(opts),
                plugin_dst=plugin_dst,
                plugin_root_abs=plugin_root_abs,
                what=opts.what,
                register_hooks=register_hooks,
            ))

        notes: list[str] = []
        if "hooks" in opts.what:
            if register_hooks:
                notes.append(
                    "Codex hooks are experimental — enable them by adding "
                    "`[features]\\ncodex_hooks = true` to ~/.codex/config.toml "
                    "(installer does not flip this flag for you)."
                )
            else:
                notes.append(
                    "Node.js was not found on PATH; Codex hooks.json was NOT "
                    "written. Install Node.js then re-run `rf-agentskills "
                    "install --agent codex` to enable hooks."
                )
        return InstallPlan(targets=tuple(targets), notes=tuple(notes))

    def _collect_targets(
        self,
        *,
        src_root: Path,
        root: Path,
        skills_root: Path,
        plugin_dst: Path,
        plugin_root_abs: str,
        what: frozenset[str],
        register_hooks: bool = True,
    ) -> Iterable[InstallTarget]:
        # 1. Skills — ``$HOME/.agents/skills/<name>/`` per Codex docs
        #    (developers.openai.com/codex/skills, USER scope row).
        #    SKILL.md format is identical to Claude Code's so we copy
        #    the whole tree (SKILL.md + references/ + assets/ + scripts/)
        #    verbatim, with ${CLAUDE_PLUGIN_ROOT} substituted at install
        #    time.
        if "skills" in what:
            skill_src = src_root / "skills"
            if skill_src.is_dir():
                for f in sorted(skill_src.rglob("*")):
                    if not f.is_file():
                        continue
                    rel = f.relative_to(skill_src)
                    yield InstallTarget(
                        dst=skills_root / rel,
                        payload=self.render_skill_dir(
                            self._read_with_substitution(f, plugin_root_abs),
                            f, skills_root / rel.parts[0],
                        ),
                        transform_name="plugin_root_substitution",
                    )

        # 2. Subagents — <root>/agents/<name>.toml, transformed.
        if "agents" in what:
            agents_src = src_root / "agents"
            if agents_src.is_dir():
                for f in sorted(agents_src.glob("*.md")):
                    md_text = _x.substitute_plugin_root(
                        f.read_text(encoding="utf-8"), plugin_root_abs
                    )
                    toml_text = _x.subagent_md_to_codex_toml(md_text)
                    yield InstallTarget(
                        dst=root / "agents" / f"{f.stem}.toml",
                        payload=toml_text.encode("utf-8"),
                        transform_name="subagent_md_to_codex_toml",
                    )

        # 3. Hooks — <root>/hooks.json. Verbatim copy of the plugin's
        #    hooks.json; the actual activation happens via
        #    [features] codex_hooks = true in config.toml, which we
        #    deliberately do NOT toggle (see post_install). Skipped when
        #    Node isn't on PATH (the hook command shells out to node).
        if register_hooks:
            hooks_src = src_root / "hooks" / "hooks.json"
            if hooks_src.is_file():
                yield InstallTarget(
                    dst=root / HOOKS_JSON_FILENAME,
                    payload=self._read_with_substitution(hooks_src, plugin_root_abs),
                    transform_name="plugin_root_substitution",
                )

        # 4. Plugin-co-located files: scripts/, hooks/. These live under
        #    <root>/rf-agentskills-files/ so the substituted
        #    ${CLAUDE_PLUGIN_ROOT} paths in skills / agents / hooks resolve.
        if {"hooks", "skills", "agents"} & what:
            for category in ("scripts", "hooks"):
                cat_src = src_root / category
                if not cat_src.is_dir():
                    continue
                for f in sorted(cat_src.rglob("*")):
                    if not f.is_file():
                        continue
                    rel = f.relative_to(src_root)
                    yield InstallTarget(
                        dst=plugin_dst / rel,
                        payload=self._read_with_substitution(f, plugin_root_abs),
                        transform_name="plugin_root_substitution",
                        executable=f.suffix in (".sh", ".ps1") or f.name.endswith(".bash"),
                    )
            # Per-skill scripts for the hooks (<plugin_dst>/skills/<skill>/scripts/;
            # the Stop hook runs skills/rf-results/scripts/rf_results.py).
            for f in skill_script_files(src_root):
                rel = f.relative_to(src_root)
                yield InstallTarget(
                    dst=plugin_dst / rel,
                    payload=f.read_bytes(),
                    transform_name="skill_script_for_hooks",
                )
            # Pin the install-time Python interpreter (see claude_code.py).
            yield InstallTarget(
                dst=plugin_dst / "scripts" / "python_runtime.json",
                payload=_x.python_runtime_config_bytes(),
                transform_name="python_runtime_pin",
            )

    # ------------------------------------------------------------------
    # post_install
    # ------------------------------------------------------------------

    def post_install(self, opts: InstallOptions) -> list[str]:
        notes = [
            "Codex will pick up skills and agents on next session start "
            "(it walks ~/.codex/skills/ and ~/.codex/agents/ at launch).",
        ]
        if "hooks" in opts.what:
            notes.append(
                "Codex hooks are EXPERIMENTAL. To enable them, add this to "
                "~/.codex/config.toml (we did not flip it for you):\n"
                "    [features]\n    codex_hooks = true"
            )
        return notes

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    @staticmethod
    def _read_with_substitution(src: Path, plugin_root_abs: str) -> bytes:
        """Read ``src`` and substitute ``${CLAUDE_PLUGIN_ROOT}``.

        Files we don't recognise as text (binaries) are passed through.
        """
        data = src.read_bytes()
        if _x.is_substitution_candidate(src):
            return _x.substitute_plugin_root_bytes(data, plugin_root_abs)
        return data
