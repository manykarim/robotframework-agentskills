"""Adapter protocol shared by every per-agent installer.

An adapter is a small class with three responsibilities:

1. ``detect()`` — best-effort check for whether the target agent is
   installed on this machine. Used by ``rf-agentskills targets`` and to
   gate ``install --all``.
2. ``plan(opts)`` — produce a :class:`InstallPlan` describing every
   file to write and every config-merge to perform. **No I/O** here so
   that ``--dry-run`` can render the plan without side effects and
   tests can assert on the plan structure.
3. ``post_install(opts)`` — return a list of human-readable warnings or
   next-step instructions printed after a successful install (e.g.
   "first MCP run will prompt for trust", "enable preview flags X, Y").

The CLI's ``install`` flow is:

    plan = adapter.plan(opts)
    if --dry-run: render(plan); return
    execute(plan)              # writes files, performs merges
    manifest.upsert(...)       # records what we wrote
    print(adapter.post_install(opts))   # nudges to user

Tests in ``tests/installer/test_adapter_*.py`` assert on plan structure
without ever touching real user homes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InstallOptions:
    """User-supplied flags passed to every adapter for one install run."""

    scope: str = "project"              # "project" (default) | "user"
    project_dir: Path | None = None     # project scope target; defaults to CWD
    prefix: Path | None = None          # override the install root (for tests / sandboxing)
    what: frozenset[str] = field(
        default_factory=lambda: frozenset({"skills", "agents", "hooks", "mcp"})
    )
    dry_run: bool = False
    force: bool = False                 # overwrite even when destination is user-modified


@dataclass(frozen=True)
class InstallTarget:
    """One file that should be written to ``dst`` (post-transform).

    ``payload`` is the bytes that go to disk. ``transform_name`` is a
    string label (e.g. ``"skill_md_to_cursor_mdc"``) recorded in the
    manifest for traceability — uninstall doesn't *use* it, but it
    makes ``rf-agentskills list --verbose`` informative.

    Marking ``executable=True`` makes the dispatcher chmod +x after
    write (no-op on Windows; harmless).
    """

    dst: Path
    payload: bytes
    transform_name: str | None = None
    executable: bool = False


@dataclass(frozen=True)
class ConfigMergeOp:
    """A merge into a pre-existing config file.

    ``apply`` is a callable that performs the merge and returns the
    list of keys it added at the location identified by ``key_path``.
    The dispatcher records the result in the manifest's
    ``config_merges`` so ``uninstall`` can later remove only those
    keys, traversing into ``key_path`` first.

    ``kind`` tags the file format so uninstall can dispatch to the
    right remover (``json_top``, ``json_nested``, ``toml_table``,
    ``yaml_block``). ``key_path`` is the parent traversal: ``()`` for
    top-level merges, e.g. ``("mcpServers",)`` for nested merges into
    ``mcpServers`` inside a ``.mcp.json`` file.

    ``revert`` is the in-process reverse — adapters expose it for
    transactional rollback in case ``apply`` later fails. Out-of-
    process uninstall (``rf-agentskills uninstall``) reconstructs
    deletion from ``kind`` + ``key_path`` + recorded ``added_keys``
    rather than calling this callback (it lives in the install
    process only).
    """

    path: Path
    description: str  # human readable, shown in --dry-run output
    apply: Callable[[], list[str]]
    revert: Callable[[], None]  # called by uninstall in same process
    kind: str = "json_top"
    key_path: tuple[str, ...] = ()
    # For kind="json_hooks": the install-dir ownership marker so that
    # out-of-process uninstall can remove only rf-agentskills-owned hook
    # matcher-groups (see transforms.remove_owned_hook_entries).
    marker: str | None = None


@dataclass(frozen=True)
class InstallPlan:
    """Everything one adapter wants to do for a single install."""

    targets: tuple[InstallTarget, ...] = ()
    merges: tuple[ConfigMergeOp, ...] = ()
    notes: tuple[str, ...] = ()         # "matched feature shipped but disabled" etc.


# ---------------------------------------------------------------------------
# Protocol — adapters implement this informally; we declare it for type checkers
# ---------------------------------------------------------------------------


class Adapter(Protocol):
    """The contract every per-agent adapter satisfies.

    Implemented as a Protocol rather than an ABC so adapters can be
    plain classes; the CLI uses :class:`AdapterBase` for shared
    helpers but adapters needn't subclass it.
    """

    name: str           # short id, e.g. "claude-code", used by --agent
    pretty: str         # display name, e.g. "Claude Code"

    def detect(self) -> bool: ...

    def plan(self, opts: InstallOptions) -> InstallPlan: ...

    def post_install(self, opts: InstallOptions) -> list[str]: ...


# ---------------------------------------------------------------------------
# Helpers shared by concrete adapters
# ---------------------------------------------------------------------------


class AdapterBase:
    """Convenience base — adapters can subclass for shared helpers.

    Not required (the protocol is structural) but eliminates a lot of
    boilerplate in each adapter for things like "where is the install
    root, with --prefix and --scope folded in".
    """

    name: str = "?"
    pretty: str = "?"

    # Default user-config root if --prefix is not set. Overridden per
    # adapter (e.g. ~/.claude or ~/.codex).
    user_root_subpath: tuple[str, ...] = ()
    project_root_subpath: tuple[str, ...] = (".claude",)

    def install_root(self, opts: InstallOptions) -> Path:
        """The base directory we write into for this install."""
        if opts.prefix is not None:
            return opts.prefix
        if opts.scope == "project":
            # project scope defaults to the current directory
            project = opts.project_dir if opts.project_dir is not None else Path.cwd()
            return project.joinpath(*self.project_root_subpath)
        return Path.home().joinpath(*self.user_root_subpath)

    @staticmethod
    def filtered(items: Iterable[Any], what: frozenset[str], category: str) -> list[Any]:
        """Filter helper for ``--what`` selectivity."""
        return list(items) if category in what else []
