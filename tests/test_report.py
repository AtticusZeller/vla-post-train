"""Method report update tests."""

from pathlib import Path

from scripts.report import BEGIN, END, build_report
from scripts.run_record import write_json


def test_report_preserves_human_narrative(tmp_path: Path) -> None:
    method_root = tmp_path / "experiments/example"
    run_root = method_root / "runs/run-1"
    report = method_root / "report.md"
    report.parent.mkdir(parents=True)
    report.write_text(
        f"# Example\n\n人工结论必须保留。\n\n{BEGIN}\nold\n{END}\n\n证据边界也必须保留。\n",
        encoding="utf-8",
    )
    write_json(
        run_root / "run.json",
        {"run_id": "run-1", "started_at": "2026-07-27T00:00:00Z"},
    )
    write_json(
        run_root / "summary.json",
        {
            "status": "completed",
            "primary_metrics": [{"name": "success_rate", "value": 0.5, "episodes": 10}],
        },
    )

    build_report("example", root=tmp_path)
    updated = report.read_text(encoding="utf-8")
    assert "人工结论必须保留。" in updated
    assert "证据边界也必须保留。" in updated
    assert "success_rate=0.5 (10 episodes)" in updated
    assert "old" not in updated
