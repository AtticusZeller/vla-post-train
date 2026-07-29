# Development Log

> 已验证完成的任务记录。最新的在最上面。

<!-- 每个任务通过全部必要验证后，在本行下方追加一条 -->

## 2026-07-29：验证 RLToken 无墙钟长跑配置与评测视频

- 新增无墙钟正式配置：保留上游 5,000 epochs 算法上限，不设置根 launcher 或原生
  runner 墙钟 timeout；恢复 64/256 train/eval env 和 simulated expert takeover。
- 评测成功率继续覆盖全部 256 个固定环境，视频只拼接前 4 路，避免录像规模改变统计口径。
- 修复 OSSFS 上直接封装 MP4 时无法回写 `moov` trailer 的问题：先在本地临时文件
  完成编码，再复制到持久化目录。
- 两卡 smoke `ifrzd3ve` 已加载 Stage 1 step 2,000 expert 并完成 train/eval；
  两个 H.264 视频均通过 `ffprobe`（4096×1024、11 帧、1.1 秒）。
- 验证通过：RLinf 录像单测 3 项、ruff format/check、根 launcher 测试 5 项、
  Hydra resolved config、根 config validate/dry-run 和 diff check。

## 2026-07-29：收尾 STEAM 并纠正 RLToken Stage 2 结论

- STEAM Medium seed 1 保留 baseline 40%、step 500 51%、step 1,000 66% 的
  单任务方向性结果；当前在 1,000-step CFG 预算处收尾。论文采用 30,000-step
  policy training，因此不把当前 checkpoint 描述为已经饱和。
- 复核 W&B ``umh3vuuo`` 和本地 metrics：RLToken 12 小时运行结束时
  ``update_step=25,200``、``ready_for_online=0``，尚未跨过 30,000-update
  warmup；67.2% 最终评测不能用于判断在线 actor 收益。
- 对照 RLinf upstream ManiSkill 示例确认现有 Stage 1 step 2,000 合规；下一轮
  Stage 2 将取消墙钟限制，恢复 256-env eval 和 simulated expert takeover。

## 2026-07-28：准备 STEAM Medium seed 1 两卡复现实验

- 将 medium 训练 seed 与评测 seed 解耦；本轮训练使用 seed 1，baseline 与两档
  STEAM checkpoint 均固定在 eval seed 0，避免把初始化分布变化混入训练 seed 比较。
- 新增正式两卡配置和 2-step value smoke 配置；原生 summary 支持从当前 run 的
  `{artifact_path}` 读取，确保每次正式运行的结果留在独立产物目录。
- 两卡真实 smoke 已完成 2 个优化步并保存 checkpoint；W&B run
  <https://wandb.ai/atticux/rlinf/runs/n28avawi> 正常结束。首次 smoke 因 Ray
  工作目录触发 uv 同步而中断，补齐 `UV_NO_SYNC=1` 和固定
  `UV_PROJECT_ENVIRONMENT` 后通过，两次记录均保留。
- 首次正式启动在 baseline EnvWorker 初始化阶段发现 Ray 会从根 `lab` 的
  `uv run` 祖先进程自动打包 RLinf 工作目录，并遗漏 `rlinf/envs/venv`；该 run
  未进入训练。正式配置现禁用此自动 hook，短 Ray worker probe 已成功从共享源码
  导入目标模块。
- 正式 run `20260728-094321__libero10-task0-medium-steam-seed1-2gpu` 已完成：
  baseline 40%，STEAM step 500 为 51%，step 1,000 为 66%，每项 100 回合；W&B
  runs 为 `dsj2xjay`、`pvious9w`、`ljh0y3rr`、`um33wjj3`。结果只覆盖 LIBERO-10
  Task 0、训练 seed 1 和固定 eval seed 0，不作为 suite 或论文级结论。
- 验证通过：根仓 monitor 测试 3 项、RLinf 针对性测试 5 项、ruff、局部 ty、
  全量配置校验、正式 dry-run、checkpoint/退出码和 diff 检查。用户明确授权
  Agent 代验后继续启动；此处仅证明工程路径，不构成 STEAM seed 1 效果结论。

## 2026-07-28：归档 RLToken ManiSkill Stage 2 十二小时运行

- 正式 run `20260727-070549__rlt-maniskill-stage2-12h-seed2026` 已结束；外层 11 小时
  50 分钟预算信号在 step 87 checkpoint 等待阶段触发，run.json 保留退出码 130，不能
  视为完整 500-step 正常退出。
- 结果证据：W&B 最终评估 64 条轨迹的 `eval/success_once=0.671875`、
  `eval/reward=0.010207`；累计 87 step、42,447 条 transition，保留
  `global_step_{25,50,75,87}` checkpoint；总运行约 11.83 小时、约 23.65 GPU·小时。
- 该结果仅覆盖 ManiSkill 单任务、seed 2026、缩短预算和 64 条评估轨迹；当时尚未
  确认 learner warmup 状态。2026-07-29 复核后确认 ``ready_for_online=0``，
  因此该运行不构成在线 RLT 效果结论。

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
