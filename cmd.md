# Command Reference

> 项目常用命令与用户侧验证入口。命令应可直接复制执行。

## 常用命令

```bash
cd /root/vla-post-train
uv sync --python 3.12 --all-groups

./lab doctor
./lab method status
./lab config validate --all

./lab experiment dry-run \
  experiments/flowdagger/configs/metaworld_assembly_smoke_b16_seed42.yaml
./lab experiment dry-run \
  experiments/dsrl-pi0/configs/libero90_task57_smoke_seed0.yaml
./lab experiment dry-run \
  experiments/rlinf/configs/libero10_task0_medium_seed0.yaml

uv run ruff format --check .
uv run ruff check .
uv run ty check scripts tests
uv run pytest
```

## 待用户验证

- **状态**：Pending
- **目的**：确认修复后的 `lab experiment summarize` 能在当前 `wandb==0.28.1` 上
  正常抓取 W&B summary 与 GPU system metrics，并写出可序列化的 `summary.json`。
- **前置条件**：`/root/.netrc` 中的 W&B 凭据可用；无需占用 GPU。
- **命令**：

```bash
cd /root/vla-post-train

uv run pytest -q tests/test_monitor.py

uv run python - <<'PY'
import json
from scripts.monitor import collect_wandb

data = collect_wandb(["https://wandb.ai/atticux/rlt-maniskill/runs/jmqtnoox"])
print("state:", data["runs"][0]["state"])
print("gpu_hours:", data["resources"].get("gpu_hours"))
print("eval/success_once:", data["summary"]["eval/success_once"])
json.dumps(data)
print("json-serializable: OK")
PY

git diff --check
```

- **通过标准**：`tests/test_monitor.py` 显示 `3 passed`；脚本输出
  `state: finished`、非空 `gpu_hours`、`eval/success_once: 0.703125` 和
  `json-serializable: OK`，且不抛 `TypeError`；`git diff --check` 无输出。
- **失败时返回**：完整命令输出与 traceback，以及
  `uv run python -c "import wandb; print(wandb.__version__)"` 的结果。

## 历史验证记录

STEAM medium 两卡复现、RLToken 无墙钟长跑和 RLToken progressive 中等预算三项
用户侧验证均已 Passed，命令、通过标准和实际结果记录在 [`docs/log.md`](docs/log.md)
对应条目中，不在本文件重复保留。

## RLToken 运行与汇总

```bash
cd /root/vla-post-train

./lab config validate \
  experiments/rlinf/configs/rlt_maniskill_stage2_progressive_seed2026.yaml
./lab experiment dry-run \
  experiments/rlinf/configs/rlt_maniskill_stage2_progressive_seed2026.yaml

./lab experiment status 20260729-021706__rlt-maniskill-stage2-progressive-seed2026
```

汇总某个 run 前，需要先把该 run 的 W&B URL 临时写入配置的 `tracking.run_urls`
（`primary_metrics` 同理），再执行下面两条命令，完成后按惯例把配置还原为空模板：

```bash
./lab experiment summarize <run-id>
./lab report build rlinf
```
