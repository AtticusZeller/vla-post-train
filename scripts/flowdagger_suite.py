"""Materialize and summarize the FlowDAgger MetaWorld-12 experiment suite."""

from __future__ import annotations

import json
import re
from pathlib import Path
from statistics import mean
from typing import Any

import yaml

from scripts.config import ROOT, ConfigError, load_config
from scripts.run_record import read_json

SUITE_RELATIVE = Path("experiments/flowdagger/metaworld12_suite.yaml")
CONFIG_PREFIX = "metaworld12_"
_SAFE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def load_suite(root: Path = ROOT) -> dict[str, Any]:
    """Load and minimally validate the versioned suite manifest."""
    path = root / SUITE_RELATIVE
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise ConfigError(f"invalid FlowDAgger suite manifest: {path}")
    tasks = raw.get("tasks")
    seeds = raw.get("seeds")
    if not isinstance(tasks, list) or len(tasks) != 12:
        raise ConfigError("FlowDAgger suite must define exactly 12 tasks")
    if not isinstance(seeds, list) or len(seeds) != 3:
        raise ConfigError("FlowDAgger suite must define exactly 3 seeds")
    slugs = []
    keys = []
    for task in tasks:
        if not isinstance(task, dict):
            raise ConfigError("each FlowDAgger suite task must be a mapping")
        key = task.get("key")
        slug = task.get("slug")
        if not isinstance(key, str) or not isinstance(slug, str) or not _SAFE.fullmatch(slug):
            raise ConfigError(f"invalid FlowDAgger task entry: {task!r}")
        keys.append(key)
        slugs.append(slug)
    if len(set(keys)) != len(keys) or len(set(slugs)) != len(slugs):
        raise ConfigError("FlowDAgger suite task keys and slugs must be unique")
    return raw


def _native_argv(
    suite: dict[str, Any],
    task: dict[str, str],
    seed: int,
    *,
    phase: str,
) -> list[str]:
    args = dict(suite["protocol_args"])
    if phase == "smoke":
        args.update(suite["smoke_args"])
    values = [
        ("--env", "metaworld"),
        ("--task_key", task["key"]),
        ("--seed", str(seed)),
        ("--wandb_entity", "1831768457"),
        ("--wandb_project", "flowdagger"),
        ("--launch_group_id", str(suite["protocol"])),
        ("--max_steps", str(args["max_steps"])),
        ("--seed_expert_episodes", str(args["seed_expert_episodes"])),
        ("--bc_steps_per_episode", str(args["bc_steps_per_episode"])),
        ("--bc_batch_size", str(args["bc_batch_size"])),
        ("--eval_episodes", str(args["eval_episodes"])),
        ("--eval_interval", str(args["eval_interval"])),
        ("--log_interval", "100" if phase == "full" else "1"),
        ("--checkpoint_interval", str(args["checkpoint_interval"])),
        ("--save_eval_video", "1"),
        ("--eval_video_episodes", str(args["eval_video_episodes"])),
        ("--eval_video_fps", str(args["eval_video_fps"])),
        ("--render", "0"),
        ("--inversion_method", "perstep_fp"),
        ("--fp_per_step", "5"),
        ("--dual_buffer", "1" if phase == "full" else "0"),
        ("--dual_buffer_auto_frac", str(args["dual_buffer_auto_frac"])),
        ("--filter_failures", "1"),
        ("--takeover_min", str(args["takeover_min"])),
        ("--takeover_max", str(args["takeover_max"])),
        ("--beta_start", "1.0"),
        ("--beta_end", "1.0"),
        ("--beta_decay_episodes", "1"),
        ("--prefix", f"mw12-{task['slug']}-{phase}"),
    ]
    return [item for pair in values for item in pair]


def _config(
    suite: dict[str, Any],
    task: dict[str, str],
    seed: int,
    *,
    phase: str,
) -> dict[str, Any]:
    formal = phase == "full"
    args = dict(suite["protocol_args"])
    if not formal:
        args.update(suite["smoke_args"])
    return {
        "schema_version": 1,
        "id": f"metaworld12-{task['slug']}-{phase}-seed{seed}",
        "method": "flowdagger",
        "repository": {
            "path": "methods/flowdagger",
            "expected_branch": "dev",
            "require_clean": formal,
        },
        "environment": {"manager": "conda", "name": "dsrl_pi0"},
        "runtime": {
            "formal": formal,
            "allow_dirty": not formal,
            "gpus": [0],
            "artifact_root": "/mnt/data/atticux/vla-post-train",
            "timeout_hours": 4 if formal else 1,
        },
        "tracking": {
            "backend": "wandb",
            "project": "flowdagger",
            "run_urls": [],
        },
        "native": {
            "env": {
                "CUDA_VISIBLE_DEVICES": "0",
                "EXP": "{artifact_path}",
                "MUJOCO_GL": "egl",
                "WANDB_MODE": "online",
            },
            "suite": {
                "protocol": suite["protocol"],
                "phase": phase,
                "task": task["key"],
                "seed": seed,
                "adaptation_rollouts": (
                    args["seed_expert_episodes"] + args["max_steps"] // args["bc_steps_per_episode"]
                ),
            },
            "argv": _native_argv(suite, task, seed, phase=phase),
            "result_file": "{artifact_path}/flowdagger_result.json",
            "summary_file": "{artifact_path}/flowdagger_result.json",
            "primary_metrics": [],
        },
    }


def materialize_configs(root: Path = ROOT) -> list[Path]:
    """Write the deterministic 12 smoke + 36 formal YAML configurations."""
    suite = load_suite(root)
    config_dir = root / "experiments/flowdagger/configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    expected: dict[Path, dict[str, Any]] = {}
    for raw_task in suite["tasks"]:
        task = {"key": str(raw_task["key"]), "slug": str(raw_task["slug"])}
        smoke_seed = int(suite["smoke_seed"])
        smoke_path = config_dir / f"{CONFIG_PREFIX}{task['slug']}_smoke_seed{smoke_seed}.yaml"
        expected[smoke_path] = _config(suite, task, smoke_seed, phase="smoke")
        for raw_seed in suite["seeds"]:
            seed = int(raw_seed)
            path = config_dir / f"{CONFIG_PREFIX}{task['slug']}_full_seed{seed}.yaml"
            expected[path] = _config(suite, task, seed, phase="full")

    for stale in config_dir.glob(f"{CONFIG_PREFIX}*.yaml"):
        if stale not in expected:
            stale.unlink()
    for path, data in expected.items():
        path.write_text(
            yaml.safe_dump(data, sort_keys=False, width=1000),
            encoding="utf-8",
        )
    return sorted(expected)


def _metric_map(result: dict[str, Any]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for metric in result.get("primary_metrics", []):
        if isinstance(metric, dict) and isinstance(metric.get("value"), int | float):
            metrics[str(metric.get("name"))] = float(metric["value"])
    return metrics


def _suite_results(root: Path, suite: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    selected: dict[tuple[str, int], dict[str, Any]] = {}
    runs_root = root / "experiments/flowdagger/runs"
    for run_path in sorted(runs_root.glob("*/run.json")):
        run = read_json(run_path)
        if run.get("historical") or run.get("exit_code") != 0:
            continue
        config_value = run.get("config")
        if not isinstance(config_value, str):
            continue
        config = load_config(config_value, root=root)
        metadata = config.native.get("suite")
        if (
            not isinstance(metadata, dict)
            or metadata.get("protocol") != suite["protocol"]
            or metadata.get("phase") != "full"
        ):
            continue
        sources = run.get("sources", [])
        if not isinstance(sources, list):
            continue
        result_path = next(
            (Path(source) for source in sources if str(source).endswith("flowdagger_result.json")),
            None,
        )
        if result_path is None or not result_path.is_file():
            continue
        result = read_json(result_path)
        key = (str(metadata["task"]), int(metadata["seed"]))
        selected[key] = {
            "run_id": run["run_id"],
            "started_at": run.get("started_at"),
            "result": result,
        }
    return selected


def build_suite_report(root: Path = ROOT) -> tuple[Path, Path]:
    """Build machine-readable and Chinese progress reports for the suite."""
    suite = load_suite(root)
    results = _suite_results(root, suite)
    rows = []
    complete_task_deltas = []
    for task in suite["tasks"]:
        task_key = str(task["key"])
        seed_results = []
        for raw_seed in suite["seeds"]:
            seed = int(raw_seed)
            entry = results.get((task_key, seed))
            if entry is None:
                continue
            metrics = _metric_map(entry["result"])
            if {"base_success_rate", "final_success_rate", "delta_success_rate"} <= metrics.keys():
                seed_results.append({"seed": seed, **metrics, "run_id": entry["run_id"]})
        bases = [item["base_success_rate"] for item in seed_results]
        finals = [item["final_success_rate"] for item in seed_results]
        deltas = [item["delta_success_rate"] for item in seed_results]
        if len(seed_results) == len(suite["seeds"]):
            complete_task_deltas.append(mean(deltas))
        rows.append(
            {
                "task": task_key,
                "completed_seeds": len(seed_results),
                "expected_seeds": len(suite["seeds"]),
                "base_success_rate": mean(bases) if bases else None,
                "final_success_rate": mean(finals) if finals else None,
                "delta_success_rate": mean(deltas) if deltas else None,
                "seeds": seed_results,
            }
        )

    expected_runs = len(suite["tasks"]) * len(suite["seeds"])
    summary = {
        "schema_version": 1,
        "suite": suite["id"],
        "protocol": suite["protocol"],
        "completed_runs": len(results),
        "expected_runs": expected_runs,
        "status": "completed" if len(results) == expected_runs else "running",
        "macro_delta_success_rate": (
            mean(complete_task_deltas) if len(complete_task_deltas) == len(suite["tasks"]) else None
        ),
        "tasks": rows,
    }
    json_path = root / "experiments/flowdagger/metaworld12-summary.json"
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    def value(item: object) -> str:
        return f"{item:.3f}" if isinstance(item, int | float) else "—"

    lines = [
        "# FlowDAgger MetaWorld-12 实验汇总",
        "",
        f"- 协议：`{suite['protocol']}`",
        f"- 进度：{len(results)}/{expected_runs} 个正式运行",
        "- 正式结论门槛：12 tasks × 3 seeds 全部完成。",
        "",
        "| Task | Seeds | Base SR | Final SR | Δ SR |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['task']}` | {row['completed_seeds']}/{row['expected_seeds']} | "
            f"{value(row['base_success_rate'])} | {value(row['final_success_rate'])} | "
            f"{value(row['delta_success_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## 证据边界",
            "",
            "- 未完成三 seed 的任务只显示进度性均值，不进入正式 macro average。",
            "- 每个任务独立训练 steering policy；这不是联合多任务 steering policy。",
            "- 本地稳定配置使用 `bc_batch_size=16`，不声称与论文全部超参数完全一致。",
            "",
        ]
    )
    markdown_path = root / "experiments/flowdagger/metaworld12-report.md"
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, markdown_path
