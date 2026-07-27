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

- **状态**：Passed（2026-07-27，用户已确认）。
- **目的**：确认 RLToken Stage 2 的 12 小时时限配置、最终保存逻辑和真实学习 smoke
  证据正确，再提交并启动长跑。
- **前置条件**：`/root/RLinf` 的 `.venv` 可用；Stage 1
  `global_step_2000` checkpoint 已存在；无需占用 GPU。

请在新终端执行：

```bash
cd /root/RLinf

PYTHONPATH=/root/RLinf .venv/bin/pytest -q \
  tests/unit_tests/test_embodied_runner_time_limit.py

grep -F 'rlt/critic_updates_run=2.000' \
  /mnt/data/atticux/rlt-maniskill/logs/stage2-learning-smoke.log
grep -F 'rlt/actor_updates_run=1.000' \
  /mnt/data/atticux/rlt-maniskill/logs/stage2-learning-smoke.log
grep -F 'replay/transition_count=8.000' \
  /mnt/data/atticux/rlt-maniskill/logs/stage2-learning-smoke.log

git diff --check
```

通过标准：

1. pytest 显示 `2 passed`。
2. 三次 `grep` 分别显示 2 次 critic update、1 次 actor update 和 8 条 replay
   transition。
3. `git diff --check` 无输出。

验证已通过。正式启动使用 11 小时原生时限与 11 小时 50 分硬保护。
