# EXPO-FT Plan

## RoboTwin 单任务上跑通 EXPO-FT（联合更新）

这是 [expo-ft-spec.md](../xense-openpi/expo-ft-spec.md) 4.4 复现路线的第一步：在仿真里、不做人工介入、按参考实现联合更新，
在一个任务上把代码调通。看成功率的正式训练和分离更新的消融放在后续事务，等这一项完成再细化。

**已定的技术路线**（2026-10-14 至 10-15 讨论）

- 不迁进 RLinf。RLinf 的仿真环境、数据和结果只作参考。
- 训练全部用 JAX。learner 用 expo-ft 参考实现；π₀.₅ 的 SFT、候选采样和 BC 改用我们自己的 xense-openpi，不再依赖
  pd-perry 的 OpenPI fork。
- 仿真接在 expo-ft 环境 RPC 的另一端，单环境，learner 逐步驱动。真机以后是同一协议的另一个环境端，放在 xense-openpi
  `examples/bi_flexiv_rizon4_rt` 旁边，不在本事务。
- 第一个任务只求快、SFT 起点在 30–60%；只评 Easy（`demo_clean`）。
- RoboTwin 按工作区规则登记为 `methods/robotwin` submodule（你的 fork 作 origin，官方作 upstream），环境端适配代码放
  expo-ft 的 `client/envs/`。
- learner 沿用上游的设计：在 `expo_ft/agents/vla/openpi` 放一份独立 checkout，只是克隆的仓库从 pd-perry 的 OpenPI fork
  换成 xense-openpi 的 `expo-ft` 分支。xense-openpi 的改动只有两处接口加 RoboTwin 配置，在 `methods/xense-openpi` 里开发
  并推送，checkout 再拉取；每次运行记下 checkout 的 commit。
- 运行机器用 `xense-training-h100` 单卡，大文件放 `/mnt/data/atticux/agent-workspace/expo-ft/`。

**依据**

- xense-openpi `rl-exp`（`bbd1c71`，官方 OpenPI `0389383` 加 375 个提交）与 pd-perry `expo_ft`（`46407a4`，官方
  `c23745b` 加 21 个提交）的 JAX 0.5.3、flax 0.10.2、orbax 0.11.13 版本相同。两个基点之间官方的改动不碰 JAX 路径。
  expo-ft 用到的 TrainState、`fsdp_sharding`、`freeze_filter`、optimizer、`_merge_params`、`compute_loss(..., train=True)`
  在 xense 里都在，缺的是多样本采样、批量 `Policy.infer`、`get_config` 的 `weight_loader_path` 参数，以及客户端包名
  （`openpi_client` 在 xense 里改名为 `xense_client`）。
- xense 已有的 `sample_actions_with_prefix` 返回 RLT 用的 prefix hidden，与 pd-perry `real-time-expo-ft` 分支同名方法
  （固定已执行前缀的 RTC 采样）语义不同。实时版才用到，本事务不碰。
- expo-ft 工作区版本 `aaf1599` 基于 `803381f`，不含上游 `21fe3d3` 的奖励对齐修正；规格按修正后的写法（spec 4.2）。
- RoboTwin 官方数据 `TianxingChen/RoboTwin2.0` 有 `lerobot_dataset/RoboTwin_lerobot_v30.zip`（4.1 GB，LeRobot v3.0，
  xense-openpi 的 lerobot 0.5.1 能读），每个任务另有 `aloha-agilex_clean_50.zip`（HDF5）。从第三方 v2.1 版本看：14 维
  关节（每臂 6 关节加夹爪）、`cam_high` 与左右腕三路 480×640 相机、标称 50 fps，`adjust_bottle` 平均约 140 步一回合。
- RoboTwin 环境接口是 `setup_demo(seed, is_test)`、`take_action`、`get_obs`、`check_success`，回合上限 `step_lim`
  （`beat_block_hammer`、`click_bell` 都是 400）。官方评测先用专家 `play_once` 筛掉专家做不成的种子，种子从
  100000×(1+seed) 起。
- 起点参照：π₀ 用 50 条 clean 示教单任务训练，Easy 档 `beat_block_hammer` 43%、`click_bell` 44%（RoboTwin 2.0 论文
  Table 5）。π₀.₅ 一般更高，我们自己 SFT 的起点要实测。

**不做**：看成功率的正式训练、人工介入、Real-Time EXPO-FT、分离更新、真机、多任务。

### Task: expo-ft 带上上游的奖励对齐修正

**Change**

- [x] 在 expo-ft fork 从 `workspace` 开分支 `robotwin-sim`，用 `git merge --allow-unrelated-histories` 合并上游
      `21fe3d3`，冲突的文件取上游版本。上游与 `aaf1599` 的源码差别只有奖励对齐，合并后不再需要自己改 transition 记录
      （合并提交 `5c0da72`，未推送）

> **更正（2026-10-15）：** 原计划写的是直接合并。执行时发现上游把历史压成了一个没有父提交的根提交 `21fe3d3`，与我们
> `803381f → aaf1599` 没有共同祖先，普通 merge 会被拒绝。可选做法是 unrelated-histories 合并，或者把 diff 原样 apply
> 成一个提交，两者代码相同。选前者：`21fe3d3` 进入我们的历史后，上游以后在它之上的提交可以普通合并；代价是历史里多一个
> 根提交，上游再压一次历史时问题会重现。验证也随之调整：本地还没有 learner 环境（Task 3 才有），且 `loop_utils.py` 会
> 经 `expo_ft.agents` 加载 openpi，所以假环境检查改在临时脚本里用桩模块替换 `expo_ft.agents`，按 `train_pi_robo.py`
> 的调用顺序驱动 `EpisodeSink`；`main()` 接线是否正确留到 Task 6 冒烟时检查真实 replay。

**Verification**

1. [x] 核对合并带来的 diff 只落在 transition 记录相关的文件：合并后的树等于 `21fe3d3` 加我们的 `AGENTS.md`、
      `CLAUDE.md`；相对 `aaf1599` 只改了 `expo_ft/utils/loop_utils.py`、`train_pi_robo.py`、`train_pi_robo_async.py`，
      另有 `README.md` 两行关于实时版 DROID 分支的说明
2. [x] 临时脚本：桩掉 `expo_ft.agents`，按 `train_pi_robo.py` 的顺序（每步先 `label_last`，非终止时再
      `record_transition`）驱动 `EpisodeSink` 走一个成功回合和一个超时回合，检查插入 replay 的 transition。另加一个
      回合中途 flush 的情形（`update_type=step` 时 `run_agent_updates` 会先 flush）。变异检查：把 `flush_transitions`
      里「保留队尾非终止 transition」改成全部插入后，中途 flush 的情形报出未打标签的 transition

**Done**

- [x] 成功回合里 r=1 记在执行最后一个动作的那一步，超时回合全为 0，两者末步 mask 都是 0（成功 5 步：
      rewards `[0,0,0,0,1]`、masks `[1,1,1,1,0]`；超时 4 步：rewards 全 0、末步 mask 0）
- [x] 终止时刻的观测不再多记一条 transition（插入的观测是 `o0…o{n-1}`，没有终止观测）。这是 `EpisodeSink` 层面的
      证据；`main()` 里的接线在 Task 6 冒烟时用真实 replay 再查

### Task: xense-openpi 补上 EXPO-FT 需要的采样接口

**Change**

- [x] 从 `rl-exp`（`bbd1c71`）开分支 `expo-ft`
- [x] `Pi0.sample_actions` 加 `num_samples` 与 `train`：prefix 只前向一次，KV cache 复制给 N 条去噪序列，返回
      (b·N, H, D)；`train` 控制 `preprocess_observation` 是否增广。与现有 RTC 参数（`inference_delay` 等）同时出现时直接
      报错，不做组合，因为同步版用不到。实现落在 `_sample_actions`，`num_samples=1` 且 `train=False` 时走原来的代码路径
- [x] `Policy.infer` 加 `is_batch` 与 `for_training`：前者跳过加减 batch 维，后者输出保留 jax array；`module_jit` 把
      `train`、`num_samples` 设为 static
- [x] `get_config` 不改签名；`weight_loader_path` 在 expo-ft 侧用 `dataclasses.replace` 替换 `weight_loader`，少动一处
      xense 的公共接口（xense 侧无改动，expo-ft 侧在 Task 3 做）
- [x] 不动现有的 `sample_actions_with_prefix`，RLT 在用

> **与原计划的出入（2026-10-15）：** `num_steps` 没有设为 static。pd-perry 的版本把它设为 static，但 xense 现有调用把它
> 当作可追踪的值传入，改成 static 会改变现有行为，而 expo-ft 不需要它是 static。另加一处计划外的改动：`Policy.__init__`
> 的 `rng or jax.random.key(0)` 改为 `is not None` 判断——expo-ft 在自己的 `jax.jit` 里传入 rng 构造 `Policy`，对 tracer
> 取真值会报错；对非空 key 的行为不变。

**Verification**

本机内存不足以跑 pi0 测试（进程被系统杀掉），测试都在 `xense-training-h100` 上用 CPU 跑：8 张卡被其他任务占满，
用 `nice -n 19`、`taskset` 限 8 核、`ulimit -v` 限内存，服务器负载保持在原来的 80 左右。环境在
`/root/data/atticux/xense-openpi-expo-ft/.venv`，按 `uv.lock` 导出的固定版本从阿里云 PyPI 与 pytorch-wheels 镜像安装。

1. [x] 新增测试（小维度假模型，CPU）：同一份噪声下，`num_samples=N` 调一次与单样本调 N 次比较
      （`model_test.py::test_sample_actions_num_samples_*`，pi0 与 pi05 各一）；另测在调用方 `jax.jit` 内构造 `Policy` 并以
      `is_batch=True, for_training=True` 调用（`policy_batch_test.py`）
2. [x] `num_samples=1` 与改动前的 `sample_actions` 比较：在同一台服务器上分别用 `bbd1c71` 原版源码和新代码对 dummy 的
      pi0、pi05 跑普通采样、给定噪声采样、`sample_actions_with_prefix` 共 8 组输出。最初拿本机生成的基线比，`pi0/sample`
      差 0.0127，同机重做后为 0，差异来自两台机器的 CPU 数值而非代码
3. [x] 按 `docs/xense-openpi/cmd.md` 跑 xense-openpi 原有单测，另跑 `src/openpi/models` 与 `src/openpi/policies`
      （排除 `manual` 和需要下载 checkpoint 的 `test_model_restore`）：后者 42 passed、2 failed。两个失败在 `bbd1c71`
      原版源码下以相同的调用栈复现，与本次改动无关：`tokenizer_test.py::test_fast_tokenizer` 要从 HuggingFace 下载，
      服务器连不上；`policy_rtc_test.py` 把字符串 prompt 交给 `jnp.asarray` 而报 `data type 'test' not understood`
4. [x] 改动文件 `ruff check` 与 `ruff format` 通过；格式化只涉及新写的行

**Done**

- [x] 两种调用逐元素一致（atol 1e-5），`num_samples=1` 与改动前逐位一致（8 组最大差值都是 0）
- [x] 原有单测全部通过，数量不变（models 与 policies 下两个已有失败除外，见验证 3）。`cmd.md` 那组为 107 passed、2 skipped（skip 均为找不到 RLinf 参照）；原计划写的
      101 是旧版本的数，`bbd1c71` 本身就是 107，本次没有改动 `src/openpi/rl` 与 `examples` 下的测试

### Task: expo-ft learner 改用 xense-openpi，去掉写死 DROID 的地方

**Change**

- [ ] `expo_ft/agents/vla/openpi` 克隆 xense-openpi 的 `expo-ft` 分支；`pyproject.toml` 里 `openpi` 的路径不变，
      `openpi-client` 换成 `packages/xense-client` 下的 `xense-client`，`openpi_client` 的 import 换成 `xense_client`
- [ ] `expo_ft/utils/train_utils.py`：`get_config(name)` 之后用 `dataclasses.replace` 换 `weight_loader`
- [ ] `train_pi_robo.py`、`eval_droid_policy.py` 里 `env_type == "droid"` 的分支加上 `robotwin`
- [ ] 新增从 LeRobot v3.0 数据集预填 replay 的读取函数，输出与 `process_droid_dataset` 相同：每条示教一个成功回合，
      最后一步 r=1 并终止
- [ ] 任务配置给出 critic 相机键、动作维度和 `example_action`；`edit_action_xyzg` 关闭，它假设第 3–5 维是旋转
- [ ] 同步更新 `docs/expo-ft/codebase.md` 里受影响的行、文件树和依赖图

**Verification**

1. [ ] learner 环境 `uv sync` 成功，`train_pi_robo.py --help` 能运行
2. [ ] 用一个小的假 LeRobot v3.0 数据集测预填
3. [ ] 按 write-codebase-doc 的路径检查与渲染检查过一遍改动的图

**Done**

- [ ] learner 进程里 `openpi.__file__` 指向 xense-openpi
- [ ] 预填出的回合数等于示教条数，每回合末步 r=1、mask=0，其余步 r=0、mask=1

### Task: RoboTwin 环境端

**Change**

- [ ] 用 add-method 把 RoboTwin 登记为 `methods/robotwin`；在运行机器上按官方脚本安装并下载资产，用独立的 Python 环境
- [ ] expo-ft `client/envs/robotwin_env.py` 实现环境 RPC 的六个操作：
      reset 按官方评测协议用专家筛种子；step 执行一个 14 维关节动作；成功由 `check_success` 判定，到 `step_lim` 按超时结束；
      观测为三路相机（缩放到 224）、14 维状态和任务指令；`action_type` 恒为 `policy`
- [ ] `configs/task/robotwin_<task>.py` 给出环境类、相机、控制步数上限和指令

**Verification**

1. [ ] 在运行机器上跑 RoboTwin 的 `scripts/test_render.py`，确认无显示器能出图
2. [ ] 对同一个种子先让专家 `play_once` 并记下关节动作，再 reset 到该种子，经环境端逐步回放这些动作

**Done**

- [ ] 渲染检查出图
- [ ] 回放专家动作经过环境端后 `check_success` 为真。这一条同时锁住动作语义：数据里的 action 与环境端执行的是同一种
      关节目标

### Task: SFT 基座落在 30–60%

**Change**

- [ ] 下载官方 v3.0 数据，取 `beat_block_hammer` 的 50 条 clean 示教；若是多任务合并的数据集，按 task 过滤
- [ ] xense-openpi 加 RoboTwin 的 data config 与 YAML：π₀.₅，`gemma_2b_lora` + `gemma_300m_lora`，三路相机，14 维；
      H=16，与规格的参考配置一致（RoboTwin 常见的是 50，起点会因此变化，靠选 checkpoint 补偿）；计算 norm stats
- [ ] 按规格的 SFT 配方训练约 4,000 步（batch 64，学习率 2.5e-5），每 500 步存一次
- [ ] 用环境端加 `eval_droid_policy.py --only_base_actions` 在 Easy 档各评 100 次，挑一个落在 30–60% 的 checkpoint。
      如果都高于 60%，先减示教条数；仍不行就换 `click_bell`，并回来报告

**Verification**

1. [ ] 每个候选 checkpoint 的 Easy 100 次评测记录

**Done**

- [ ] 选定的 checkpoint Easy 100 次成功率在 30–60%，连同步数、示教条数写进 `docs/expo-ft/experiments.md`

### Task: 联合更新冒烟

只验证工程路径，不看成功率。参数取规格的参考默认（N=K=8、β=0.2、C=8、M=10、U=20、B=64），每回合 3 次 update call。

**Change**

- [ ] 冒烟（标为 smoke，允许 dirty checkout）：至少 15 个回合，让前 10 个回合之后真正发生更新；中途停一次，从
      checkpoint 和 replay 恢复后再跑几个回合
- [ ] 冒烟命令按 `docs/AGENTS.md` 的格式写进 `docs/expo-ft/cmd.md`

**Verification**

1. [ ] 冒烟日志：update call 次数、critic loss、Q 值、checkpoint 与 replay 落盘、恢复后继续跑
2. [ ] 同一个 checkpoint 分别用完整策略与 `only_base_actions` 在 Easy 档评几回合，两条评测路径都能跑完

**Done**

- [ ] 更新后 rollout 用的 π₀.₅ 参数与更新前不同，critic loss 与 Q 值都是有限值
- [ ] 恢复后 replay 大小与已跑回合数接上，回合计数从中断处继续
