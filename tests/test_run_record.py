"""Run readiness and historical evidence tests."""

from pathlib import Path

import pytest

from scripts import run_record
from scripts.config import ConfigError, load_config
from scripts.run_record import finalize_run_record, read_json, verify_run_readiness
from tests.helpers import write_config


def test_formal_run_rejects_dirty_method(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = write_config(tmp_path, runtime={"formal": True, "allow_dirty": False})
    config = load_config(config_path, root=tmp_path)

    def snapshot(path: Path) -> dict[str, object]:
        return {
            "revision": "a" * 40,
            "branch": "main",
            "dirty": path == config.repository_path,
        }

    monkeypatch.setattr(run_record, "git_snapshot", snapshot)
    monkeypatch.setattr(run_record, "_config_committed", lambda _config: True)
    monkeypatch.setattr(run_record, "revision_on_remote", lambda _path, _revision: True)

    with pytest.raises(ConfigError, match="clean method"):
        verify_run_readiness(config)


@pytest.mark.parametrize(
    ("exit_code", "signal_number", "expected_status"),
    [(0, None, "completed"), (7, None, "failed"), (143, 15, "failed")],
)
def test_finalize_records_every_terminal_path(
    exit_code: int,
    signal_number: int | None,
    expected_status: str,
) -> None:
    record: dict[str, object] = {
        "finished_at": None,
        "exit_code": None,
        "signal": None,
        "pid": None,
    }
    finalize_run_record(
        record,
        pid=123,
        exit_code=exit_code,
        signal_number=signal_number,
    )
    assert record["finished_at"]
    assert record["exit_code"] == exit_code
    assert record["signal"] == signal_number
    status = "completed" if record["exit_code"] == 0 else "failed"
    assert status == expected_status


def test_historical_medium_preserves_multiple_revisions() -> None:
    path = run_record.ROOT / "experiments/rlinf/runs/historical__libero10-task0-medium/run.json"
    record = read_json(path)
    assert record["historical"] is True
    assert record["method_code"] is None
    assert len(record["code_revisions"]) == 4
    assert {item["revision"] for item in record["code_revisions"]} == {
        "b6b62a4b6f3ba0a031d66d718151fe40a3a5daf0",
        "450e9272ac27a1528d334943a80d54ce80199b9a",
        "a5780853fe1d42a81bc5e039026c1e4a1ae276ba",
        "193a60dae89256476b67b2c08fd9d00d87343e48",
    }
