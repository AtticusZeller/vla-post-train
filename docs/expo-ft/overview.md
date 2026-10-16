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

验证边界（2026-10-16）：SFT、基座评测和联合更新都已在 GPU 上跑通；`beat_block_hammer` 上 15k 步 LoRA 基座 72%，
联合更新的显存布局与编辑幅度仍待讨论（见 [experiments.md](experiments.md) 与 [plan.md](plan.md)）。没有真机记录。
