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
