# Development Log

> 已验证完成的任务记录。最新的在最上面。

<!-- 每个任务通过全部必要验证后，在本行下方追加一条 -->

## 2026-07-27：启动 RLToken ManiSkill Stage 2 十二小时实验

- Stage 1 正式运行以 `STAGE1_FULL_EXIT=0` 完成，使用
  `global_step_2000/actor` checkpoint 作为 Stage 2 初始化权重。
- 将 Stage 2 调整为最多 500 epochs、64 个训练环境、64 个评估环境、每 25 轮评估与
  保存；内部墙钟上限 11 小时，结束当前 step 后强制最终评估和 checkpoint，外层
  11 小时 50 分钟发送 `INT` 作为保险，整体控制在 12 小时预算内。
- 真实 learning smoke 已观测每轮 8 条 transition、2 次 critic update 和 1 次
  actor update；时间上限单测、ruff、ty、22 项根测试、配置展开及用户验收均通过。
- 正式 run
  `20260727-070549__rlt-maniskill-stage2-12h-seed2026` 已在 tmux
  `rlt-maniskill:10` 启动，W&B：
  <https://wandb.ai/atticux/rlt-maniskill/runs/umh3vuuo>。Ray workers 已注册，
  两张 H20 已进入 rollout。
- 运行代码证据为根仓库 `57c4e7c`、RLinf `3fa4702d`；此前两次未进入 GPU 训练的
  初始化失败均已停止并保留独立 run 记录。

## 2026-07-27：恢复实验产物挂载写权限

- 用户已恢复 `/mnt/data` 的写权限；`findmnt -T /mnt/data` 显示 `rw`，且路径可写。
- 后续新实验可以按方法 runbook 执行；LeRobot 尚未创建实验配置，因此不会被自动启动。

## 2026-07-27：接入 LeRobot framework 与统一 method onboarding

- 保留旧 LeRobot `dev` 分支不变；从官方 `main` 创建并推送用户 fork 的干净 `workspace`
  分支，根仓库固定 revision `0d383d09f2051444de211739196a28cc94736861`。
- 清理四个旧 fork 中重复的根 Agent 托管块和纯空模板，并分别提交推送：FlowDAgger
  `e19a36f`、DSRL π0 `3ed73b5`、RLinf `547d21b`、StarVLA `6d30816`。
- 新增 `methods/lerobot`，将 StarVLA、RLinf、LeRobot 标注为 framework；LeRobot 暂不创建
  `experiments/lerobot` 配置或运行入口。
- 新增并验证 `.codex/skills/add-method`，将 framework 配置文件命名约定写入架构文档。
- 全量验证通过：ruff format/check、ty、21 个 pytest、根与 method Agent 检查、三个 Skill
  校验、`lab doctor`、`lab method status` 和 submodule recursive 状态；用户验收和 Explain
  Diff 五题均通过。
- Notion Explain Diff 页面：<https://app.notion.com/p/3aaf56e2b51c81008325c4f38dcbe4b1>。
- 当前 `/mnt/data` 为只读挂载，因此未启动 GPU、W&B 在线运行或 LeRobot 代码；运行产物规则和
  历史路径保持不变。
- 根仓库提交 `b9885e2` 已推送到私有远端；authenticated recursive clone 在重试初始化后恢复
  五个顶层 method 及全部嵌套 submodule，工作树干净。

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
