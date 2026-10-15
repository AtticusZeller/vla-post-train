# EXPO-FT Plan

## RoboTwin 单任务上跑通 EXPO-FT（联合更新）

这是 [expo-ft-spec.md](../xense-openpi/expo-ft-spec.md) 4.4 复现路线的第一步：仿真里、不做人工介入、按参考实现联合更新，
在 `beat_block_hammer`（Easy）上把代码调通，并看 RL 能否把成功率推到 SFT 基座之上。分离更新的消融与真机放在后续事务。

前四个 Task（奖励对齐、xense-openpi 采样接口、learner 改用 xense-openpi、RoboTwin 环境端）已完成，见 [log.md](log.md)。

**现役技术路线**（2026-10-14 至 10-15 讨论与执行中确定）

- 不迁进 RLinf；训练全用 JAX。learner 是 expo-ft 参考实现，π₀.₅ 的 SFT、候选采样与 BC 用 xense-openpi。
- 代码版本：expo-ft `robotwin-sim`，learner 内的独立 checkout 是 xense-openpi `expo-ft`，RoboTwin 是 `methods/robotwin`
  的 `workspace`。每次运行记下 expo-ft 与 checkout 的 commit。
- 仿真接在 expo-ft 环境 RPC 的另一端（`client/envs/robotwin_env.py`），单环境，learner 逐步驱动；环境进程跑在 RoboTwin
  自己的 Python 3.10 环境里，与 learner 放同一张卡，learner 先监听、环境端再拨号。
- 观测约定：键沿用数据集特征名（`observation.images.cam_high` 等、`observation.state`、`prompt`），图像 CHW uint8；
  动作列叫 `actions`。一份 xense-openpi data config（`LeRobotAlohaDataConfig`，与 RoboTwin 官方 π₀.₅ 基线相同）同时管
  SFT 与 replay。
- 数据：官方单任务原始数据 `aloha-agilex_clean_50`（50 条、种子 0–67），经 `scripts/convert_robotwin_to_lerobot.py`
  转成 v3.0（5682 帧、15 fps、240×320，存图像不存视频）。评测种子从 100000 起，用 `ROBOTWIN_SEED_INDEX` 分段：
  评测分片 0–7，在线训练 100。
- 运行机器：`xense-training-h100`。白天 8 卡被他人任务占满，按用户同意（2026-10-15）只在凌晨无人训练时用卡，
  占用不得挤到他人任务。数据、checkpoint、日志在 `/root/data/atticux/agent-workspace/expo-ft/`。W&B 用用户账号，
  entity `atticux`，项目 `expo-ft`。
- 本地笔记本（RTX 4060）装有同一套 RoboTwin 环境，用于不占服务器 GPU 的环境端调试。

**依据**

- 起点参照：π₀ 用 50 条 clean 示教单任务训练，Easy 档 `beat_block_hammer` 43%（RoboTwin 2.0 论文 Table 5）。
  π₀.₅ 一般更高，我们自己 SFT 的起点要实测。
- RoboTwin 环境端一个进程的显存：渲染（光线追踪 32 spp + OIDN，三路相机）约 2.1 GB，加两只手臂的 CuRobo 规划子进程
  合计超过 3 GB。渲染设置与官方数据一致，不降。

**不做**：人工介入、Real-Time EXPO-FT、分离更新、真机、多任务。

### Task: SFT 基座落在 30–60%

**Change**

- [x] 数据转换与 norm stats（见上方数据约定）；xense-openpi `configs/_examples/pi05_robotwin_beat_block_hammer_lora.yaml`：
      π₀.₅，`gemma_2b_lora` + `gemma_300m_lora`，三路相机，14 维，H=16，batch 64，AdamW 恒定 2.5e-5，无 EMA，
      4,000 步，每 500 步存一次（50 条示教约 45 遍数据；参考实现也是约 4,000 步，在线阶段加载第 2,000 步）
- [ ] 训练：凌晨空闲卡上用能整除 batch 的 8/4/2/1 张卡，`scripts/robotwin/night_run.sh` 自动完成
- [ ] 评测：只评最后一个 checkpoint，基座策略（`eval_droid_policy.py --only_base_actions`）共 50 回合，分到训练用的
      卡上并行，每个分片一个种子段；落在 30–60% 即选定。高于 60% 先回退到更早的 checkpoint（每 500 步都留着），仍高再
      减示教条数；低于 30% 回来讨论

**Verification**

1. [ ] 第 0 步护栏：`param_norm` 与初始化值 1803.25 相差不超过 5、loss 有限（CPU 上反复出现参数损坏，见下方说明）
2. [ ] 训练日志与 W&B：4,000 步跑完，loss 有限
3. [ ] 50 回合评测的分片日志与汇总 k/50

**Done**

- [ ] 选定的 checkpoint Easy 50 回合成功率在 30–60%，连同步数、示教条数写进 `docs/expo-ft/experiments.md`

> **已做的检查与未解决的风险（2026-10-15）：**
>
> - CPU 上训练入口跑通：配置、数据、权重加载、LoRA 冻结、存 checkpoint。但同一命令在 CPU 上重复 7 次只有第一次正常，
>   其余 `param_norm` 为 NaN、2e17 或中途崩溃；关闭 XLA CPU 的 thunk runtime 则编译即断言失败。同一 CPU 上初始化重复
>   6 次都是 1803.249（与 donate 无关），DataLoader worker 数也不影响。判断是 XLA CPU 后端的问题，未在 GPU 上验证；
>   夜间脚本的第 0 步护栏用来兜底。
> - 评测链路已端到端跑通（learner 在服务器 CPU、环境端在本地 GPU，经 SSH 隧道）：创建环境、复位筛种子、三次推理、
>   24 步、输出成功率。所用 checkpoint 来自参数已损坏的 CPU 小跑，动作为 NaN，环境端按约定换成 0，所以这只证明链路通。

### Task: 联合更新上线，观察成功率能否高于基座

原计划只做冒烟、不看成功率；用户要求（2026-10-15）评完基座后直接起联合更新，并监测成功率是否继续上升。参数取规格的
参考默认：N=K=8、β=0.2、C=8、M=10、U=20、B=64，每回合 3 次 update call，前 10 回合之后开始更新。

**Change**

- [ ] 由 `night_run.sh` 在评测后调用 `scripts/robotwin/rl_joint.sh`：从选定（今晚即最后一个）SFT checkpoint 起，
      `train_pi_robo.py` 在训练用的前至多 4 张卡上数据并行，环境端在第一张卡，训练种子段 100；预填 50 条示教；
      每 2,000 步存 agent 与 replay
- [ ] 中途停一次，从 checkpoint 和 replay 恢复（`--resume`）后再跑几个回合
- [ ] 冒烟与长跑的命令写进 `docs/expo-ft/cmd.md`

**Verification**

1. [ ] learner 日志：回合数、update call 次数、critic loss、Q 值有限；checkpoint 与 replay 落盘
2. [ ] W&B `training/success_rate`（最近 10 回合）随回合的曲线，与基座的 k/50 对照
3. [ ] 同一个 RL checkpoint 分别用完整策略与 `only_base_actions` 评几回合，两条评测路径都能跑完

**Done**

- [ ] 更新后 rollout 用的 π₀.₅ 参数与更新前不同，critic loss 与 Q 值都是有限值
- [ ] 恢复后 replay 大小与已跑回合数接上，回合计数从中断处继续
- [ ] 记录 RL 成功率相对基座的走势（上升、持平或下降，附回合数），写进 `docs/expo-ft/experiments.md`

### 今晚（2026-10-16 凌晨）的运行与预期

`xense-training-h100` 的 tmux `atticux-night-sft` 运行 `/root/data/atticux/night_sft.sh`（与 expo-ft
`scripts/robotwin/night_run.sh` 相同），总日志 `logs/night_20261016.log`。阶段与各自的产物：

| 阶段 | 触发与条件 | 产物（相对 `/root/data/atticux/agent-workspace/expo-ft/`） |
|---|---|---|
| 等卡 | 02:00–03:30 内某些卡连续 10 分钟显存 < 1 GB 且利用率 0；到 03:30 没有就不训练 | 总日志写明用哪些卡或不训练的原因 |
| SFT | 用空卡中的 8/4/2/1 张；第 0 步护栏不过或 loss 非有限即终止 | `logs/train_sft_bbh_clean50_h16.log`、`checkpoints/pi05_robotwin_beat_block_hammer_lora/sft_bbh_clean50_h16/<step>`、W&B |
| 评测 | 最后一个 checkpoint，50 回合分到各卡 | `.../sft_bbh_clean50_h16/evals_night/<step>/shard*/`，总日志里的 k/50 |
| RL | 评测结束后立即启动，前至多 4 张卡 | `rl/expo_bbh_joint/{learner,env}.log`、`logs/rl_expo_bbh_joint.log`、W&B |

当晚的预期终点：SFT 跑完 4,000 步、得到最后一个 checkpoint 的 k/50，RL 已开始并跑过前 10 回合进入更新，W&B 上有
`training/success_rate`。已知会提前停下的情况：没有空卡、第 0 步护栏触发、RL 首次在 GPU 上启动报错（这条路径此前没在
GPU 上跑过）。早上据日志决定：k/50 是否落在 30–60%，RL 是否在跑、成功率走势如何。
