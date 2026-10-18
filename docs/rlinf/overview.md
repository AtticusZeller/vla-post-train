# RLinf 概览

RLinf 是面向具身与智能体强化学习的训练基础设施（Apache-2.0）。本工作区目前只把它当参考：调研并迁移它接 RoboTwin
的环境端做法到 EXPO-FT；它的训练栈（learner、调度）不在当前范围内。

- **RoboTwin 接入位置：** `rlinf/envs/sim/robotwin/robotwin_env.py`，环境注册在 `rlinf/envs/__init__.py`。
- **证据边界：** 只做了接入，没有安装依赖、运行或读懂实现；场景复用与多环境并行的具体机制待调研。
