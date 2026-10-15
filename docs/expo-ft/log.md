# EXPO-FT Log

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
