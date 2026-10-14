# EXPO-FT 概览

EXPO-FT 与 Real-Time EXPO-FT 是面向 VLA 的强化学习微调框架。前者研究样本效率；
后者把推理延迟、动作块前缀和执行时的快速编辑策略纳入实时控制流程。当前仓库以
DROID 任务和 pi0.5 为示例，提供训练、采样、评估及对应配置。

系统分为 learner 和 actor：learner 在服务器侧训练并通过 WebSocket 与 actor 通信；
actor 在机器人侧采集观测、执行动作。两侧使用独立的 Python 环境。运行前还需按上游
README 克隆匹配分支的 OpenPI 与 DROID fork；它们不是本 submodule 内的嵌套 submodule。
启动入口、文件职责与模块交互见 [codebase.md](codebase.md)。

工作区仅接入并固定源码版本。当前没有 EXPO-FT 实验配置、Xense 适配、训练运行、
checkpoint 评估或真机验证记录。
