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

## 2026-08-05 · RLToken progressive-full（跑满 actor weight ramp）

- **状态：** Open（功能验证已完成，算法结果待运行结束）
- **范围：** RLinf `43ad729e..99bbb1e4`；根仓库
  `rlt_maniskill_stage2_progressive_full_seed2026.yaml`、
  `stage2-progressive-full.yaml` budget、launch.sh 新 case、runbook.md、
  `.gitignore`（补充 `.claude/`）。
- **暂缓原因：** 用户要求把 progressive run 的 `actor_weight_ramp_progress`
  跑到 1.0；先与用户对齐了续跑方式（resume 会丢失 update_step，选择重开更长单
  次 run）和 GPU 占用时机（现在启动），选择 Type C−，将 Explain Diff 理解
  Review 延后；配置验证和正式启动可恢复性不延后。
- **验证证据：** `lab doctor`、config validate/dry-run 通过；Hydra resolved
  config 确认 `max_epochs=220`、`val_check_interval=20`、`save_interval=20`、
  `resume_dir=null`/`ckpt_path=null`（非 resume）、
  `warmup_updates=20000`/`ramp_updates=50000`、
  `warmup_min_size=5000`/`warmup_post_collect_updates=10000`、train/eval 均
  64 环境、train `expert_takeover.enable=true`/eval `=false`，且不存在
  `max_run_duration`；根 ruff、12 项相关 pytest 通过；root+method 提交均已推送
  远端（root `a7a807f`、method `99bbb1e4`）。真实两卡正式启动
  `20260805-100651__rlt-maniskill-stage2-progressive-full-seed2026` 已通过
  smoke 级验证：两卡 rollout/env worker 正常初始化、显存正常爬升、Global
  Step 2/220 后无 Traceback/Error，W&B run
  <https://wandb.ai/atticux/rlt-maniskill/runs/hndbuens> 已创建并持续写入。
- **待理解内容：** `update_step` 为何不随 checkpoint 持久化（`fsdp_sac_policy_worker.py`
  的 save/load_checkpoint 实现边界）、`desired_total_updates`/
  `max_updates_per_train_step` 如何把"新增 transition 数量"转换成"本轮允许跑
  的 update 数"，以及 220 epochs 的选择如何从这个封顶速率反推而来。
- **偿还标准：** 针对本次 RLinf 与根仓提交运行 explain-diff-html，阅读解释并通过
  全部五题；记录日期和对应提交。
- **偿还记录：** Pending

## 2026-08-03 · N0-VTLA ZMQ 与 4090 UniVTAC 跨机闭环

- **状态：** Open（功能验证已完成）
- **范围：** N0-VTLA ZMQ 服务、UniVTAC `N0VTLA/deploy` adapter、4090 WebRTC
  5-episode smoke 配置，以及根仓运行手册和结果证据。
- **暂缓原因：** 用户选择先以可运行的跨机仿真链路收尾，暂不执行 Explain Diff 五题；
  真实 4090/H20 功能验证和证据边界没有延后。
- **验证证据：** H20 模型与 ZMQ 同机 smoke 通过；4090 经 SSH 转发完成闭环，用户通过
  WebRTC 观察 5/5。文本直接保存 4/4 和第五回合运行，根摘要 exit code 0 / completed；
  22.27 秒视频可见末次插孔连续运动。最终行未保存且 `results={}` 的限制已明确记录。
- **待理解内容：** baseline-difference 触觉观测如何映射到 N0-VTLA schema、50×32
  服务输出为何只执行前 8 维、每回合 ZMQ reset/触觉基线的时序，以及根汇总器与方法原生
  成功率之间的证据边界。
- **偿还标准：** 针对相关 N0-VTLA、UniVTAC 与根仓提交运行 explain-diff-html，阅读解释
  并通过全部五题；届时把本条改为 Repaid。
- **偿还记录：** Pending

## 2026-08-02 · UniVTAC 安装器与本地/云端运行边界

- **状态：** Open（功能验证已完成）
- **范围：** UniVTAC fork 至 `b443b32` 的 `scripts/install.sh`、libuipc Python binding
  搜索顺序、恢复的 `Gelpad_low_res.usd`、`docs/Installation.md`，以及根仓 gitlink、
  安装诊断和运行边界文档。
- **暂缓原因：** 用户选择 Type C− 优先完成跨本地/云端实装与故障收敛，暂不执行
  Explain Diff 五题；功能验证、真实 GPU 证据和失败边界没有延后。
- **验证证据：** 本地 RTX 4060 完整安装、Isaac Sim GUI、GelSight 触觉窗口和连续 reset
  通过，详见 [`docs/univtac-smoke-20260802.md`](univtac-smoke-20260802.md)。云端全部
  vcpkg ports、`tacex_uipc 0.1.0`、`pyuipc 0.9.0`、`pip check`、
  `import uipc` 和 H20 `sm_90` CUDA 编译通过；H20 headless smoke 暴露空 Vulkan GPU
  表与 `No device could be created`。修订后的同机复验正确 exit 1，消除旧版假阳性；
  NVIDIA 论坛和 Isaac Sim 官方仓库的 H20 专门答复进一步确认其没有 RT Cores、不受
  Isaac Sim 支持。
- **待理解内容：** 安装器为何绕开 Isaac Lab wrapper 的 torch 2.7/cu128 重装，vcpkg/
  libuipc/pyuipc 构建链，Kit 的 CUDA 与 Vulkan/RTX 双重设备边界，以及未来本地仿真与
  云端模型训练/推理通信接口。
- **偿还标准：** 针对最终 method/root 提交运行 explain-diff-html，阅读解释并通过全部
  五题；届时把本条改为 Repaid。
- **偿还记录：** Pending

## 2026-08-02 · UniVTAC benchmark 接入与安装边界诊断

- **状态：** Open
- **范围：** `methods/univtac` submodule、根仓 method registry/测试、VLA/VTLA
  工作区说明与 UniVTAC 模块文档；fork `dev@1e9272a` 撤销 Agent 文件后与官方
  `main@05bcd3e` 文件树等价。安装脚本未修改。
- **暂缓原因：** 用户优先统一接入 VTLA 仿真 benchmark，并要求保留可搜索的安装失败
  证据；选择 Type C−，将 Explain Diff 理解 Review 延后，submodule 可恢复性、用户验收
  和安装故障复现不延后。
- **验证证据：** `lab doctor`、method status、递归 submodule、Agent scaffold、ruff
  format/check、ty 和 29 个 pytest 全部通过；用户于 2026-08-02 明确确认最终验收通过。
  fork/官方完整 tree 和安装脚本 blob 分别一致；撤销个人文件后再次安装仍在创建 Conda
  环境前以 exit code 1 结束，trace 与分析保存在
  `/mnt/data/atticux/vla-post-train/univtac/install-20260801T132145Z-reverted/`。
- **待理解内容：** benchmark 与 framework 的工作区角色边界、父仓 gitlink 与 fork
  `origin/upstream` 的可恢复链路，以及 Bash `set -e` 如何让无匹配 `grep` 在命令替换中
  提前结束官方安装脚本。
- **偿还标准：** 针对本次根仓提交和 UniVTAC fork 的 add/revert 提交运行
  explain-diff-html，阅读解释并通过全部五题；记录日期和对应 closeout commit。
- **偿还记录：** Pending

## 2026-07-29 · RLToken progressive 中等预算

- **状态：** Open
- **范围：** RLinf progressive budget/launcher；根仓正式配置、launcher 测试、
  unlimited 中断记录与运行文档。
- **暂缓原因：** 用户优先在当前两张 H20 上启动约 11–14 小时的渐进实验，选择
  Type C−，将 Explain Diff 理解 Review 延后；配置验证、正式可恢复性和运行监控不延后。
- **验证证据：** Hydra resolved config 明确为 100 steps、64/64 train/eval、
  5,000/10,000 replay/RLT warmup，且不存在 `max_run_duration`；RLinf 配置单测、
  根 ruff、ty、25 个 pytest、config validate/dry-run 和 diff check 通过。
- **待理解内容：** update-step gate 如何控制 actor/reference 路由、缩短 warmup 对
  官方可比性的影响，以及 step 20/40/60/80/100 五档评测的证据边界。
- **偿还标准：** 针对本次 RLinf 与根仓提交运行 explain-diff-html，阅读解释并通过
  全部五题；记录日期和对应提交。
- **偿还记录：** Pending

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
