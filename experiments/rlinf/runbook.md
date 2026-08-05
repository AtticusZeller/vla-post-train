# RLinf RECAP / STEAM 运行手册

## 定位与环境

- 代码：`methods/rlinf`；入口为
  `examples/offline_rl/run_libero10_task0_comparison.sh`。
- 目标：LIBERO-10 task 0 上比较 SFT baseline、RECAP 与 STEAM。
- 第三方依赖和训练环境保持 RLinf 原有方式；根 workspace 不重构其依赖闭包。
- 历史产物位于 `/mnt/data/atticux/rlinf/experiments/`；新运行写入
  `/mnt/data/atticux/vla-post-train/rlinf/`。

```bash
./lab config validate experiments/rlinf/configs/libero10_task0_medium_seed0.yaml
./lab experiment dry-run experiments/rlinf/configs/libero10_task0_medium_seed0.yaml
```

## MVP 与 medium

- MVP：30 条 SFT + 64 条 rollout，RECAP value 1,000 steps、STEAM value 100 steps，
  两组 CFG 200 steps，评测各 100 回合。
- medium：256 条确定性分层 rollout，RECAP value 2,000 steps、STEAM value 500 steps，
  CFG 1,000 steps，评测 step 500/1,000 各 100 回合。
- medium 的 W&B 可观测阶段合计约 34 GPU·小时；RECAP 需要 4 张约 80 GiB，
  STEAM CFG 需要 2 张约 80 GiB。

长跑必须先 dry-run，再由 Skill 放入 tmux。脚本自身负责阶段幂等和原生路径；根 launcher
只选择 `mvp` 或 `medium` argv。

## STEAM Medium seed 1 两卡复现

- 正式配置：
  `experiments/rlinf/configs/libero10_task0_medium_steam_seed1_2gpu.yaml`。
- 训练使用 seed 1；baseline 与 STEAM step 500/1,000 均使用 eval seed 0。
  不同评测 seed 会写入 checkpoint 方法目录下的 `eval-seed-<seed>/`，避免覆盖训练
  seed 同名结果。
- 数据与预算保持 Medium 不变：30 条 SFT、固定清单中的 256 条 rollout、500-step
  STEAM ensemble value、1,000-step CFG、每个 checkpoint 100 回合评测。
- 本轮只复现 STEAM，不重复 RECAP；baseline 在本轮独立 artifact 中重新评测，
  summary 仅汇总 baseline、STEAM step 500 和 step 1,000。
- `RLINF_NPROC=2`，复用 `/root/RLinf/.venv`，并设置 `UV_NO_SYNC=1` 与
  `UV_PROJECT_ENVIRONMENT=/root/RLinf/.venv`，避免 Ray worker 切换目录后触发
  uv 重建环境。另设置 `RAY_ENABLE_UV_RUN_RUNTIME_ENV=0`，禁止 Ray 从根
  `lab` 的 `uv run` 祖先进程自动构造 working-dir runtime env；当前单节点 worker
  直接使用共享的已提交 RLinf 源码。
- 2026-07-28 的两卡 2-step value smoke 已通过：
  `20260728-080517__libero10-task0-medium-steam-value-smoke-2gpu`，
  W&B <https://wandb.ai/atticux/rlinf/runs/n28avawi>。此前
  `20260728-080217__libero10-task0-medium-steam-value-smoke-2gpu` 因缺少上述 uv
  环境约束在进入 GPU 优化前中断，作为失败工程证据保留。
- 首次正式启动
  `20260728-093657__libero10-task0-medium-steam-seed1-2gpu` 在 baseline
  EnvWorker 初始化时退出：Ray 的 `uv run` 自动 working-dir 包遗漏
  `rlinf/envs/venv`。该 run 未进入 GPU 训练；禁用上述自动 hook 后，短 Ray worker
  probe 已从共享源码成功导入 `rlinf.envs.venv`。

## STEAM Medium seed 1 续训至 10k（已中止，见 `docs/plan.md`）

- 配置：
  `experiments/rlinf/configs/libero10_task0_medium_steam_seed1_continue10k_2gpu.yaml`；
  从 `RLINF_STEAM_MEDIUM_RESUME_DIR` 指向的 `global_step_1000` DCP checkpoint
  恢复，`actor.optim.total_training_steps=10000`，依次训练/评测到 3000、5000、
  10000（脚本 `run_steam_medium_continuation`，按 checkpoint 是否存在自动跳过
  已完成阶段，可安全重跑同一命令续接）。
- 2026-08-01/02 第二次 continuation 顺利产出 step 3,000（28%）、5,000（32%）两
  个 eval 点，均低于 step 1,000（66%）与 baseline（40%）；同区间 loss/grad_norm/
  learning_rate 均正常，判断为代理训练目标与真实成功率脱钩，不是训练不稳定。
  用户据此在 stage 3（约 step 5,840）主动 SIGINT 中止，不再自动重启到 10,000。
- 若后续要继续排查，先看是否是"延长 cosine schedule"本身的效应（对比不延长
  schedule 或缩短续训步数），而不是默认调大 timeout 硬跑到 10k。

## 恢复、评测与故障

- 当前根 launcher 不声明通用 resume。阶段恢复继续使用方法脚本的原生命令并先写入 runbook。
- seed 1 正式复现的各阶段在同一 artifact 下幂等：存在完整 value 或 policy
  checkpoint 时复用；评测重跑前应先检查对应 `eval.log`，根层不提供自动 resume。
- medium 是跨多次执行和机器迁移的聚合实验，必须保留 `code_revisions[]`，不能压缩为单 commit。
- W&B 只读取配置列出的 stage runs；本地 summary 和退出/traceback 具有更高判定优先级。
- medium 中 STEAM advantage 曾发生 SIGSEGV，后以三卡继续；CFG 在 step 514 主动迁移后由
  step 500 checkpoint 在两卡恢复。
- 结论只覆盖 LIBERO-10 task 0、seed 0，不自动扩展到 full。

## RLToken ManiSkill Stage 2（12 小时预算）

- 根配置：
  `experiments/rlinf/configs/rlt_maniskill_stage2_12h_seed2026.yaml`。
- Stage 1 输入固定为
  `/mnt/data/atticux/rlt-maniskill/runs/full/stage1/stage1-full/checkpoints/global_step_2000/actor`；
  本地日志已确认 `STAGE1_FULL_EXIT=0`。
- Stage 2 保留 64 个训练环境、500-step episode、原始 replay warmup 与 BC/Q
  schedule；只增加 11 小时原生时限、500 epochs 第二上限，并将评估环境缩为 64。
- 原生时限到达后完成当前 step，强制最终评估和 checkpoint；tmux 启动时另加
  11 小时 50 分硬保护，确保总墙钟预算不超过 12 小时。
- 新产物写入
  `/mnt/data/atticux/vla-post-train/rlinf/rlt-maniskill/stage2-12h/`，W&B 项目为
  `atticux/rlt-maniskill`。当前机器复用 `/root/RLinf/.venv`，由根配置中的
  `RLINF_VENV`、`UV_PROJECT_ENVIRONMENT` 与 `UV_NO_SYNC=1` 显式传入，确保 Ray
  切换工作目录后仍复用已安装好的 `/root/RLinf/.venv`，且正式启动期间不会自动同步
  或改写依赖。
- 学习 smoke 使用 `critical_phase` 强制进入 actor 路径，仅证明 replay 与
  update 工程链路：每轮 8 条 transition，第二轮执行 2 次 critic update 和
  1 次 actor update；不作为算法收益证据。

### Stage 2 结果与当前决策

- `20260727-070549__rlt-maniskill-stage2-12h-seed2026` 在 11 小时 50 分预算结束时完成
  87 个 global step，并保留 step 25、50、75、87 checkpoint；最终 step 87 checkpoint
  等待阶段收到外层中断，run 状态保持 `failed`/budget interrupt。
- 最终 64 条轨迹评估为 `success_once=0.671875`、`reward=0.010207`。结束时 learner
  `update_step=25,200`、`ready_for_online=0`，尚未达到
  `warmup_post_collect_updates=30,000`；该成功率不能用于判断在线 actor 收益。
- step 87 checkpoint 保存模型、优化器、target model 和 38,852 条 replay
  transition，但 worker `update_step` 没有持久化；直接 `resume_dir` 会重置
  learner gate，因此下一轮从 Stage 2 头部按 upstream 配置运行。

## RLToken ManiSkill Stage 2（无墙钟限制）

- 根配置：
  `experiments/rlinf/configs/rlt_maniskill_stage2_unlimited_seed2026.yaml`；
  原生入口：`experiments/rlt-maniskill/launch.sh stage2-unlimited`。
- 复用 Stage 1 `global_step_2000/actor`，不重复训练 Stage 1。
- 算法与 RLinf upstream `maniskill_rlt_stage2_ac_mlp.yaml` 对齐：64 个训练环境、
  30,000-update warmup、BC/Q schedule、simulated expert takeover、256 个固定
  reset-state 评测环境、5,000 epochs 算法上限。
- 根 launcher 和 native runner 均不设置墙钟 timeout；5,000 epochs 是可复现的
  算法终止条件，不是时间预算。
- 正式成功率使用全部 256 个评测环境。录像仅选固定环境子集拼成 MP4，避免视频编码
  改变评测样本数或训练算法参数；正式配置录制前 4 路，写入
  `/mnt/data/atticux/vla-post-train/rlinf/rlt-maniskill/stage2-unlimited/video/eval/`。
- OSSFS 不支持 MP4 编码器可靠地回写 trailer；录像先在本地临时文件完成封装，再复制到
  `/mnt/data`。两卡真实 smoke `ifrzd3ve` 已加载 Stage 1 expert 并完成 train/eval；
  两个 H.264 文件均通过 `ffprobe`（4096×1024、11 帧、1.1 秒）。
- 必须在 W&B 同时观察 `train/rlt/ready_for_online=1`、
  `train/replay/actor_switch_rate>0` 和跨 gate 后的 `eval/success_once`，才进入
  方法效果判断。
- run `20260729-013931__rlt-maniskill-stage2-unlimited-seed2026` 实测单个完整
  rollout 约 6 分 19 秒。用户决定不把 5,000 steps 作为首轮预算后，该 run 在约
  32 分钟处中止并保留为工程/耗时证据，不支持算法结论。

## RLToken ManiSkill Stage 2（progressive 中等预算）

- 根配置：
  `experiments/rlinf/configs/rlt_maniskill_stage2_progressive_seed2026.yaml`；
  原生入口：`experiments/rlt-maniskill/launch.sh stage2-progressive`。
- 不设置根或原生墙钟 timeout；以 100 global steps 作为算法终止条件，按已观测
  6–8 分钟/step 估计约 11–14 小时。
- 训练环境保持 64；固定评测环境为 64，每 20 steps 评测和保存，预计得到
  step 20/40/60/80/100 五档成功率与 checkpoint。录像取固定前 4 路。
- 为确保中等预算内进入 online control，只缩短两项预热：
  `warmup_min_size=5000`、`warmup_post_collect_updates=10000`。仍保留官方
  `max_updates_per_train_step=400`、`update_epoch=5`、critic:actor=4、
  gamma=0.96 和完整 BC/Q weight schedule。
- 预期 step 20 仍处于 base/reference 路由；约 step 35–40 时
  `rlt/update_step>=10000`、`ready_for_online=1`，后续评测才用于判断 RLT actor
  接管后的方向性效果。该结果必须标记为 accelerated-warmup progressive baseline，
  不能等同于官方 30,000-update warmup full reproduction。
- 已完成 `20260729-021706__rlt-maniskill-stage2-progressive-seed2026`：100/100
  steps、exit 0、`rlt/update_step=35,600`，但
  `actor_weight_ramp_progress` 只到 0.316（未跑满，需
  `update_step≥warmup_updates(20000)+ramp_updates(50000)=70,000`）。

## RLToken ManiSkill Stage 2（progressive-full，跑满 actor weight ramp）

- 根配置：
  `experiments/rlinf/configs/rlt_maniskill_stage2_progressive_full_seed2026.yaml`；
  原生入口：`experiments/rlt-maniskill/launch.sh stage2-progressive-full`；方法预算
  `methods/rlinf/experiments/rlt-maniskill/budget/stage2-progressive-full.yaml`。
- 目的：让 `actor_weight_ramp_progress` 真正到 1.0。原 progressive-100 run 的
  checkpoint 保存逻辑（`fsdp_sac_policy_worker.py:757-847`，RLT AC worker 复用）不
  持久化 `update_step`，直接 `resume` 会把 warmup/ramp 计数器清零、扔掉已跑的
  35,600 updates；因此本轮从 Stage 1 `global_step_2000/actor` 重新起步的全新单次
  run，不是 resume。
- 与 progressive-100 完全相同：64 训练环境、64 固定评测环境、
  `warmup_min_size=5000`、`warmup_post_collect_updates=10000`、
  `max_updates_per_train_step=400`、`update_epoch=5`、critic:actor=4、
  `expert_takeover(trigger_mode=stalled_progress)`、每 20 steps 评测/保存、前 4 路
  录像。唯一差异是 `max_epochs: 100→220`。
- 220 epochs 的依据：progressive-100 结束时 `update_step` 由
  `max_updates_per_train_step=400` 按 step 封顶增长（非固定线性外推），
  `desired_total_updates` 已达 57,980、仍有 21,980 积压未跑；按同样的封顶速率，
  达到 70,000 门槛约需 186 步，220 步留出安全余量，避免刚好卡在门槛之下就结束。
  预计约 35 小时墙钟（约 70 GPU·小时，2×H20），是 progressive-100（约 16 小时/32
  GPU·小时）的约两倍。
- 不设置根或原生墙钟 timeout，以 220 global steps 作为终止条件。
