"""Command-line entry point for workspace orchestration."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts import focus
from scripts.config import ROOT, ConfigError, ExperimentConfig, find_configs, load_config
from scripts.launchers import build_launch_spec
from scripts.monitor import build_summary
from scripts.process import run_foreground
from scripts.report import build_report
from scripts.run_record import (
    finalize_run_record,
    find_run,
    initial_run_record,
    new_run_id,
    read_json,
    utc_now,
    verify_run_readiness,
    write_json,
)

_METHODS = {
    "lerobot": {
        "branch": "workspace",
        "upstream": "https://github.com/huggingface/lerobot.git",
    },
    "xense-openpi": {
        "branch": "main",
        "upstream": "https://github.com/XenseRobotics-AI/xense-openpi.git",
    },
    "lerobot-xense": {
        "branch": "main",
        "upstream": "https://github.com/Vertax42/lerobot-xense.git",
    },
    "fastwam": {
        "branch": "workspace",
        "upstream": "https://github.com/yuantianyuan01/FastWAM.git",
    },
    "tacwam": {
        "branch": "main",
        "upstream": "https://github.com/Hubo1231/TacWAM.git",
    },
}


def _git(path: Path, *args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode, (result.stdout.strip() or result.stderr.strip())


def _branch_matches(path: Path, branch: str, expected: str) -> bool:
    """Accept a branch checkout or a submodule pin contained by its remote branch."""

    if branch:
        return branch == expected
    code, _ = _git(
        path,
        "merge-base",
        "--is-ancestor",
        "HEAD",
        f"refs/remotes/origin/{expected}",
    )
    return code == 0


def _doctor() -> int:
    # None marks a check that does not apply, so inactive methods neither pass
    # nor fail the run.
    checks: list[tuple[str, str, bool | None]] = []
    checks.append(("Python", sys.version.split()[0], sys.version_info[:2] == (3, 12)))
    checks.append(("uv.lock", str(ROOT / "uv.lock"), (ROOT / "uv.lock").is_file()))
    checks.append(("Git root", str(ROOT / ".git"), (ROOT / ".git").exists()))
    active = focus.active_methods(_METHODS)
    checks.append(
        (
            "focus",
            f"{focus.current_profile(_METHODS)} ({len(active)}/{len(_METHODS)} active)",
            True,
        )
    )
    for method in _METHODS:
        path = ROOT / "methods" / method
        if method not in active:
            checks.append((f"method:{method}", f"{path} (inactive)", None))
            continue
        initialized = path.is_dir() and (path / ".git").exists()
        checks.append((f"method:{method}", str(path), initialized))
    recursive = subprocess.run(
        ["git", "-C", str(ROOT), "submodule", "status", "--recursive"],
        check=False,
        capture_output=True,
        text=True,
    )
    active_paths = tuple(focus.submodule_name(method) for method in active)
    uninitialized = [
        line
        for line in recursive.stdout.splitlines()
        if line.lstrip().startswith("-") and line.split()[1].startswith(active_paths)
    ]
    checks.append(
        (
            "nested submodules",
            "all initialized" if not uninitialized else "; ".join(uninitialized),
            recursive.returncode == 0 and not uninitialized,
        )
    )

    mount = subprocess.run(
        ["findmnt", "-n", "-o", "TARGET,OPTIONS", "-T", "/mnt/data"],
        check=False,
        capture_output=True,
        text=True,
    )
    mount_text = mount.stdout.strip() or "not mounted"
    mount_ok = mount.returncode == 0
    checks.append(("artifact mount", mount_text, mount_ok))

    artifact_root = Path("/mnt/data/atticux/agent-workspace")
    mount_read_only = "ro" in {
        option for token in mount_text.split() for option in token.split(",")
    }
    artifact_detail = str(artifact_root)
    if mount_read_only:
        artifact_detail += " (mount is read-only; runs are disabled until remounted rw)"
    print("检查项\t状态\t详情")
    for name, detail, passed in checks:
        state = "SKIP" if passed is None else ("OK" if passed else "FAIL")
        print(f"{name}\t{state}\t{detail}")
    print(f"artifact writes\t{'WARN' if mount_read_only else 'OK'}\t{artifact_detail}")
    return 0 if all(passed for _, _, passed in checks if passed is not None) else 1


def _method_status() -> int:
    print("method\tbranch\trevision\tclean\torigin\tupstream")
    failed = False
    active = focus.active_methods(_METHODS)
    for method, expected in _METHODS.items():
        if method not in active:
            print(f"{method}\tinactive\t-\t-\t-\t-")
            continue
        path = ROOT / "methods" / method
        code, revision = _git(path, "rev-parse", "--short=12", "HEAD")
        if code:
            print(f"{method}\t-\t-\t-\t-\t-")
            failed = True
            continue
        _, branch = _git(path, "branch", "--show-current")
        _, status = _git(path, "status", "--porcelain")
        _, origin = _git(path, "remote", "get-url", "origin")
        _, upstream = _git(path, "remote", "get-url", "upstream")
        branch_matches = _branch_matches(path, branch, expected["branch"])
        if not branch_matches or upstream != expected["upstream"]:
            failed = True
        branch_display = branch or f"detached@{expected['branch']}"
        print(
            f"{method}\t{branch_display}\t{revision}\t{'yes' if not status else 'no'}"
            f"\t{origin or '-'}\t{upstream or '-'}"
        )
    return int(failed)


def _focus_status() -> int:
    """Print which methods this worktree currently keeps."""
    active = focus.active_methods(_METHODS)
    print(f"profile\t{focus.current_profile(_METHODS)}")
    print("method\tstate\tpopulated")
    for method in _METHODS:
        state = "active" if method in active else "inactive"
        print(f"{method}\t{state}\t{'yes' if focus.is_populated(method) else 'no'}")
    return 0


def _print_manifest(removals: list[focus.Removal]) -> None:
    for removal in removals:
        print(f"  {removal.method}\t{focus.human_bytes(removal.size_bytes)}")
        for entry, size in removal.unrecoverable:
            print(f"      {entry}\t{focus.human_bytes(size)}\t无法从 git 恢复")
        if removal.unrecoverable_extra:
            print(f"      (另有 {removal.unrecoverable_extra} 项小体积未跟踪/忽略内容)")


def _method_focus(profile: str | None, dry_run: bool, assume_yes: bool) -> int:
    """Switch this worktree to one focus profile."""
    if profile is None:
        return _focus_status()

    name, selected = focus.load_profile(profile, _METHODS)
    active = focus.active_methods(_METHODS)
    # A method counts as needing work whenever the active flag and the worktree
    # disagree with the profile, so an interrupted switch is resumable.
    to_deactivate = [
        method
        for method in _METHODS
        if method not in selected and (method in active or focus.is_populated(method))
    ]
    to_activate = [
        method for method in selected if method not in active or not focus.is_populated(method)
    ]
    if not to_deactivate and not to_activate:
        print(f"focus\t{name}\t无需变更")
        return 0

    removals = focus.deletion_manifest(to_deactivate)
    if removals:
        total = sum(removal.size_bytes for removal in removals)
        lost = sum(removal.unrecoverable_bytes for removal in removals)
        print(
            f"将删除 {len(removals)} 个工作树，共 {focus.human_bytes(total)}"
            f"（其中 {focus.human_bytes(lost)} 无法从 git 恢复）："
        )
        _print_manifest(removals)
    if to_activate:
        print(f"将 checkout：{', '.join(sorted(to_activate))}")
    if dry_run:
        print("dry-run：未做任何改动")
        return 0

    if removals and not assume_yes:
        if not sys.stdin.isatty():
            raise ConfigError("非交互环境下删除工作树需显式传入 --yes")
        if input("继续？[y/N] ").strip().lower() not in ("y", "yes"):
            print("已取消")
            return 1

    # Record the target set first so an interrupted switch still leaves the
    # worktree consistent with the profile, then normalize again afterwards
    # because `submodule update --init` writes per-submodule active keys back.
    focus.set_active(selected, _METHODS)
    for method in to_deactivate:
        focus.drop_worktree(method)
        print(f"deactivated\t{method}")
    for method in to_activate:
        focus.restore_worktree(method)
        print(f"activated\t{method}")
    focus.set_active(selected, _METHODS)
    return _focus_status()


def _validate(path: str) -> int:
    config = load_config(path)
    spec = build_launch_spec(config)
    print(
        json.dumps(
            {
                "config": str(config.path.relative_to(ROOT)),
                "id": config.experiment_id,
                "method": config.method,
                "cwd": str(spec.cwd),
                "argv": list(spec.argv),
                "environment": dict(spec.environment),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _dry_run(path: str) -> int:
    config = load_config(path)
    spec = build_launch_spec(config)
    print(
        json.dumps(
            {
                "schema_version": 1,
                "id": config.experiment_id,
                "method": config.method,
                "formal": config.is_formal,
                "allow_dirty": config.allow_dirty,
                "repository": str(config.repository_path),
                "cwd": str(spec.cwd),
                "resolved_command": list(spec.argv),
                "resolved_environment": dict(spec.environment),
                "artifact_root": str(config.artifact_root),
                "tracking": {
                    "project": config.tracking.get("project"),
                    "run_urls": config.run_urls,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _unique_run_id(config_id: str, runs_root: Path) -> str:
    base = new_run_id(config_id)
    candidate = base
    suffix = 2
    while (runs_root / candidate).exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _terminal_summary(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "completed" if record["exit_code"] == 0 else "failed",
        "primary_metrics": [],
        "resources": {},
        "evidence": {
            "local_exit_code": record["exit_code"],
            "local_traceback": None,
            "wandb_runs": [],
            "local_summary": None,
        },
        "results": {},
    }


def _record_native_result(config: ExperimentConfig, record: dict[str, Any]) -> None:
    """Attach dynamic evidence emitted by a method to its run record."""
    result_file = config.native.get("result_file")
    if not isinstance(result_file, str):
        return
    result_path = Path(result_file.replace("{artifact_path}", str(record.get("artifact_path", ""))))
    if not result_path.is_absolute():
        result_path = config.repository_path / result_path
    if not result_path.is_file():
        return
    result = read_json(result_path)
    sources = record.setdefault("sources", [])
    if str(result_path) not in sources:
        sources.append(str(result_path))
    run_url = result.get("wandb_run_url")
    if isinstance(run_url, str) and run_url:
        urls = record.setdefault("tracking", {}).setdefault("run_urls", [])
        if run_url not in urls:
            urls.append(run_url)


def _run(path: str) -> int:
    config = load_config(path)
    spec = build_launch_spec(config)
    verify_run_readiness(config)

    runs_root = ROOT / "experiments" / config.method / "runs"
    run_id = _unique_run_id(config.experiment_id, runs_root)
    metadata_dir = runs_root / run_id
    artifact_path = config.artifact_root / config.method / run_id
    if not os.access(config.artifact_root.parent, os.W_OK):
        raise ConfigError(f"artifact mount is not writable: {config.artifact_root.parent}")
    artifact_path.mkdir(parents=True, exist_ok=False)
    (artifact_path / "logs").mkdir()
    resolved_environment = {
        key: value.replace("{artifact_path}", str(artifact_path)) for key, value in spec.environment
    }

    record_path = metadata_dir / "run.json"
    record = initial_run_record(
        config,
        run_id,
        spec.argv,
        spec.cwd,
        artifact_path,
        environment=resolved_environment,
    )
    write_json(record_path, record)

    def started(pid: int) -> None:
        record["pid"] = pid
        write_json(record_path, record)

    try:
        result = run_foreground(
            spec.argv,
            spec.cwd,
            artifact_path / "logs" / "console.log",
            environment=resolved_environment,
            on_started=started,
        )
        finalize_run_record(
            record,
            pid=result.pid,
            exit_code=result.exit_code,
            signal_number=result.signal_number,
        )
    except BaseException:
        finalize_run_record(
            record,
            pid=record.get("pid"),
            exit_code=1,
            signal_number=None,
        )
        raise
    finally:
        if record["finished_at"] is None:
            record["finished_at"] = utc_now()
        _record_native_result(config, record)
        write_json(record_path, record)
        write_json(metadata_dir / "summary.json", _terminal_summary(record))
    return int(record["exit_code"])


def _resume(run_id: str) -> int:
    run_path = find_run(run_id)
    record = read_json(run_path)
    if record.get("historical"):
        raise ConfigError("historical run is immutable and cannot be resumed")
    config_value = record.get("config")
    if not isinstance(config_value, str):
        raise ConfigError("run record does not contain a reusable config path")
    config = load_config(config_value)
    spec = build_launch_spec(config)
    if not spec.supports_resume:
        raise ConfigError(f"launcher for {config.method} does not support resume")
    raise ConfigError("resume support was declared but no implementation is available")


def _status(run_id: str) -> int:
    record = read_json(find_run(run_id))
    print(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _summarize(run_id: str) -> int:
    run_path = find_run(run_id)
    record = read_json(run_path)
    if record.get("historical"):
        raise ConfigError("historical summary is immutable")
    config_value = record.get("config")
    if not isinstance(config_value, str):
        raise ConfigError("historical run has no executable config; its summary is immutable")
    config = load_config(config_value)
    log_path = Path(str(record["artifact_path"])) / "logs" / "console.log"
    summary = build_summary(config, record, log_path)
    summary_path = run_path.with_name("summary.json")
    write_json(summary_path, summary)
    print(summary_path)
    return 0


def _report(method: str) -> int:
    if method not in _METHODS:
        raise ConfigError(f"unknown method: {method}")
    path = build_report(method)
    print(path)
    return 0


def _all_configs() -> int:
    for path in find_configs():
        _validate(str(path))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the stable root command hierarchy."""

    parser = argparse.ArgumentParser(prog="lab")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")

    method = commands.add_parser("method")
    method_commands = method.add_subparsers(dest="method_command", required=True)
    method_commands.add_parser("status")
    method_focus = method_commands.add_parser("focus")
    method_focus.add_argument("profile", nargs="?", help="omit to print the current state")
    method_focus.add_argument("--dry-run", action="store_true")
    method_focus.add_argument("--yes", action="store_true", help="skip the deletion prompt")

    config = commands.add_parser("config")
    config_commands = config.add_subparsers(dest="config_command", required=True)
    validate = config_commands.add_parser("validate")
    validate.add_argument("config", nargs="?", help="experiment YAML; omit with --all")
    validate.add_argument("--all", action="store_true")

    experiment = commands.add_parser("experiment")
    experiment_commands = experiment.add_subparsers(dest="experiment_command", required=True)
    for name in ("dry-run", "run"):
        child = experiment_commands.add_parser(name)
        child.add_argument("config")
    for name in ("resume", "status", "summarize"):
        child = experiment_commands.add_parser(name)
        child.add_argument("run_id")
    report = commands.add_parser("report")
    report_commands = report.add_subparsers(dest="report_command", required=True)
    build = report_commands.add_parser("build")
    build.add_argument("method")
    return parser


def dispatch(args: argparse.Namespace) -> int:
    """Execute one parsed command."""

    if args.command == "doctor":
        return _doctor()
    if args.command == "method":
        if args.method_command == "focus":
            return _method_focus(args.profile, args.dry_run, args.yes)
        return _method_status()
    if args.command == "config":
        if args.all:
            return _all_configs()
        if not args.config:
            raise ConfigError("provide a config path or --all")
        return _validate(args.config)
    if args.command == "experiment":
        if args.experiment_command == "dry-run":
            return _dry_run(args.config)
        if args.experiment_command == "run":
            return _run(args.config)
        if args.experiment_command == "resume":
            return _resume(args.run_id)
        if args.experiment_command == "status":
            return _status(args.run_id)
        return _summarize(args.run_id)
    return _report(args.method)


def main() -> int:
    """CLI main with concise user-facing failures."""

    try:
        return dispatch(build_parser().parse_args())
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
