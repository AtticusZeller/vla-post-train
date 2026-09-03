# FastWAM 概览
## 定位

FastWAM 是 Fast-WAM 的官方实现，用 Wan2.2 视频骨干与 ActionDiT 动作头研究一个核心问题：
测试时是否必须先生成未来视频，还是可以直接从当前观测预测动作。它同时提供带 IDM 想象、
first-frame 直接动作以及联合/可选条件等变体，主要面向 LIBERO 与 RoboTwin。

## 非显然边界

- 评测 checkpoint 与 action scheduler 的 `sigma shift` 必须配套；早期 checkpoint 使用的
  shift 与当前默认值不同，结果比较不能忽略这一条件。
- RoboTwin 的 seen/unseen instruction 设置会影响结果，成功率必须与 instruction type 一起解释。
- 仓库内包含若干 vendored 数据与评测实现，它们不是根工作区 LeRobot submodule 的同一份代码。

## 证据边界

当前工作区只固定了源码版本，尚未建立 FastWAM 实验配置，也没有本地训练或评测证据。
论文与 upstream 报告的成功率只能视为上游声明，不能写成本工作区复现结果。
