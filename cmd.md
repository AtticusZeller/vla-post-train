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

## RLToken 无墙钟长跑验证

- **状态**：Passed（2026-07-29，用户要求 Agent 完成验证后直接启动）。
- **目的**：确认正式配置无墙钟限制、关键参数与 RLinf upstream 对齐、Stage 1
  checkpoint 可作为 expert 加载，且 OSSFS 上生成的视频可播放。
- **前置条件**：两张 H20、`/root/RLinf/.venv`、Stage 1 step 2,000 checkpoint 和
  `/mnt/data` 可写。
- **命令**：

```bash
cd /root/vla-post-train

./lab config validate \
  experiments/rlinf/configs/rlt_maniskill_stage2_unlimited_seed2026.yaml
./lab experiment dry-run \
  experiments/rlinf/configs/rlt_maniskill_stage2_unlimited_seed2026.yaml

(
  cd methods/rlinf
  /root/RLinf/.venv/bin/python -m pytest -q \
    tests/unit_tests/test_record_video.py
)

ffprobe -v error \
  -show_entries stream=codec_name,width,height,nb_frames \
  -show_entries format=duration,size -of json \
  /mnt/data/atticux/vla-post-train/rlinf/rlt-maniskill/smoke/stage2-unlimited/video/eval/seed_2026/0.mp4
```

- **通过标准**：dry-run 只解析为 `stage2-unlimited` 且 runtime 不含
  `timeout_hours`；录像单测 3 项通过；`ffprobe` 返回 H.264、非零帧数与时长。
- **失败时返回**：完整终端输出、对应 W&B run URL，以及视频文件大小和
  `ffprobe -v trace` 尾部。

验证结果：根 launcher 测试 5 项、录像单测 3 项、Hydra 展开、ruff 和 dry-run
均通过；真实两卡 smoke `ifrzd3ve` 正常退出，两个 MP4 均为 H.264、11 帧、1.1 秒。

## RLToken progressive 中等预算验证

- **状态**：Passed（2026-07-29，用户要求 Agent 验证后直接启动）。
- **目的**：确认新 run 以 100 steps 自然结束、没有墙钟 timeout，并能在中等预算内
  跨过缩短后的 10,000-update online gate。
- **前置条件**：`/root/RLinf/.venv`、Stage 1 step 2,000 checkpoint、两张 H20 和
  可写 `/mnt/data`。
- **命令**：

```bash
cd /root/vla-post-train

./lab config validate \
  experiments/rlinf/configs/rlt_maniskill_stage2_progressive_seed2026.yaml
./lab experiment dry-run \
  experiments/rlinf/configs/rlt_maniskill_stage2_progressive_seed2026.yaml

grep -E \
  'max_epochs: 100|warmup_min_size: 5000|warmup_post_collect_updates: 10000|total_num_envs: 64' \
  /tmp/rlt-progressive.yaml
! grep -q max_run_duration /tmp/rlt-progressive.yaml
```

- **通过标准**：dry-run 仅解析为 `stage2-progressive`；resolved config 包含目标数值，
  不含 `max_run_duration`；根测试、静态检查和 diff check 全部通过。
- **失败时返回**：完整命令输出、resolved config 和对应 run 的本地 console 尾部。

验证结果：Hydra 展开、bash 语法、RLinf 配置单测、根 ruff/ty、25 个 pytest、
config validate/dry-run 及两层 diff check 均通过。
