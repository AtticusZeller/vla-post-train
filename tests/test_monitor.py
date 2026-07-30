"""W&B and local summary reconciliation tests."""

from pathlib import Path
from typing import Any

from scripts.config import load_config
from scripts.monitor import build_summary, collect_wandb
from scripts.run_record import write_json
from tests.helpers import write_config


class FakeRun:
    state = "finished"
    summary = {"success_rate": 0.75}

    def history(self, *, stream: str, pandas: bool) -> list[dict[str, Any]]:
        assert stream == "system"
        assert pandas is False
        return [
            {"_timestamp": 0.0, "system.gpu.0.gpu": 50.0},
            {"_timestamp": 3600.0, "system.gpu.0.gpu": 80.0},
        ]


class FakeApi:
    def __init__(self) -> None:
        self.paths: list[str] = []

    def run(self, path: str) -> FakeRun:
        self.paths.append(path)
        return FakeRun()


def test_wandb_reads_only_explicit_run_and_system_stream() -> None:
    api = FakeApi()
    result = collect_wandb(["https://wandb.ai/entity/project/runs/run-id"], api=api)
    assert api.paths == ["entity/project/run-id"]
    assert result["summary"] == {"success_rate": 0.75}
    assert result["resources"]["gpu_hours"] == 1.0
    assert result["resources"]["gpu_count"] == 1


def test_local_summary_import_and_traceback_priority(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    write_json(source, {"methods": {"baseline": {"success_rate": 0.5}}})
    config_path = write_config(
        tmp_path,
        native={
            "command": ["python", "-c", "print('ok')"],
            "summary_file": str(source),
            "primary_metrics": [{"name": "success_rate", "value": 0.5}],
        },
    )
    config = load_config(config_path, root=tmp_path)
    log = tmp_path / "console.log"
    log.write_text("Traceback (most recent call last):\nboom\n", encoding="utf-8")
    summary = build_summary(config, {"exit_code": 0}, log_path=log)
    assert summary["status"] == "failed"
    assert summary["evidence"]["local_traceback"] is True
    assert summary["results"]["local"]["methods"]["baseline"]["success_rate"] == 0.5


def test_local_summary_resolves_artifact_path_placeholder(tmp_path: Path) -> None:
    artifact_path = tmp_path / "artifacts" / "run-id"
    source = artifact_path / "native" / "summary.json"
    write_json(source, {"methods": {"steam": {"success_rate": 0.6}}})
    config_path = write_config(
        tmp_path,
        native={
            "command": ["python", "-c", "print('ok')"],
            "summary_file": "{artifact_path}/native/summary.json",
            "primary_metrics": [],
        },
    )
    config = load_config(config_path, root=tmp_path)

    summary = build_summary(
        config,
        {"exit_code": 0, "artifact_path": str(artifact_path)},
    )

    assert summary["results"]["local"]["methods"]["steam"]["success_rate"] == 0.6
    assert summary["evidence"]["local_summary"] == str(source)
