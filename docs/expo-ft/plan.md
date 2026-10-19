# EXPO-FT Plan

## 提高 RoboTwin 上 EXPO-FT 的训练效率

上一个事务“RoboTwin 单任务上跑通 EXPO-FT”已完成（用户 2026-10-18：代码通过，原算法有效；见 [log.md](log.md) 与
[experiments.md](experiments.md)）。固定种子上从 72% 与 31% 的基座出发都拉到 90% 以上，但到 90% 要 3–4.5 h、
一个基座一晚只够跑一次。这个事务让同样的验证跑得更快，为恢复场景随机性、扩展任务做准备。

**已定**（用户 2026-10-18）

- 主要慢在仿真，不在策略计算与更新（用户判断；实测见 [experiments.md](experiments.md) 白天诊断一节：每步约 0.45 s 几乎
  都在环境侧，固定种子时 reset 约 23 s，update 约 22 s/回合）。
- **单任务标准实验环境（用户 2026-10-19 定）：随机种子（种子表）+ 步数上限 150、上限内重试成功也算。** 单次尝试判定不再用：
  300 回合内停在 63%（用户推断：Q 能从重试中学到有用的东西，未验证）。150 与 200 步回推只差约 1%，不再跑 200 步对照；
  300 回合内成功率主要受回合数限制，不受步数上限限制（官方协议 400 步的 201–300 回合也只有 85%）。随机种子不论快慢都用：
  真实情况需要泛化（用户判断）；它是否加速学习，再多观察几次运行。写论文的完整评测用官方协议（`ROBOTWIN_SINGLE_ATTEMPT=0`）。
- 其余任务的步数上限（用户 2026-10-19 定）：示教平均长度的 1.3 倍、取整到 10（bbh 正好 150），做 RL 前再用 Hard 下成功
  回合的步数核对（数据见 [experiments.md](experiments.md) 10 任务联训一节）。
- 联训的 3k–27k 九个 checkpoint（约 81 GB）是否删除，Hard 评完再定（用户 2026-10-19）。
- 每次 RL 运行到第 300 回合停（用户 2026-10-18）：最终要上真机，总回合本来就不该这么多。比较时看同一回合段的成功率。
- debug 阶段超参不变（含 β=0.05 与 `adjust_target_entropy=False`），评估超参时再看。
- 放开种子（用户 2026-10-18 晚）：放开后单任务的标准实验环境才算完成，但 reset 不能太慢。照搬 RLinf 的种子表
  （`rlinf/envs/sim/robotwin/seeds/train_seeds.json`：启动时读表，reset 按顺序取下一个，不跑专家检查），给我们的配置
  （aloha-agilex、demo_clean）自己算。与在线逐个检查得到的种子序列相同，只把专家检查挪到训练前。先只算
  `beat_block_hammer`；其余 9 个任务的种子表还没算，做 RL 前再算。
- 暂不评测“去掉编辑策略、只用 RL 后的 π₀.₅”；留到消融或研究 π₀.₅ 吸收了多少时再做。
- 改用单次尝试判定后不重测基座：评测只用来判断 checkpoint 可不可用，不求精确。
- 先做环境端；learner 是否也迁移，之后再看适配复杂度。
- 不做“块末只渲染一次”（RLinf 的默认做法）：它让 replay 只在动作块起点有图像，属于算法与数据的改动。
- **异步训练与多环境放弃**（用户 2026-10-18 晚）。N=4（修掉线程共享 `_last_state` 之后）与 N=1 在单次尝试判定下
  成功率都低于同步，N=1 每小时回合只比同步多约 13%（[experiments.md](experiments.md)）。代码留在 expo-ft `f85fc6a`
  与 `8798c5d`，不再使用。提速改走两条：缩短回合（上面的判定）与放开种子时的种子表（见下面的 Task）。

**RLinf 环境端调研**（2026-10-18；RLinf `a78b6d7`，它依赖的 RoboTwin 是官方 `RLinf_support` 分支 `dca9ec6`，
`robotwin/envs/vector_env.py`）

只借 RLinf 接 RoboTwin 的环境端做法，learner 仍是 expo-ft（JAX）（用户决定 2026-10-18）。

1. **场景对象怎样复用：RLinf 不复用 SAPIEN 场景。**
   - 每次 reset 都丢掉 engine、renderer、scene、robot、相机，用 `setup_demo` 重建。`RLinf_support` 的 `close_env`
     连 robot 也置空，planner 每回合重建。
   - 跨回合保留的只有 SAPIEN 的全局渲染缓存，每 `clear_cache_freq` 次 reset 清一次；RLinf 的 `beat_block_hammer`
     配置设为 1，即每次都清。
   - 官方评测脚本反而复用得更多：跨回合用同一个 task 对象，`load_robot` 走 `robot.reset`，机器人与 curobo planner
     只建一次。我们的 `RoboTwinEnv` 每次 reset（以及每次专家检查）都新建 task。
   - reset 的时间构成。实测于 h100 GPU 7，固定种子第 2、3 次 reset 分别 27.0 s、27.2 s：
     - curobo planner 初始化 18.3 s（两臂各一次，主要是 warmup）；
     - 新场景第一次取观测 7.3 s（光线追踪）；
     - 其余约 1 s。
   - 同一次测量里，每步环境动作 46 ms，取观测 212 ms，与 10-16 的诊断一致。
   - RLinf 训练时不跑专家检查。它用离线算好的有效种子表（`beat_block_hammer` 训练 1000 个、评测 320 个，
     由 `check_seeds` 生成），reset 只在 `UnStableError` 时顺延种子。这份表是在 piper、杂乱桌面配置下算的，
     我们的 aloha-agilex、demo_clean 不能直接用。它的 `beat_block_hammer` 配置还用了 mplib planner，并且只用头部相机。
2. **多环境：多进程加进程内多线程，不是批量仿真**（没有 GPU 并行物理）。
   - Ray 上每个 env worker 是一个进程。`beat_block_hammer` 配置把 128 个环境分到 8 个进程，每个进程 16 个，
     种子按 `seed_offset`/`total_num_processes` 切分。
   - 进程内由 RoboTwin 的 `VectorEnv` 持有 N 个 `SubEnv`，每个有自己的 SAPIEN engine、renderer、scene，
     用 `ThreadPoolExecutor(N)` 并行 step；`setup_demo` 由一个全局锁串行。
   - 一次 step 收一整个动作块，默认只在块末渲染一次（`skip_intermediate_renders=True`）。
   - 线程能并行多少，取决于 SAPIEN 在物理与渲染时是否释放 GIL。RLinf 文档没有给吞吐数。我们的扩展测试
     （1/2/4/8 个环境放进线程或进程，在同一张卡上）没跑完：训练机可能有人用，用户 2026-10-18 叫停。本机
     （RTX 4060 Laptop 8 GB、内存 16 GB）只够 1 个环境。
3. **怎样接到我们的环境 RPC。**
   - 现状：
     - 一个连接只服务一个环境；每个动作一次 `step`，每步一次 `get_observation`。
     - `train_pi_robo.py` 逐步驱动这一个环境。
     - `sample_actions` 只接收一个观测。
   - 两种接法：
     - **(a) 多进程。** 开 N 个环境进程，各用现有协议拨不同端口，learner 持有 N 个 `EnvClientWrapper`。环境端代码
       不用改，进程间没有 GIL，单个环境的 reset 自然是异步的。
     - **(b) 照 RLinf 的线程做法。** 一个环境进程里开 N 个线程，协议增加按环境编号的批量 `reset`、`step` 与
       `get_observation`。
   - 两种接法都要改 learner 的 rollout 循环：
     - 每个环境有自己的动作计划、回合状态与转移队列。
     - replay 的动作块回填要求同一回合的转移连续写入，所以一个回合结束后才整段写入。
     - 推理先逐个环境调用现有的 `sample_actions`（单次约 70 ms），不改 agent。
   - 收益估计见 [experiments.md](experiments.md) 10-18 两节；多环境已放弃。

**沿用的技术路线**（2026-10-14 至 10-16 确定；环境端的提速按上面的调研改）

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

**长期方向**（用户 2026-10-18 提出，未排期；baseline 跑出来之后再逐步安排）

- 最终回到真机。真机侧不放大算力去微调参数：VLA 的训练在云端做；在线推理与在线 RL 在推理机上做。
- LoRA（π₀.₅ 参数）的更新希望放到离线做，在线只做 RL。理由（用户判断）：原方法对 π₀.₅ 参数的改动本来就很小
  （10-18 两次运行约 500 回合后参数范数只变 0.04）。这就是 spec 里的分离更新
  （[expo-ft-spec.md §4.4](../xense-openpi/expo-ft-spec.md)）。
- 第一个消融：不更新 LoRA，只更新 critic 与编辑策略（分离更新的 M=∞，即原文 Fig. 6 的冻结设置），看参数更新到底
  影响多少成功率。
- 在这个前提下，用户自己的方法大概率用同步版本。
- 冻结 checkpoint、多台机器共享 learner 来攒编辑策略的数据，往后搁置。理由（用户判断）：真机最终是“跑一回合、更新一次”，
  不会一次收多台机器的数据再训练。可以另做一个方案单独评测。
- 可做的消融：编辑策略更新后，新参数是在回合结束时换上，还是在动作块级别就换上。

### Task: 同步训练上比较两种回合判定

用户 2026-10-18 晚定。都在 `02-xense-training` GPU 0–4，同步联合更新（`rl_joint.sh`，参考默认、β=0.05），15k 基座，固定种子，
各跑到第 300 回合，先后进行。

**Change**

- [x] expo-ft `ROBOTWIN_STEP_LIMIT`：回合在第 n 步判失败（覆盖任务的 `step_lim`），上限内重试成功也算成功；0 保持原样
      （2026-10-18，expo-ft `ca1a4d9`）

**Verification**

1. [x] 只跑环境端（本机）：`ROBOTWIN_STEP_LIMIT=150` 时两个原地不动的回合都在第 150 步结束，判失败、mask 为 0
2. [x] 单次尝试判定 `expo_bbh_sync_fs_b005_sa`（W&B `pontu579`，19:54 起）跑到第 300 回合停（10-19 01:40）
3. [x] 步数上限 150 `expo_bbh_sync_fs_b005_sl150`（W&B `6j0thy2w`）紧接着起，跑到第 300 回合停（10-19 01:43–06:45）

**Done**

- [x] 两次运行与 10-18 官方协议那次的分段成功率（1–10、11–50、51–100、101–200、201–300）、每小时回合数、20 回合滑动成功率
      首次到 90% 的墙钟时间并列写进 [experiments.md](experiments.md)（10-19：步数上限 150 固定种子 1.8 h 到 90%，单次尝试没到；待用户定是否改用步数上限）

### Task: 随机种子上的步数上限 150 运行

用户 2026-10-18 晚定。与 02 上固定种子的步数上限 150 运行并行，看放开种子后的学习速度。

**Change**

- [x] expo-ft `ROBOTWIN_SEED_TABLE`：reset 按表里的顺序取种子与指令，不跑专家检查；建场景报 `UnStableError` 时顺延到下一个
- [x] `scripts/robotwin/make_seed_table.py`：每个进程检查一段连续的候选种子，再按种子号合并（以上 expo-ft `a75e8e6`）
- [x] `beat_block_hammer` 训练种子表：从 10100000（`ROBOTWIN_SEED_INDEX=100`，与在线训练相同）起检查 600 个候选，451 个
      有效，`data/robotwin_seeds/beat_block_hammer_demo_clean/train_seeds.json`。300 回合每回合一个新种子，够用；表用完
      会报错，不循环
- [x] h100 GPU 0–4 起 `expo_bbh_sync_rs_b005_sl150`（W&B `hf4w1so7`，10-19 02:40–08:28）：随机种子（种子表）、步数上限 150、可以重试，15k 基座，β=0.05，
      跑到第 300 回合（种子表在 02 GPU 5–7 上趁联训期间算；联训约 02:30 结束后起）

**Verification**

1. [x] 本机：用表时前 3 次 reset 的种子、指令、关节状态与头部图像均值都和在线检查一致；reset 0.4 s（在线检查 1.3–1.8 s）
2. [x] 训练机（02 GPU 5–7，3 进程）：600 个候选 451 个有效，每个约 1.0 s（第一个含 planner 初始化 22 s），共约 4 min。
       复用 task 对象之后在线检查本来就只多约 1 s/回合，种子表省得很少；原先估的 20–60 s 是复用之前的数字
3. [x] 运行中回合的种子逐个不同、指令与表一致（`hf4w1so7` 前 10 回合的 prompt 与表的前 10 项一一对应）

**Done**

- [x] 随机种子与固定种子两次步数上限 150 运行的分段成功率、每小时回合数并列写进 [experiments.md](experiments.md)（随机种子 201–300 回合 83%）

### Task: 跨回合复用 RoboTwin task 对象

照官方评测的做法：`RoboTwinEnv` 只建一个 task 对象，reset 与专家检查都在它上面调用 `close_env` 和 `setup_demo`，机器人与
curobo planner 只在第一次建。不改 RoboTwin，也不改协议与 learner。

**Change**

- [x] expo-ft `client/envs/robotwin_env.py`：`reset` 与 `_expert_succeeds` 复用同一个 task 对象，不再每次新建
      （2026-10-18，expo-ft `3fbdd2d`）

**Verification**

1. [x] 只跑环境端（本机 `~/.venvs/robotwin` 或训练机单卡）：固定种子第 2、3 次 reset 少掉 curobo 初始化的时间
       （训练机上是 18.3 s，27 s 降到约 9 s）
       （2026-10-18 本机：13.6 s → 0.5 s；训练机未测）
2. [x] 同一种子复用前后，reset 后的 `observation.state` 一致，三路图像的平均差在渲染噪声量级（10-16 测过：8 spp 与 32 spp
       的平均差是 0.45/255）（本机：逐像素相同；先移动左臂再 reset 也相同）
3. [x] 不固定种子时连续 reset 3 次（含专家检查），种子序列与新建 task 时一致（本机：10100000–10100002，一致）

**Done**

- [x] 复用前后的 reset 耗时与一致性结果写进 [experiments.md](experiments.md)（本机部分；训练机耗时晚上补）

## RoboTwin 10 任务 baseline：联训 LoRA 基座

在 `beat_block_hammer` 之外选一组任务，构建我们自己 baseline 里的 EXPO-FT 结果。先训一个所有任务共用的 SFT 基座，
再逐任务做 RL。

**2026-10-19 晚的安排**（用户 2026-10-19 定；卡从 00:00 起可用，不保证都空，有几组卡就起几组）

1. 00:00 起，用 seen 指令把 29999 的 Hard 从头评一遍：10 个任务各 50 回合（两片各 25），两台机 16 张卡，约 2 h。白天那批
   用的是 unseen，只作参考。同时占 1–2 张卡给 RL 做 smoke（约 20 min）。
2. 按 seen 的 Hard 成功率严格挑 30–70% 的任务；给每个选中的任务算 Hard 种子表（`demo_randomized`、seen，600 个候选，
   3 张卡约 20 min），按示教平均长度 1.3 倍定步数上限，并用 Hard 下成功回合的步数核对。
3. 约 02:30 起 RL：每台机 GPU 0–4（1 张推理与环境、4 张更新）与 GPU 5–7（1+2）各一组，最多 4 组；卡不够按优先级
   `beat_block_hammer`、`place_empty_cup`、`stack_blocks_two`、`place_phone_stand`（只取落在区间里的）。每组跑到第 300 回合。
   3 卡的组 update 较慢，与 5 卡的组比较时要打折扣。
4. 早上把结果补进 RL 总表，再定是否删联训 3k–27k 的 checkpoint。

**已定**（用户 2026-10-18）

- 任务（10 个，Easy / `demo_clean`，Aloha-AgileX，每个 50 条官方示教 `aloha-agilex_clean_50`）：`beat_block_hammer`、
  `pick_dual_bottles`、`place_empty_cup`、`move_can_pot`、`handover_block`、`stack_blocks_two`、`press_stapler`、
  `place_phone_stand`、`move_playingcard_away`、`click_alarmclock`。前 5 个 RLinf 有 RL 结果；后 5 个按技能多样性补充。
  官方榜单 π₀ 单任务的 Easy 成功率在 35–63% 之间。
- 联训一个 π₀.₅ LoRA（10 个任务的示教合在一个数据集里），所有任务统一用同一个 checkpoint 做 RL 起点，省空间。
- RL 起点的基座成功率要在 30–70%：太高 RL 没有意义。挑一个大多数任务落在区间里的 checkpoint，区间外的任务不做 RL。
- 不和官方 π₀.₅ 联训对比（我们是 LoRA，官方是全参）。
- SFT 只用 Easy（`demo_clean`）数据。Hard（clean2random）训练数据相同，评测换成 `demo_randomized`（桌上有杂物、
  随机背景与光照、桌高 ±3 cm）。
- **只看场景泛化，不看语言泛化（用户 2026-10-19）：** RL 训练与 Hard 评测都用 seen 指令（`ROBOTWIN_INSTRUCTION_TYPE`
  保持默认 `seen`）；官方榜单 Hard 用的 unseen 指令不用。
- RL 的 replay 预填用该任务微调用的 50 条 clean 示教（`<task>_aloha_clean_50`，即联训数据里属于该任务的部分），与 Hard
  场景不一致，照 bbh 的做法不改（用户 2026-10-19）。
- **RL 做在 Hard 上（用户 2026-10-19 定）。** 微调就能到很高成功率的任务，现实中做 RL 没有意义；RL 是为微调上不去的任务
  （用户判断与偏好）。联训 29999 在 Easy 上 8 个任务已超过 80%，所以用最强的 checkpoint（29999）评 Hard，挑 Hard 成功率
  在 30–70% 的任务，在 `demo_randomized` 上做 RL；Easy 不再往前评更早的 checkpoint（3k、9k 已评的部分记在 experiments.md）。
- 不用 RoboDojo：仿真换成 Isaac Sim（H100 没有 RT core，大概率渲染不了，未核实），任务基座成功率太低，榜单比的是一个
  策略做全部任务；作为以后的第二个 benchmark。
- 参考数字：官方榜单（`robotwin-platform.github.io/leaderboard`）的“π₀ 单任务”是每个任务一个 checkpoint；“π₀.₅ 联训”
  是一个模型用 50 个任务各 50 条示教一起训。`beat_block_hammer` 上两者分别是 43% 与 93%，我们的单任务 π₀.₅ LoRA 15k
  是 72%。

- SFT 配方沿用 bbh（batch 64、恒定 2.5e-5、无 EMA），8 卡先训 30k 步（约 4 h），每 3k 步存一次；从 9k 步开始评，之后
  每隔 6k 步评一次（9k、15k、21k、27k）。依据：bbh 单任务 15k 步约 170 遍数据到 72%；联训约 6–7.5 万帧，30k 步时每个
  任务只过 25–30 遍，相当于单任务 3k 步左右，而目标本来就只要 30–70%。多数任务到 30k 仍低于 30% 就续训，已高于 70%
  就用更早的 checkpoint。每个 checkpoint 约 9 GB，评完不用的即删，同时最多留 3–4 个。
- 挑基座时 10 个任务都用官方协议评（`ROBOTWIN_SINGLE_ATTEMPT=0`，可以重试到步数上限）；单次尝试判定现在只有
  `beat_block_hammer` 有，RL 前再为要做 RL 的任务补。

### Task: 10 任务数据与联训 SFT

**进度（2026-10-18 23:00）**

- 数据（`/root/data/atticux/agent-workspace/expo-ft/data/lerobot/robotwin/`）：10 个单任务数据集与联训数据集
  `cotrain10_aloha_clean_50` 都已转完；数据目录里转换脚本的副本 `data/convert_robotwin_to_lerobot.py` 可以删。
- norm stats 已算，在 `assets/pi05_robotwin_cotrain10_lora/robotwin/cotrain10_aloha_clean_50/`（在 `$W` 下运行
  `compute_norm_stats.py`，它不收 `--assets-base-dir`）。
- 联训 `sft_cotrain10_30k`：h100 GPU 0–7，tmux `atx_cotrain`，23:00 起，日志 `logs/sft/sft_cotrain10_30k.log`
  （末行 `TRAIN_EXIT=`），checkpoint 在 `checkpoints/pi05_robotwin_cotrain10_lora/sft_cotrain10_30k/`。
- 评测命令：`TASK=<task> PI05_CONFIG=pi05_robotwin_cotrain10_lora ASSET_ID=robotwin/cotrain10_aloha_clean_50` 加
  `eval_sft_ckpt.sh`；bbh 还要 `ROBOTWIN_SINGLE_ATTEMPT=0`（它的配置默认开判定）。

**Change**

- [x] expo-ft `scripts/convert_robotwin_to_lerobot.py`：`--raw_dir` 接受多个任务目录，写成一个多任务数据集，每回合用
      自己任务的指令（单任务时输出不变）
- [x] 数据：下载 9 个新任务的原始示教（代理返回 403，改走 `hf-mirror.com`），转出联训数据集
      `robotwin/cotrain10_aloha_clean_50` 与 9 个单任务数据集（单任务的给之后 RL 的 replay 预填）
- [x] xense-openpi `pi05_robotwin_cotrain10_lora`：配方同 bbh，数据换成联训数据集；在联训数据上算 norm stats
      （xense-openpi `1045ecc`）
- [x] expo-ft 任务配置与评测脚本按任务名参数化：`configs/task/robotwin_task.py` 与 `eval_sft_ckpt.sh`
      （以上代码 2026-10-18，expo-ft `31e467a`）
- [x] 联训 30k 步（h100 8 卡，W&B 见 checkpoint 目录的 `wandb_id.txt`；23:07–02:40，`TRAIN_EXIT=0`）

**Verification**

1. [x] 联训数据集：500 回合、80,173 帧，等于 10 个单任务数据集之和；每个任务抽查一回合，prompt 是本任务的指令
2. [ ] 每个任务用联训配置跑一次推理（不必成功），确认 10 个任务的环境端都能起、步数上限与指令正确
       （环境端已过；learner 侧由 29999 的评测验证：6 个任务的推理正常、已有成功回合）
3. [x] 29999 的 Easy，每个任务 50 回合、官方协议（10-19 02:40–06:18）：8 个任务 ≥80%，click_alarmclock 42%，handover_block 16%
4. [ ] 29999 的 Hard（`ROBOTWIN_TASK_CONFIG=demo_randomized`，seen 指令），每个任务 50 回合，10-19 00:00 起（见本节开头的安排）。
       10-19 09:00–10:10 用 unseen 评过一部分后按用户要求停了，结果只作参考（experiments.md）

**Done**

- [ ] 29999 在 10 个任务上的 Easy 与 Hard 成功率表写进 [experiments.md](experiments.md)，按 Hard 30–70% 选出做 RL 的任务

### Task: 联训基座上的 Hard RL（2026-10-19 晚）

**Change**

- [x] expo-ft `rl_joint.sh` 按任务参数化：`TASK`、`PI05_CONFIG`、`ASSET_ID`，默认仍是 bbh 单任务基座；`robotwin_task.py`
      加 `ROBOTWIN_STEP_LIMIT`
- [ ] 每个选中任务的 Hard 种子表与步数上限
- [ ] 每组：联训 29999、随机种子（种子表）、步数上限、`demo_randomized`、seen 指令、β=0.05、参考默认，跑到第 300 回合
      （bbh 走自己的配置 `robotwin_beat_block_hammer.py`，默认开单次尝试判定，要设 `ROBOTWIN_SINGLE_ATTEMPT=0`）

**Verification**

1. [x] 本机只跑环境端：通用配置 `robotwin_task.py`（用 bbh，本机缺其他任务的物体资源）在 `ROBOTWIN_STEP_LIMIT=150` 下第 150 步结束
2. [ ] 训练机 smoke：每组前几回合场景逐个不同、失败回合在上限处结束、10 回合后开始 update

**Done**

- [ ] 各组的分段成功率、首次到 80%/90% 的回合与墙钟时间写进 experiments.md 的 RL 总表
