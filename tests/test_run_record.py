"""Run readiness and historical evidence tests."""

from pathlib import Path

import pytest

from scripts import run_record
from scripts.config import ConfigError, load_config
from scripts.run_record import finalize_run_record, verify_run_readiness
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
