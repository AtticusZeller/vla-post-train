# Workspace 概览
## 定位

这是一个由研究者设定边界、Agent 负责实现与验证的研究工作区，覆盖 VLA、WAM、Agent
及相关具身智能方向。根仓库只承担 method 接入、文档和证据管理；算法、框架、
benchmark 与复现代码保留在独立的 `methods/*` submodule 中。

当前登记六个 method：LeRobot、lerobot-xense、xense-openpi、TacXense、EXPO-FT 与 RoboTwin。
它们不是一套统一算法栈：LeRobot 提供通用机器人学习框架，Xense 三个仓库分别覆盖真机
数据/控制、模型/推理和触觉 VLA 模型，EXPO-FT 提供 VLA 强化学习微调框架，RoboTwin 是
双臂仿真 benchmark。

## 实验与证据

根仓不含启动器或脚本（2026-11-10 移除）。实验由各 method 自己的命令启动；method 仅被接入不代表
环境、训练、推理或评测已经验证。

大型日志、checkpoint、视频和数据写入 `/mnt/data/atticux/agent-workspace/`。本地退出码与
traceback 优先于跟踪服务表面状态；smoke 只证明工程链路，不能代替正式算法结论。

## 文档边界

`docs/workspace/` 记录跨 method 的计划、变更与稳定机制；`docs/<method>/` 记录对应方法的
计划、变更和高层理解。过程历史留在 Git，不在现役文档里维护第二份流水账。
