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

- [x] `expo_ft/agents/vla/openpi` 克隆 xense-openpi 的 `expo-ft` 分支；`pyproject.toml` 里 `openpi` 的路径不变，
      `openpi-client` 换成 `packages/xense-client` 下的 `xense-client`，`openpi_client` 的 import 换成 `xense_client`
- [x] `expo_ft/utils/train_utils.py`：`get_config(name)` 之后用 `dataclasses.replace` 换 `weight_loader`
- [x] `train_pi_robo.py`、`eval_droid_policy.py` 里 `env_type == "droid"` 的分支加上 `robotwin`
- [x] 新增从 LeRobot v3.0 数据集预填 replay 的读取函数，输出与 `process_droid_dataset` 相同：每条示教一个成功回合，
      最后一步 r=1 并终止
- [x] 任务配置给出 critic 相机键、动作维度和 `example_action`；`edit_action_xyzg` 关闭，它假设第 3–5 维是旋转
- [x] 同步更新 `docs/expo-ft/codebase.md` 里受影响的行、文件树和依赖图

> **与原计划的出入（2026-10-15）：**
>
> - 依赖：`requires-python` 与 `.python-version` 升到 3.12（xense-client 要求）；去掉 `datasets>=3.0,<4.0` 的 override，
>   它是给旧 lerobot 的，留着会与 lerobot 0.5.1 冲突而无解。重新 lock 后 jax、flax、orbax、lerobot、datasets、torch、
>   transformers、numpy 与 xense-openpi 的 `uv.lock` 同版本。
> - `get_config` 只去掉 `weight_loader_path` 参数：后面已有的 `dataclasses.replace` 本来就在路径非空时换成
>   `FlexibleCheckpointWeightLoader`。
> - 演示读取放在新文件 `expo_ft/env/lerobot_utils.py` 的 `process_lerobot_dataset`。观测的键沿用数据集的特征名
>   （如 `observation.images.cam_high`、`observation.state`），图像转回 HWC uint8，另加 `prompt`（取该帧的 task）。
>   用 PyAV 解码视频：lerobot 默认的 torchcodec 要系统装 FFmpeg 动态库，本机版本不对，训练服务器上没有。
>   这定下了两条约定：Task 4 环境端发出的观测用同一组键；Task 5 的 data config 的 repack 要从 replay 的
>   `actions` 键读动作（replay 插入时用的是 `actions`，不是数据集的 `action`）。
> - 任务配置是 `configs/task/robotwin_base.py`，只放 RoboTwin 公共项（`env_type`、14 维 `example_action`、三路
>   critic 相机、`edit_action_xyzg=False`）；环境类、指令、`auto_reset_steps`、`control_hz` 留给 Task 4 的任务文件。
> - 机器人端（`client/run_client.py`、`client/envs/utils.py`、`client/pyproject.toml`）仍是 `openpi_client`，没有改：
>   client 环境依赖 DROID fork，本地没有检出，无法重新 lock。Task 4 搭 RoboTwin 环境端时一起换。
> - 发现两处 Task 4/6 要处理的问题，没有在本任务里改：训练循环建好环境后先执行一次全零的 `example_action`，在
>   RoboTwin 的关节目标语义下会把两臂拉向零位。用户确认（2026-10-15）只要零位就是两臂的初始位置即可，Task 4 实现
>   环境端时核对 reset 后的关节状态是否为零；RTC 与 Real-Time 线路调用的 `sample_actions_with_prefix(prefix=...)`
>   在 xense-openpi 里是 RLT 的另一个同名接口，这两条线路在本分支不能用（同步版 EXPO-FT 不受影响）。

**Verification**

都在本机 CPU 上跑，不加载模型。

1. [x] learner 环境 `uv sync` 成功；`train_pi_robo.py --help` 打出全部 flag（退出码 1 是 absl 处理 `--help` 的固定
      行为）；`eval_droid_policy`、`pi05`、`train_utils`、`lerobot_utils` 都能 import
2. [x] 临时脚本用 lerobot 0.5.1 写一个假 v3.0 数据集：3 条演示（5、3、4 步），三路相机为视频、14 维 state 与 action，
      动作里编码了回合号和步号。分别以全部、`num_data=2`、`episode_indices=[2]` 读取并逐步检查。变异检查：把每个
      回合的步序倒过来，检查报出动作不对
3. [x] write-codebase-doc 路径检查：报出的条目是还没提交的两个新文件和原有的外部 checkout、占位符；改动的依赖图
      渲染正常，布局未变

**Done**

- [x] learner 进程里 `openpi.__file__` 指向 `expo_ft/agents/vla/openpi/src/openpi/__init__.py`（xense-openpi `expo-ft`
      分支 `c57caa5`），`xense_client` 来自同一 checkout 的 `packages/xense-client`
- [x] 预填出的回合数等于示教条数，每回合末步 r=1、mask=0，其余步 r=0、mask=1

### Task: RoboTwin 环境端

**Change**

- [x] 用 add-method 把 RoboTwin 登记为 `methods/robotwin`；在运行机器上按官方脚本安装并下载资产，用独立的 Python 环境
- [x] expo-ft `client/envs/robotwin_env.py` 实现环境 RPC 的六个操作：
      reset 按官方评测协议用专家筛种子；step 执行一个 14 维关节动作；成功由 `check_success` 判定，到 `step_lim` 按超时结束；
      观测为三路相机（缩放到 224）、14 维状态和任务指令；`action_type` 恒为 `policy`
- [x] `configs/task/robotwin_<task>.py` 给出环境类、相机、控制步数上限和指令

> **进展与出入（2026-10-15）：**
>
> - 已登记 `methods/robotwin`：fork `AtticusZeller/RoboTwin` 作 origin，`workspace` 从上游 `main` 的 `ea8b211` 开出，
>   只加 Agent 说明。上游已改用 XPolicyLab 做评测，环境端直接 import `envs/`，不经过 XPolicyLab。
> - 环境端的观测键沿用 Task 3 的约定（数据集特征名）；每回合指令按官方 `seen` 规则生成；`get_info_for_step` 与
>   DroidEnv 同约定（成功 r=1，done 时 mask=0）；`control_hz` 设为无穷大，仿真里 learner 不按墙钟等待。
>   机器人端的 `openpi_client` 在本任务一并换成 `xense_client` 并重新 lock（借用 pd-perry 的 DROID fork 解析依赖）；
>   `run_client` 启动时把任务配置路径转成绝对路径，因为 RoboTwinEnv 会切换工作目录。
> - 运行机器的出入：两台训练服务器的 8 张卡都被同一个预分配显存的任务占满，每张只剩约 3.9 GB。实测 RoboTwin
>   渲染（光线追踪 32 spp + OIDN 降噪，三路相机）约 +2.1 GB，两只手臂的 CuRobo 规划子进程各带一个 CUDA 上下文，合计
>   超过 3 GB，会挤掉对方任务池外的余量；渲染设置是官方数据的设置，不能降。所以环境端验证改在本地笔记本
>   （RTX 4060 8 GB）上跑，用户确认（2026-10-15）。服务器上的环境（`/root/data/atticux/robotwin`，独立 Python 3.10、
>   CuRobo、资产）已装好，渲染要把 Vulkan ICD 指向 `libEGL_nvidia.so.0`（`/root/data/atticux/vulkan/`），
>   等有空卡时供 Task 5/6 使用。
> - 系统自带的 Python 3.10 没有头文件，CuRobo 编译不过；改用 uv 管理的独立 CPython 3.10。
> - 本地环境：venv 在 `~/.venvs/robotwin`（放在 checkout 外，免得弄脏 submodule），按官方方式用 `python -m pip` 装；
>   本地 CUDA 12.1 的 nvcc 不支持系统的 gcc 13，CuRobo 用 conda-forge 的 g++ 12（`~/.venvs/gcc12`）作宿主编译器。
>   资产只取 `beat_block_hammer` 用到的 `embodiments/aloha-agilex`、`objects/020_hammer`，加 import 时就要读的
>   `objects/same.json`、`objects/objaverse/list.json`；Easy 档不开随机背景，不需要 `background_texture`。
>   环境端还要 `ml-collections`（任务配置用 `ConfigDict`）。
> - `example_action` 改为复位姿态：复位后的关节读数是两臂 0、两夹爪 1（张开），全零会让夹爪在训练开始的第一步合上。
>   用户此前确认零位即初始位置可以接受（2026-10-15），实测发现夹爪不是 0，改成复位姿态后第一步不动。

**Verification**

1. [x] `scripts/test_render.py`：本地与服务器都输出 Render Well（服务器要用上面的 EGL ICD）
2. [x] 本地 RTX 4060：临时脚本在专家 `play_once` 时记下每个保存帧的 14 维关节状态（与数据转换里
      `action[t] = state[t+1]` 同一取法），再经 `RoboTwinEnv.reset` 到同一种子，用 `step` 逐帧回放。对照：同一种子
      保持复位姿态同样步数。另跑一次 RPC 冒烟：learner 侧 `EnvClientWrapper` 经 `run_client` 驱动 RoboTwinEnv，
      依次 create_env、reset、step（`example_action`）、get_observation、get_info_for_step、render

**Done**

- [x] 渲染检查出图：头部相机看到方块和锤子，三路图像 224×224 uint8
- [x] 回放专家动作经过环境端后 `check_success` 为真：种子 100000，专家 113 帧，回放到第 107 步成功（r=1、mask=0、
      done），每步约 0.036 s；对照组 112 步未成功。RPC 冒烟中观测键与数据集一致、prompt 为每回合生成的指令，
      `example_action` 执行后关节状态不变。这一条同时锁住动作语义：数据里的 action 与环境端执行的是同一种
      关节目标

### Task: SFT 基座落在 30–60%

**Change**

- [x] 下载官方 v3.0 数据，取 `beat_block_hammer` 的 50 条 clean 示教；若是多任务合并的数据集，按 task 过滤
- [x] xense-openpi 加 RoboTwin 的 data config 与 YAML：π₀.₅，`gemma_2b_lora` + `gemma_300m_lora`，三路相机，14 维；
      H=16，与规格的参考配置一致（RoboTwin 常见的是 50，起点会因此变化，靠选 checkpoint 补偿）；计算 norm stats
- [ ] 按规格的 SFT 配方训练约 4,000 步（batch 64，学习率 2.5e-5），每 500 步存一次
- [ ] 用环境端加 `eval_droid_policy.py --only_base_actions` 在 Easy 档各评 100 次，挑一个落在 30–60% 的 checkpoint。
      如果都高于 60%，先减示教条数；仍不行就换 `click_bell`，并回来报告

> **进展与出入（2026-10-15）：**
>
> - 数据没有用 4.1 GB 的多任务 v3.0 合并包，改取单任务原始数据 `dataset/beat_block_hammer/aloha-agilex_clean_50.zip`
>   （229 MB，正好是 Easy 的 50 条示教，种子 0–67，与评测种子 100000 起不重叠），用 expo-ft 新增的
>   `scripts/convert_robotwin_to_lerobot.py` 转成 v3.0：规则同 XPolicyLab 的转换（`action[t]` 取第 t+1 帧关节、
>   `decode_image_bit` 解码、每条示教取一句 `seen` 指令作 task，fps 15）。两处不同：相机帧存图像而非视频，训练机的
>   venv 没有 FFmpeg 动态库；动作列叫 `actions`，与 replay 插入的键一致，这样一份 data config 同时管 SFT 和 replay。
>   结果 50 条、5682 帧，首帧与仿真渲染颜色一致，初始状态为两臂 0、夹爪 1。
> - data config 直接用 `LeRobotAlohaDataConfig`，与 RoboTwin 官方 π₀.₅ 基线相同：`adapt_to_pi=false`，关节 delta、夹爪
>   绝对值。它的输入变换要 CHW 图像，所以 Task 3 的预填与 Task 4 的环境端改为发 CHW uint8（原为 HWC）。YAML 是
>   xense-openpi `configs/_examples/pi05_robotwin_beat_block_hammer_lora.yaml`；恒定学习率用 `CosineDecaySchedule`
>   在 `warmup_steps=0`、`peak_lr = decay_lr` 时表达。norm stats 已算好。
> - 训练机：两台训练服务器白天被一个 8 卡任务占满（预计 10-16 0:20 左右结束）。用户同意在凌晨无人训练时训练
>   （2026-10-15）。`xense-training-h100` 上的 tmux `atticux-night-sft` 从 02:00 起每 30 s 查一次，某张卡连续 10 分钟
>   显存低于 1 GB 且利用率为 0 才在这张卡上启动 SFT；到 03:30 仍没有就不训练。checkpoint 与日志在
>   `/root/data/atticux/agent-workspace/expo-ft/` 下。启动前在 CPU 上跑过 2 步（batch 2），数据、权重加载、LoRA
>   冻结与存 checkpoint 都通。
> - 后续调整（2026-10-15，用户确认）：空闲卡有几张就用几张训练（取能整除 batch 64 的 8/4/2/1 张）；训练完在同一批卡上
>   每卡一个 checkpoint 并行评测，每个 checkpoint 先评 20 次，之后再决定对候选补评；W&B 用用户账号、entity
>   `atticux`、项目 `expo-ft`（key 从用户工作站的登录写入服务器上仅 root 可读的文件，只导入训练进程）。
> - CPU 上的 SFT 训练步不可靠：同一命令重复 7 次，只有第一次正常（`param_norm` 1803），其余为 NaN、2e17 或中途崩溃；
>   关闭 XLA CPU 的 thunk runtime 则编译即断言失败。同一 CPU 上初始化重复 6 次都是 1803.249，与 donate 无关，
>   DataLoader worker 数也不影响。判断是 XLA CPU 后端的问题，GPU 训练用同一 `train.py`（其他人的任务在跑）；
>   这是推断，夜里第一步会验证：夜间脚本在第 0 步 `param_norm` 偏离 1803.25 超过 5 或 loss 非有限时立即终止。
> - 评测链路已端到端跑通：learner 侧 `eval_droid_policy.py --only_base_actions` 在服务器 CPU、RoboTwin 环境端在本地
>   GPU，经 SSH 隧道连通，跑完 24 步并输出成功率。途中修了 expo-ft `process_raw_inputs` 的假动作缺时间维
>   （`DeltaActions` 要 (T, D)）；环境端只拨号一次，评测脚本因此先起 learner、监听后再起环境端。

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
