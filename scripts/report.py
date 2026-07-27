"""Generated result-table maintenance for method reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.config import ROOT, ConfigError
from scripts.run_record import read_json

BEGIN = "<!-- lab:results:begin -->"
END = "<!-- lab:results:end -->"


def _metric_text(summary: dict[str, Any]) -> str:
    metrics = summary.get("primary_metrics", [])
    if not isinstance(metrics, list) or not metrics:
        return "—"
    rendered: list[str] = []
    for metric in metrics:
        if not isinstance(metric, dict):
            continue
        name = metric.get("name", "metric")
        value = metric.get("value")
        episodes = metric.get("episodes")
        suffix = f" ({episodes} episodes)" if episodes is not None else ""
        rendered.append(f"{name}={value}{suffix}")
    return "<br>".join(rendered) or "—"


def generated_table(method: str, root: Path = ROOT) -> str:
    """Render the deterministic summary table for one method."""

    rows: list[str] = []
    runs_root = root / "experiments" / method / "runs"
    for run_json in sorted(runs_root.glob("*/run.json")):
        summary_path = run_json.with_name("summary.json")
        if not summary_path.is_file():
            continue
        run = read_json(run_json)
        summary = read_json(summary_path)
        rows.append(
            "| `{}` | {} | {} | {} |".format(
                run.get("run_id", run_json.parent.name),
                summary.get("status", "unknown"),
                _metric_text(summary),
                run.get("started_at") or "unknown",
            )
        )
    header = [
        "| Run | 状态 | 主要指标 | 开始时间 |",
        "| --- | --- | --- | --- |",
    ]
    if not rows:
        rows.append("| — | 无记录 | — | — |")
    return "\n".join([*header, *rows])


def build_report(method: str, root: Path = ROOT) -> Path:
    """Replace only the marked generated block and preserve human prose."""

    report_path = root / "experiments" / method / "report.md"
    if not report_path.is_file():
        raise ConfigError(f"method report does not exist: {report_path}")
    text = report_path.read_text(encoding="utf-8")
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ConfigError(f"report must contain exactly one {BEGIN}/{END} block")
    before, remainder = text.split(BEGIN, 1)
    _, after = remainder.split(END, 1)
    replacement = f"{BEGIN}\n{generated_table(method, root)}\n{END}"
    report_path.write_text(f"{before}{replacement}{after}", encoding="utf-8")
    return report_path
