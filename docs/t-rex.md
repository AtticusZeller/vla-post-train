# T-Rex 模块

## 角色

`methods/t-rex/` 是 T-Rex（Tactile-Reactive Dexterous Manipulation）官方实现的 fork，
在根仓库中作为 `method` 管理。父仓库只记录 submodule revision、实验意图和运行证据，
不复制 T-Rex 的训练实现或依赖。

## 当前固定版本

- fork：`https://github.com/AtticusZeller/T-Rex.git`
- upstream：`https://github.com/ZhuoyangLiu2005/T-Rex.git`
- 分支：`workspace`
- 基线：官方 `main`，当前集成提交由 fork 的仓库指导文件提交组成

官方仓库的 `main` 分支提供 post-training 与 inference；`full-pipeline` 分支包含
pretraining 与 midtraining 代码。T-Rex 使用 Qwen3-VL-2B、异步 Mixture-of-Transformers
和 temporal tactile VQ-VAE，并提供 LeRobot v3 数据读取路径。

## 边界

当前只完成仓库接入，没有创建 `experiments/t-rex/`、runbook、launcher 或训练配置。
后续运行前必须阅读 `methods/t-rex/README.md` 与其方法级 `AGENTS.md`，并明确数据、模型
checkpoint、GPU 和真实机器人验证范围。
