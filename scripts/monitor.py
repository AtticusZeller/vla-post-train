"""Local and W&B summary collection."""

from __future__ import annotations

import re
from contextlib import suppress
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from scripts.config import ConfigError, ExperimentConfig
from scripts.run_record import read_json

_RUN_PATH = re.compile(r"^/([^/]+)/([^/]+)/runs/([^/]+)/?$")


def _wandb_path(url: str) -> str:
    parsed = urlparse(url)
    match = _RUN_PATH.fullmatch(parsed.path)
    if parsed.netloc not in {"wandb.ai", "www.wandb.ai"} or not match:
        raise ConfigError(f"unsupported W&B run URL: {url}")
    return "/".join(match.groups())


def collect_wandb(
    run_urls: list[str],
    api: Any | None = None,
    gpu_indices: list[int] | None = None,
) -> dict[str, Any]:
    """Read only explicitly configured W&B runs, preferring run summaries."""

    if not run_urls:
        return {"runs": [], "summary": {}, "resources": {}}
    if api is None:
        import wandb

        api = wandb.Api()

    evidence: list[dict[str, Any]] = []
    merged_summary: dict[str, Any] = {}
    system_rows: list[dict[str, Any]] = []
    for url in run_urls:
        run = api.run(_wandb_path(url))
        raw_summary = getattr(run.summary, "_json_dict", run.summary)
        summary = dict(raw_summary)
        merged_summary.update(summary)
        evidence.append(
            {
                "url": url,
                "state": getattr(run, "state", None),
                "summary_keys": sorted(summary),
            }
        )
        with suppress(AttributeError, TypeError):
            system_rows.extend(dict(row) for row in run.history(stream="system", pandas=False))

    gpu_keys = {
        key
        for row in system_rows
        for key in row
        if key.startswith("system.gpu.") and key.endswith(".gpu")
    }
    if gpu_indices is not None:
        configured_gpu_keys = {f"system.gpu.{index}.gpu" for index in gpu_indices}
        gpu_keys &= configured_gpu_keys
    timestamps = [
        float(row["_timestamp"])
        for row in system_rows
        if isinstance(row.get("_timestamp"), int | float)
    ]
    resources: dict[str, Any] = {"wandb_system_samples": len(system_rows)}
    if len(timestamps) >= 2 and gpu_keys:
        elapsed = max(timestamps) - min(timestamps)
        resources["gpu_hours"] = elapsed * len(gpu_keys) / 3600
        resources["gpu_count"] = len(gpu_keys)
    return {"runs": evidence, "summary": merged_summary, "resources": resources}


def build_summary(
    config: ExperimentConfig,
    run_record: dict[str, Any],
    log_path: Path | None = None,
    api: Any | None = None,
) -> dict[str, Any]:
    """Build the common summary envelope from local and explicit W&B evidence."""

    native = config.native
    local_results: dict[str, Any] = {}
    local_summary = native.get("summary_file")
    if isinstance(local_summary, str):
        resolved_summary = local_summary.replace(
            "{artifact_path}", str(run_record.get("artifact_path", ""))
        )
        source = Path(resolved_summary)
        if not source.is_absolute():
            source = config.repository_path / source
        if source.is_file():
            local_results = read_json(source)
        local_summary = str(source)

    recorded_urls = run_record.get("tracking", {}).get("run_urls", config.run_urls)
    if not isinstance(recorded_urls, list):
        recorded_urls = config.run_urls
    configured_gpus = config.runtime.get("gpus")
    gpu_indices = (
        [int(index) for index in configured_gpus] if isinstance(configured_gpus, list) else None
    )
    wandb_data = collect_wandb(
        [str(url) for url in recorded_urls],
        api=api,
        gpu_indices=gpu_indices,
    )
    exit_code = run_record.get("exit_code")
    traceback_found = False
    if log_path and log_path.is_file():
        traceback_found = "Traceback (most recent call last)" in log_path.read_text(
            encoding="utf-8", errors="replace"
        )
    if exit_code not in (None, 0) or traceback_found:
        status = "failed"
    elif exit_code == 0:
        status = "completed"
    else:
        status = "running"

    primary_metrics = local_results.get("primary_metrics", native.get("primary_metrics", []))
    if not isinstance(primary_metrics, list):
        raise ConfigError("native.primary_metrics must be a list")
    resources = dict(wandb_data["resources"])
    if isinstance(native.get("resources"), dict):
        resources.update(native["resources"])
    return {
        "schema_version": 1,
        "status": status,
        "primary_metrics": primary_metrics,
        "resources": resources,
        "evidence": {
            "local_exit_code": exit_code,
            "local_traceback": traceback_found,
            "wandb_runs": wandb_data["runs"],
            "local_summary": str(local_summary) if local_summary else None,
        },
        "results": {
            "local": local_results,
            "wandb_summary": wandb_data["summary"],
        },
    }
