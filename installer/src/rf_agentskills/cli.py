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
    grp = sp.add_mutually_exclusive_group(required=True)
    grp.add_argument("--agent", choices=all_names(), help="Single agent to install into.")
    grp.add_argument("--all", action="store_true", help="Install into every detected agent.")
    sp.add_argument("--scope", choices=("user", "project"), default="user")
    sp.add_argument("--project", type=Path, help="Project directory (required with --scope project).")
    sp.add_argument("--prefix", type=Path, help="Override install root (used by tests).")
    sp.add_argument(
        "--what",
        default="skills,agents,hooks,mcp",
        help="Comma-separated subset of categories to install (default: all).",
    )
    sp.add_argument("--dry-run", action="store_true", help="Show plan without writing.")
    sp.add_argument("--force", action="store_true", help="Overwrite user-modified files.")

    # uninstall -------------------------------------------------------------
    sp = sub.add_parser("uninstall", help="Remove a previous install (manifest-tracked).")
    sp.add_argument("--agent", choices=all_names(), required=True)
    sp.add_argument("--scope", choices=("user", "project"), default="user")
    sp.add_argument("--project", type=Path)
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
    return InstallOptions(
        scope=args.scope,
        project_dir=args.project,
        prefix=args.prefix,
        what=what,
        dry_run=args.dry_run,
        force=args.force,
    )


def cmd_install(args: argparse.Namespace) -> int:
    if args.scope == "project" and args.project is None:
        err_console.print("[red]error:[/red] --project is required when --scope project")
        return 2

    opts = _opts_from_args(args)
    if args.all:
        agents = [cls for cls in ALL_ADAPTERS if cls().detect()]
        if not agents:
            err_console.print("[red]error:[/red] no installed agents detected on this machine")
            return 1
    else:
        cls = by_name(args.agent)
        if cls is None:
            err_console.print(f"[red]error:[/red] unknown agent {args.agent!r}")
            return 2
        agents = [cls]

    rc = 0
    for cls in agents:
        adapter = cls()
        plan = adapter.plan(opts)
        if opts.dry_run:
            _render_plan_dry_run(adapter, plan)
            continue
        rc |= _execute_plan(adapter, plan, opts)
    return rc


def cmd_uninstall(args: argparse.Namespace) -> int:
    if args.scope == "project" and args.project is None:
        err_console.print("[red]error:[/red] --project is required when --scope project")
        return 2

    manifest = _m.Manifest.load()
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
        manifest.save()

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
    manifest = _m.Manifest.load()
    if not manifest.installations:
        console.print("[dim]no installations recorded[/dim]")
        return 0
    table = Table(title="rf-agentskills installations")
    table.add_column("agent")
    table.add_column("scope")
    table.add_column("bundle")
    table.add_column("installed_at")
    table.add_column("files")
    for ins in manifest.iter_agents():
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
    console.print(__version__)
    return 0


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


def _execute_plan(adapter: Adapter, plan: InstallPlan, opts: InstallOptions) -> int:
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
            existing_owned = _is_already_owned(tgt.dst, adapter.name, opts.scope)
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
            ))
        except Exception as exc:
            err_console.print(f"[red]error:[/red] {merge.path}: {exc}")
            rc = max(rc, 2)

    # 3. Manifest.
    manifest = _m.Manifest.load()
    manifest.upsert(_m.Installation(
        agent=adapter.name,
        scope=opts.scope,
        installed_at=_m.now_iso(),
        bundle_version=__version__,
        files=files_written,
        config_merges=config_merges,
        notes=list(plan.notes),
    ))
    manifest.save()

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


def _is_already_owned(path: Path, agent: str, scope: str) -> bool:
    """Check if ``path`` is recorded in our manifest for this (agent, scope)."""
    manifest = _m.Manifest.load()
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
