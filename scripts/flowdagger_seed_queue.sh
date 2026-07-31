#!/usr/bin/env bash
# Sequentially run all 12 MetaWorld-12 FlowDAgger formal configs for one seed.
#
# Skips tasks that already have a completed, non-historical run matching the
# current suite protocol (see scripts/flowdagger_suite.py::_suite_results).
# Formal runs in this repo write to a shared root working tree, so they must
# stay sequential even when multiple GPUs are idle.
#
# Usage: scripts/flowdagger_seed_queue.sh <seed>
set -euo pipefail

SEED="${1:?usage: flowdagger_seed_queue.sh <seed>}"
cd "$(dirname "$0")/.."

SLUGS=(assembly bin-picking box-close coffee-pull dial-turn door-lock hammer hand-insert lever-pull pick-place soccer stick-push)

is_done() {
  local config_path="$1"
  uv run python - "$config_path" <<'PYEOF'
import sys
import yaml
from pathlib import Path
from scripts.config import ROOT
from scripts.flowdagger_suite import load_suite, _suite_results

suite = load_suite()
results = _suite_results(ROOT, suite)
cfg = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8"))
key = (cfg["native"]["suite"]["task"], cfg["native"]["suite"]["seed"])
print("yes" if key in results else "no")
PYEOF
}

for slug in "${SLUGS[@]}"; do
  config="experiments/flowdagger/configs/metaworld12_${slug}_full_seed${SEED}.yaml"
  id="metaworld12-${slug}-full-seed${SEED}"

  if [ "$(is_done "$config")" = "yes" ]; then
    echo "[$(date -u +%FT%TZ)] skipping completed ${id}"
    continue
  fi

  echo "[$(date -u +%FT%TZ)] validating ${config}"
  ./lab config validate "$config"

  echo "[$(date -u +%FT%TZ)] running ${id}"
  ./lab experiment run "$config"

  run_id="$(ls -td experiments/flowdagger/runs/*"__${id}" | head -1 | xargs basename)"
  echo "[$(date -u +%FT%TZ)] summarizing ${run_id}"
  ./lab experiment summarize "$run_id"
  ./lab report suite flowdagger

  git add "experiments/flowdagger/runs/${run_id}" \
    experiments/flowdagger/metaworld12-report.md \
    experiments/flowdagger/metaworld12-summary.json
  git commit -m "data(flowdagger): archive MetaWorld run"
  git push

  echo "[$(date -u +%FT%TZ)] ${id} completed, summarized, committed, and pushed"
done

echo "[$(date -u +%FT%TZ)] all available seed-${SEED} task runs completed"
