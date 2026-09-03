"""Generic command launcher tests."""

from pathlib import Path

import yaml

from scripts.config import load_config
from scripts.launchers import build_launch_spec
from tests.helpers import write_config


def test_command_launcher_preserves_argv_and_method_cwd(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        native={"command": ["python", "train.py", "--steps", "10"]},
    )
    config = load_config(config_path, root=tmp_path)

    spec = build_launch_spec(config)

    assert spec.cwd == tmp_path / "methods/example"
    assert spec.argv == ("python", "train.py", "--steps", "10")
    assert spec.environment == ()


def test_command_environment_prefix_remains_declarative(tmp_path: Path) -> None:
    config_path = write_config(tmp_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["environment"] = {"manager": "command", "prefix": ["env", "DEVICE=0"]}
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    config = load_config(config_path, root=tmp_path)

    spec = build_launch_spec(config)

    assert spec.argv == ("env", "DEVICE=0", "python", "-c", "print('ok')")
