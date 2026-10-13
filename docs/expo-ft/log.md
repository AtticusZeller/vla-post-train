# EXPO-FT Log

## 2026-09-29 · 接入 EXPO-FT 框架

- **背景与目的：** 将 EXPO-FT 与 Real-Time EXPO-FT 作为现役 VLA 强化学习微调框架接入工作区。
- **实现思路：** 从上游当前 `main` 建立个人 fork 的 `workspace` 分支，保留 fork 原有历史，并固定已推送的 method revision；训练依赖和实验事务留待具体任务。
- **组件变化：** 新增 `methods/expo-ft` 及 method 专属 Agent 指引，登记上游和分支。
- **主要文件：** `methods/expo-ft/AGENTS.md` 约束 method 内工作；`docs/expo-ft/overview.md` 记录系统组成与验证边界。
- **验证：** 确认 fork 的 `workspace` 远端 revision 与 gitlink 一致，新 submodule 可递归初始化；当前 `main` 工作树中 `lab method status`、根仓 43 项测试、配置校验、ruff 和 ty 检查通过。
