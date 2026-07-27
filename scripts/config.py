"""Experiment configuration loading and validation."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")
_REQUIRED_SECTIONS = ("repository", "environment", "runtime", "tracking", "native")


class ConfigError(ValueError):
    """Raised when an experiment configuration violates the workspace schema."""


@dataclass(frozen=True)
class ExperimentConfig:
    """Validated experiment configuration."""

    path: Path
    data: dict[str, Any]
    root: Path = ROOT

    @property
    def experiment_id(self) -> str:
        return str(self.data["id"])

    @property
    def method(self) -> str:
        return str(self.data["method"])

    @property
    def repository_path(self) -> Path:
        return (self.root / str(self.data["repository"]["path"])).resolve()

    @property
    def native(self) -> dict[str, Any]:
        return dict(self.data["native"])

    @property
    def runtime(self) -> dict[str, Any]:
        return dict(self.data["runtime"])

    @property
    def tracking(self) -> dict[str, Any]:
        return dict(self.data["tracking"])

    @property
    def environment(self) -> dict[str, Any]:
        return dict(self.data["environment"])

    @property
    def is_formal(self) -> bool:
        return bool(self.runtime.get("formal", True))

    @property
    def allow_dirty(self) -> bool:
        return bool(self.runtime.get("allow_dirty", False))

    @property
    def artifact_root(self) -> Path:
        value = self.runtime.get("artifact_root", "/mnt/data/atticux/vla-post-train")
        return Path(str(value)).expanduser().resolve()

    @property
    def run_urls(self) -> list[str]:
        value = self.tracking.get("run_urls", [])
        return [str(item) for item in value]

    def digest(self) -> str:
        return hashlib.sha256(self.path.read_bytes()).hexdigest()


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{name} must be a mapping")
    return value


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{name} must be a non-empty string")
    return value


def load_config(path: str | Path, root: Path = ROOT) -> ExperimentConfig:
    """Load and validate one schema-version-1 experiment YAML."""

    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = root / config_path
    config_path = config_path.resolve()
    if not config_path.is_file():
        raise ConfigError(f"config does not exist: {config_path}")

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML: {exc}") from exc
    data = _mapping(raw, "config")

    if data.get("schema_version") != 1:
        raise ConfigError("schema_version must be 1")
    experiment_id = _string(data.get("id"), "id")
    method = _string(data.get("method"), "method")
    if not _ID_PATTERN.fullmatch(experiment_id):
        raise ConfigError("id must use lowercase letters, digits, dots, underscores, or dashes")
    if not _ID_PATTERN.fullmatch(method):
        raise ConfigError("method must use lowercase letters, digits, dots, underscores, or dashes")

    for section in _REQUIRED_SECTIONS:
        _mapping(data.get(section), section)

    repository = _mapping(data["repository"], "repository")
    repository_value = _string(repository.get("path"), "repository.path")
    repository_relative = Path(repository_value)
    if repository_relative.is_absolute() or ".." in repository_relative.parts:
        raise ConfigError("repository.path must be a safe repository-relative path")
    expected = Path("methods") / method
    if repository_relative != expected:
        raise ConfigError(f"repository.path must be {expected.as_posix()}")
    repository_path = (root / repository_relative).resolve()
    methods_root = (root / "methods").resolve()
    if not repository_path.is_relative_to(methods_root) or not repository_path.is_dir():
        raise ConfigError(f"method repository does not exist: {repository_path}")

    tracking = _mapping(data["tracking"], "tracking")
    run_urls = tracking.get("run_urls", [])
    if not isinstance(run_urls, list) or not all(isinstance(url, str) for url in run_urls):
        raise ConfigError("tracking.run_urls must be a list of strings")

    runtime = _mapping(data["runtime"], "runtime")
    if bool(runtime.get("formal", True)) and bool(runtime.get("allow_dirty", False)):
        raise ConfigError("formal runs cannot allow a dirty working tree")

    return ExperimentConfig(path=config_path, data=data, root=root.resolve())


def find_configs(root: Path = ROOT) -> list[Path]:
    """Return every versioned experiment YAML in deterministic order."""

    return sorted((root / "experiments").glob("*/configs/*.yaml"))
