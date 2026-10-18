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

- [ ] `train_pi_robo_async.py` 接上 RoboTwin（LeRobot 演示读取），并移入同步脚本在 `robotwin-sim` 上的修复：在 CPU 上取
      batch（否则推理卡多占约 45 GB）、恢复后复制单设备的叶子、新的恢复语义、`--max_to_keep`。update 的起点与频率沿用
      参考实现的异步做法（buffer 够一个 batch 就开始，更新线程连续跑），属于已定里接受的偏差。
- [ ] 多环境按接法 (a)：N 个环境进程各拨一个端口，learner 每个环境一个 actor 线程（各自的连接、采样器、回合状态与
      转移队列），共用推理卡上的参数，在动作块边界换上更新线程发布的新参数；一回合结束时在 buffer 锁内整段写入并标记
      成功；W&B 与 checkpoint 用全局步数。扩展测试若显示线程明显更好，再改 (b)。
- [ ] `scripts/robotwin/rl_async.sh`：起 learner 与 N 个环境进程（端口 `PORT` 到 `PORT+N-1`）

**Verification**

1. [ ] 训练机单卡补完扩展测试（1/2/4/8 个环境，线程与进程），定下 N
2. [ ] N=1 短跑：回合、update 与 W&B 指标正常，推理卡显存不涨到同步脚本修复前的水平
3. [ ] N>1 短跑：每个环境的回合各自完整写入 replay（回合数、成功标记与各环境日志对得上），停止再 `--resume` 能接上
4. [ ] 固定种子整夜运行（15k 基座、β=0.05、单次尝试判定）：`rl_status.sh` 看分段成功率与 critic 走势

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
