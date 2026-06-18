"""Console-script entrypoint: ``rf-agentskills <subcommand> ...``.

The CLI wires four moving pieces together:

1. ``adapters`` — per-agent plan() builders.
2. ``manifest`` — the JSON record of what this machine has installed.
3. ``transforms`` — pure transforms used by the adapters and re-used
   here only for ``${CLAUDE_PLUGIN_ROOT}`` substitution display in
   --dry-run.
4. argparse — subcommand dispatch.

Subcommands implemented:

* ``install``    — write files, perform config merges, update manifest.
* ``uninstall``  — read manifest, remove only matching files (skipping
                   user-edited ones), revert config merges.
* ``list``       — show the manifest.
* ``targets``    — show which adapters detect their target on this machine.
* ``doctor``     — combined health check (assets, manifest, adapters).
* ``version``    — print bundle version.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

from rich.console import Console
from rich.table import Table

from . import __version__, _assets, manifest as _m
from .adapters import ALL_ADAPTERS, all_names, by_name
from .adapters._base import (
    Adapter,
    ConfigMergeOp,
    InstallOptions,
    InstallPlan,
    InstallTarget,
)


console = Console()
err_console = Console(stderr=True)


# ---------------------------------------------------------------------------
# argparse
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rf-agentskills",
        description="Cross-agent installer for Robot Framework agent skills.",
    )
    parser.add_argument(
        "--version", action="version", version=f"rf-agentskills {__version__}"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # install ---------------------------------------------------------------
    sp = sub.add_parser("install", help="Install rf-agentskills into one or more agents.")
    grp = sp.add_mutually_exclusive_group(required=False)
    grp.add_argument("--agent", choices=all_names(), help="Single agent (back-compat).")
    grp.add_argument("--all", action="store_true", help="Every detected agent (back-compat).")
    grp.add_argument(
        "--agents",
        metavar="SEL",
        help="Selection: 'all' (every known agent), 'none', 'detected', "
        "or a comma-separated list of agent ids. Omit for the interactive "
        "wizard (or detected agents when non-interactive).",
    )
    sp.add_argument("--scope", choices=("project", "user"), default="project",
                    help="Install scope (default: project).")
    sp.add_argument("--project", type=Path, help="Project directory for --scope project (default: CWD).")
    sp.add_argument("--prefix", type=Path, help="Override install root (used by tests).")
    sp.add_argument(
        "--what",
        default="skills,agents,hooks,mcp",
        help="Comma-separated subset of categories to install (default: all).",
    )
    sp.add_argument("--yes", "-y", action="store_true",
                    help="Accept the detected default without prompting.")
    sp.add_argument("--no-input", action="store_true",
                    help="Never prompt; fail instead of asking (CI).")
    sp.add_argument("--dry-run", action="store_true", help="Show plan without writing.")
    sp.add_argument("--force", action="store_true", help="Overwrite user-modified files.")

    # uninstall -------------------------------------------------------------
    sp = sub.add_parser("uninstall", help="Remove a previous install (manifest-tracked).")
    sp.add_argument("--agent", choices=all_names(), required=True)
    sp.add_argument("--scope", choices=("project", "user"), default="project",
                    help="Install scope (default: project).")
    sp.add_argument("--project", type=Path, help="Project directory for --scope project (default: CWD).")
    sp.add_argument("--dry-run", action="store_true")

    # list ------------------------------------------------------------------
    sub.add_parser("list", help="Show what the manifest records as installed.")

    # targets ---------------------------------------------------------------
    sub.add_parser("targets", help="Show which agents are detected on this machine.")

    # doctor ----------------------------------------------------------------
    sub.add_parser("doctor", help="Health check (assets, adapters, manifest).")

    # version ---------------------------------------------------------------
    sub.add_parser("version", help="Print bundle version.")

    return parser


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------


def _opts_from_args(args: argparse.Namespace) -> InstallOptions:
    what = frozenset(s.strip() for s in str(args.what).split(",") if s.strip())
    project = args.project
    if args.scope == "project" and project is None:
        project = Path.cwd()
    return InstallOptions(
        scope=args.scope,
        project_dir=project,
        prefix=args.prefix,
        what=what,
        dry_run=getattr(args, "dry_run", False),
        force=getattr(args, "force", False),
    )


def _manifest_path(opts: InstallOptions) -> Path:
    """Where this install's manifest lives — per scope (project-local for
    project scope, global for user). ``--prefix`` overrides only the install
    *root*, not the manifest, so install/uninstall stay symmetric and the
    manifest never lands inside the install tree."""
    return _m.manifest_path_for(opts.scope, opts.project_dir)


def _detected_names() -> list[str]:
    return [cls().name for cls in ALL_ADAPTERS if cls().detect()]


class _SelectionError(ValueError):
    """Raised for an invalid --agents value."""


def _explicit_selection(args: argparse.Namespace) -> list[str] | None:
    """Resolve an explicit selection from flags, or None if none was given.

    Returns a (possibly empty) list of agent names. An empty list ('none')
    is distinct from None ('no flag given' → wizard / detected fallback).
    """
    if getattr(args, "agent", None):
        return [args.agent]
    if getattr(args, "all", False):
        return _detected_names()
    sel = getattr(args, "agents", None)
    if sel is None:
        return None
    token = sel.strip().lower()
    if token == "all":
        return list(all_names())
    if token == "none":
        return []
    if token == "detected":
        return _detected_names()
    names = [s.strip() for s in sel.split(",") if s.strip()]
    unknown = [n for n in names if n not in all_names()]
    if unknown:
        raise _SelectionError(
            f"unknown agent(s): {', '.join(unknown)}. "
            f"valid: {', '.join(all_names())}"
        )
    return names


def _is_interactive(args: argparse.Namespace) -> bool:
    """Prompt only on a real TTY and when not opted out via --yes/--no-input."""
    if getattr(args, "no_input", False) or getattr(args, "yes", False):
        return False
    try:
        return sys.stdin.isatty()
    except (ValueError, OSError):
        return False


def _select_agents_interactively(detected: list[str]) -> list[str] | None:
    """Multi-select wizard; questionary if available, else stdlib fallback.

    Returns the chosen agent names, or None if the user cancelled.
    """
    choices = list(all_names())
    try:
        import questionary  # optional [interactive] extra
    except ImportError:
        return _select_agents_stdlib(detected, choices)
    answer = questionary.checkbox(
        "Select agents to install rf-agentskills into:",
        choices=[
            questionary.Choice(
                f"{by_name(n)().pretty} ({n})",
                value=n,
                checked=n in detected,
            )
            for n in choices
        ],
    ).ask()
    return answer  # None when cancelled (Ctrl-C/Esc)


def _select_agents_stdlib(detected: list[str], choices: list[str]) -> list[str] | None:
    """Dependency-free numbered selector used when questionary is absent."""
    console.print("Select agents (comma/space-separated numbers; Enter = detected):")
    for i, n in enumerate(choices, 1):
        mark = "*" if n in detected else " "
        console.print(f"  [{mark}] {i}. {by_name(n)().pretty} ({n})")
    try:
        raw = input("> ").strip()
    except EOFError:
        return detected
    if not raw:
        return detected
    picks: list[str] = []
    for tok in raw.replace(",", " ").split():
        if tok.isdigit() and 1 <= int(tok) <= len(choices):
            name = choices[int(tok) - 1]
            if name not in picks:
                picks.append(name)
    return picks


def cmd_install(args: argparse.Namespace) -> int:
    # 1. Resolve selection: explicit flags → wizard (TTY) → detected fallback.
    try:
        selection = _explicit_selection(args)
    except _SelectionError as exc:
        err_console.print(f"[red]error:[/red] {exc}")
        return 2

    if selection is None:
        if _is_interactive(args):
            selection = _select_agents_interactively(_detected_names())
            if selection is None:
                console.print("[dim]cancelled[/dim]")
                return 0
        else:
            selection = _detected_names()
            if not selection:
                err_console.print(
                    "[red]error:[/red] no agents detected and none selected."
                )
                err_console.print(f"valid agents: {', '.join(all_names())}")
                err_console.print(
                    "pass --agents all|detected|<csv>, or --agent <name>."
                )
                return 1

    if not selection:
        console.print("[dim]nothing selected — nothing to install[/dim]")
        return 0

    opts = _opts_from_args(args)
    manifest_path = _manifest_path(opts)

    rc = 0
    for name in selection:
        cls = by_name(name)
        if cls is None:
            err_console.print(f"[red]error:[/red] unknown agent {name!r}")
            rc = max(rc, 2)
            continue
        adapter = cls()
        plan = adapter.plan(opts)
        if opts.dry_run:
            _render_plan_dry_run(adapter, plan)
            continue
        rc |= _execute_plan(adapter, plan, opts, manifest_path)
    return rc


def cmd_uninstall(args: argparse.Namespace) -> int:
    project = args.project
    if args.scope == "project" and project is None:
        project = Path.cwd()
    manifest_path = _m.manifest_path_for(args.scope, project)

    manifest = _m.Manifest.load(manifest_path)
    record = manifest.for_agent(args.agent, args.scope)
    if record is None:
        err_console.print(
            f"[yellow]nothing to do:[/yellow] no manifest entry for "
            f"agent={args.agent!r} scope={args.scope!r}"
        )
        return 0

    removed_files: list[str] = []
    skipped_files: list[str] = []
    for entry in record.files:
        p = Path(entry.path)
        if not p.is_file():
            continue
        if _m.is_user_modified(entry):
            skipped_files.append(str(p))
            continue
        if not args.dry_run:
            try:
                p.unlink()
                _m.prune_empty_parents(p)
            except OSError as exc:
                err_console.print(f"[yellow]warn:[/yellow] {p}: {exc}")
        removed_files.append(str(p))

    if not args.dry_run:
        for merge in record.config_merges:
            # Reconstruct deletion from kind + key_path + added_keys.
            # The in-process `revert` callback isn't reachable from
            # this fresh CLI invocation; we replay the metadata.
            from . import transforms as _x
            path = Path(merge.path)
            if not path.is_file():
                continue
            try:
                if merge.kind == "json_top":
                    _x.remove_json_keys(path, merge.added_keys)
                elif merge.kind == "json_nested":
                    _x.remove_json_keys_at_path(
                        path, key_path=merge.key_path, keys=merge.added_keys
                    )
                elif merge.kind == "json_hooks":
                    _x.remove_owned_hook_entries(
                        path,
                        marker=merge.marker or "",
                        events=merge.added_keys,
                        top_key=merge.key_path[0] if merge.key_path else "hooks",
                    )
                elif merge.kind == "toml_table":
                    _x.remove_toml_table(path, merge.key_path)
                elif merge.kind == "yaml_block":
                    _x.remove_yaml_keys(
                        path, merge.added_keys,
                        parent_key=merge.key_path[0] if merge.key_path else None,
                    )
                else:
                    err_console.print(
                        f"[yellow]warn:[/yellow] unknown merge kind "
                        f"{merge.kind!r} for {path} — skipping revert"
                    )
            except Exception as exc:
                err_console.print(f"[yellow]warn:[/yellow] revert {path}: {exc}")

    if not args.dry_run:
        manifest.remove(args.agent, args.scope)
        manifest.save(manifest_path)

    table = Table(title=f"uninstall {args.agent} ({args.scope})")
    table.add_column("removed", style="green")
    table.add_column("skipped (user-edited)", style="yellow")
    rows = max(len(removed_files), len(skipped_files))
    for i in range(rows):
        table.add_row(
            removed_files[i] if i < len(removed_files) else "",
            skipped_files[i] if i < len(skipped_files) else "",
        )
    if rows == 0:
        table.add_row("(nothing to remove)", "")
    console.print(table)
    if args.dry_run:
        console.print("[dim](dry run — no files actually removed)[/dim]")
    return 0


def cmd_list(_args: argparse.Namespace) -> int:
    # Show the global (user-scope) manifest plus the project-local manifest
    # in the current directory, if any (project installs live in-repo).
    installs = list(_m.Manifest.load().iter_agents())
    proj_manifest = Path.cwd() / ".rf-agentskills" / "installed.json"
    if proj_manifest.is_file():
        installs.extend(_m.Manifest.load(proj_manifest).iter_agents())
    if not installs:
        console.print("[dim]no installations recorded[/dim]")
        return 0
    table = Table(title="rf-agentskills installations")
    table.add_column("agent")
    table.add_column("scope")
    table.add_column("bundle")
    table.add_column("installed_at")
    table.add_column("files")
    for ins in installs:
        table.add_row(
            ins.agent,
            ins.scope,
            ins.bundle_version,
            ins.installed_at,
            str(len(ins.files)),
        )
    console.print(table)
    return 0


def cmd_targets(_args: argparse.Namespace) -> int:
    table = Table(title="agent detection")
    table.add_column("agent")
    table.add_column("display")
    table.add_column("detected")
    for cls in ALL_ADAPTERS:
        adapter = cls()
        table.add_row(
            adapter.name,
            adapter.pretty,
            "[green]yes[/green]" if adapter.detect() else "[dim]no[/dim]",
        )
    console.print(table)
    return 0


def cmd_doctor(_args: argparse.Namespace) -> int:
    rc = 0
    table = Table(title="rf-agentskills doctor")
    table.add_column("check")
    table.add_column("status")
    table.add_column("details")

    # 1. Bundled assets present.
    try:
        with _assets.asset_root_path() as root:
            n = sum(1 for _ in _assets.asset_files())
            table.add_row(
                "bundled assets",
                "[green]ok[/green]" if n > 0 else "[red]MISSING[/red]",
                f"root={root} files={n}",
            )
            if n == 0:
                rc = 1
    except Exception as exc:
        table.add_row("bundled assets", "[red]ERROR[/red]", str(exc))
        rc = 1

    # 2. Manifest readable.
    try:
        manifest = _m.Manifest.load()
        table.add_row(
            "manifest",
            "[green]ok[/green]",
            f"path={_m.default_manifest_path()} entries={len(manifest.installations)}",
        )
    except Exception as exc:
        table.add_row("manifest", "[red]ERROR[/red]", str(exc))
        rc = 1

    # 3. Per-adapter detection.
    for cls in ALL_ADAPTERS:
        adapter = cls()
        ok = adapter.detect()
        table.add_row(
            f"adapter:{adapter.name}",
            "[green]detected[/green]" if ok else "[dim]not detected[/dim]",
            adapter.pretty,
        )

    console.print(table)
    return rc


def cmd_version(_args: argparse.Namespace) -> int:
    """Print the installer version and the bundled-content version.

    The two are versioned independently on purpose (see RELEASING.md):
    the installer's ``__version__`` tracks adapter / CLI / manifest
    changes; the bundled content (skills, agents, hooks, MCP server)
    has its own version from the upstream plugin manifest, surfaced
    here so support tickets and triage can be precise without
    requiring alignment.
    """
    console.print(f"rf-agentskills {__version__}")
    bundled = _bundled_content_version()
    if bundled is not None:
        console.print(
            f"bundled content: {bundled}  "
            f"[dim](from rf-agentskills plugin manifest)[/dim]"
        )
    return 0


def _bundled_content_version() -> str | None:
    """Read the version of the staged plugin bundle.

    Reads ``_assets/.claude-plugin/plugin.json`` via importlib.resources
    so it works under wheel install, editable install, and zipapp.
    Returns ``None`` if the file isn't present (e.g. pre-build editable
    install before the hatch hook ran).
    """
    try:
        with _assets.asset_root_path() as root:
            manifest = root / ".claude-plugin" / "plugin.json"
            if not manifest.is_file():
                return None
            data = json.loads(manifest.read_text(encoding="utf-8"))
        version = data.get("version")
        return str(version) if version else None
    except (OSError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------------------
# plan execution / rendering
# ---------------------------------------------------------------------------


def _render_plan_dry_run(adapter: Adapter, plan: InstallPlan) -> None:
    table = Table(title=f"[dry-run] {adapter.pretty} ({adapter.name})")
    table.add_column("op", style="cyan")
    table.add_column("destination")
    table.add_column("details")

    for tgt in plan.targets:
        table.add_row(
            "write",
            str(tgt.dst),
            f"{len(tgt.payload)} bytes"
            + (f", transform={tgt.transform_name}" if tgt.transform_name else "")
            + (", +x" if tgt.executable else ""),
        )
    for merge in plan.merges:
        table.add_row("merge", str(merge.path), merge.description)
    for note in plan.notes:
        table.add_row("note", "—", note)
    if not plan.targets and not plan.merges and not plan.notes:
        table.add_row("—", "—", "no-op (adapter produced an empty plan)")
    console.print(table)


def _execute_plan(
    adapter: Adapter,
    plan: InstallPlan,
    opts: InstallOptions,
    manifest_path: Path,
) -> int:
    """Write every target, perform every merge, update the manifest.

    Returns 0 on success, non-zero if any target failed safety checks.
    """
    if not plan.targets and not plan.merges:
        if plan.notes:
            for note in plan.notes:
                console.print(f"[dim]{adapter.name}:[/dim] {note}")
        return 0

    files_written: list[_m.FileEntry] = []
    config_merges: list[_m.ConfigMerge] = []
    rc = 0

    # 1. Files.
    for tgt in plan.targets:
        if tgt.dst.is_file() and not opts.force:
            # Conflict: file exists. Check whether it's already ours
            # (manifest record matches hash) — if so, overwrite freely.
            # Otherwise, warn and skip (force flag overrides).
            existing_owned = _is_already_owned(tgt.dst, adapter.name, opts.scope, manifest_path)
            if not existing_owned:
                err_console.print(
                    f"[yellow]warn:[/yellow] {tgt.dst} already exists (not "
                    f"installed by us). Skipping. Use --force to overwrite."
                )
                rc = max(rc, 1)
                continue

        tgt.dst.parent.mkdir(parents=True, exist_ok=True)
        # Atomic-ish write: tmp + replace.
        tmp = tgt.dst.with_suffix(tgt.dst.suffix + ".rfagentskills.tmp")
        tmp.write_bytes(tgt.payload)
        os.replace(tmp, tgt.dst)
        if tgt.executable and os.name != "nt":
            os.chmod(tgt.dst, 0o755)
        files_written.append(_m.file_entry_for(tgt.dst, transform=tgt.transform_name))

    # 2. Config merges.
    for merge in plan.merges:
        try:
            added_keys = merge.apply()
            config_merges.append(_m.ConfigMerge(
                path=str(merge.path),
                added_keys=list(added_keys),
                kind=merge.kind,
                key_path=list(merge.key_path),
                backup_path=None,
                marker=merge.marker,
            ))
        except Exception as exc:
            err_console.print(f"[red]error:[/red] {merge.path}: {exc}")
            rc = max(rc, 2)

    # 3. Manifest.
    manifest = _m.Manifest.load(manifest_path)
    manifest.upsert(_m.Installation(
        agent=adapter.name,
        scope=opts.scope,
        installed_at=_m.now_iso(),
        bundle_version=__version__,
        files=files_written,
        config_merges=config_merges,
        notes=list(plan.notes),
    ))
    manifest.save(manifest_path)

    # 4. Post-install nudges.
    table = Table(title=f"installed {adapter.pretty}")
    table.add_column("op", style="cyan")
    table.add_column("destination")
    table.add_row("files", f"{len(files_written)} written")
    table.add_row("merges", f"{len(config_merges)} performed")
    console.print(table)
    for note in adapter.post_install(opts):
        console.print(f"  [dim]→[/dim] {note}")

    return rc


def _is_already_owned(path: Path, agent: str, scope: str, manifest_path: Path) -> bool:
    """Check if ``path`` is recorded in our manifest for this (agent, scope)."""
    manifest = _m.Manifest.load(manifest_path)
    record = manifest.for_agent(agent, scope)
    if record is None:
        return False
    target_str = str(path)
    return any(entry.path == target_str for entry in record.files)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    handlers = {
        "install": cmd_install,
        "uninstall": cmd_uninstall,
        "list": cmd_list,
        "targets": cmd_targets,
        "doctor": cmd_doctor,
        "version": cmd_version,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
