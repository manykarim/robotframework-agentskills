"""Manifest of files written by the installer, used for safe uninstall.

Every successful ``rf-agentskills install`` writes (or updates) a JSON
record at ``$XDG_DATA_HOME/rf-agentskills/installed.json`` listing
every destination path, its sha256 at install time, and any
config-merge that added keys to a pre-existing file.

``uninstall`` re-reads the manifest:
* For each tracked file, re-hash the on-disk copy. If it still matches
  what we wrote, delete it. If it differs, leave it (the user has
  edited it) and just drop the manifest entry.
* For each tracked config-merge, parse the current file, remove only
  the keys we added, write back. Never blow away the whole file.

Borrowed from ``pre-commit install/uninstall`` and ``jupyter
labextension install/uninstall`` — every robust external-file
installer in the Python ecosystem uses the same pattern.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterator, Sequence


MANIFEST_VERSION = 1


def default_manifest_path() -> Path:
    """Return ``$XDG_DATA_HOME/rf-agentskills/installed.json``.

    Honours ``XDG_DATA_HOME``; falls back to ``~/.local/share`` on
    Linux/macOS and ``%LOCALAPPDATA%`` on Windows (set by Python's
    ``Path.home()`` callers separately — we just read what's set).
    """
    base = os.environ.get("XDG_DATA_HOME")
    if base:
        return Path(base) / "rf-agentskills" / "installed.json"
    if os.name == "nt":
        appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "rf-agentskills" / "installed.json"
    return Path.home() / ".local" / "share" / "rf-agentskills" / "installed.json"


def sha256_file(path: Path) -> str:
    """SHA256 hex digest of the file at ``path``."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class FileEntry:
    """One file the installer wrote to a destination path."""
    path: str          # absolute destination path
    sha256: str        # hash at install time (used to detect user edits)
    transform: str | None = None  # name of transform applied, if any


@dataclass
class ConfigMerge:
    """A merge into a pre-existing config file (settings.json, .toml, .yaml).

    ``added_keys`` lists the keys we added at the location identified
    by ``key_path``. ``key_path`` is the parent traversal: ``[]`` for
    top-level merges (e.g. settings.json's ``hooks`` block);
    ``["mcpServers"]`` for nested merges (e.g. ``.mcp.json`` MCP server
    additions). The kind tags the file format so uninstall can
    dispatch to the right remover (json_top / json_nested today;
    toml_table / yaml_block in later phases).
    """
    path: str
    added_keys: list[str]
    kind: str = "json_top"             # "json_top" | "json_nested" | "toml_table" | "yaml_block"
    key_path: list[str] = field(default_factory=list)
    backup_path: str | None = None     # optional pre-merge backup we can restore


@dataclass
class Installation:
    """All side-effects of one ``install --agent X`` invocation."""
    agent: str
    scope: str                       # "user" | "project"
    installed_at: str                # ISO-8601 UTC
    bundle_version: str              # rf-agentskills version that wrote this
    files: list[FileEntry] = field(default_factory=list)
    config_merges: list[ConfigMerge] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class Manifest:
    """Top-level manifest record. There is at most one per machine."""
    version: int = MANIFEST_VERSION
    installations: list[Installation] = field(default_factory=list)

    # ---- I/O ---------------------------------------------------------------

    @classmethod
    def load(cls, path: Path | None = None) -> "Manifest":
        path = path or default_manifest_path()
        if not path.is_file():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()
        if not isinstance(data, dict) or data.get("version") != MANIFEST_VERSION:
            return cls()
        installations = []
        for entry in data.get("installations", []):
            installations.append(
                Installation(
                    agent=entry["agent"],
                    scope=entry.get("scope", "user"),
                    installed_at=entry.get("installed_at", ""),
                    bundle_version=entry.get("bundle_version", "unknown"),
                    files=[FileEntry(**f) for f in entry.get("files", [])],
                    config_merges=[
                        # Tolerate older manifest entries that lack the
                        # newer `kind` / `key_path` fields by
                        # supplying defaults.
                        ConfigMerge(
                            path=m["path"],
                            added_keys=list(m.get("added_keys", [])),
                            kind=m.get("kind", "json_top"),
                            key_path=list(m.get("key_path", [])),
                            backup_path=m.get("backup_path"),
                        )
                        for m in entry.get("config_merges", [])
                    ],
                    notes=list(entry.get("notes", [])),
                )
            )
        return cls(version=MANIFEST_VERSION, installations=installations)

    def save(self, path: Path | None = None) -> Path:
        path = path or default_manifest_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": self.version,
            "installations": [
                {
                    "agent": ins.agent,
                    "scope": ins.scope,
                    "installed_at": ins.installed_at,
                    "bundle_version": ins.bundle_version,
                    "files": [asdict(f) for f in ins.files],
                    "config_merges": [asdict(m) for m in ins.config_merges],
                    "notes": ins.notes,
                }
                for ins in self.installations
            ],
        }
        # Atomic-ish write: tmp + rename.
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")
        os.replace(tmp, path)
        return path

    # ---- queries -----------------------------------------------------------

    def for_agent(self, agent: str, scope: str = "user") -> Installation | None:
        for ins in self.installations:
            if ins.agent == agent and ins.scope == scope:
                return ins
        return None

    def iter_agents(self) -> Iterator[Installation]:
        yield from self.installations

    # ---- mutators ----------------------------------------------------------

    def upsert(self, installation: Installation) -> None:
        """Replace any existing record for the same (agent, scope) pair."""
        self.installations = [
            ins
            for ins in self.installations
            if not (ins.agent == installation.agent and ins.scope == installation.scope)
        ]
        self.installations.append(installation)

    def remove(self, agent: str, scope: str = "user") -> Installation | None:
        """Drop and return the matching installation record."""
        for i, ins in enumerate(self.installations):
            if ins.agent == agent and ins.scope == scope:
                return self.installations.pop(i)
        return None


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def file_entry_for(dest: Path, transform: str | None = None) -> FileEntry:
    """Build a FileEntry by reading the on-disk hash at ``dest``."""
    return FileEntry(path=str(dest), sha256=sha256_file(dest), transform=transform)


def is_user_modified(entry: FileEntry) -> bool:
    """True if the on-disk file differs from what we recorded.

    Treats a missing file as 'not user-modified' (unrelated event;
    uninstall just skips it).
    """
    p = Path(entry.path)
    if not p.is_file():
        return False
    return sha256_file(p) != entry.sha256


def files_to_remove(installation: Installation) -> Iterator[Path]:
    """Yield paths whose hash still matches the recorded one (safe to delete)."""
    for entry in installation.files:
        p = Path(entry.path)
        if not p.is_file():
            continue
        if not is_user_modified(entry):
            yield p


def prune_empty_parents(path: Path, stop_at: Path | None = None) -> None:
    """Remove parent dirs of ``path`` while they are empty, up to ``stop_at``.

    Stops at the first non-empty directory or at ``stop_at`` (exclusive).
    Used to clean up ``~/.claude/skills/<name>/`` after the SKILL.md is
    deleted, but never to traverse above a sentinel root.
    """
    parent = path.parent
    home = stop_at or Path.home()
    while parent != home and parent.exists():
        try:
            parent.rmdir()
        except OSError:
            return
        parent = parent.parent
