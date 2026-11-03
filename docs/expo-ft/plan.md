# EXPO-FT Plan

## RoboTwin 多任务 baseline：联训基座上的 Hard RL

在 `beat_block_hammer`（bbh）之外选一组任务，构建我们自己 baseline 里的 EXPO-FT 结果：所有任务共用一个联训 SFT 基座，
在 Hard 场景上逐任务做 RL。前两个事务（单任务跑通、提高训练效率）已完成，见 [log.md](log.md)；各次 RL 运行的对照见
[experiments.md](experiments.md) 顶部的 RL 总表。

**夜间安排**（用户 2026-10-22 定：10-22 晚重跑 RL，卡从 10-23 00:00 用到 09:00，有几组卡就起几组。原定 10-22 00:30 那次，00:29–05:26 两台机 16 卡一直被他人训练占满，没有起）

1. 服务器 checkout 用 expo-ft `4b58d63`（含清缓存修复，已推送）。
2. 选中的任务（10-21 Hard seen，30–70% 含端点，用户 2026-10-21 定）：pick_dual_bottles 70%、place_empty_cup 58%、
   stack_blocks_two 48%、place_phone_stand 40%、bbh 38%、click_alarmclock 30%（[experiments.md](experiments.md)）。
   RL 优先级仍是 bbh、`place_empty_cup`、`stack_blocks_two`、`place_phone_stand`；这 4 个的 Hard 种子表已有，步数上限
   bbh 150、cup 220、stack 410、phone 180。
3. 00:00 起 RL：每台机 GPU 0–4（1 张推理与环境、4 张更新）与 GPU 5–7（1+2）各一组，`MEM_FRACTION=0.85`（修复后环境端
   约 9 GB，与 learner 同卡放得下，1+2 的更新卡也要 0.85；未在 RL 中验证）。每组跑到第 300 回合或 09:00 前停，记下回合数。
4. 09:00 后把结果补进 RL 总表，再定是否删联训 3k–27k 的 checkpoint 与 10-21 的 `rl_cotrain_hard_bbh_1021b`（45 GB）。

**交接状态（2026-10-21 09:10）**

- 02 的 8 卡空着，没有我们的会话与进程；h100 被他人训练占满（10-20 19:18 起）。`/root/data` 用了 69%。
- 服务器 checkout 在 expo-ft `4b58d63`（含清缓存修复），与远端一致。
- 保留：`evals_hard_seen/29999/` 各片的 `eval.log`；4 张 Hard 种子表；`rl/rl_cotrain_hard_bbh_1021b`（中途重起过，不作正式
  结果）。已删：10-21 失败的 3 个 RL 目录、本次的运行日志、环境端日志与 W&B 本地缓存（用户 2026-10-21：服务器上尽量
  不留命令记录与日志）。
- 本地看守：每 4 分钟查 W&B 回合数，到 300 回合发 Ctrl-C；环境端报 `cannot create buffer`、learner 退出或环境日志
  15 分钟不动时停掉会话并用同一命令 `--resume` 重起，最多 3 次，08:30 后不再重起。10-21 的脚本在会话临时目录，新会话要重写。

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
- 写论文的完整评测用官方协议（不设 `ROBOTWIN_STEP_LIMIT`，用任务自己的步数上限）。
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

### Task: 联训基座上的 Hard RL

**Change**

- [x] expo-ft `rl_joint.sh` 按任务参数化：`TASK`、`PI05_CONFIG`、`ASSET_ID`，默认仍是 bbh 单任务基座；`robotwin_task.py`
      加 `ROBOTWIN_STEP_LIMIT`（2026-10-19，expo-ft `3338fbf`）
- [x] 优先级 4 个任务的 Hard 种子表与步数上限（2026-10-21；pick_dual_bottles、click_alarmclock 做 RL 前再算）
- [x] 环境端每 `clear_cache_freq` 回合清渲染缓存（2026-10-21，GPU 7 上 Hard 30 次 reset 显存稳定在 8–9 GB；expo-ft `4b58d63`）
- [x] 单次尝试判定默认关（bbh 配置原先默认开；2026-10-19，expo-ft `1fcffc9`）
- [ ] 每组：联训 29999、随机种子（种子表）、步数上限、`demo_randomized`、seen 指令、β=0.05、参考默认，跑到第 300 回合

**Verification**

1. [x] 本机只跑环境端：通用配置 `robotwin_task.py`（用 bbh，本机缺其他任务的物体资源）在 `ROBOTWIN_STEP_LIMIT=150` 下第 150 步结束
2. [ ] 训练机 smoke：每组前几回合场景逐个不同、失败回合在上限处结束、10 回合后开始 update

**Done**

- [ ] 各组的分段成功率、首次到 80%/90% 的回合与墙钟时间写进 experiments.md 的 RL 总表
