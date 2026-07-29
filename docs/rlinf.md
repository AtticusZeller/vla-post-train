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
- 下一轮使用无墙钟限制的 upstream-aligned Stage 2：复用 Stage 1 step 2,000，
  64 个训练环境、256 个固定评测环境、simulated expert takeover，并录制固定评测子集。
- 无墙钟正式配置为
  `experiments/rlinf/configs/rlt_maniskill_stage2_unlimited_seed2026.yaml`。评测指标仍覆盖
  全部 256 个固定环境，MP4 只拼接前 4 路；录像先在本地完成 MP4 封装再复制到 OSSFS。
  两卡 smoke `ifrzd3ve` 已验证 expert 初始化、train/eval 和可播放 H.264 文件。

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
- W&B 项目为 `atticux/rlt-maniskill`；本地退出码和 traceback 的判定优先级高于
  W&B 状态。
- W&B run：<https://wandb.ai/atticux/rlt-maniskill/runs/umh3vuuo>；完整结果见根仓库
  `experiments/rlinf/runs/20260727-070549__rlt-maniskill-stage2-12h-seed2026/summary.json`。
