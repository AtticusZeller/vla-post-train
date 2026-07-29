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

## 2026-07-29 · RLToken upstream-aligned 无墙钟长跑

- **状态：** Open
- **范围：** RLinf 无墙钟/冒烟配置、视频环境上限与 OSSFS MP4 封装；根仓正式配置、
  launcher 测试和运行文档。
- **暂缓原因：** 用户要求完成 Agent 侧验证、提交后立即占用当前两张 H20 启动长跑，
  因此将 Explain Diff 理解 Review 延后；配置、真实 GPU smoke、视频验证和远端可恢复性
  不延后。
- **验证证据：** RLinf 录像单测 3 项和 ruff 通过；Hydra resolved config 不含
  `max_run_duration`；根 launcher 测试 5 项、config validate/dry-run 通过；真实两卡
  smoke `ifrzd3ve` 完成 expert 初始化和 train/eval，两个 MP4 均通过 `ffprobe`。
- **待理解内容：** warm-up gate 与 simulated expert takeover 的交互、256-env 评测和
  4-env 视频子集的统计边界，以及 MP4 在 FUSE/OSSFS 上需要本地 finalize 的原因。
- **偿还标准：** 针对本次 RLinf 与根仓提交运行 explain-diff-html，阅读解释并通过
  全部五题；记录日期和对应提交。
- **偿还记录：** Pending

## 2026-07-28 · STEAM Medium 固定评测 seed 的两卡复现

- **状态：** Open
- **范围：** RLinf medium launcher、结果汇总器与测试；根仓两卡 smoke/formal
  配置、artifact-relative summary 解析及运行证据。
- **暂缓原因：** 用户优先启动当前两张 H20 上的 seed 1 复现实验，选择 Type C−，
  将 Explain Diff 理解 Review 延后；代码、配置和真实 GPU smoke 验证不延后。
- **验证证据：** 根仓 monitor 测试 3 项、RLinf 针对性测试 5 项、ruff
  format/check、范围内 ty、全量配置校验和正式 dry-run 通过；两卡 value smoke
  完成 2 个优化步并以 exit code 0 保存 `global_step_2` checkpoint；用户明确授权
  Agent 执行 `cmd.md` 验证并继续运行。
- **待理解内容：** 训练 seed 与 eval seed 的路径隔离方式、固定评测初始状态对
  paired comparison 的意义，以及 native summary 如何通过 `{artifact_path}` 绑定
  单次正式 run。
- **偿还标准：** 针对本次 RLinf 与根仓提交运行 explain-diff-html，阅读解释并通过
  全部五题；记录日期和对应提交。
- **偿还记录：** Pending

## 2026-07-27 · RLToken Stage 2 十二小时运行时限

- **状态：** Open
- **范围：** RLinf `e1801fd1..3fa4702d`；根仓库
  `rlt_maniskill_stage2_12h_seed2026.yaml`、RLinf launcher、runbook 与 gitlink。
- **暂缓原因：** 用户优先在当日 GPU 预算内启动实验，选择 Type C−，将代码理解
  Review 延后；功能验证和正式运行可恢复性不延后。
- **验证证据：** 时间上限单测 2 项通过；ruff format/check 通过；Hydra 最终配置
  展开通过；真实学习 smoke 记录每轮 8 条 transition，并执行 2 次 critic update
  与 1 次 actor update；用户已完成只读验收；外部环境绑定测试解析到
  `/root/RLinf/.venv/bin/python3`，并以 `UV_NO_SYNC=1` 禁止正式运行期间同步依赖。
- **待理解内容：** embodied runner 如何在 step 边界检查墙钟时限，以及
  `check_progress` 如何在时限结束时强制最终评估和 checkpoint。
- **偿还标准：** 针对上述提交运行 explain-diff-html，阅读解释并通过全部五题；
  记录日期和偿还提交。
- **偿还记录：** Pending
