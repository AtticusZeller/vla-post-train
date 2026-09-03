"""CLI registration and no-side-effect behavior tests."""

from pathlib import Path

import pytest

from scripts import lab
from scripts.config import ConfigError
from scripts.run_record import read_json, write_json


def test_current_method_registry_is_exact() -> None:
    assert set(lab._METHODS) == {
        "fastwam",
        "lerobot",
        "lerobot-xense",
        "tacwam",
        "xense-openpi",
    }


def test_lerobot_framework_registration() -> None:
    assert lab._METHODS["lerobot"] == {
        "branch": "workspace",
        "upstream": "https://github.com/huggingface/lerobot.git",
    }


def test_detached_submodule_pin_may_follow_expected_remote_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lab, "_git", lambda *_args: (0, ""))

    assert lab._branch_matches(tmp_path, "", "workspace")
    assert lab._branch_matches(tmp_path, "workspace", "workspace")
    assert not lab._branch_matches(tmp_path, "main", "workspace")


def test_historical_resume_and_summarize_are_immutable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_path = tmp_path / "experiments/example/runs/historical-example/run.json"
    summary_path = run_path.with_name("summary.json")
    write_json(run_path, {"historical": True})
    write_json(summary_path, {"status": "completed"})
    before_run = run_path.read_bytes()
    before_summary = summary_path.read_bytes()
    monkeypatch.setattr(lab, "find_run", lambda _run_id: run_path)

    with pytest.raises(ConfigError, match="historical run is immutable"):
        lab._resume("historical-example")

    with pytest.raises(ConfigError, match="historical summary is immutable"):
        lab._summarize("historical-example")

    assert read_json(run_path)["historical"] is True
    assert run_path.read_bytes() == before_run
    assert summary_path.read_bytes() == before_summary


def test_retired_suite_commands_are_not_exposed() -> None:
    parser = lab.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["experiment", "suite-configs", "example"])

    with pytest.raises(SystemExit):
        parser.parse_args(["report", "suite", "example"])
