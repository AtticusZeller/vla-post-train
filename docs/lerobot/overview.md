# LeRobot 概览
## 定位

该 submodule 是工作区使用的通用 LeRobot 框架，负责数据集、策略、训练、机器人接口与 rollout
基础设施。Xense 真机扩展保留在独立的 `lerobot-xense`，两者不能互相替代。

## Rollout 与动作 chunk

Base strategy 下的 sync inference 会完整消费本地 action chunk 后再推理，没有“按剩余比例
提前重规划”的语义。需要基于新观测提前重规划时，应使用 rollout 体系中的 RTC inference；
它是独立的异步后端，而不是 sync 的一个阈值选项。

`async_inference/` 又是另一套独立的远程异步推理链路。客户端会在动作队列低于阈值时提前请求
新 chunk，并按 timestep 丢弃过期动作、融合重叠动作、接纳纯未来动作。它不能与 rollout
中的 RTC engine 混为同一实现。

## 数据边界

Strategy、inference engine、组帧和动作重排属于 policy 无关的共用骨架；processor pipeline
与 action chunk 生成属于模型专属层。Base strategy 本身不写入 rollout dataset，若需要采集
数据必须选择具有数据记录语义的 strategy。
