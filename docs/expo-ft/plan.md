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
  自己的 Python 3.10 环境里，learner 先监听、环境端再拨号。评测时与 learner 同卡。联合更新用 5 张卡（用户 2026-10-16）：
  第一张只做推理并跑环境端，其余 4 张组成更新 mesh，与 `train_pi_robo_async.py` 的分工相同。
- 观测约定：键沿用数据集特征名（`observation.images.cam_high` 等、`observation.state`、`prompt`），图像 CHW uint8；
  动作列叫 `actions`。一份 xense-openpi data config（`LeRobotAlohaDataConfig`，与 RoboTwin 官方 π₀.₅ 基线相同）同时管
  SFT 与 replay。
- 数据：官方单任务原始数据 `aloha-agilex_clean_50`（50 条、种子 0–67），经 `scripts/convert_robotwin_to_lerobot.py`
  转成 v3.0（5682 帧、15 fps、240×320，存图像不存视频）。评测种子从 100000 起，用 `ROBOTWIN_SEED_INDEX` 分段：
  评测分片 0–7，在线训练 100。
- 运行机器：`xense-training-h100`。白天 8 卡被他人任务占满，按用户同意（2026-10-15）只在凌晨无人训练时用卡，
  占用不得挤到他人任务。数据、checkpoint、日志在 `/root/data/atticux/agent-workspace/expo-ft/`。W&B 用用户账号，
  entity `atticux`，项目 `expo-ft`。夜间无人值守运行的做法见 [experiment-ops.md](experiment-ops.md)。
- 两个基座分工（用户 2026-10-16）：先用 72% 的 15k 基座调试 RL，并要求成功率能高于基座；约 40% 的基座用于评估 RL
  算法上限，暂缓。
- 调试 RL 只用单一场景（用户 2026-10-16）：同一任务、同一种子反复跑，以最小改动快速看到成功率变化，不考虑泛化。
  环境端 `ROBOTWIN_FIXED_SEED=1` 每回合复用训练种子段里第一个专家能做成的种子（段 100 是 10100000）。
- 本地笔记本（RTX 4060）装有同一套 RoboTwin 环境，用于不占服务器 GPU 的环境端调试。

**依据**

- 起点参照：π₀ 用 50 条 clean 示教单任务训练，Easy 档 `beat_block_hammer` 43%（RoboTwin 2.0 论文 Table 5）。
  π₀.₅ 一般更高，我们自己 SFT 的起点要实测。
- SFT 训练量：RoboTwin 官方 `stable_2.0` 分支的 π₀.₅ LoRA 基线（`pi05_base_aloha_lora`）是 30,000 步 × batch 32，
  约 96 万样本；全量基线（`pi05_aloha_full_base`）是 20,000 × 64，约 128 万。expo-ft 参考实现的约 4,000 步是在它自己的
  真机任务上说够用，起点和机器人都不同。仍用 LoRA：在线阶段的 actor 更新沿用参考实现的 LoRA，SFT 与之保持同一套参数化。
- 实测（2026-10-16，[experiments.md](experiments.md)）：4,000 步 14%、约 7,000 步 31%（32 回合）、15,000 步 72%；
  loss 在 4,000 步时已到 0.0014，不能代替成功率选步数。
- RoboTwin 环境端一个进程的显存：渲染（光线追踪 32 spp + OIDN，三路相机）约 2.1 GB，加两只手臂的 CuRobo 规划子进程
  合计超过 3 GB。渲染设置与官方数据一致，不降。

**不做**：人工介入、Real-Time EXPO-FT、分离更新、真机、多任务。

### Task: 从 72% 基座出发，联合更新把成功率推上去

这是对 RL 最起码的能力检验（用户 2026-10-16）：15k 基座 72%，在线回合里成功轨迹多、信号好，先在它上面把算法调通，
并看成功率能否高于基座。

已有：两次运行都跑过 10 回合进入更新，更新数值有限、actor 参数确有变化，checkpoint 与 replay 落盘，`--resume` 能接上；
显存布局已拆开、单场景开关已加（[log.md](log.md)）。

**下一次运行（用户 2026-10-16 定）**

- Change：15k 基座、β=0.05、`ROBOTWIN_FIXED_SEED=1`，5 张卡，其余取参考默认（N=K=8、UTD 20、每回合 3 次 update、
  10 回合后开始更新），命令见 [cmd.md](cmd.md)。
- Verification：用 `rl_episodes.sh` 读每回合成败与步数，按"更新前 10 回合"与"更新后每 10 回合"分段统计；同时看
  critic loss、Q 均值是否有限。
- [ ] Done：固定种子上更新前后的分段成功率写进 [experiments.md](experiments.md)，由用户判断是否算明显上升。

**待讨论**

1. **编辑幅度与冷启动。** β=0.2（参考默认）在归一化关节增量上过大：同种子无编辑 8/10、β=0.2 0/5，RL 更新后 0/10；
   β=0.05 为 4/10。下一次运行先用 β=0.05；之后是否改成 critic 训好前不用编辑、或把编辑放到别的动作空间，等用户看过
   官方参数策略再定。DROID 参考实现的动作空间与这里不同，β 不能直接照搬。
2. **恢复语义。** `--resume` 只回到最近的 agent checkpoint，之后的 replay 被丢弃；W&B 的 `_step` 因此倒退，较小的步数
   会被丢掉，回合记录要到超过原最大步数后才恢复。是否改成按回合存或给 W&B 另一个计数，需要定。
3. **仿真里的采样效率。** 实测每步约 0.45 s，其中取观测 335 ms、环境动作 102 ms、模型推理平均 9 ms；固定种子后 reset
   约 23 s（换种子时约 60 s）。GPU 大部分时间在等环境，10 回合要 15–30 分钟才开始更新。可选：查清循环里比单独计时多出的
   约 180 ms（疑似传输开销，未验证）、复用 RoboTwin 场景对象、多环境并行采样；"10 回合后开始更新"是写死的门槛。
   用户判断渲染不是主要问题，不降渲染设置。
4. **跑多久。** 夜里一个窗口能跑的更新回合有限，需要定每次运行的回合预算与判定走势的回合数。

**Done**

- [ ] 固定种子上 RL 更新后的成功率明显高于更新前（判定标准随下一次运行的结果与用户定）

### Task（暂缓）: 1 万步基座落在 40% 左右

理想实验用的基座：有了约 40% 的起点，才能评估当前 RL 算法的上限。用户 2026-10-16 决定暂缓，先完成上一个 Task。

**Change**

- [ ] 今晚（2026-10-17 凌晨）卡空时用 `night_run.sh` 训 `STEPS=10000`、`NO_RL=1`，其余配置同 15k 次
- [ ] 只评最后一个 checkpoint，基座策略 50 回合，分片到训练用的卡上

**Verification**

1. [ ] 第 0 步护栏（`param_norm` 与 1803.25 相差不超过 5、loss 有限）与 W&B loss 曲线
2. [ ] 50 回合分片日志与汇总 k/50

**Done**

- [ ] 1 万步 checkpoint 的 k/50 写进 [experiments.md](experiments.md)；落在 40% 左右即作为衡量基座，偏离时与用户定下一个步数
