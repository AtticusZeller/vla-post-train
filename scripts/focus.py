"""Focus profiles: which method submodules stay checked out in this worktree.

The root repository always records every method's gitlink. A focus profile only
decides which of them are populated locally, so switching sets never rewrites
`.gitmodules` and never diverges from `main`.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from scripts.config import ROOT, ConfigError

FOCUS_FILE = ROOT / "focus.yaml"
_ALL = "*"

# The repository-wide pathspec list is the only flag that holds a submodule out
# of the worktree: a plain `git submodule update --init` rewrites every
# per-submodule `submodule.<name>.active` back to true, but leaves this alone.
_ACTIVE_KEY = "submodule.active"

# Only ignored/untracked entries at least this large are worth naming in the
# deletion manifest; the rest is __pycache__-grade noise.
_MANIFEST_MIN_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class Removal:
    """One method whose worktree a focus switch would delete."""

    method: str
    path: Path
    size_bytes: int
    unrecoverable: list[tuple[str, int]] = field(default_factory=list)
    unrecoverable_extra: int = 0

    @property
    def unrecoverable_bytes(self) -> int:
        return sum(size for _, size in self.unrecoverable)


def _git(path: Path, *args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode, (result.stdout.strip() or result.stderr.strip())


def human_bytes(size: int) -> str:
    """Render a byte count the way `du -h` does."""
    value = float(size)
    for unit in ("B", "K", "M", "G", "T"):
        if value < 1024 or unit == "T":
            return f"{value:.0f}{unit}" if unit == "B" else f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}T"


def _load_document() -> dict[str, Any]:
    if not FOCUS_FILE.is_file():
        raise ConfigError(f"missing focus config: {FOCUS_FILE}")
    data = yaml.safe_load(FOCUS_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("profiles"), dict):
        raise ConfigError(f"{FOCUS_FILE} must define a 'profiles' mapping")
    return data


def profile_names() -> list[str]:
    """Profile names declared in `focus.yaml`, in declaration order."""
    return list(_load_document()["profiles"])


def load_profile(name: str | None, known: Iterable[str]) -> tuple[str, set[str]]:
    """Resolve a profile name to the set of methods it keeps.

    Args:
        name: Profile name, or None to use the file's `default`.
        known: Method names registered in the workspace.

    Returns:
        The resolved profile name and its member methods.

    Raises:
        ConfigError: The profile is missing or names an unregistered method.
    """
    document = _load_document()
    profiles: dict[str, Any] = document["profiles"]
    resolved = name or document.get("default")
    if not resolved:
        raise ConfigError(f"{FOCUS_FILE} defines no 'default' profile; pass one explicitly")
    if resolved not in profiles:
        raise ConfigError(f"unknown focus profile: {resolved} (available: {', '.join(profiles)})")

    known_set = set(known)
    members = list(profiles[resolved] or [])
    unknown = sorted(m for m in members if m != _ALL and m not in known_set)
    if unknown:
        raise ConfigError(
            f"profile {resolved!r} references unregistered methods: {', '.join(unknown)}"
        )
    if _ALL in members:
        return resolved, known_set
    return resolved, set(members)


def submodule_name(method: str) -> str:
    """Git registers these submodules under their path, not a short name."""
    return f"methods/{method}"


def method_path(method: str) -> Path:
    return ROOT / "methods" / method


def is_populated(method: str) -> bool:
    """Whether the method's worktree is actually checked out."""
    return (method_path(method) / ".git").exists()


def active_methods(known: Iterable[str]) -> set[str]:
    """Methods git currently treats as active.

    Mirrors git's own precedence: a per-submodule `submodule.<name>.active` key
    wins, then the repository-wide `submodule.active` pathspec list, then the
    default of active. Only literal submodule paths are ever written here, so
    plain membership stands in for pathspec matching.
    """
    code, output = _git(ROOT, "config", "--get-regexp", r"^submodule\.")
    overrides: dict[str, bool] = {}
    patterns: set[str] = set()
    if code == 0:
        for line in output.splitlines():
            key, _, value = line.partition(" ")
            value = value.strip()
            if key == _ACTIVE_KEY:
                patterns.add(value)
            elif key.endswith(".active"):
                name = key[len("submodule.") : -len(".active")]
                overrides[name] = value.lower() != "false"

    active: set[str] = set()
    for method in known:
        name = submodule_name(method)
        if name in overrides:
            if overrides[name]:
                active.add(method)
        elif not patterns or name in patterns:
            active.add(method)
    return active


def current_profile(known: Iterable[str]) -> str:
    """Name of the profile matching the current active set, or 'custom'."""
    known_list = list(known)
    active = active_methods(known_list)
    for name in profile_names():
        try:
            _, members = load_profile(name, known_list)
        except ConfigError:
            continue
        if members == active:
            return name
    return "custom"


def _entry_size(path: Path) -> int:
    result = subprocess.run(
        ["du", "-sb", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return 0
    return int(result.stdout.split("\t", 1)[0] or 0)


def _unrecoverable(path: Path) -> tuple[list[tuple[str, int]], int]:
    """Ignored and untracked entries that deinit deletes and git cannot restore."""
    code, output = _git(path, "status", "--porcelain", "--ignored")
    if code:
        return [], 0
    sized: list[tuple[str, int]] = []
    extra = 0
    for line in output.splitlines():
        if line[:2] not in ("!!", "??"):
            continue
        entry = line[3:].strip().strip('"').rstrip("/")
        size = _entry_size(path / entry)
        if size >= _MANIFEST_MIN_BYTES:
            sized.append((entry, size))
        else:
            extra += 1
    sized.sort(key=lambda item: item[1], reverse=True)
    return sized, extra


def deletion_manifest(methods: Iterable[str]) -> list[Removal]:
    """What a focus switch would delete, heaviest method first."""
    removals: list[Removal] = []
    for method in methods:
        path = method_path(method)
        if not path.is_dir():
            continue
        unrecoverable, extra = _unrecoverable(path)
        removals.append(
            Removal(
                method=method,
                path=path,
                size_bytes=_entry_size(path),
                unrecoverable=unrecoverable,
                unrecoverable_extra=extra,
            )
        )
    removals.sort(key=lambda removal: removal.size_bytes, reverse=True)
    return removals


def set_active(selected: Iterable[str], known: Iterable[str]) -> None:
    """Record the active set as a `submodule.active` pathspec list.

    Per-submodule `submodule.<name>.active` keys are cleared on the way, because
    `git submodule update --init` (and `git submodule init`) overwrite them back
    to true and would resurrect a deactivated method. Writing this before and
    after the worktree work also makes an interrupted switch resumable.
    """
    for method in known:
        # Missing keys make `--unset-all` exit non-zero; that is not an error.
        _git(ROOT, "config", "--unset-all", f"submodule.{submodule_name(method)}.active")
    _git(ROOT, "config", "--unset-all", _ACTIVE_KEY)
    for method in sorted(selected):
        code, output = _git(ROOT, "config", "--add", _ACTIVE_KEY, submodule_name(method))
        if code:
            raise ConfigError(f"could not record active submodule {method}: {output}")


def _skip_worktree(method: str, enabled: bool) -> None:
    """Toggle the gitlink's skip-worktree bit.

    This is local index state that never reaches a commit; it exists only so a
    removed submodule directory does not show up as a deleted gitlink.
    """
    flag = "--skip-worktree" if enabled else "--no-skip-worktree"
    code, output = _git(ROOT, "update-index", flag, submodule_name(method))
    if code:
        raise ConfigError(f"could not apply {flag} to {submodule_name(method)}: {output}")


def drop_worktree(method: str) -> None:
    """Remove a method's worktree and its directory.

    `git submodule deinit` empties the directory but leaves the empty shell
    behind. Removing it makes git report the gitlink as deleted, which the
    skip-worktree bit then hides so `git status` stays clean.
    """
    name = submodule_name(method)
    if is_populated(method):
        code, output = _git(ROOT, "submodule", "deinit", "-f", name)
        if code:
            raise ConfigError(f"deinit failed for {name}: {output}")
    path = method_path(method)
    if path.is_dir():
        if any(path.iterdir()):
            # Something survived deinit; leaving it visible beats guessing.
            return
        path.rmdir()
    _skip_worktree(method, True)


def restore_worktree(method: str) -> None:
    """Check a method's worktree back out, nested submodules included.

    An explicit path plus `--init` works even while the method sits outside the
    current `submodule.active` list, which is what makes a switch reversible.
    The skip-worktree bit has to go first, or git will not repopulate the path.
    """
    name = submodule_name(method)
    _skip_worktree(method, False)
    code, output = _git(ROOT, "submodule", "update", "--init", "--recursive", name)
    if code:
        raise ConfigError(f"submodule update failed for {name}: {output}")
