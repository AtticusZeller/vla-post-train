# RLinf RECAP / STEAM 实验汇总

## 当前结论

MVP 的 RECAP 9% 和 STEAM 14% 均低于 32% SFT baseline，只证明工程链路成立。
medium 增加 rollout 与训练预算后，baseline 为 35%，RECAP step 1000 为 60%，
STEAM step 500 为 55%；STEAM step 1000 回落到 52%。

RLToken ManiSkill Stage 2 在 12 小时预算下运行到 87 个 global step，最终 64 条轨迹
评估 `success_once=67.2%`、`reward=0.0102`；该结果仅为单任务、单 seed、缩短预算的
方向性证据，效果一般。按当前研究决策，RLToken 暂不进入后续主线实验或预算分配；运行
产物与 checkpoint 保留供复核。

## 结果索引

<!-- lab:results:begin -->
| Run | 状态 | 主要指标 | 开始时间 |
| --- | --- | --- | --- |
| `20260727-065532__rlt-maniskill-stage2-12h-seed2026` | failed | — | 2026-07-27T06:55:33.883082Z |
| `20260727-070215__rlt-maniskill-stage2-12h-seed2026` | failed | — | 2026-07-27T07:02:16.863412Z |
| `20260727-070549__rlt-maniskill-stage2-12h-seed2026` | failed | eval/success_once=0.671875 (64 episodes)<br>eval/reward=0.010207230225205421 (64 episodes)<br>eval/episode_len=211.265625 (64 episodes)<br>global_step=87 | 2026-07-27T07:05:50.276934Z |
| `historical__libero10-task0-medium` | completed | baseline_success_rate=0.35 (100 episodes)<br>recap_step1000_success_rate=0.6 (100 episodes)<br>steam_step500_success_rate=0.55 (100 episodes) | unknown |
| `historical__libero10-task0-mvp` | completed | baseline_success_rate=0.32 (100 episodes)<br>recap_success_rate=0.09 (100 episodes)<br>steam_success_rate=0.14 (100 episodes) | unknown |
<!-- lab:results:end -->

## 资源与恢复

medium 的 W&B 可观测阶段合计约 34 GPU·小时。该聚合实验跨 baseline、value、CFG、
evaluation 和迁移恢复阶段，`run.json` 保留四个已知代码 revision 与九个 W&B URL，
不声称存在单一 revision。

## 证据边界与下一步

正向结果来自单任务、单 seed、每配置 100 回合。它支持继续研究 medium 配置，但不是
论文级统计结论。后续比较应保留 STEAM step 500 checkpoint，并优先扩展 seed 或 benchmark。
