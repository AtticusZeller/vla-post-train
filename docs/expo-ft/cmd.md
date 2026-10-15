# EXPO-FT Commands

## 启动 RoboTwin 环境端

用途：在 RoboTwin 的环境里起 `run_client`，拨号到 learner（`train_pi_robo.py` 或 `eval_droid_policy.py`）监听的端口，
为它执行环境 RPC。

前提：RoboTwin 环境与资产已装好（见 [robotwin/overview.md](../robotwin/overview.md)）；learner 已在 `<port>` 上监听；
在 `methods/expo-ft` 下运行。服务器上另需 `VK_ICD_FILENAMES=/root/data/atticux/vulkan/nvidia_icd_egl.json`。

```bash
ROBOTWIN_ROOT=<robotwin checkout> PYTHONPATH=$PWD:$PWD/expo_ft/agents/vla/openpi/packages/xense-client/src <robotwin venv>/bin/python -m client.run_client --host <learner host> --port <port> --config-task-path configs/task/robotwin_beat_block_hammer.py
```

预期：日志出现 `Environment robotwin_beat_block_hammer_train_1 created successfully`；每次 reset 先跑一次专家筛种子，
再按该种子摆场景。

## RoboTwin 示教转 LeRobot 并算 norm stats

用途：把官方 `dataset/<task>/aloha-agilex_clean_50.zip` 解压后的每回合 HDF5 转成 SFT 与 replay 共用的 LeRobot v3.0 数据集。

前提：在 `methods/expo-ft` 下、learner 环境中；`<lerobot home>` 是数据集根目录（训练机上为
`/root/data/atticux/agent-workspace/expo-ft/data/lerobot`）；norm stats 写到当前目录的 `assets/` 下，在
`<workspace>` 目录运行，训练时用 `--assets-base-dir=<workspace>/assets` 指向它。

```bash
HF_LEROBOT_HOME=<lerobot home> .venv/bin/python scripts/convert_robotwin_to_lerobot.py --raw_dir <.../beat_block_hammer/aloha-agilex_clean_50> --robotwin_root <robotwin checkout> --repo_id robotwin/beat_block_hammer_aloha_clean_50
```

```bash
cd <workspace> && JAX_PLATFORMS=cpu HF_LEROBOT_HOME=<lerobot home> <expo-ft>/.venv/bin/python <expo-ft>/expo_ft/agents/vla/openpi/scripts/compute_norm_stats.py --config-name pi05_robotwin_beat_block_hammer_lora
```

预期：输出 `Wrote 50 episodes, 5682 frames`；`assets/pi05_robotwin_beat_block_hammer_lora/robotwin/beat_block_hammer_aloha_clean_50/norm_stats.json`。

## 训练机上的夜间 SFT → 评测 → 联合更新

用途：凌晨卡空时自动训练 SFT、评最后一个 checkpoint 的基座成功率、再起 EXPO-FT 联合更新。

前提：`xense-training-h100` 上 `/root/data/atticux/agent-workspace/expo-ft/` 已有 `src/expo-ft`（含 learner venv 与
xense-openpi checkout）、数据集、norm stats；`/root/data/atticux/robotwin` 有 RoboTwin 环境；三份脚本与
`scripts/robotwin/` 相同，放在 `/root/data/atticux/`（`night_sft.sh` 即 `night_run.sh`）；W&B key 在
`/root/data/atticux/.wandb_key`。可用 `START`、`DEADLINE`、`EVAL_EPISODES`、`EXP`、`RL_RUN` 环境变量覆盖默认值。

```bash
tmux new-session -d -s atticux-night-sft "/root/data/atticux/night_sft.sh > /root/data/atticux/agent-workspace/expo-ft/logs/night_$(date +%Y%m%d).log 2>&1"
```

预期：日志先写 `waiting until ... 02:00`；有空卡后依次出现 `step 0 ok`、`training exited rc=0`、各分片结果与
`base-policy success: k/50`、`starting RL`。单独评测或单独起 RL 用 `eval_sft_ckpt.sh <gpu> <step_dir> <port>
<episodes> <out_dir> [seed_index]` 与 `rl_joint.sh <gpus> <step_dir> <run_name>`。
