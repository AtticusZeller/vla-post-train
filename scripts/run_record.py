"""Git, host, and run-evidence snapshots."""

from __future__ import annotations

import json
import platform
import re
import socket
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.config import ROOT, ConfigError, ExperimentConfig


def utc_now() -> str:
    """Return an RFC 3339 UTC timestamp."""

    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _git(path: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode:
        message = result.stderr.strip() or result.stdout.strip()
        raise ConfigError(f"git {' '.join(args)} failed in {path}: {message}")
    return result.stdout.strip()


def git_snapshot(path: Path) -> dict[str, Any]:
    """Capture the current repository revision and cleanliness."""

    return {
        "repository": str(path),
        "revision": _git(path, "rev-parse", "HEAD"),
        "branch": _git(path, "branch", "--show-current"),
        "dirty": bool(_git(path, "status", "--porcelain")),
    }


def revision_on_remote(path: Path, revision: str) -> bool:
    """Return whether any configured remote-tracking ref contains a revision."""

    refs = _git(path, "branch", "-r", "--contains", revision, check=False)
    return bool(refs.strip())


def _config_committed(config: ExperimentConfig) -> bool:
    try:
        relative = config.path.relative_to(config.root)
    except ValueError:
        return False
    tracked = subprocess.run(
        ["git", "-C", str(config.root), "ls-files", "--error-unmatch", str(relative)],
        check=False,
        capture_output=True,
    )
    if tracked.returncode:
        return False
    unstaged = subprocess.run(
        ["git", "-C", str(config.root), "diff", "--quiet", "--", str(relative)],
        check=False,
    )
    staged = subprocess.run(
        ["git", "-C", str(config.root), "diff", "--cached", "--quiet", "--", str(relative)],
        check=False,
    )
    return unstaged.returncode == 0 and staged.returncode == 0


def verify_run_readiness(config: ExperimentConfig) -> None:
    """Enforce traceability requirements before a foreground run."""

    root_snapshot = git_snapshot(config.root)
    method_snapshot = git_snapshot(config.repository_path)
    repository = config.data["repository"]
    expected_branch = repository.get("expected_branch")
    if expected_branch and method_snapshot["branch"] != expected_branch:
        raise ConfigError(
            f"method branch is {method_snapshot['branch']!r}; expected {expected_branch!r}"
        )
    require_clean = bool(repository.get("require_clean", config.is_formal))
    if require_clean and method_snapshot["dirty"]:
        raise ConfigError("run requires a clean method working tree")
    if config.is_formal:
        if not _config_committed(config):
            raise ConfigError("formal run requires a committed, unchanged root config")
        if root_snapshot["dirty"]:
            raise ConfigError("formal run requires a clean root working tree")
        if not revision_on_remote(config.root, str(root_snapshot["revision"])):
            raise ConfigError("formal run root revision is not available from a remote")
        if not revision_on_remote(config.repository_path, str(method_snapshot["revision"])):
            raise ConfigError("formal run method revision is not available from a remote")
    elif method_snapshot["dirty"] and not config.allow_dirty:
        raise ConfigError("dirty smoke/debug run requires runtime.allow_dirty: true")


def gpu_snapshot() -> list[dict[str, str]]:
    """Read a lightweight GPU inventory without importing a training framework."""

    result = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,name,uuid,memory.total",
            "--format=csv,noheader,nounits",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        return []
    gpus: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        fields = [field.strip() for field in line.split(",", 3)]
        if len(fields) == 4:
            gpus.append(
                {"index": fields[0], "name": fields[1], "uuid": fields[2], "memory_mb": fields[3]}
            )
    return gpus


def new_run_id(experiment_id: str, now: datetime | None = None) -> str:
    """Create a sortable and filesystem-safe run identifier."""

    stamp = (now or datetime.now(UTC)).strftime("%Y%m%d-%H%M%S")
    slug = re.sub(r"[^a-z0-9.-]+", "-", experiment_id.lower()).strip("-")
    return f"{stamp}__{slug}"


def initial_run_record(
    config: ExperimentConfig,
    run_id: str,
    argv: tuple[str, ...],
    cwd: Path,
    artifact_path: Path,
    environment: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a run record before process start."""

    return {
        "schema_version": 1,
        "run_id": run_id,
        "historical": False,
        "config": str(config.path.relative_to(config.root)),
        "config_sha256": config.digest(),
        "method": config.method,
        "root": git_snapshot(config.root),
        "method_code": git_snapshot(config.repository_path),
        "code_revisions": [],
        "cwd": str(cwd),
        "resolved_command": list(argv),
        "resolved_environment": environment or {},
        "host": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "gpus": gpu_snapshot(),
        },
        "started_at": utc_now(),
        "finished_at": None,
        "pid": None,
        "exit_code": None,
        "signal": None,
        "artifact_path": str(artifact_path),
        "tracking": {
            "backend": config.tracking.get("backend"),
            "project": config.tracking.get("project"),
            "run_urls": config.run_urls,
        },
    }


def finalize_run_record(
    record: dict[str, Any],
    *,
    pid: int | None,
    exit_code: int,
    signal_number: int | None,
) -> dict[str, Any]:
    """Complete process fields without discarding the initial snapshot."""

    record["pid"] = pid
    record["exit_code"] = exit_code
    record["signal"] = signal_number
    record["finished_at"] = utc_now()
    return record


def write_json(path: Path, value: dict[str, Any]) -> None:
    """Write stable UTF-8 JSON atomically enough for local run evidence."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object with a clear error for malformed evidence."""

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigError(f"expected a JSON object: {path}")
    return raw


def find_run(run_id: str, root: Path = ROOT) -> Path:
    """Resolve one run ID across method evidence directories."""

    matches = list((root / "experiments").glob(f"*/runs/{run_id}/run.json"))
    if len(matches) != 1:
        raise ConfigError(f"expected exactly one run named {run_id}, found {len(matches)}")
    return matches[0]
