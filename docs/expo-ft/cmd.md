# EXPO-FT Commands

## 启动 RoboTwin 环境端

用途：在 RoboTwin 的环境里起 `run_client`，拨号到 learner（`train_pi_robo.py` 或 `eval_droid_policy.py`）监听的端口，
为它执行环境 RPC。

前提：RoboTwin 环境与资产已装好（见 [robotwin/overview.md](../robotwin/overview.md)）；learner 已在 `<port>` 上监听；
在 `methods/expo-ft` 下运行。服务器上另需 `VK_ICD_FILENAMES=/root/data/atticux/vulkan/nvidia_icd_egl.json`。

```bash
ROBOTWIN_ROOT=<robotwin checkout> PYTHONPATH=$PWD:$PWD/expo_ft/agents/vla/openpi/packages/xense-client/src <robotwin venv>/bin/python -m client.run_client --host <learner host> --port <port> --config-task-path configs/task/robotwin_beat_block_hammer.py
```

预期：日志出现 `Environment robotwin_beat_block_hammer_train_1 created successfully`；每次 reset 先跑一次专家筛种子
（约 1 s），再按该种子摆场景；设了 `ROBOTWIN_SEED_TABLE` 时直接从表里取种子。其他任务用 `configs/task/robotwin_task.py`，
两侧都要设 `ROBOTWIN_TASK=<task>`。

## 生成训练种子表

用途：离线算出专家能做成的种子与对应指令，RL 的 reset 按表取种子（`ROBOTWIN_SEED_TABLE`），与在线逐个检查的序列相同。

前提：RoboTwin 环境（服务器上加 `VK_ICD_FILENAMES` 与 `CUDA_VISIBLE_DEVICES`，02 另加 `LD_LIBRARY_PATH`）；在 `methods/expo-ft`
下运行。每张卡一个进程，各查一段连续的种子；训练种子段从 10100000 起。Hard 加 `--task_config demo_randomized`。

```bash
ROBOTWIN_ROOT=<robotwin checkout> PYTHONPATH=$PWD:$PWD/expo_ft/agents/vla/openpi/packages/xense-client/src <robotwin venv>/bin/python scripts/robotwin/make_seed_table.py check --task <task> --task_config demo_clean --start 10100000 --count 200 --out <dir>/shard_0.json
```

```bash
<robotwin venv>/bin/python scripts/robotwin/make_seed_table.py merge --out <dir>/train_seeds.json <dir>/shard_*.json
```

预期：每个种子一行 `seed ... ok=... 1.0s`（Hard 更慢）；合并后输出 `k/n seeds in [start, end)`。bbh demo_clean 600 个候选
451 个有效。

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

用途：凌晨卡空时自动训练 SFT、评最后一个 checkpoint 的基座成功率，不低于 30% 时再起 EXPO-FT 联合更新。

前提：`xense-training-h100` 上 `/root/data/atticux/agent-workspace/expo-ft/` 已有 `src/expo-ft`（`robotwin-sim` checkout、
learner venv、xense-openpi checkout）、数据集与 norm stats；`/root/data/atticux/robotwin` 有 RoboTwin 环境；W&B key 在
`/root/data/atticux/.wandb_key`。资源与规则见 [experiment-ops.md](experiment-ops.md)。常用环境变量：`START`、`DEADLINE`
（等卡窗口）、`TRAIN_STOP`、`RL_STOP`、`EXP`、`STEPS`、`NO_RL=1`（评完即停）、`TRAIN_MODE=--resume`（同卡数续训）、
`SKIP_TRAIN=<gpu 列表>`（只评测与 RL）、`EXTRA_TRAIN_ARGS`（例如 `--weight-loader.params-path=<step>/params`）。

```bash
tmux new-session -d -s atx_night_sft "EXP=sft_bbh_clean50_10k STEPS=10000 NO_RL=1 /root/data/atticux/agent-workspace/expo-ft/src/expo-ft/scripts/robotwin/night_run.sh > /root/data/atticux/agent-workspace/expo-ft/logs/night_$(date +%Y%m%d).log 2>&1"
```

预期：日志先写 `waiting until ... 01:30`；有空卡后依次出现 `step 0 ok`、`training exited rc=0`、各分片结果与
`base-policy success: k/50`；未设 `NO_RL` 且不低于 30% 时接着 `starting RL`。退出码 2 表示低于 30%、停在 RL 之前。

## 单独评测一个 checkpoint

用途：基座策略（`eval_sft_ckpt.sh`）或完整 EXPO 策略（`eval_full_policy.sh`，新初始化的 edit actor 与 critic）评若干回合。

前提：同上；一对 learner 与环境端占一张卡约 47 GB；并行时每对用不同端口与 `seed_index`。完整策略可用 `N_EDIT`、
`EDIT_SCALE` 覆盖编辑样本数与幅度。其他任务与联训基座加 `TASK=<task> PI05_CONFIG=pi05_robotwin_cotrain10_lora
ASSET_ID=robotwin/cotrain10_aloha_clean_50`；bbh 用官方协议要加 `ROBOTWIN_SINGLE_ATTEMPT=0`（它的配置默认开单次尝试判定）；
Hard 加 `ROBOTWIN_TASK_CONFIG=demo_randomized`（指令保持默认 seen）。

```bash
/root/data/atticux/agent-workspace/expo-ft/src/expo-ft/scripts/robotwin/eval_sft_ckpt.sh <gpu> <step_dir> <port> <episodes> <out_dir> <seed_index>
```

```bash
N_EDIT=0 /root/data/atticux/agent-workspace/expo-ft/src/expo-ft/scripts/robotwin/eval_full_policy.sh <gpu> <step_dir> <port> <episodes> <out_dir> <seed_index>
```

预期：`<out_dir>/eval.log` 每回合一行 `success=... len=...`，结尾 `Evaluation complete: success_rate=... (k/n)`。

## 单独起联合更新并查看回合结果

用途：从一个 SFT checkpoint 起 EXPO-FT 联合更新（同名运行带 `--resume`，会从最近的 agent checkpoint 接上），并从 W&B
读已结束的回合。

前提：5 张空卡。第一张做推理并放环境端，其余做更新（更新卡数要能整除 batch 64，1 + 2 张也行）；参数取参考默认，`EDIT_SCALE`
可覆盖 β。同一台机器并行第二次运行时换卡并设不同的 `PORT`。单任务标准实验环境（用户 2026-10-19）：随机种子
（`ROBOTWIN_SEED_TABLE`）+ `ROBOTWIN_STEP_LIMIT`（bbh 150，其余为示教平均长度的 1.3 倍）+ `ROBOTWIN_SINGLE_ATTEMPT=0`；每次运行到
第 300 回合手动停。其他任务与联训基座加 `TASK`、`PI05_CONFIG`、`ASSET_ID`（同评测），Hard 加 `ROBOTWIN_TASK_CONFIG=demo_randomized`。
单场景调试用 `ROBOTWIN_FIXED_SEED=1`（每回合用种子段里第一个有效种子）。在 `02-xense-training` 上先
`export LD_LIBRARY_PATH=/root/data/atticux/nvidia-gl-580.65.06`。

```bash
tmux new-session -d -s atx_rl "EDIT_SCALE=0.05 ROBOTWIN_SINGLE_ATTEMPT=0 ROBOTWIN_STEP_LIMIT=150 ROBOTWIN_SEED_TABLE=/root/data/atticux/agent-workspace/expo-ft/data/robotwin_seeds/beat_block_hammer_demo_clean/train_seeds.json /root/data/atticux/agent-workspace/expo-ft/src/expo-ft/scripts/robotwin/rl_joint.sh 0,1,2,3,4 <sft_step_dir> <run_name> > /root/data/atticux/agent-workspace/expo-ft/logs/rl_<run_name>.log 2>&1"
```

```bash
/root/data/atticux/agent-workspace/expo-ft/src/expo-ft/scripts/robotwin/rl_status.sh $(cat /root/data/atticux/agent-workspace/expo-ft/rl/<run_name>/checkpoints/wandb_id.txt)
```

预期：`rl/<run_name>/learner.log` 出现 `EnvClient listening` 与 tqdm 步数，10 回合后出现 update 进度；`rl_status.sh` 输出回合数、
每 10 回合成功数（第一段在 update 之前）、最新 critic/actor 指标与 Q 走势；`checkpoints/` 下只留最新两份 agent checkpoint。
