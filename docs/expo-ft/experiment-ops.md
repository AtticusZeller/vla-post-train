# 实验管理

在共享训练机上无人值守跑 EXPO-FT 实验的做法：用哪些资源、Agent 夜里能自己做什么、怎样盯、踩过哪些坑。
命令见 [cmd.md](cmd.md)，实验结果见 [experiments.md](experiments.md)。

## 机器与资源

| 项 | 现状（2026-10-16） |
|---|---|
| 机器 | `xense-training-h100`，8 × H100 80 GB，192 核，约 2 TB 内存；`/root/data` 是与 `02-xense-training` 共享的 ceph 卷 |
| 共享约束 | 白天 8 卡常被他人任务占满。只在凌晨卡空时用，09:00 前全部停下；他人任务出现在我们的卡上时不抢显存 |
| 判定空卡 | 连续 10 分钟显存 < 1 GB 且利用率 0（`night_run.sh` 内置）；batch 64 要能被卡数整除，取 8/4/2/1 张 |
| 工作目录 | `/root/data/atticux/agent-workspace/expo-ft/`：`src/expo-ft`（learner venv 与 xense-openpi checkout）、`data/`、`assets/`、`checkpoints/`、`rl/`、`logs/` |
| RoboTwin | `/root/data/atticux/robotwin`（Python 3.10 venv、CuRobo、资产）；无头渲染需 `VK_ICD_FILENAMES=/root/data/atticux/vulkan/nvidia_icd_egl.json` |
| 网络 | 外网只能经平台加速器：在启动命令里 `source /public/bin/network_accelerate`，不写进 `.bashrc`。装包用 uv 与阿里云镜像（uv 在 `/root/data/atticux/tools/`） |
| W&B | 用户账号，key 在 `/root/data/atticux/.wandb_key`（只导出给训练、评测与 RL 进程，不打印），entity `atticux`，项目 `expo-ft` |
| 磁盘 | 一个 LoRA SFT checkpoint 约 9 GB；RL 每条 transition 单独存一个文件，一次运行十几到几十 GB |

单进程的量：SFT 8 卡约 0.41 s/步（需 32 个 DataLoader worker）；评测一对 learner + 环境端占一张卡约 47 GB，一回合
最长 400 步、约 2 分钟；联合更新用 5 张卡：GPU 0 推理加环境端，峰值约 40 GB；4 张更新卡各约 68 GB（`MEM_FRACTION=0.85` 的上限）。
联合更新每步约 0.45 s，几乎都在环境侧；换种子时每回合 reset 约 60 s，`ROBOTWIN_FIXED_SEED=1` 后约 23 s。

## 夜间运行的组织

- 长任务都放在 tmux 会话里，会话名以 `atticux-` 开头，脚本从 `src/expo-ft/scripts/robotwin/` 运行（不在别处放副本）。
  每个阶段的产物与日志按 [cmd.md](cmd.md) 的约定落在工作目录下。
- 只存、只评最后一个 checkpoint（用户 2026-10-15）；成功率用 50 回合、按卡分片、每片一个种子段，在线训练用种子段 100。
- 开跑前写一份 runbook：目标、每个阶段的产物路径、成功或失败时下一步怎么走、停止时间。夜间检查按它行事。
- 一个 driver 只占自己的卡。卡有空余时可以加并行任务（例如另一个基座），但用不同的 tmux 会话、实验名与端口
  （评测 8300+、诊断评测 8310+、RL 8400）。

## 监控

- Agent 会话里设定时检查（夜里每 5 分钟一次），只有会话开着、电脑不休眠时才触发。没有变化时只回一行。
- 每次检查：driver 总日志末尾，当前阶段日志里的 `Traceback`/`Error`/`RESOURCE_EXHAUSTED`/`loss=nan`，`nvidia-smi`。
- SFT 看 `Step N:` 行；RL 的回合结果只在 W&B，用 `rl_episodes.sh <run id>` 读（run id 在 `rl/<run>/checkpoints/wandb_id.txt`）。
- 夜间记录写在会话的临时目录，早上整理进 `experiments.md`（结果）和 `log.md`（代码与脚本改动）。

## Agent 夜里能自己做的事

用户授权（2026-10-15）：代码与脚本问题自行排查、修复、重启；实验不及预期时可以做有依据的尝试。边界：

- 修复先在服务器 checkout 与本地同步改，验证后再继续；不在夜里 commit 或 push，早上列给用户。
- 每次重试检验一个具体假设；同一问题没有新证据时停下，留给早上。
- 只按明确 PID 停自己的进程树（从 tmux pane 的 PID 往下找子进程），不用 `pkill -f`；不碰他人的任务、checkout 与环境。
- 到停止时间（09:00）先停掉所有占卡任务，再汇报。

## 已知的坑

- 正在执行的 bash 脚本不能原地改写；改动另存新文件，停掉旧会话后再启动。
- `pgrep -f <脚本名>` 会匹配到执行这条命令的 ssh shell 自己，曾因此杀掉自己的会话。
- 训练日志行带时间戳前缀，按行首 `^Step` 匹配会全部落空；护栏要用不带锚点的模式。
- openpi 的 checkpoint 在不同卡数上 `--resume` 会报 sharding 为 None；换卡数时改用权重初始化新实验。
- RL `--resume` 只回到最近的 agent checkpoint，W&B 的步数倒退，在超过原最大步数前新回合不进 W&B。
- 服务器与本地的 venv 可能不一致（这次服务器 RoboTwin venv 缺 `ml-collections`）；新环境先做一次端到端短跑。
