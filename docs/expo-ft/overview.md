# EXPO-FT 概览

EXPO-FT 与 Real-Time EXPO-FT 是面向 VLA 的强化学习微调框架。前者研究样本效率；
后者把推理延迟、动作块前缀和执行时的快速编辑策略纳入实时控制流程。当前仓库以
DROID 任务和 pi0.5 为示例，提供训练、采样、评估及对应配置。

系统分为 learner 和 actor：learner 在服务器侧训练并通过 WebSocket 与 actor 通信；
actor 在机器人侧采集观测、执行动作。两侧使用独立的 Python 环境。运行前还需按上游
README 克隆匹配分支的 OpenPI 与 DROID fork；它们不是本 submodule 内的嵌套 submodule。
启动入口、文件职责与模块交互见 [codebase.md](codebase.md)。

`robotwin-sim` 分支把 learner 接到 xense-openpi，并加了 RoboTwin 2.0 仿真环境端：仿真进程在
RoboTwin 自己的环境里跑，作为另一个 actor 经同一协议被 learner 逐步驱动；观测键与 LeRobot
数据集一致，SFT 与 replay 共用一份 openpi data config。

验证边界（2026-10-19）：仿真上 SFT、基座评测与同步联合更新都已跑通。`beat_block_hammer` 单任务 15k 步 LoRA 基座
（官方协议 72%）在固定种子与随机种子上都能被 RL 拉到 80–90%，步数上限 150 时固定种子 1.8 h 到 90%；10 任务联训 LoRA 在
Easy 上 8 个任务 ≥80%，下一步在 Hard 场景上做 RL（见 [experiments.md](experiments.md) 与 [plan.md](plan.md)）。证据边界：
单任务、每个设定一次运行。没有真机记录。

## 长期方向

用户 2026-10-18 提出，未排期；baseline 跑出来之后再逐步安排。

- 最终回到真机。真机侧不放大算力去微调参数：VLA 的训练在云端做，在线推理与在线 RL 在推理机上做。
- LoRA（π₀.₅ 参数）的更新希望放到离线做，在线只做 RL。理由（用户判断）：原方法对 π₀.₅ 参数的改动本来就很小（10-18 两次
  运行约 500 回合后参数范数只变 0.04）。这就是 spec 里的分离更新（[expo-ft-spec.md §4.4](../xense-openpi/expo-ft-spec.md)）。
- 第一个消融：不更新 LoRA，只更新 critic 与编辑策略（分离更新的 M=∞，即原文 Fig. 6 的冻结设置），看参数更新影响多少成功率。
  在这个前提下，用户自己的方法大概率用同步版本。
- 冻结 checkpoint、多台机器共享 learner 来攒编辑策略的数据，往后搁置：真机最终是“跑一回合、更新一次”（用户判断）。
- 可做的消融：编辑策略更新后，新参数在回合结束时换上，还是在动作块级别换上。
