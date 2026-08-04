# RLinf 模块

> `methods/rlinf/` 是 RLinf framework 的固定 submodule；根仓库负责正式实验配置、
> 运行证据和可恢复入口。

## 当前实验入口

- RECAP / STEAM LIBERO-10 Task 0：见 `experiments/rlinf/runbook.md` 中的 MVP 与
  Medium 记录。
- STEAM Medium seed 1 两卡复现配置为
  `experiments/rlinf/configs/libero10_task0_medium_steam_seed1_2gpu.yaml`：
  训练 seed 1，固定 eval seed 0，复用历史 Medium 的固定数据清单，独立产物目录由
  根 launcher 注入。两卡 2-step value smoke 已通过；正式结果为 baseline 40%、
  STEAM step 500 51%、step 1,000 66%（各 100 回合）。
- RLToken ManiSkill：Stage 1 已完成 2,000 steps，本地退出标记为
  `STAGE1_FULL_EXIT=0`，最终特征模型位于
  `/mnt/data/atticux/rlt-maniskill/runs/full/stage1/stage1-full/checkpoints/global_step_2000/actor`。
- 12 小时 Stage 2 根配置为
  `experiments/rlinf/configs/rlt_maniskill_stage2_12h_seed2026.yaml`；方法配置位于
  `methods/rlinf/experiments/rlt-maniskill/`。
- Stage 2 run `20260727-070549__rlt-maniskill-stage2-12h-seed2026` 已归档：87 个
  global step，最终 64 条轨迹评估 `success_once=0.671875`、`reward=0.010207`，
  约 11.83 小时后在 step 87 checkpoint 等待阶段被外层预算中断。最终 learner
  `update_step=25,200`、`ready_for_online=0`，尚未跨过 30,000-update warmup，
  因而不能评价在线 actor 收益。
- 5,000-step unlimited run
  `20260729-013931__rlt-maniskill-stage2-unlimited-seed2026` 已按用户决定在约 32 分钟后
  中止；它验证了官方参数路径和单轮约 6 分 19 秒的耗时，不作为算法结果。
- progressive 配置为
  `experiments/rlinf/configs/rlt_maniskill_stage2_progressive_seed2026.yaml`：100 steps、
  64 个训练环境、64 个固定评测环境、每 20 steps 评测/保存、5,000 replay warmup 和
  10,000 RLT warmup update，不设置墙钟限制。
- progressive run `20260729-021706__rlt-maniskill-stage2-progressive-seed2026` 已跑满
  100/100 steps 并以 exit code 0 正常结束，实际耗时约 16 小时、约 32 GPU·小时。
  最终 64 条固定评测轨迹为 `eval/success_once=0.703125`、`eval/reward=0.011972`、
  `eval/episode_len=191.578`。这是首个真正跨过 online gate 的 run
  （`rlt/update_step=35,600` > 10,000 warmup、`ready_for_online=1`），但结束时
  `actor_weight_ramp_progress` 只到 0.316，在线 actor 权重尚未爬满，因此 0.703 相对
  12 小时跑的 0.672 只能算方向性小幅提升，不是 ramp 完整后的效果上限。
- progressive 训练 rollout 启用 simulated expert takeover（配置见
  `methods/rlinf/examples/embodiment/config/maniskill_rlt_stage2_ac_mlp.yaml:122-144`）：
  `trigger_mode=stalled_progress`，策略进入 critical phase 后连续 3 个 action chunk
  （`stuck_chunks_before_takeover=3`）在 x/yz/综合插入进度上均未达到阈值
  （`min_x_progress=0.003`/`min_yz_progress=0.0015`/`min_score_progress=0.002`）才触发
  接管；评测阶段 `expert_takeover.enable=False`，全程不允许 expert。该 run 结束时
  （wandb `jmqtnoox` 的 summary）实测 `train/replay/intervention_rate≈2.97%`、
  `train/replay/actor_switch_rate`（base policy→RLT actor 切换占比）`≈14.7%`、
  `env/actor_switch_step` 均值≈40.3 步（满 episode 500 步）、
  `env/entered_actor_phase_once≈82.8%`。MP4 只拼接前 4 路，并沿用本地封装后复制到
  OSSFS 的可靠写入方式。

## RECAP 四阶段与介入机制

RECAP（RL with Experience and **Corrections** via Advantage-conditioned Policies）
是 RLinf 原生的离线 pipeline，按 tag（`returns_tag`→`advantage_tag`）串联执行四个
顺序阶段，本地 launcher 入口见
`methods/rlinf/examples/offline_rl/run_libero10_task0_comparison.sh`：

1. **Compute Returns**：对每条轨迹逆序计算折扣回报
   `G_t = r_t + γ·G_{t+1}`。SFT 数据集（全部成功轨迹）每步 `reward=-1`、终止步
   `=0`；rollout 数据集（含失败）失败轨迹终止步 `reward=-300`（tag `fail300`）；
   `γ` 默认 `1.0`（不折扣）。只写 `meta/returns_{tag}.parquet` sidecar，不改原数据。
2. **Value Model SFT**：用 Step1 的 return 做监督信号训练 value model（SigLIP2
   视觉编码器 + Gemma3 语言模型 + 可学习 Critic Expert head），输出 201-bin
   分类分布，预测归一化回报 ∈`[-1,0]`。
3. **Compute Advantages**：用训好的 value model 计算每个 timestep 的 N-step
   advantage：`A_t = normalize(r_{t:t+N}) + γᴺ·V(o_{t+N}) − V(o_t)`（N 默认
   10），按分位数阈值（默认 top 30%，`positive_quantile`）标 positive/negative，
   写 `meta/advantages_{tag}.parquet`。
4. **CFG Training**：用 advantage 标签做 classifier-free guidance 训练 π0.5
   policy：positive（高 advantage）样本作条件输入，negative 样本永远
   unconditional；`positive_only_conditional=true` 时 positive 样本还以
   `unconditional_prob=0.1` 概率被随机丢到 unconditional 做正则；推理时
   `cfgrl_guidance_scale` 控制引导强度。

支持迭代优化：用 Step4 训出的 policy 收集新 rollout 数据后回到 Step1，用新 tag
（如 `fail300_iter2`）重跑一轮，避免覆盖上一轮证据。

**RECAP 本身没有在线介入机制**，这是和 FlowDAgger 的 scripted takeover、RL Token
的 `expert_takeover` 最大的区别：RECAP 全程离线，不做任何新的环境交互/rollout，
代码和上游文档都没有 intervention/takeover 概念。名字里的 "Corrections" 指的不是
实时人类或专家接管，而是"把失败轨迹也纳入训练数据、用 `reward=-300` 惩罚 +
advantage 分位数阈值筛选做修正"——本质是离线数据加权/过滤策略，不是在线策略切换。

## RLToken 十二小时运行边界

- 保留 64 个训练环境、500-step episode、原始 replay warmup、update budget 和
  BC/Q 权重 schedule，不把时间缩量伪装成算法等价的 full 结果。
- 原生 runner 时限为 11 小时；到时完成当前 step，再强制最终评估和 checkpoint。
  外层 11 小时 50 分保护只处理 runner 卡死等异常。
- 评估环境缩为 64；结果只能作为单任务、单 seed、12 小时预算证据。
- 学习 smoke 强制从 critical phase 开始，只证明 replay ingestion 和
  actor/critic update 链路，不证明任务成功率或算法收益。
- step 87 checkpoint 保存模型、优化器、target model 与 replay buffer，但未保存
  worker `update_step`；不能直接作为保持 warmup 进度的正式 resume 入口。

## 恢复与证据

- Stage 2 checkpoint 由 `runner.save_interval` 和运行时限终止路径保存；恢复必须先
  检查 runbook、对应根配置和本地退出码。
- 完整日志、checkpoint、W&B 本地目录和后续 summary 写入
  `/mnt/data/atticux/vla-post-train/rlinf/rlt-maniskill/stage2-12h/`。
- 无墙钟长跑的原生产物写入
  `/mnt/data/atticux/vla-post-train/rlinf/rlt-maniskill/stage2-unlimited/`。
- progressive 产物写入
  `/mnt/data/atticux/vla-post-train/rlinf/rlt-maniskill/stage2-progressive/`。
- W&B 项目为 `atticux/rlt-maniskill`；本地退出码和 traceback 的判定优先级高于
  W&B 状态。
- 12 小时 run 的 W&B 为 <https://wandb.ai/atticux/rlt-maniskill/runs/umh3vuuo>，
  progressive run 为 <https://wandb.ai/atticux/rlt-maniskill/runs/jmqtnoox>；完整结果见
  根仓库对应 `experiments/rlinf/runs/<run-id>/summary.json`。
- `lab experiment summarize` 依赖 wandb Public API。当前锁定的 `wandb==0.28.1` 只在
  `history()` 上支持 `stream="system"`，且 `run.summary` 需要经 `_json_dict` 才能
  JSON 序列化；相关处理在 `scripts/monitor.py::collect_wandb`，背景见 `docs/bug.md`。
- 汇总某个 run 时需要临时把该 run 的 W&B URL 填进配置的 `tracking.run_urls`
  （`primary_metrics` 同理），跑完 `summarize` / `report build` 后按惯例还原为空模板；
  运行证据以 `run.json`/`summary.json`/`report.md` 为准。
