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
- 不做“块末只渲染一次”（RLinf 的默认做法）：它让 replay 只在动作块起点有图像，属于算法与数据的改动。
- **加速路线：参考实现的异步训练，加上多个环境共享一个 learner。** 这个事务的目标是尽快把 baseline 跑出来，所以接受与
  原文的两处不一致（用户决定 2026-10-18）：
  - 多个环境同时 rollout，相当于多台真机；
  - 用异步训练（`train_pi_robo_async.py`），新参数可以在动作块级别换上。异步下 update 不再按“每回合 3 次”计，
    其余超参不变。
  现在 `train_pi_robo_async.py` 只接 DROID，要像 `train_pi_robo.py` 那样接上 RoboTwin，再改成多环境。

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
   - 收益估计见下面待讨论第 2 条。

**待讨论**

1. **多环境用 (a) 还是 (b)。** 用户 2026-10-18：等扩展测试出来再定，训练机晚上空了再测。Agent 建议：除非线程的扩展
   明显好于进程，否则选 (a)，改动面小，也没有 GIL 风险。每个环境约 3.5 GB 显存，和推理共用 GPU 0（推理峰值约 40 GB），
   最多约 8 个环境。
2. **收益估计。** 用户 2026-10-18 已接受多环境（相当于多台真机）用于 baseline，见已定。每个环境一回合结束就写进
   replay，不等其他环境；“整段写入”只是 replay 的存储要求（同一回合的转移要连续存放）。
   - Agent 推断（未验证），按同步、每回合 3 次 update 计：一回合的时间账（15k 基座、固定种子）是走步约 45 s（约 100 步 × 0.45 s，其中渲染 212 ms、
     物理 46 ms），加上回合之间 reset 27 s 与 update 22 s 中较长的那个，合计约 72 s，对上实测的 50 回合/h。
     - 复用 task 对象后，回合之间由 update 的 22 s 决定，约 67 s/回合，只快约 8%。不固定种子时，加上种子表，
       可从约 125 s/回合降到约 67 s/回合。
     - 多环境只能并行“走步”这一段。update 仍是每回合 22 s、而且串行，所以上限约 160 回合/h。若 update 阻塞所有
       环境，4 个环境约 108 回合/h，8 个约 130 回合/h。
   - 参考实现的异步训练仍是一台机器人：更新线程在其余卡上连续 update，把新参数交给采样线程，省掉的是回合结束时
     等 update 的时间（README：回合很长时才用）。它解决 update 挡住走步，多环境解决走步太慢，两者叠加后不再受
     “每回合 22 s”的上限约束。
3. **验收方式。** 用户意见：迁移后直接评估效果，不预设提速比例。具体看什么（同一固定种子上到 90% 的墙钟时间、每小时
   回合数），随方案确定。
4. **恢复随机种子时的种子表。** 用户 2026-10-18 倾向照 RLinf 的做法，给我们自己的配置（aloha-agilex、demo_clean）
   离线算一份有效种子表。种子按同样的顺序检查，生成的种子序列与官方评测协议一致，reset 时不再跑约 60 s 的专家检查
   （第一次 reset 实测 79.6 s）。到恢复场景随机性时再定。

**沿用的技术路线**（2026-10-14 至 10-16 确定；环境端的提速按上面的调研与待讨论改）

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

### Task: RoboTwin 上的异步训练与多环境

用户 2026-10-18 定：今晚 20:00 起在训练机上调试，夜里监督训练，早上汇报。数据和时间允许的话，固定这套做法，再换其他
任务，构建我们自己的 baseline 里的 EXPO-FT 结果。

**Change**

- [x] `train_pi_robo_async.py` 接上 RoboTwin（LeRobot 演示读取），并移入同步脚本在 `robotwin-sim` 上的修复：在 CPU 上取
      batch（否则推理卡多占约 45 GB）、恢复后复制单设备的叶子、新的恢复语义、`--max_to_keep`。update 的起点与频率沿用
      参考实现的异步做法（buffer 够一个 batch 就开始，更新线程连续跑），属于已定里接受的偏差。更新线程另加了与同步脚本
      相同的一步预取（不加时取 batch 约 12 s 串行，每次 update 约 20 s；加后约 8 s）。
- [x] 多环境按接法 (a)：N 个环境进程各拨一个端口，learner 每个环境一个 actor 线程（各自的连接、采样器、回合状态与
      转移队列），共用推理卡上的参数，在动作块边界换上更新线程发布的新参数；一回合结束时在 buffer 锁内整段写入并标记
      成功；W&B 与 checkpoint 用全局步数（写入 replay 的转移数）。扩展测试线程不随数量增长，(a) 定下。
- [x] `scripts/robotwin/rl_async.sh`：起 learner 与 N 个环境进程（端口 `PORT` 到 `PORT+N-1`，每个环境一张渲染卡）
      （以上 2026-10-18，expo-ft `f85fc6a`）

**Verification**

1. [x] 训练机扩展测试：线程与同卡多进程都不增长，一卡一个环境线性增长；用户定 N=4（见 experiments.md）
2. [x] N=1 短跑：回合、update 与 W&B 指标正常，推理卡显存不涨到同步脚本修复前的水平
       同时看：单次尝试判定的失败回合在第一次落锤后约 10 步内结束（失败回合 82–217 步结束，未跑满 400 步；没抬起锤子的
       回合仍跑满 400 步，符合判定设计）
3. [x] N>1 短跑：每个环境的回合各自完整写入 replay（回合数、成功标记与各环境日志对得上），停止再 `--resume` 能接上
4. [ ] 固定种子整夜运行（15k 基座、β=0.05、单次尝试判定）：`rl_status.sh` 看分段成功率与 critic 走势
       （2026-10-18 18:46 起，`expo_bbh_async4_fs_b005`，h100，N=4）

**Done**

- [ ] 每小时回合数、20 回合滑动成功率首次到 90% 的墙钟时间写进 [experiments.md](experiments.md)，与 10-18 夜里同步
      运行的 50 回合/h、3.2 h 并列

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
再逐任务做 RL（RL 的排期等基座选定后再定）。

今晚（2026-10-18）的两件事：`xense-training-h100` 上跑异步多环境的整夜运行（上一节的 Task），`02-xense-training` 的
8 张卡空闲，用来做本节的数据与联训 SFT。

**已定**（用户 2026-10-18）

- 任务（10 个，Easy / `demo_clean`，Aloha-AgileX，每个 50 条官方示教 `aloha-agilex_clean_50`）：`beat_block_hammer`、
  `pick_dual_bottles`、`place_empty_cup`、`move_can_pot`、`handover_block`、`stack_blocks_two`、`press_stapler`、
  `place_phone_stand`、`move_playingcard_away`、`click_alarmclock`。前 5 个 RLinf 有 RL 结果；后 5 个按技能多样性补充。
  官方榜单 π₀ 单任务的 Easy 成功率在 35–63% 之间。
- 联训一个 π₀.₅ LoRA（10 个任务的示教合在一个数据集里），所有任务统一用同一个 checkpoint 做 RL 起点，省空间。
- RL 起点的基座成功率要在 30–70%：太高 RL 没有意义。挑一个大多数任务落在区间里的 checkpoint，区间外的任务不做 RL。
- 不和官方 π₀.₅ 联训对比（我们是 LoRA，官方是全参）。
- 只做 Easy：训练与评测都用 `demo_clean`。Hard（clean2random）训练数据相同，评测换成 `demo_randomized`（桌上有杂物、
  随机背景与光照、桌高 ±3 cm、未见过的指令），考的是泛化，这里不做。
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

**交接状态（2026-10-18 20:25）**

- 卡：本来计划 02 的 8 张卡联训，但另一会话 19:54 起在 02 GPU 0–4 跑同步对照 `expo_bbh_sync_fs_b005_sa`，在 h100
  GPU 0–5 跑异步 N=1 `expo_bbh_async1_fs_b005_sa`。现在空的只有 02 GPU 5–7、h100 GPU 6–7。batch 64 要整除卡数，
  02 只能用 2 张。用户定（2026-10-18）：等 02 的卡空了再 8 卡联训（约 4 h），不用两卡先训。
- 数据（`02-xense-training` 与 h100 共享 `/root/data/atticux/agent-workspace/expo-ft/data/`）：
  - 原始示教 `raw/dataset/<task>/aloha-agilex_clean_50/`，10 个任务各 50 回合，共 7.3 GB。
  - 单任务 LeRobot 数据集 `lerobot/robotwin/<task>_aloha_clean_50`（20:23 时已完成 6 个：pick_dual_bottles 6,129 帧、
    move_can_pot 7,568、place_empty_cup 8,617、handover_block 14,084、stack_blocks_two 15,647、press_stapler；
    剩 place_phone_stand、move_playingcard_away、click_alarmclock 在 tmux `atx_conv_per` 里依次跑，约 15 min）。
  - 联训数据集 `lerobot/robotwin/cotrain10_aloha_clean_50`：tmux `atx_conv` 里在转，20:23 时 304/500 回合，约 25 min。
  - 日志 `logs/convert/<task>.log`、`logs/convert/cotrain10.log`，结束时末行 `EXIT=0`。
  - 转换脚本在 02 上用的是数据目录里的副本 `data/convert_robotwin_to_lerobot.py`（与本机 expo-ft 未提交的改动相同），
    共享 checkout 保持干净；转完可删。
- 环境端检查（Verification 2 的一部分）已过：02 GPU 7 上 10 个任务都能建环境并 reset，指令与步数上限正确，状态 14 维、
  图像 3×224×224（handover_block 第一个种子专家失败，取了下一个，属正常）。learner 侧推理还没测。
- 本机 expo-ft（`robotwin-sim`）未提交的改动：
  - `scripts/convert_robotwin_to_lerobot.py`：`--raw_dir` 收多个目录；
  - `configs/task/robotwin_task.py`（新）：任务名取 `ROBOTWIN_TASK`，步数上限读 `_eval_step_limit.yml`，单次尝试判定
    默认关（官方协议）；本机 10 个任务都能加载，步数上限 400/500/800 正确；
  - `scripts/robotwin/eval_sft_ckpt.sh`：`TASK`、`PI05_CONFIG`、`ASSET_ID` 三个环境变量，默认值仍是 bbh；
  - xense-openpi（expo-ft 里的 submodule，分支 `expo-ft`）`configs/_examples/pi05_robotwin_cotrain10_lora.yaml`（新）：
    bbh 配方，数据换成联训数据集，30k 步、每 3k 存一次且全留，去掉了 bbh 的 default_prompt。02 上已放一份到 openpi
    checkout 的 `configs/`（gitignored，供训练直接用）。
- 接下来（数据转完后）：
  1. norm stats：在 `/root/data/atticux/agent-workspace/expo-ft` 下
     `JAX_PLATFORMS=cpu HF_LEROBOT_HOME=$W/data/lerobot $SRC/.venv/bin/python $O/scripts/compute_norm_stats.py --config-name pi05_robotwin_cotrain10_lora`
     （写到 `assets/pi05_robotwin_cotrain10_lora/robotwin/cotrain10_aloha_clean_50/`）。
  2. 核对联训数据集：500 回合，帧数等于 10 个单任务之和（bbh 5,682）。
  3. 02 的 8 张卡空出来后训练，命令同 `night_run.sh` 的训练段：在 `$O` 下
     `scripts/train.py pi05_robotwin_cotrain10_lora --exp-name=sft_cotrain10_30k --project-name=expo-ft --assets-base-dir=$W/assets --checkpoint-base-dir=$W/checkpoints --overwrite --num-workers=32`
     （W&B key 与 `network_accelerate` 同 `night_run.sh`）。
  4. 9k 起每 6k 评一次：`TASK=<task> PI05_CONFIG=pi05_robotwin_cotrain10_lora ASSET_ID=robotwin/cotrain10_aloha_clean_50`
     加 `eval_sft_ckpt.sh`；bbh 还要 `ROBOTWIN_SINGLE_ATTEMPT=0`（它的配置默认开判定）。

**Change**

- [x] expo-ft `scripts/convert_robotwin_to_lerobot.py`：`--raw_dir` 接受多个任务目录，写成一个多任务数据集，每回合用
      自己任务的指令（单任务时输出不变）（未提交）
- [ ] 数据：下载 9 个新任务的原始示教，转出联训数据集 `robotwin/cotrain10_aloha_clean_50` 与 9 个单任务数据集
      （单任务的给之后 RL 的 replay 预填）（已下载；代理返回 403，改走 `hf-mirror.com`；转换进行中，见交接状态）
- [ ] xense-openpi `pi05_robotwin_cotrain10_lora`：配方同 bbh，数据换成联训数据集；在联训数据上算 norm stats
      （配置已写、未提交；norm stats 未算）
- [x] expo-ft 任务配置与评测脚本按任务名参数化：`configs/task/robotwin_task.py` 与 `eval_sft_ckpt.sh`（未提交）
- [ ] 联训（等 02 的 8 张卡空出来）

**Verification**

1. [ ] 联训数据集：500 回合，各任务帧数之和与 9 个单任务数据集加 bbh 的 5682 帧一致，抽查每个任务的 prompt 是本任务的指令
2. [ ] 每个任务用联训配置跑一次推理（不必成功），确认 10 个任务的环境端都能起、步数上限与指令正确
       （环境端已过，learner 侧未测）
3. [ ] 9k、15k、21k、27k 步的 checkpoint 各评 10 个任务、每个 50 回合（8 片并行，官方协议）

**Done**

- [ ] 各 checkpoint 在 10 个任务上的成功率表写进 [experiments.md](experiments.md)，选出 RL 用的 checkpoint 与任务
