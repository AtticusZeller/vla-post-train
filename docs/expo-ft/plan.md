# EXPO-FT Plan

## RoboTwin 多任务 baseline：联训基座上的 Hard RL

在 `beat_block_hammer`（bbh）之外选一组任务，构建我们自己 baseline 里的 EXPO-FT 结果：所有任务共用一个联训 SFT 基座，
在 Hard 场景上逐任务做 RL。前两个事务（单任务跑通、提高训练效率）已完成，见 [log.md](log.md)；各次 RL 运行的对照见
[experiments.md](experiments.md) 顶部的 RL 总表。

**2026-10-19 晚的安排**（用户 2026-10-19 定；卡从 00:00 起可用，不保证都空，有几组卡就起几组）

1. 00:00 起，用 seen 指令把联训 29999 的 Hard 从头评一遍：10 个任务各 50 回合（两片各 25），两台机 16 张卡，约 2 h。同时占
   1–2 张卡给 RL 做 smoke（约 20 min）。
2. 按 seen 的 Hard 成功率严格挑 30–70% 的任务；给每个选中的任务算 Hard 种子表（`demo_randomized`、seen，600 个候选，
   3 张卡约 20 min），按示教平均长度 1.3 倍定步数上限，并用 Hard 下成功回合的步数核对。
3. 约 02:30 起 RL：每台机 GPU 0–4（1 张推理与环境、4 张更新）与 GPU 5–7（1+2）各一组，最多 4 组；卡不够按优先级
   bbh、`place_empty_cup`、`stack_blocks_two`、`place_phone_stand`（只取落在区间里的）。每组跑到第 300 回合。
   3 卡的组 update 较慢，与 5 卡的组比较时要打折扣。
4. 早上把结果补进 RL 总表，再定是否删联训 3k–27k 的 checkpoint。

**已定**

- 任务（用户 2026-10-18）：10 个，Aloha-AgileX，每个 50 条官方示教 `aloha-agilex_clean_50`：bbh、`pick_dual_bottles`、
  `place_empty_cup`、`move_can_pot`、`handover_block`、`stack_blocks_two`、`press_stapler`、`place_phone_stand`、
  `move_playingcard_away`、`click_alarmclock`。前 5 个 RLinf 有 RL 结果，后 5 个按技能多样性补充。
- 基座（用户 2026-10-19）：所有任务共用联训 π₀.₅ LoRA `sft_cotrain10_30k/29999`（Easy 上 8 个任务 ≥80%）。
- **RL 做在 Hard 上**（用户 2026-10-19）：微调就能到很高成功率的任务，现实中做 RL 没有意义，RL 是为微调上不去的任务
  （用户判断与偏好）。挑 29999 在 Hard 上成功率 30–70% 的任务，在 `demo_randomized`（桌上杂物、随机背景与光照、桌高
  ±3 cm）上做 RL；区间外的任务不做。
- **只看场景泛化，不看语言泛化**（用户 2026-10-19）：RL 训练与 Hard 评测都用 seen 指令；官方榜单 Hard 用的 unseen 不用。
- **单任务标准实验环境**（用户 2026-10-19）：随机种子（种子表）+ 步数上限、上限内重试成功也算。
  - 单次尝试判定不再用：300 回合内停在 63%（用户推断：Q 能从重试中学到有用的东西，未验证）。
  - bbh 上限 150；其余任务取示教平均长度的 1.3 倍、取整到 10，做 RL 前用 Hard 下成功回合的步数核对（数据见
    experiments.md 联训一节）。300 回合内成功率主要受回合数限制，不受上限限制，不再跑 200 步对照。
  - 随机种子不论快慢都用：真实情况需要泛化（用户判断）；它是否加速学习，再多观察几次运行。
  - 种子表照搬 RLinf 的做法、按我们的配置自己算；每个任务每种场景配置一张，bbh 的 demo_clean 表已有，其余做 RL 前再算。
- 每次 RL 运行到第 300 回合停（用户 2026-10-18）：最终要上真机，总回合本来就不该多。比较时看同一回合段的成功率。
- RL 的 replay 预填用该任务微调用的 50 条 clean 示教（`<task>_aloha_clean_50`），与 Hard 场景不一致，不改（用户 2026-10-19）。
- 超参用参考默认（N=K=8、UTD 20、每回合 3 次 update、10 回合后开始更新），β=0.05、`adjust_target_entropy=False`；评估超参时
  再看。同步联合更新；异步与多环境已放弃（用户 2026-10-18）。
- 写论文的完整评测用官方协议（`ROBOTWIN_SINGLE_ATTEMPT=0`、任务自己的步数上限）。
- 不和官方 π₀.₅ 联训对比（我们是 LoRA，官方是全参）。参考：官方榜单 bbh 上 π₀ 单任务 43%、π₀.₅ 联训（50 个任务）93%。
- 不用 RoboDojo：仿真换成 Isaac Sim（H100 没有 RT core，大概率渲染不了，未核实），任务基座成功率太低；作为以后的第二个
  benchmark。
- 暂不评测“去掉编辑策略、只用 RL 后的 π₀.₅”；不做“块末只渲染一次”（RLinf 的默认做法，属于算法与数据的改动）。

**沿用的技术路线**

- learner 是 expo-ft 参考实现（JAX，`train_pi_robo.py` 同步联合更新），π₀.₅ 的 SFT、候选采样与 BC 用 xense-openpi。代码版本：
  expo-ft `robotwin-sim`，learner 内的独立 checkout 是 xense-openpi `expo-ft`，RoboTwin 是 `methods/robotwin` 的 `workspace`。
  每次运行记下 expo-ft 与 checkout 的 commit。
- 仿真接在 expo-ft 环境 RPC 的另一端（`client/envs/robotwin_env.py`），单环境，learner 逐步驱动；一个 task 对象跨回合复用。
  联合更新的第一张卡只做推理并跑环境端，其余卡组成更新 mesh。按任务起 RL 用 `rl_joint.sh` 的 `TASK`、`PI05_CONFIG`、
  `ASSET_ID`，场景与回合判定用 `ROBOTWIN_*` 环境变量（[cmd.md](cmd.md)）。
- 种子：评测从 100000 起，用 `ROBOTWIN_SEED_INDEX` 分段（评测分片 0–7），在线训练用种子段 100（10100000 起）。
- 机器：`xense-training-h100` 与 `02-xense-training`，共享 `/root/data`，只在他人不用时用卡；做法见
  [experiment-ops.md](experiment-ops.md)。渲染（光线追踪 32 spp + OIDN，三路相机）与官方数据一致，不降。

**不做**：人工介入、Real-Time EXPO-FT、分离更新、真机。

### Task: 29999 的 Hard 评测（seen）与选任务

**Change**

- [x] expo-ft `ROBOTWIN_TASK_CONFIG` 与 `ROBOTWIN_INSTRUCTION_TYPE`：选场景配置与指令类型，默认 `demo_clean`、`seen`
      （2026-10-19，expo-ft `1a9993d`；h100 上 `demo_randomized` 能建场景，reset 约 6.5 s）

**Verification**

1. [ ] 29999 的 Hard（`ROBOTWIN_TASK_CONFIG=demo_randomized`，seen 指令），每个任务 50 回合，10-19 00:00 起。10-19 09:00–10:10
       用 unseen 评过一部分，按用户要求停了，只作参考（experiments.md）

**Done**

- [ ] 29999 在 10 个任务上的 Hard 成功率写进 [experiments.md](experiments.md)（Easy 已有），按 30–70% 选出做 RL 的任务

### Task: 联训基座上的 Hard RL

**Change**

- [x] expo-ft `rl_joint.sh` 按任务参数化：`TASK`、`PI05_CONFIG`、`ASSET_ID`，默认仍是 bbh 单任务基座；`robotwin_task.py`
      加 `ROBOTWIN_STEP_LIMIT`（2026-10-19，expo-ft `3338fbf`）
- [ ] 每个选中任务的 Hard 种子表与步数上限
- [ ] 每组：联训 29999、随机种子（种子表）、步数上限、`demo_randomized`、seen 指令、β=0.05、参考默认，跑到第 300 回合
      （bbh 走自己的配置 `robotwin_beat_block_hammer.py`，默认开单次尝试判定，要设 `ROBOTWIN_SINGLE_ATTEMPT=0`）

**Verification**

1. [x] 本机只跑环境端：通用配置 `robotwin_task.py`（用 bbh，本机缺其他任务的物体资源）在 `ROBOTWIN_STEP_LIMIT=150` 下第 150 步结束
2. [ ] 训练机 smoke：每组前几回合场景逐个不同、失败回合在上限处结束、10 回合后开始 update

**Done**

- [ ] 各组的分段成功率、首次到 80%/90% 的回合与墙钟时间写进 experiments.md 的 RL 总表
