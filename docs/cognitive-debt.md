# Cognitive Debt

> 记录 Type C− 中已经通过 Agent 与用户功能验证、但暂缓 Explain Diff 理解门禁的改动。最新条目在最上方。

<!--
## YYYY-MM-DD · <变更名称>
- **状态：** Open | Repaid
- **范围：** <commit、diff 或文件范围>
- **暂缓原因：** <为什么选择 Type C− 并推迟理解 Review>
- **验证证据：** <已通过的命令与结果>
- **待理解内容：** <尚未建立的概念或心智模型>
- **偿还标准：** 使用 explain-diff-html 阅读解释并通过全部五题；记录日期和对应提交
- **偿还记录：** <通过日期、解释产物、closeout commit；未偿还时写 Pending>
-->

## 2026-07-27 · RLToken Stage 2 十二小时运行时限

- **状态：** Open
- **范围：** RLinf `e1801fd1..bf28ff64`；根仓库
  `rlt_maniskill_stage2_12h_seed2026.yaml`、RLinf launcher、runbook 与 gitlink。
- **暂缓原因：** 用户优先在当日 GPU 预算内启动实验，选择 Type C−，将代码理解
  Review 延后；功能验证和正式运行可恢复性不延后。
- **验证证据：** 时间上限单测 2 项通过；ruff format/check 通过；Hydra 最终配置
  展开通过；真实学习 smoke 记录每轮 8 条 transition，并执行 2 次 critic update
  与 1 次 actor update；用户已完成只读验收；外部环境绑定测试解析到
  `/root/RLinf/.venv/bin/python3`。
- **待理解内容：** embodied runner 如何在 step 边界检查墙钟时限，以及
  `check_progress` 如何在时限结束时强制最终评估和 checkpoint。
- **偿还标准：** 针对上述提交运行 explain-diff-html，阅读解释并通过全部五题；
  记录日期和偿还提交。
- **偿还记录：** Pending
