# EXPO-FT Log

## 2026-10-18 · RoboTwin 单任务上跑通 EXPO-FT（事务完成）

- **背景与目的：** [expo-ft-spec.md](../xense-openpi/expo-ft-spec.md) 4.4 复现路线的第一步：仿真、无人工介入、按参考实现
  联合更新，在 `beat_block_hammer`（Easy）上把代码调通，并看 RL 能否把成功率推到 SFT 基座之上。
- **实现思路：** 2026-10-15 至 10-16 接好 learner（xense-openpi）、RoboTwin 环境端、数据转换与 replay 预填，修掉动作还原、
  replay 回填、恢复与显存布局的问题（见下面各条）；调试只用一个固定种子，超参取参考默认，β=0.05。
- **组件变化：** 这一事务的代码都在 expo-ft `robotwin-sim`（`40127b5` 至 `77cb999`）。
- **主要文件：** 见 [codebase.md](codebase.md)。
- **验证：** 用户结论（2026-10-18）：代码通过，原算法有效。固定种子上 15k 基座（官方协议 72%）更新前 6/10、最近 50 回合
  49/50；约 7k 基座（31%）1/10 → 46/50；20 回合滑动成功率首次到 90% 分别用 3.2 h 与 4.2 h。证据边界：单任务、单种子、
  在线训练回合、每个基座一次（[experiments.md](experiments.md)）。
  暂缓的“1 万步基座落在 40% 左右”Task 取消（用户决定 2026-10-18：31% 的基座已证明能拉上去）。

## 2026-10-18 · 第二台训练机、并行 RL、单次尝试判定与 checkpoint 上限

- **背景与目的：** `xense-training-h100` 被占满时改用 `02-xense-training`，并在一台 8 卡机上同时跑两个基座；RL 的 agent
  checkpoint 把共享盘吃得太快；训练数据要只含一次成功的轨迹（用户 2026-10-18）。
- **实现思路：**
  - 02 的容器只注入了 NVIDIA 计算库，缺 EGL/GLX、glcore、rtcore 等图形库，RoboTwin 光线追踪渲染起不来。Codex 把
    h100 上同版本（580.65.06）的这些库复制到共享盘，环境端靠 `LD_LIBRARY_PATH` 加载，不改系统目录与原 ICD。
  - `rl_joint.sh` 新增可覆盖的 `PORT` 与 `N_EDIT`，两次运行用不同端口；W&B 汇总改用 `rl_status.sh`（替换 `rl_episodes.sh`），
    多给每 10 回合成功率与 critic 走势。
  - `initialize_checkpoint_dir` 与 `train_pi_robo.py` 加 `max_to_keep`（默认 100 不变），`rl_joint.sh` 只留最新两份。
  - 单次尝试判定（用户在本机写）：RoboTwin 原协议允许没打中后重试到 `step_lim`；`HammerStrikeJudge` 按锤头相对木块的
    高度判断第一次落锤，没成功就结束回合、记失败。`ROBOTWIN_SINGLE_ATTEMPT` 默认 1，训练与评测都用；0 回到官方协议。
- **组件变化：** expo-ft `e0aba36`（判定）、`c408f62`（checkpoint 上限）、`2be2105`（启动与汇总脚本）；共享盘新增
  `/root/data/atticux/nvidia-gl-580.65.06/` 与 `vulkan/nvidia_icd_egl_02.json`。
- **主要文件：** `client/envs/robotwin_attempts.py`（判定）、`expo_ft/agents/alg/agent.py`（保留份数）、
  `scripts/robotwin/{rl_joint,rl_status}.sh`。
- **验证：**
  - 02：复制的 10 个库与源文件 SHA-256 一致；环境端三路图像正常，进程加载的是新目录的 rtcore 与 glvkspirv；1 + 4 与
    1 + 2 两种布局都跑过 update、无 OOM，随后两次 RL 并行跑了 11 h 以上。
  - `max_to_keep=2`：临时目录里存 4 个 checkpoint，只剩最新两份。
  - `rl_status.sh` 在两次运行中的 W&B 上输出分段成功率与 Q 走势。
  - 判定：编译通过，引用的 `hammer`、`block` 与功能点在 RoboTwin 任务里存在；阈值取自用户会话里的专家回放测量，
    Agent 没有在仿真里跑过这个判定。

## 2026-10-16 · 联合更新的显存布局拆开、单场景调试开关

- **背景与目的：** 夜里的联合更新在 GPU 0 上 OOM。按用户决定，推理卡和训练卡分开；调试 RL 只用单一场景，省掉每回合
  换种子时的专家预跑。
- **实现思路：**
  - 显存布局：同步入口 `train_pi_robo.py` 原来让所有卡组成数据并行 mesh，推理又固定在 `jax.devices()[0]`，GPU 0 多放一整份
    推理副本。改为与 `train_pi_robo_async.py` 相同：有 2 张卡及以上时 mesh 只用 `jax.devices()[1:]`，第一张卡只推理并跑
    环境端（单卡时仍用全部）。
  - 预取 batch：回放采样里的 `jnp.asarray` 和图像转 float32 原本落在默认设备 GPU 0，预取队列加在用批次约 45 GB。取 batch
    的线程改在 CPU 默认设备上执行，`apply_data_sharding` 再把它直接发到更新卡。
  - 单场景：环境端 `ROBOTWIN_FIXED_SEED=1` 时，`RoboTwinEnv.reset` 记住第一个专家能做成的种子与对应指令，之后每回合直接用它
    搭场景；不设时仍按官方协议逐个换种子。
  - 启动脚本：`rl_joint.sh` 的第一张卡做推理与环境端；`night_run.sh` 给 RL 取 1 + 4 张卡（只有 4 张时 1 + 2）。
- **组件变化：** expo-ft `robotwin-sim` 新增 `e0b363b`（显存布局与取 batch）、`77cb999`（固定种子）。
- **主要文件：** `train_pi_robo.py`（mesh 与取 batch 线程）、`client/envs/robotwin_env.py`（固定种子）、
  `configs/task/robotwin_beat_block_hammer.py`（开关）、`scripts/robotwin/{rl_joint,night_run}.sh`。
- **验证：**
  - 显存：15k 基座、β=0.05、全新启动（夜里 OOM 的场景），关掉预分配。只拆卡时 GPU 0 峰值 72.9 GB，第二轮 update 已回到
    7.4 s/次；加上 CPU 取 batch 后（`smoke_layout_split2`）3 轮 update 无 OOM，GPU 0 峰值 39.6 GB，更新卡各 68.4 GB
    （`MEM_FRACTION=0.85` 的上限，实际需求未测）。
  - 单场景：连续 3 次 reset 的种子、指令与初始状态相同，耗时 62.5 s、23.5 s、23.4 s。
  - `train_pi_robo.py` 的 ruff 报错数与改动前相同（19 条，均为原有）。

## 2026-10-16 · RoboTwin 夜间运行：动作还原与 replay 修正、GPU 上跑通 SFT 与联合更新

- **背景与目的：** 第一次在 `xense-training-h100` 的 GPU 上跑 [plan.md](plan.md) 的 SFT → 基座评测 → 联合更新。夜里暴露的
  问题按用户授权就地排查修复；结果见 [experiments.md](experiments.md)。
- **实现思路：**
  - 动作还原：`process_transformed_outputs` 原先给输出变换一个全零 state，`Unnormalize` 把它还原成状态区间中值，
    `AbsoluteActions` 加回的是假状态，增量动作配置下机械臂被拉向固定姿态（评测全部 400 步失败）。改为记下最近一次
    `process_raw_inputs` 的归一化 state 交给输出变换。DROID 配置没有增量动作，参考实现里不暴露。
  - replay 回填：`insert` 把新动作按当前行的 state 转成增量后，原样填进前 H−1 行的动作块；那些块应相对各自的首个 state。
    按两行归一化 state 之差乘每维 `scale_state/scale_action`（从 `DeltaActions` mask 与 norm stats 推出）修正。
  - 恢复：orbax 恢复出的数组固定在单卡，update 的 jit 拒绝与复制的 rng 混用；恢复后把单卡叶子复制到全部设备。
  - 启动脚本：`night_run.sh` 只保留最新 checkpoint、DataLoader worker 8→32、日志行带时间戳故护栏 grep 去掉 `^`，加
    `TRAIN_MODE`（续训）、`SKIP_TRAIN`（只评测与 RL）、`NO_RL`、`EXTRA_TRAIN_ARGS`、低于 30% 交接与定时停；从 checkout 调用
    同目录脚本。`rl_joint.sh` 加 `ENV_GPU`、`MEM_FRACTION`、`EDIT_SCALE`；新增完整策略评测 `eval_full_policy.sh` 与从 W&B
    读回合结果的 `rl_episodes.sh`。
  - 环境：服务器 RoboTwin venv 补装 `ml-collections`（任务配置在环境端导入它，本地装过、服务器漏装）。
- **组件变化：** expo-ft `robotwin-sim` 新增 `40127b5`、`75bc4b3`、`54a64b5`、`2a5a1e8`、`bbd07c2`。
- **主要文件：** `expo_ft/agents/vla/pi05.py`（输出变换的 state）、`expo_ft/data/replay_buffer.py`（回填修正）、
  `train_pi_robo.py`（恢复后复制）、`scripts/robotwin/`（启动与诊断脚本）。
- **验证：**
  - 动作还原：数据集一帧经输入、输出变换往返，最大误差 3e-17（零 state 时 1.35）；修复后 15k 基座评测第一回合 8/8 成功。
  - replay：服务器隔离副本上把示教第 0 条插入 buffer，5 个位置的动作块与按真实首帧 state 变换的真值比对，最大误差 2e-7
    （修复前 1.91）。
  - 恢复：同一 checkpoint 续跑后第一轮 3 次 update 完成，无设备错误。
  - GPU 上 SFT：第 0 步 `param_norm` 1803.86，与 1803.25 相差 0.6，loss 有限；CPU 上的参数损坏没有在 GPU 复现。32 worker
    时 8 卡每步 0.41 s（8 worker 时 1.18 s，受 CPU 解码限制）。
  - 夜间遇到的其他情况：checkpoint 存于 4 卡时在 2 卡上 `--resume` 报 sharding 为 None，改用权重初始化新实验；`pgrep -f`
    会匹配到 ssh 自身的命令行，只按明确 PID 停进程；正在执行的 bash 脚本不能原地改写。

## 2026-10-15 · expo-ft 接上 xense-openpi 与 RoboTwin 仿真

- **背景与目的：** 按 [expo-ft-spec.md](../xense-openpi/expo-ft-spec.md) 4.4 的复现路线，先在 RoboTwin 仿真单任务上跑
  EXPO-FT（[plan.md](plan.md)）。这一步把 learner、数据和环境端都接通，为 SFT 与在线 RL 做准备。
- **实现思路：**
  - 分支 `robotwin-sim`：先合并上游 `21fe3d3` 的奖励对齐修正（上游是无共同祖先的根提交，用
    `--allow-unrelated-histories`，冲突取上游）。
  - learner 的独立 checkout 换成 xense-openpi `expo-ft` 分支，客户端包改为 `xense_client`；Python 升到 3.12，去掉给旧
    lerobot 的 `datasets<4` override，锁定后关键依赖与 xense-openpi 同版本。`get_config` 不再传 `weight_loader_path`。
  - RoboTwin：环境端 `RoboTwinEnv` 按官方评测协议用专家筛种子、每回合按 `seen` 规则生成指令、`check_success` 或
    `step_lim` 结束；观测键与数据集特征名一致、图像 CHW uint8。任务的 `example_action` 是复位姿态（两臂 0、夹爪 1），
    训练循环开头那一步不动。`run_client` 启动时把任务配置转成绝对路径（环境会切换工作目录）。
  - 数据：`convert_robotwin_to_lerobot.py` 把官方每回合 HDF5 转成 LeRobot v3.0（`action[t]` 取下一帧关节、官方
    `decode_image_bit` 解码、动作列 `actions`、存图像）；`lerobot_utils.process_lerobot_dataset` 把它预填进 replay，
    每条示教一个成功回合（末步 r=1、mask=0）。
  - 推理时塞给输入变换的假动作补上时间维（`DeltaActions` 需要）。
- **组件变化：** 新增 `client/envs/robotwin_env.py`、`configs/task/robotwin_{base,beat_block_hammer}.py`、
  `expo_ft/env/lerobot_utils.py`、`scripts/convert_robotwin_to_lerobot.py`、`scripts/robotwin/`（夜间训练、评测、RL 启动）；
  训练与评测入口接受 `env_type == "robotwin"`。
- **主要文件：** 见 [codebase.md](codebase.md) 的文件地图与已知耦合。
- **验证：**
  - 奖励对齐：桩掉 `expo_ft.agents` 驱动 `EpisodeSink`，成功回合 rewards `[0,0,0,0,1]`、masks `[1,1,1,1,0]`，超时回合全 0；
    变异检查能报出未打标签的 transition。
  - learner 环境 `uv sync`、`train_pi_robo.py --help`，进程内 `openpi.__file__` 指向 xense-openpi checkout。
  - 假 RoboTwin 原始数据经转换与预填逐步核对：动作取下一帧、末步标签、CHW、颜色无通道互换。真实数据 50 条 5682 帧，
    首帧颜色与仿真渲染一致。
  - 环境端（本地 RTX 4060）：渲染检查通过；专家关节目标经环境端回放第 107 步成功，同种子保持复位 112 步不成功；
    learner 侧 `EnvClientWrapper` 经 `run_client` 走通 create、reset、step、observe、判定、render。
  - 评测链路：服务器 CPU 上的 `eval_droid_policy.py --only_base_actions` 与本地环境端经 SSH 隧道跑完一回合并输出成功率。

## 2026-09-29 · 接入 EXPO-FT 框架

- **背景与目的：** 将 EXPO-FT 与 Real-Time EXPO-FT 作为现役 VLA 强化学习微调框架接入工作区。
- **实现思路：** 从上游当前 `main` 建立个人 fork 的 `workspace` 分支，保留 fork 原有历史，并固定已推送的 method revision；训练依赖和实验事务留待具体任务。
- **组件变化：** 新增 `methods/expo-ft` 及 method 专属 Agent 指引，登记上游和分支。
- **主要文件：** `methods/expo-ft/AGENTS.md` 约束 method 内工作；`docs/expo-ft/overview.md` 记录系统组成与验证边界。
- **验证：** 确认 fork 的 `workspace` 远端 revision 与 gitlink 一致，新 submodule 可递归初始化；当前 `main` 工作树中 `lab method status`、根仓 43 项测试、配置校验、ruff 和 ty 检查通过。
