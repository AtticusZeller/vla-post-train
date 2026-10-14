#!/usr/bin/env python
"""Pull one W&B run's config, summary, and full history into a local directory.

Run this once per analysis instead of re-querying W&B for each question. The
history download is the slow part, so it is cached as a pickle that every
follow-up script reads locally.

Usage:
    uv run --with wandb --with pandas python fetch_wandb_run.py <url-or-path> --out <dir>

``<url-or-path>`` accepts a browser URL (query string and anchors are ignored)
or a bare ``entity/project/run_id``.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path


def parse_run_path(raw: str) -> str:
    """Normalize a W&B browser URL or bare path into ``entity/project/run_id``."""
    cleaned = raw.split("?")[0].split("#")[0].rstrip("/")
    match = re.search(r"([^/]+)/([^/]+)/runs/([^/]+)$", cleaned)
    if match:
        return "/".join(match.groups())
    parts = cleaned.split("/")
    if len(parts) == 3:
        return cleaned
    raise SystemExit(f"Cannot parse a W&B run path out of {raw!r}.")


def fetch_history(run, samples: int, attempts: int = 4):
    """Download the full history, retrying the server-side timeout.

    A run with tens of thousands of rows and a wide column set regularly trips
    W&B's ``service process is busy`` timeout on the first try; the same query
    succeeds on a retry, so a hard failure here would be a false negative.
    """
    for attempt in range(1, attempts + 1):
        try:
            return run.history(samples=samples, pandas=True)
        except Exception as exc:  # noqa: BLE001 - the API raises several unrelated types
            if attempt == attempts:
                raise
            delay = 5 * attempt
            print(f"history attempt {attempt}/{attempts} failed ({exc}); retrying in {delay}s")
            time.sleep(delay)
    raise AssertionError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", help="W&B run URL or entity/project/run_id")
    parser.add_argument("--out", required=True, help="output dir (use the session scratchpad)")
    parser.add_argument("--samples", type=int, default=100000, help="history row cap")
    args = parser.parse_args()

    import wandb

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    run = wandb.Api().run(parse_run_path(args.run))

    config = {key: value for key, value in run.config.items() if not key.startswith("_")}
    raw_summary = dict(run.summary).items()
    summary = {key: value for key, value in raw_summary if not key.startswith("_wandb")}
    (out / "config.json").write_text(json.dumps(config, indent=1, default=str))
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str))

    history = fetch_history(run, args.samples)
    history.to_pickle(out / "history.pkl")

    # The metric-group inventory is what tells the analyst which log streams exist
    # (episode/*, update/*, chunk/*, ...) and how often each one was written.
    groups: dict[str, list[str]] = {}
    for column in history.columns:
        groups.setdefault(column.split("/")[0], []).append(column)

    meta = {
        "run_path": parse_run_path(args.run),
        "url": run.url,
        "name": run.name,
        "group": run.group,
        "state": run.state,
        "created_at": str(run.created_at),
        "runtime_s": summary.get("_runtime"),
        "tags": list(run.tags),
        "notes": run.notes,
        "history_rows": int(history.shape[0]),
        "metric_groups": {name: len(columns) for name, columns in sorted(groups.items())},
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1, default=str))

    print(json.dumps(meta, indent=1, default=str))
    print(f"\nwrote config.json summary.json meta.json history.pkl -> {out}")
    print("State other than 'finished' means it stopped early; ask the user why.")


if __name__ == "__main__":
    main()
