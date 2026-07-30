"""Method-specific command construction."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from scripts.config import ConfigError, ExperimentConfig


@dataclass(frozen=True)
class LaunchSpec:
    """Fully resolved foreground process specification."""

    argv: tuple[str, ...]
    cwd: Path
    supports_resume: bool = False
    environment: tuple[tuple[str, str], ...] = ()


def _argv(value: object, name: str = "native.argv") -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{name} must be a list of strings")
    return [str(item) for item in value]


def _environment_prefix(config: ExperimentConfig) -> list[str]:
    environment = config.environment
    manager = str(environment.get("manager", "none"))
    if manager == "none":
        return []
    if manager == "conda":
        name = environment.get("name")
        if not isinstance(name, str) or not name:
            raise ConfigError("environment.name is required for conda")
        return ["conda", "run", "--no-capture-output", "-n", name]
    if manager == "uv":
        return ["uv", "run"]
    if manager == "command":
        return _argv(environment.get("prefix"), "environment.prefix")
    raise ConfigError(f"unsupported environment manager: {manager}")


def _native_environment(config: ExperimentConfig) -> tuple[tuple[str, str], ...]:
    value = config.native.get("env", {})
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(item, str) for key, item in value.items()
    ):
        raise ConfigError("native.env must be a string-to-string mapping")
    environment = {str(key): str(item) for key, item in value.items()}
    if config.environment.get("manager") == "conda":
        name = str(config.environment.get("name", ""))
        conda = shutil.which("conda")
        if not conda or not name:
            raise ConfigError("conda executable and environment.name are required")
        conda_root = Path(conda).resolve().parents[1]
        environment_bin = conda_root / "envs" / name / "bin"
        if not environment_bin.is_dir():
            raise ConfigError(f"conda environment does not exist: {environment_bin.parent}")
        # `lab` itself runs under uv, whose .venv/bin otherwise remains ahead
        # of the target Conda environment even after `conda run`.
        environment["PATH"] = f"{environment_bin}:{os.environ.get('PATH', '')}"
    return tuple(sorted(environment.items()))


def build_launch_spec(config: ExperimentConfig) -> LaunchSpec:
    """Dispatch configuration to a lightweight method launcher."""

    if config.method == "flowdagger":
        from scripts.launchers.flowdagger import build
    elif config.method == "dsrl-pi0":
        from scripts.launchers.dsrl_pi0 import build
    elif config.method == "rlinf":
        from scripts.launchers.rlinf import build
    else:
        from scripts.launchers.command import build
    spec = build(config)
    return LaunchSpec(
        argv=tuple([*_environment_prefix(config), *spec.argv]),
        cwd=spec.cwd,
        supports_resume=spec.supports_resume,
        environment=_native_environment(config),
    )


__all__ = ["LaunchSpec", "build_launch_spec"]
