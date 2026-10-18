# RLinf Log

## 2026-10-18 · 接入 RLinf

- **背景与目的：** EXPO-FT 在 RoboTwin 上的采样慢在仿真侧；用户决定借 RLinf 接 RoboTwin 的环境端做法（复用场景、
  多环境并行），learner 仍用 expo-ft（见 [expo-ft/plan.md](../expo-ft/plan.md)）。
- **实现思路：** fork `AtticusZeller/RLinf` 作 origin，官方 `RLinf/RLinf` 作 upstream；fork 原有分支不动，新开
  `workspace` 分支，指向上游 `main` 的 `a78b6d7`，没有改动。上游自带 `AGENTS.md`、`CLAUDE.md`，保留。
- **组件变化：** 新增 `methods/rlinf`，登记到 `scripts/lab.py` 与 README。
- **主要文件：** `methods/rlinf/rlinf/envs/sim/robotwin/robotwin_env.py`（RoboTwin 环境封装，待调研）。
- **验证：** `./lab method status` 显示 `rlinf` 在 `workspace`、`a78b6d7`、干净，origin 与 upstream 如上；无嵌套 submodule。
