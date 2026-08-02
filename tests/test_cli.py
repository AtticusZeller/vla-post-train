"""CLI no-side-effect behavior tests."""

import pytest

from scripts import lab
from scripts.config import ConfigError
from scripts.run_record import read_json


def test_lerobot_framework_registration() -> None:
    assert lab._METHODS["lerobot"] == {
        "branch": "workspace",
        "upstream": "https://github.com/huggingface/lerobot.git",
    }


def test_univtac_benchmark_registration() -> None:
    assert lab._METHODS["univtac"] == {
        "branch": "dev",
        "upstream": "https://github.com/univtac/UniVTAC.git",
    }


def test_historical_resume_and_summarize_are_immutable() -> None:
    run_id = "historical__libero10-task0-medium"
    run_path = lab.ROOT / "experiments/rlinf/runs" / run_id / "run.json"
    summary_path = run_path.with_name("summary.json")
    before_run = run_path.read_bytes()
    before_summary = summary_path.read_bytes()

    with pytest.raises(ConfigError, match="historical run is immutable"):
        lab._resume(run_id)

    with pytest.raises(ConfigError, match="historical summary is immutable"):
        lab._summarize(run_id)

    assert read_json(run_path)["historical"] is True
    assert run_path.read_bytes() == before_run
    assert summary_path.read_bytes() == before_summary
