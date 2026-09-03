# Workspace 概览
## 定位

这是一个由研究者设定边界、Agent 负责实现与验证的研究工作区，覆盖 VLA、WAM、Agent
及相关具身智能方向。根仓库只承担 method 接入、实验编排、文档和证据管理；算法、框架、
benchmark 与复现代码保留在独立的 `methods/*` submodule 中。

当前登记五个 method：LeRobot、lerobot-xense、xense-openpi、FastWAM 与 TacWAM。它们不是
一套统一算法栈：LeRobot 提供通用机器人学习框架，Xense 两个 fork 分别覆盖真机数据/控制
和模型/推理，FastWAM 与 TacWAM 属于 WAM 研究线。

## 实验与证据

根工具保留通用的 YAML 校验、启动、运行记录、监控和报告能力。只有形成具体实验事务时才
创建 `experiments/<method>/`；method 仅被接入不代表环境、训练、推理或评测已经验证。

实验信息流为：完整 YAML 配置解析为 method 原生进程，运行元数据留在根仓库，大型日志、
checkpoint、视频和数据写入 `/mnt/data/atticux/agent-workspace/`。本地退出码与 traceback
优先于跟踪服务表面状态；smoke 只证明工程链路，不能代替正式算法结论。

## 文档边界

`docs/workspace/` 记录跨 method 的计划、变更与稳定机制；`docs/<method>/` 记录对应方法的
计划、变更和高层理解。过程历史留在 Git，不在现役文档里维护第二份流水账。
