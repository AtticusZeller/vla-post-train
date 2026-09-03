# lerobot-xense 概览
## 定位

lerobot-xense 是 Xense 真机侧的 LeRobot fork，负责机械臂与夹爪控制、遥操作、触觉相机、
recipe 化配置和数据采集。模型训练、策略服务与推理客户端属于 `xense-openpi`；两边通过
LeRobotDataset 和约定的数据字段衔接。

## 关键设计

- 硬件 SDK 以嵌套 submodule 或 Python 包提供，可按硬件族选择性安装；未安装的设备应在实例化
  时失败，而不应阻塞核心包和无关设备。
- 夹爪是与 robot、camera 平级的设备抽象，robot 只依赖位置/状态等小接口，不绑定具体夹爪。
- recipe 描述一套可复用的硬件组合与标定关系。运行时覆盖规则必须由具体 CLI 说明，不能假设
  所有入口具有相同优先级。
- Xense camera 只整理 SDK 已提供的图像、深度、marker、力和网格等模态；图像到力或深度的
  推理属于 SDK，不在 LeRobot 封装中重新实现。数组 shape 应以设备和运行时结果为准。

## 数据与接口边界

触觉、相机、robot state 和 action 最终作为 LeRobotDataset feature 写入。不同 robot/夹爪
组合会产生不同维度，消费侧应依据 dataset schema，而不是硬编码某个 bench 的列宽。

该方法与 xense-openpi 共享运行环境，是根仓“method 环境通常隔离”规则的明确例外。两个仓库
各自可能保存 recipe 副本，部署前必须确认使用的是同一 bench 语义。

## 证据边界

当前工作区固定了源码与嵌套依赖，但没有根级实验配置和运行记录，也没有在本机完成整套硬件
安装与真机验证。
