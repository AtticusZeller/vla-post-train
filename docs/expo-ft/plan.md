# EXPO-FT Plan

## 提高 RoboTwin 上 EXPO-FT 的训练效率

上一个事务“RoboTwin 单任务上跑通 EXPO-FT”已完成（用户 2026-10-18：代码通过，原算法有效；见 [log.md](log.md) 与
[experiments.md](experiments.md)）。固定种子上从 72% 与 31% 的基座出发都拉到 90% 以上，但到 90% 要 3–4.5 h、
一个基座一晚只够跑一次。这个事务让同样的验证跑得更快，为恢复场景随机性、扩展任务做准备。

**已定**（用户 2026-10-18）

- 主要慢在仿真，不在策略计算与更新（用户判断；实测见 [experiments.md](experiments.md) 白天诊断一节：每步约 0.45 s 几乎
  都在环境侧，固定种子时 reset 约 23 s，update 约 22 s/回合）。
- 训练与平时评测用单次尝试判定：第一次尝试没成功就判失败、结束回合，不考虑 recovery；写论文的完整评测再用官方协议
  （`ROBOTWIN_SINGLE_ATTEMPT=0`）。理由（用户判断）：真机评测一次没成功就算失败，多次尝试的数据示教里通常没有，对编辑
  策略学习没有意义，还增加复杂度。`beat_block_hammer` 的判定已在 expo-ft `e0aba36`。
- debug 阶段超参不变（含 β=0.05 与 `adjust_target_entropy=False`），评估超参时再看。
- 效率提上去之后再恢复场景随机性（不再只用固定种子）。
- 暂不评测“去掉编辑策略、只用 RL 后的 π₀.₅”；留到消融或研究 π₀.₅ 吸收了多少时再做。

**待讨论**（单独讨论后再定 Task）

1. **怎样提速。** 用户倾向迁移 RLinf 接 RoboTwin 的做法（复用场景对象、多环境并行采样），或直接用 RLinf 的分支再适配；
   也考虑 RLinf 的 ManiSkill3。这与原技术路线“不迁进 RLinf、训练全用 JAX”冲突，需要定：是只借 RLinf 的环境端做法、
   learner 仍是 expo-ft（JAX），还是整体换到 RLinf。
2. **验收方式。** 用户意见：迁移后直接评估效果，不预设提速比例。具体看什么（同一固定种子到 90% 的墙钟时间、每小时
   回合数）随方案定。
3. **单次尝试判定下的基座。** 72%、31% 是官方协议下的数；改用新协议后是否重测基座。
4. **恢复语义**（10-16 遗留）。`--resume` 只回到最近的 agent checkpoint，之后的 replay 被丢弃，W&B 步数倒退；是否改成
   按回合存或给 W&B 另一个计数。

**沿用的技术路线**（2026-10-14 至 10-16 确定，迁移 RLinf 时按上面第 1 条重新定）

- learner 是 expo-ft 参考实现（JAX），π₀.₅ 的 SFT、候选采样与 BC 用 xense-openpi。代码版本：expo-ft `robotwin-sim`，
  learner 内的独立 checkout 是 xense-openpi `expo-ft`，RoboTwin 是 `methods/robotwin` 的 `workspace`。每次运行记下
  expo-ft 与 checkout 的 commit。
- 仿真接在 expo-ft 环境 RPC 的另一端（`client/envs/robotwin_env.py`），单环境，learner 逐步驱动；环境进程跑在 RoboTwin
  自己的 Python 3.10 环境里，learner 先监听、环境端再拨号。联合更新的第一张卡只做推理并跑环境端，其余卡组成更新 mesh。
- 观测约定：键沿用数据集特征名（`observation.images.cam_high` 等、`observation.state`、`prompt`），图像 CHW uint8；
  动作列叫 `actions`。一份 xense-openpi data config（`LeRobotAlohaDataConfig`，与 RoboTwin 官方 π₀.₅ 基线相同）同时管
  SFT 与 replay。
- 数据：官方单任务原始数据 `aloha-agilex_clean_50`（50 条、种子 0–67）转成 LeRobot v3.0（5682 帧、15 fps、240×320）。
  评测种子从 100000 起，用 `ROBOTWIN_SEED_INDEX` 分段：评测分片 0–7，在线训练 100。
- 基座：`sft_bbh_clean50_15k/14999`（官方协议 50 回合 72%）与 `sft_bbh_clean50_4k_plus4k/3000`（32 回合 31%）。
- 机器：`xense-training-h100` 与 `02-xense-training`，共享 `/root/data`，只在他人不用时用卡；做法见
  [experiment-ops.md](experiment-ops.md)。
- 渲染（光线追踪 32 spp + OIDN，三路相机）与官方数据一致，不降。

**不做**：人工介入、Real-Time EXPO-FT、分离更新、真机、多任务。

### Task（暂缓）: 1 万步基座落在 40% 左右

理想实验用的基座：有了约 40% 的起点，才能评估当前 RL 算法的上限。用户 2026-10-16 决定暂缓。2026-10-18 用 31% 的
约 7k 步基座做了同样的检验（固定种子上 1/10 → 46/50），是否还需要这个基座待用户定。

**Change**

- [ ] 卡空时用 `night_run.sh` 训 `STEPS=10000`、`NO_RL=1`，其余配置同 15k 次
- [ ] 只评最后一个 checkpoint，基座策略 50 回合，分片到训练用的卡上

**Verification**

1. [ ] 第 0 步护栏（`param_norm` 与 1803.25 相差不超过 5、loss 有限）与 W&B loss 曲线
2. [ ] 50 回合分片日志与汇总 k/50

**Done**

- [ ] 1 万步 checkpoint 的 k/50 写进 [experiments.md](experiments.md)；落在 40% 左右即作为衡量基座，偏离时与用户定下一个步数
