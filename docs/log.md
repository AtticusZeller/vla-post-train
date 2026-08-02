# Development Log

> 已验证完成的任务记录。最新的在最上面。

<!-- 每个任务通过全部必要验证后，在本行下方追加一条 -->

## 2026-08-02：完成 UniVTAC 云端安装并收敛 H20 runtime 边界

- 同步本地成功分支后，云端使用经 gzip、源码内容和 tag commit 校验的 tinygltf 临时
  overlay 安装余下 5 个 vcpkg ports；补齐 libuipc 未声明的 `mypy` 和嵌套 pip 官方源，
  最终构建 `tacex_uipc 0.1.0`、`pyuipc 0.9.0` 与 H20 `sm_90` CUDA backend。
- 修复 pyuipc wheel 的 stub-only 顶层 namespace 遮蔽编译 `.so`：`import uipc` 现在
  优先加载 Release binding。`pip check` 无冲突，cuRobo/uipc 无 GPU 导入通过。
- 用户释放 RLinf GPU 并接受 Omniverse EULA 后执行真实 headless smoke。Kit 显示
  `Driver Version: 0`、空 GPU 表与 `No device could be created`；默认 `vulkaninfo`
  只见 llvmpipe，显式 NVIDIA ICD 仍报 `VK_ERROR_INCOMPATIBLE_DRIVER`。因此确认当前 DSW
  不可运行 Isaac Sim RTX/Vulkan 仿真，但不把该结果外推为 H20 硬件的最终官方结论。
- 旧 smoke 因 `AppLauncher` 在 GPU foundation 失败时提前 exit 0 而误报安装成功；新版
  同时检查 graphics device count、Kit 错误和最终成功哨兵，同机复验正确 exit 1。
- 本地 RTX 4060 的单环境 GUI/触觉仿真仍是运行正证据；当前工作模式确定为本地仿真、
  云端模型推理。完整云端证据位于
  `/mnt/data/atticux/vla-post-train/univtac/install-cloud-20260802T1612Z/` 及同级 smoke 日志。
- 本任务为 Type C−，开放认知债务见 `docs/cognitive-debt.md` 的
  “UniVTAC 安装器与本地/云端运行边界”条目。

## 2026-08-02：STEAM Medium seed 1 续训至 10k 因退化被用户中止

- run `20260801-034909__libero10-task0-medium-steam-seed1-continue10k-2gpu` 从
  `global_step_1000` checkpoint 正常恢复，双卡稳定训练，顺利产出 step 3,000、
  5,000 两个 eval 检查点（各 100 回合，eval seed 0）：28%、32%，均明显低于
  step 1,000 的 66%，也低于 40% 的 baseline。
- 复核 step 1000→3000 区间的 `train/loss`/`train/grad_norm`/
  `train/learning_rate`（W&B `p3bekf52`）：cosine 学习率平滑衰减、loss 稳定在
  0.007~0.013、grad_norm 全程 0.05~0.12，无发散或尖峰——排除训练不稳定，判断
  为继续训练后代理训练目标与真实任务成功率脱钩，偏离了 step 1,000 的优质点。
- 用户判断"肯定有问题"，主动要求中止；在 stage 3（目标 10,000，训练到约
  step 5,840）以 SIGINT 终止，run 记录 exit 130 / signal 2，GPU 显存归零。
  已 `./lab experiment summarize` 归档（status=failed，中止运行证据，不构成
  正面结论）；`docs/plan.md` STEAM Medium 章节记录完整五点曲线与结论。
- 已停止 tmux 会话 `rlinf-steam-continue10k` 与日志 Monitor。



## 2026-08-02：收敛 UniVTAC vcpkg/tinygltf 安装证据

- 云端 `retry-9` 证明 `zip` 修复后 vcpkg bootstrap 成功，GNU 11.4 与 CUDA 12.4
  detection 均通过；同时定位到失败 manifest 残留会把 `VCPKG_MANIFEST_INSTALL` 设为
  `OFF`，从而把空依赖目录伪装成 Eigen3 missing。
- 隔离旧 build 后，`retry-10` 正常安装 34/39 个 vcpkg ports，首错收敛为 tinygltf
  2.9.3 GitHub archive SHA512 变化；后续 Make/C/C++ 提示再次确认为级联输出。该现象
  与活跃的 microsoft/vcpkg #53143 属于同类上游事件。
- 用户本地对下载归档完成 gzip、源码内容和 tar commit `14ba27113e…` 校验，并通过临时
  overlay 越过 hash 点进入 libuipc 配置/编译。附件没有最终 exit code、`import uipc`
  或 GPU/GUI smoke，因此本条只关闭故障诊断与知识同步，不将安装标记为 Passed。
- `docs/bug.md` 保留权威根因与证据边界；`docs/univtac.md`、`docs/plan.md`、
  `docs/cognitive-debt.md`、`cmd.md` 和 method 安装说明已同步。云端原始日志继续保存在
  `/mnt/data/atticux/vla-post-train/univtac/install-fixed-20260802/`。

## 2026-08-02：完成 UniVTAC 本地安装与单环境触觉仿真验收

- 在 Ubuntu 24.04、RTX 4060 Laptop 8 GB 上完整安装 Python 3.10、PyTorch
  2.5.1+cu124、Isaac Sim 4.5.0、Isaac Lab 2.1.1、cuRobo、TacEx 与 `tacex_uipc`；
  `pip check`、`uipc`/`curobo` 导入和 CUDA 张量计算通过。
- 首次 TacEx GUI 启动失败定位为 vendored TacEx 缺少 `Gelpad_low_res.usd`，不是 OOM。
  从 UniVTAC 历史 `b371b18` 恢复完全相同的 blob 后，单环境 `performance` GUI 进入
  `Setup complete`，GelSight debug view 可见并连续完成多次 reset。
- 用户截图与控制台证据确认 GPU compute 39–50%、显存 74.66–77.65%；该结果只证明
  单环境工程链路，不外推到数据采集、512-env 训练或策略质量。结构化证据见
  [`docs/univtac-smoke-20260802.md`](univtac-smoke-20260802.md)。
- method 恢复资产提交为 `4423bb7`，收尾终点为 `9ffd768`；根 `cmd.md` 固定 Conda CUDA
  库优先级、单环境与 `performance` 验证命令，并忽略安装器可重建的
  `third_party/IsaacLab/` checkout。
- 门禁结果：`ruff format --check`、`ruff check`、`ty check scripts tests`、`pytest`
  （29 passed）、`./lab config validate --all` 与排除原始 Kit 日志后的
  `git diff --check` 均通过；原始日志保留上游输出中的行尾空格以维持证据原貌。
  `./lab doctor` 的方法仓库/嵌套子模块检查通过，本机仅因不存在 `/mnt/data` 而报告
  制品盘挂载告警。

## 2026-08-02：接入 UniVTAC benchmark 并归档官方安装器首错

- 将 `AtticusZeller/UniVTAC` 作为 `methods/univtac` submodule 接入，登记为
  `benchmark`；`origin` 指向用户 fork，`upstream` 指向 `univtac/UniVTAC`，根仓
  registry、README、模块索引和 `docs/univtac.md` 已同步。暂不创建
  `experiments/univtac/`、launcher 或 runbook。
- 按用户要求撤销 Agent 新增文件：fork `dev@1e9272a` 保留 add/revert 审计历史，但
  最终文件树与官方 `main@05bcd3e` 完全一致，`scripts/install.sh` blob 也一致；父仓
  gitlink 固定 `1e9272afca41`。
- 两次实装均确认官方 `scripts/install.sh` 在首次安装时因 `set -e` 与
  `conda env list | grep UniVTAC` 无匹配而在 `conda create` 前 exit 1；没有创建
  Conda 环境或安装依赖。撤销后复验证据位于
  `/mnt/data/atticux/vla-post-train/univtac/install-20260801T132145Z-reverted/`，
  后续 vcpkg 与工作目录风险见 `docs/bug.md`。
- Agent 验证通过：`lab doctor`、method status、递归 submodule、Agent scaffold、
  ruff format/check、ty、29 个 pytest，以及 fork/官方 tree/blob 等价检查；用户于
  2026-08-02 明确确认最终验收通过。
- 本任务为 Type C−，开放认知债务记录见
  [`docs/cognitive-debt.md`](cognitive-debt.md) 的同名条目；安装器修复和真实 GPU smoke
  不在本次已完成范围内。

## 2026-07-31：完成 FlowDAgger 协议 v2 seed0 12/12 并收尾 Bin Picking 排查

- 协议 v2（`takeover_min/max=5/60`）下的 12 任务 seed0 全部顺序跑完（tmux
  `flowdagger-mw12-v2`），逐任务通过 `scripts/flowdagger_seed_queue.sh 0`
  自动 validate → run → summarize → report → commit → push，`experiments/
  flowdagger/metaworld12-report.md` 显示 12/36，macro 50.0%→60.0%（+10.0pp）。
- Box Close 按预期修复（−20pp→+32pp），确认接管窗口诊断成立。Bin Picking
  仍是 −48pp（比 v1 的 −44pp 还差一点）；抽帧+动作日志复核确认失败模式和
  v1 完全一致（整段 300 步机械臂静止），且两次不同协议下收敛动作向量数值
  高度接近，判定为 π0.5 底座策略对该场景的行为吸引点，不是接管窗口覆盖
  问题。
- 对照原论文（arXiv:2607.08877, Table 1）核实：官方报告 Bin Picking 为
  +13pp（未出现任何任务下降），但发布代码
  `methods/flowdagger/README.md` 明确写着只在 Assembly 上验证过；当前
  12-task 套件里 Coffee Pull/Dial Turn/Lever Pull/Pick Place/Soccer 5 个
  任务是本仓库自建扩展，论文没有报告过，且论文正文没有公开 MetaWorld
  仿真里干预调度的具体超参数（原文对干预的描述是人类操作员反应式介入，
  更接近代码里已实现但当前协议未启用的 `intervention_mode=disagreement`）。
- 用户决定收尾：不再追加 Bin Picking 专项实验，标记为协议 v2 下的已知未
  解决限制；`disagreement` 模式作为未来可选、未实测的方向记录在案。转向
  其他实验，是否继续 FlowDAgger seed1/seed42 留待后续会话确认。
- 已停止 tmux 会话 `flowdagger-mw12-v2` 与对应日志 Monitor；工作树干净。

## 2026-07-31：修复 FlowDAgger takeover 窗口过窄并升级协议到 v2

- 用户在协议 v1（12 任务 seed0 全部完成，`50.0%→59.7%`）的评估视频里直接看到
  Box Close 机械臂"抓住不动"；抽帧核对（对照同批次真实成功案例排除录像管线
  故障）确认失败 episode 从第 5 步左右起整段 300 步逐像素静止，console.log
  逐步诊断显示底层动作持续钳制在执行边界或收敛到近似恒定值，是观测-动作闭环
  卡进自洽定点，而非零输出。
- 追查 `shared/intervention_handler.py` 确认根因：`beta_decay` 模式下接管时机
  只按每回合开始时采样的固定步数触发，不看策略表现；`metaworld12_suite.yaml`
  协议 v1 把该窗口从上游官方默认 `5/60` 收窄到 `0/25`（300 步任务的 8%），且
  未启用课程扩展，导致策略几乎没有任务后半段/精细接触阶段的自主训练覆盖。
  Box Close、Bin Picking 恰好难点集中在后半段，因而在 eval 时进入未训练状态并
  卡死；`filter_failures=1` 排除了 buffer 污染的可能。判定为协议配置问题，
  不是代码逻辑错误。
- 修复：`metaworld12_suite.yaml` 的 `takeover_min/max` 改回官方默认 `5/60`；
  `protocol`/`id` 升级为 `metaworld12-v2`；重新生成 48 份 smoke/formal YAML；
  把协议 v1 下已完成的 15 个正式 run 的 `run.json` 标记 `historical: true`，
  `metaworld12-report.md` 干净回到 `0/36`，旧证据保留不删除。
- 验证通过：根 `ruff check`/`format --check`、28 个 pytest、
  `./lab config validate --all`、`./lab report suite flowdagger` 输出核对。
- 详见 `docs/bug.md` 2026-07-31 条目；下一步在协议 v2 下重跑 12 任务 seed0。

## 2026-07-30：完成 FlowDAgger MetaWorld-12 正式实验准备

- 将 method 的任务与 scripted-expert registry 从 Assembly 扩展到论文 12 tasks；
  每个任务使用 MT50 对应 prompt，并通过固定 seed 的 5/5 expert 预检。
- 新增 `metaworld12-v1` suite manifest、12 份 smoke 和 36 份 formal YAML。正式协议为
  seeds `0/1/42`、50 条 adaptation rollout、4,000 BC steps、dual buffer 50/50、
  batch size 16 和每评估点 25 episodes。
- 方法运行现在写出 `flowdagger_result.json`；根 `lab` 自动接回真实 W&B URL，
  suite 汇总只纳入成功且协议匹配的正式 run。
- 修复训练循环多做一步的边界；修复根 `uv run` 的 PATH 抢占 Conda Python 问题。
  第一次失败 smoke 与后续成功 smoke 都保留为运行证据。
- 将策略相机与视频相机解耦：π0.5 保持 `corner3` 观察，视频使用独立 `corner`
  renderer，输出 640×480、30 FPS。Assembly smoke 已生成两段 300 帧视频并通过
  `ffprobe` 与用户视觉验收。
- 验证通过：根 ruff/format/ty、28 个 pytest、FlowDAgger 3 个 pytest、全部配置解析、
  正式 dry-run、W&B summary 和结构化结果核对。
- 用户完成 Explain Diff 5/5；Notion 页面：
  <https://app.notion.com/p/3adf56e2b51c8136be73eb0b7ff0f273>。
- 本条仅表示正式实验准备完成；36 个 formal run 尚未启动，当前进度为 0/36。

## 2026-07-30：按用户要求暂停 STEAM 10k continuation

- formal run `20260730-015126__libero10-task0-medium-steam-seed1-continue10k-2gpu`
  已验证从原 `global_step_1000` DCP 恢复，双卡稳定训练到 step 1243；两张 H20
  各约占用 77 GiB，正常 step 用时约 21 秒，loss/grad norm 均为有限值。
- 为释放两张卡给 FlowDAgger，用户要求暂停后以 SIGINT 正常终止；run 记录为
  exit 130 / signal 2，所有 Ray worker 均退出，GPU 显存归零。
- 本轮尚未到 step 3000 保存点，因此没有新 checkpoint；后续继续时仍从原 step
  1000 恢复，重跑 1001–1243。W&B run
  <https://wandb.ai/atticux/rlinf/runs/oa1lo7sb> 仅作为中断运行证据，不构成评测结果。

## 2026-07-29：归档 RLToken progressive 中预算运行并修复汇总工具

- 正式 run `20260729-021706__rlt-maniskill-stage2-progressive-seed2026` 已跑满
  100/100 steps 正常退出（exit_code=0），总耗时约 16 小时；W&B
  <https://wandb.ai/atticux/rlt-maniskill/runs/jmqtnoox>。
- 最终固定评测（64 episodes）：`eval/success_once=0.703125`、
  `eval/reward=0.011972`、`eval/episode_len=191.578`；训练侧已跨过 online gate
  （`rlt/update_step=35,600` > `warmup_required_updates=10,000`），但运行结束时
  `actor_weight_ramp_progress` 只爬到 0.316，在线 actor 权重尚未爬满，因此当前
  0.703 相对上一轮 12 小时跑的 0.672 只是方向性的小幅提升，不能算作 ramp 完整后
  的效果上限。
- 修复 `scripts/monitor.py::collect_wandb`：当前锁定的 `wandb==0.28.1` 已把
  `stream` 参数从 `scan_history()` 移到 `history()`，且 `run.summary` 顶层
  `dict()` 转换保留了不可序列化的嵌套 `SummarySubDict`，导致
  `lab experiment summarize` 报错。改用 `run.history(stream="system",
  pandas=False)` 和 `run.summary._json_dict`（对测试 fake 的 plain dict 兼容
  降级）修复；详见 `docs/bug.md`。
- 已用该 run 的 W&B URL 临时展开 `primary_metrics` 跑通
  `lab experiment summarize` 和 `lab report build rlinf`，随后按既有惯例把
  `experiments/rlinf/configs/rlt_maniskill_stage2_progressive_seed2026.yaml` 的
  `tracking.run_urls`/`native.primary_metrics` 还原为空模板，只保留
  `run.json`/`summary.json`/`report.md` 作为该次运行的证据。
- 验证通过：25 个根仓 pytest（含更新后的 `test_monitor.py`）、ruff
  check/format、summarize/report build 命令实测通过。
- 洁癖收尾：README 与 `docs/plan.md` 补上新增的 `methods/expo-ft` submodule；
  `docs/rlinf.md` 与 `experiments/rlinf/report.md` 把 progressive 从「计划」改写为
  已归档结果并写明 ramp 未爬满的边界；`cmd.md` 把三个已 Passed 的验证块收敛为一个
  当前待验证块，历史验证指向本文件。

## 2026-07-29：将 RLToken 调整为 progressive 中等预算

- 5,000-step unlimited run
  `20260729-013931__rlt-maniskill-stage2-unlimited-seed2026` 实测首轮 rollout
  6 分 19 秒；按用户决定在约 32 分钟后以 SIGINT 中止，run.json/summary 和 W&B
  `o1ya9qaw` 均保留。该 run 没有正式评测，不支持算法结论。
- 新增 100-step progressive 配置，不设置墙钟限制；64-env 训练、64-env 固定评测，
  每 20 steps 评测/保存并录制前 4 路视频，预计约 11–14 小时自然完成。
- 将 replay/RLT warmup 缩为 5,000 transitions / 10,000 updates，确保预算内跨过
  online gate；官方 update cadence、critic:actor、gamma、BC/Q schedule 和训练期
  simulated expert takeover 保持不变。
- 验证通过：Hydra resolved config、bash 语法、RLinf 配置单测、根 ruff/ty、
  25 个 pytest、config validate/dry-run 和 diff check。

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
