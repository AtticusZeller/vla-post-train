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
- 改用单次尝试判定后不重测基座：评测只用来判断 checkpoint 可不可用，不求精确。
- 先做环境端；learner 是否也迁移，之后再看适配复杂度。

**待讨论**（单独讨论后再定 Task）

1. **怎样提速。** 只借 RLinf 接 RoboTwin 的环境端做法（复用场景对象、多环境并行采样），learner 仍是 expo-ft（JAX）
   （用户决定 2026-10-18）。RLinf 已接入 `methods/rlinf`（`workspace`，上游 `main` 的 `a78b6d7`）。下一步：调研它的
   RoboTwin 环境端（`rlinf/envs/sim/robotwin/`），回答场景怎样复用、多环境是多进程还是批量仿真、与我们的环境 RPC
   怎样对接，结论与迁移方案写回这里，再定 Task。
2. **验收方式。** 用户意见：迁移后直接评估效果，不预设提速比例。具体看什么（同一固定种子到 90% 的墙钟时间、每小时
   回合数）随方案定。

**沿用的技术路线**（2026-10-14 至 10-16 确定；环境端的提速按上面第 1 条改）

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

### Task: 单次尝试判定下的固定种子联合更新

用户 2026-10-18 定的下一次实验：除 `ROBOTWIN_SINGLE_ATTEMPT=1`（现在的默认）外，配置与 10-18 夜里两次运行相同，看训练数据
只含一次成功的轨迹后，收敛快慢与每小时回合数怎样变化。这是训练数据的调整，不是环境端提速。

**Change**

- [ ] expo-ft `cb4a760`（含判定、`--max_to_keep=2` 与新的恢复语义），`02-xense-training` 上并行两次：15k 基座 GPU 0–4，
      约 7k 基座 GPU 5–7（`PORT=8401`），β=0.05，`ROBOTWIN_FIXED_SEED=1`
- [ ] 中途拿第一个 agent checkpoint 做一次停止再 `--resume`，验证新的恢复语义

**Verification**

1. [ ] 判定短跑（用户选“只看结果”）：基座策略在同一固定种子上跑 10 回合，失败回合在第一次落锤后约 10 步内结束，
       成功回合不被判失败
       （2026-10-18 12:17 部分：15k 基座 7 回合全部成功，111–154 步，没有被误判；没出现失败回合，提前结束未验证。
       02 可能有人要用，按用户要求停下）
2. [ ] 恢复：日志里 `Resuming at step N` 的 N 大于 checkpoint 步数，W&B 步数不倒退，恢复后的回合接着记
3. [ ] `rl_status.sh` 的分段成功率与 critic 走势；与 10-18 夜里比每小时回合数、20 回合滑动成功率首次到 90% 的墙钟时间

**Done**

- [ ] 两次运行的分段成功率与上面两个效率数写进 [experiments.md](experiments.md)，与 10-18 夜里的两次并列
