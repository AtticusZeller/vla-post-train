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

- **状态**：Passed（2026-07-28，用户明确授权 Agent 按原样命令代验）。
- **目的**：确认 STEAM medium 的训练 seed 与评测 seed 已解耦、两卡启动配置正确，
  且真实 value-training smoke 已完成优化并保存 checkpoint。
- **前置条件**：`/root/RLinf/.venv` 可用；无需重新占用 GPU，smoke 产物已保存在
  `/mnt/data/atticux/vla-post-train/rlinf/`。
- **命令**：

请在新终端执行：

```bash
cd /root/vla-post-train

uv run pytest -q tests/test_monitor.py

(
  cd methods/rlinf
  /root/RLinf/.venv/bin/python -m pytest -q \
    tests/unit_tests/test_recap_steam_summary.py \
    tests/unit_tests/test_recap_steam_medium_configs.py
)

./lab experiment dry-run \
  experiments/rlinf/configs/libero10_task0_medium_steam_seed1_2gpu.yaml

test -f \
  /mnt/data/atticux/vla-post-train/rlinf/20260728-080517__libero10-task0-medium-steam-value-smoke-2gpu/native/smoke-seed-1/steam/steam-medium-value-2gpu-smoke/checkpoints/global_step_2/actor/model_state_dict/full_weights.pt
grep -F '"exit_code": 0' \
  experiments/rlinf/runs/20260728-080517__libero10-task0-medium-steam-value-smoke-2gpu/run.json

git diff --check
git -C methods/rlinf diff --check
```

- **通过标准**：根仓测试显示 `3 passed`，RLinf 测试显示 `5 passed`；dry-run
  显示 `steam-medium-replication 1 0`、`CUDA_VISIBLE_DEVICES=0,1` 和
  `RLINF_NPROC=2`；checkpoint 检查成功；`grep` 显示 `"exit_code": 0`；
  两次 diff 检查均无输出。
- **失败时返回**：完整命令输出；若 checkpoint 检查失败，再返回
  `ls -lah` 对应的 `global_step_2/actor/model_state_dict/` 目录。

验证结果：根仓 `3 passed`、RLinf `5 passed`；dry-run、checkpoint、退出码及
两次 diff 检查均通过。
