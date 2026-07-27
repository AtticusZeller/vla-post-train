"""Test workspace builders."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def write_config(
    root: Path,
    *,
    method: str = "example",
    native: dict[str, Any] | None = None,
    runtime: dict[str, Any] | None = None,
    tracking: dict[str, Any] | None = None,
) -> Path:
    """Create a minimal valid experiment workspace and YAML."""

    (root / "methods" / method).mkdir(parents=True, exist_ok=True)
    config_path = root / "experiments" / method / "configs" / "test.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": 1,
        "id": "test-config",
        "method": method,
        "repository": {"path": f"methods/{method}"},
        "environment": {"manager": "none"},
        "runtime": {
            "formal": False,
            "allow_dirty": False,
            "artifact_root": str(root / "artifacts"),
            **(runtime or {}),
        },
        "tracking": {"backend": "wandb", "project": "test", "run_urls": [], **(tracking or {})},
        "native": native or {"command": ["python", "-c", "print('ok')"]},
    }
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return config_path
