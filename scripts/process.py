"""Foreground subprocess execution with tee logging and signal forwarding."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
from typing import Any


@dataclass(frozen=True)
class ProcessResult:
    """Observed child-process completion."""

    pid: int
    exit_code: int
    signal_number: int | None


def run_foreground(
    argv: tuple[str, ...],
    cwd: Path,
    log_path: Path,
    environment: dict[str, str] | None = None,
    on_started: Callable[[int], None] | None = None,
) -> ProcessResult:
    """Run one process in the foreground and tee merged output to disk."""

    log_path.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=True,
        env={**os.environ, **(environment or {})},
    )
    if on_started:
        on_started(process.pid)

    forwarded_signal: int | None = None
    previous_handlers: dict[int, Any] = {}

    def forward(signum: int, _frame: FrameType | None) -> None:
        nonlocal forwarded_signal
        forwarded_signal = signum
        if process.poll() is None:
            os.killpg(process.pid, signum)

    for signum in (signal.SIGINT, signal.SIGTERM):
        previous_handlers[signum] = signal.getsignal(signum)
        signal.signal(signum, forward)

    try:
        assert process.stdout is not None
        with log_path.open("a", encoding="utf-8") as log:
            for line in process.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                log.write(line)
                log.flush()
        return_code = process.wait()
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)

    signal_number = -return_code if return_code < 0 else forwarded_signal
    exit_code = 128 + signal_number if signal_number else return_code
    return ProcessResult(pid=process.pid, exit_code=exit_code, signal_number=signal_number)
