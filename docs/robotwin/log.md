# RoboTwin Log

## 2026-10-15 · 接入 RoboTwin 2.0

- **背景与目的：** EXPO-FT 的仿真复现选用 RoboTwin 2.0 作环境（见 [expo-ft/plan.md](../expo-ft/plan.md)）。
- **实现思路：** fork `AtticusZeller/RoboTwin` 作 origin，官方 `RoboTwin-Platform/RoboTwin` 作 upstream；`workspace`
  分支从上游 `main` 的 `ea8b211` 开出，只加了 Agent 说明。嵌套 submodule `XPolicyLab` 固定在上游登记的 `fa431ec`。
- **组件变化：** 新增 `methods/robotwin`，登记到 `scripts/lab.py` 与 README。
- **主要文件：** `methods/robotwin/AGENTS.md`。
- **验证：** submodule 递归初始化成功；`./lab method status` 显示 `robotwin` 在 `workspace`。
