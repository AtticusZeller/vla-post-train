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

## 恢复、评测与故障

- 当前根 launcher 不声明通用 resume。阶段恢复继续使用方法脚本的原生命令并先写入 runbook。
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
  `RLINF_VENV` 与 `UV_PROJECT_ENVIRONMENT` 显式传入，确保 Ray 切换工作目录后仍复用
  已安装好的 `/root/RLinf/.venv`，不会临时重建环境。
- 学习 smoke 使用 `critical_phase` 强制进入 actor 路径，仅证明 replay 与
  update 工程链路：每轮 8 条 transition，第二轮执行 2 次 critic update 和
  1 次 actor update；不作为算法收益证据。
