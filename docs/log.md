# Development Log

> 已验证完成的任务记录。最新的在最上面。

<!-- 每个任务通过全部必要验证后，在本行下方追加一条 -->

## 2026-07-27：建立首期研究工作区

- 创建 Python 3.12 + uv 根环境和四个 HTTPS submodule。
- 使用 `init-repo-agents` 更新根与四个 method 的协作基线；method 更新已检查、提交并推送。
- 实现 schema v1、稳定 CLI、三个专用 launcher、前台进程记录、W&B/local summary 和
  report 标记表格更新。
- 迁移 FlowDAgger 4 条、DSRL π0 4 条、RLinf 2 条历史 run，不复制大型产物。
- ruff、ty、20 个 pytest、全部配置、三个代表 dry-run、根与四个 method 的 Agent 检查、
  两个 Skill 校验均通过。
- 用户完成只读 CLI 验收并通过 Explain Diff 五题。
- 根提交已推送到私有 GitHub 远端；authenticated recursive clone 已从零恢复四个
  method 及其嵌套 submodule。
