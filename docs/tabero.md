# Tabero 模块

## 角色

`methods/tabero/` 是 Tabero tactile foundation model / benchmark 官方实现的 fork，
在根仓库中作为 `method` 管理。它包含 Isaac Lab 触觉环境、数据转换、评测工具和 OpenPI
推理客户端；训练代码维护在配套的 `Tabero-VTLA` 仓库中。

## 当前固定版本

- fork：`https://github.com/AtticusZeller/Tabero.git`
- upstream：`https://github.com/NathanWu7/Tabero.git`
- 分支：`workspace`
- revision：`1ad2078d25a7106084b9c2f247217c3f5be801e8`
- upstream 默认分支：`main`
- 协议：Apache-2.0（GitHub 仓库元数据）

Tabero 的环境依赖 Isaac Sim 5.0+、Isaac Lab 2.2+、Python 3.10+ 和 CUDA 12.0+。
论文协议包含 gentle/firm 语言条件下的成功率与接触力指标；不同 Isaac Sim/Isaac Lab
版本的力传感器绑定可能改变结果，不能直接把 smoke 结果当作论文复现结论。

## 边界

本次只完成仓库接入，没有创建 `experiments/tabero/`、runbook、launcher 或训练配置。
后续运行前必须阅读 `methods/tabero/README.md` 与其方法级 `AGENTS.md`，并单独确认
Isaac Sim/Isaac Lab 版本、GPU、LIBERO 数据和触觉标定资产。
