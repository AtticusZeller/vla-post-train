"""Configuration validation tests."""

from pathlib import Path

import pytest
import yaml

from scripts.config import ConfigError, load_config
from scripts.launchers import build_launch_spec
from tests.helpers import write_config


def test_missing_config_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="does not exist"):
        load_config("missing.yaml", root=tmp_path)


def test_missing_required_section_is_rejected(tmp_path: Path) -> None:
    config_path = write_config(tmp_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    del data["native"]
    config_path.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(ConfigError, match="native must be a mapping"):
        load_config(config_path, root=tmp_path)


def test_repository_escape_is_rejected(tmp_path: Path) -> None:
    config_path = write_config(tmp_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["repository"]["path"] = "../outside"
    config_path.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(ConfigError, match="safe repository-relative"):
        load_config(config_path, root=tmp_path)


def test_formal_dirty_permission_is_invalid(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        runtime={"formal": True, "allow_dirty": True},
    )
    with pytest.raises(ConfigError, match="formal runs cannot allow"):
        load_config(config_path, root=tmp_path)


def test_command_launcher_rejects_shell_string(tmp_path: Path) -> None:
    config_path = write_config(tmp_path, native={"command": "python train.py && echo unsafe"})
    config = load_config(config_path, root=tmp_path)
    with pytest.raises(ConfigError, match="argv list"):
        build_launch_spec(config)
