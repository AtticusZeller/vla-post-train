"""Foreground process behavior tests."""

import signal
import sys
from pathlib import Path

from scripts.process import run_foreground


def test_success_is_teed(tmp_path: Path) -> None:
    log = tmp_path / "success.log"
    result = run_foreground(
        (sys.executable, "-c", "print('PROCESS_OK')"),
        tmp_path,
        log,
    )
    assert result.exit_code == 0
    assert result.signal_number is None
    assert "PROCESS_OK" in log.read_text(encoding="utf-8")


def test_failure_exit_code_is_preserved(tmp_path: Path) -> None:
    result = run_foreground(
        (sys.executable, "-c", "raise SystemExit(7)"),
        tmp_path,
        tmp_path / "failure.log",
    )
    assert result.exit_code == 7
    assert result.signal_number is None


def test_signal_exit_is_preserved(tmp_path: Path) -> None:
    code = "import os, signal; os.kill(os.getpid(), signal.SIGTERM)"
    result = run_foreground(
        (sys.executable, "-c", code),
        tmp_path,
        tmp_path / "signal.log",
    )
    assert result.exit_code == 128 + signal.SIGTERM
    assert result.signal_number == signal.SIGTERM
