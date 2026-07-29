# RLinf RECAP / STEAM 实验汇总

## 当前结论

MVP 的 RECAP 9% 和 STEAM 14% 均低于 32% SFT baseline，只证明工程链路成立。
medium 增加 rollout 与训练预算后，baseline 为 35%，RECAP step 1000 为 60%，
STEAM step 500 为 55%；STEAM step 1000 回落到 52%。

STEAM Medium 第二个训练 seed 已完成：固定 eval seed 0 下，baseline 为 40%，
STEAM step 500 为 51%（+11 pp），step 1000 为 66%（+26 pp）。这支持继续检查
STEAM 的跨 seed 稳定性，但仍是单任务、单训练 seed、每配置 100 回合的方向性结果。
当前在 1,000-step CFG 预算处收尾；论文采用 30,000-step policy training，因此
不声称当前结果已饱和。

RLToken ManiSkill Stage 2 在 12 小时预算下运行到 87 个 global step，最终 64 条轨迹
评估 `success_once=67.2%`、`reward=0.0102`。复核发现结束时 learner
`update_step=25,200`、`ready_for_online=0`，尚未达到 30,000-update warmup，
所以这不是在线 RLT 效果结果。下一轮将复用 Stage 1 step 2,000，按 RLinf upstream
ManiSkill 配置无墙钟限制重跑 Stage 2。

## 结果索引

<!-- lab:results:begin -->
| Run | 状态 | 主要指标 | 开始时间 |
| --- | --- | --- | --- |
| `20260727-065532__rlt-maniskill-stage2-12h-seed2026` | failed | — | 2026-07-27T06:55:33.883082Z |
| `20260727-070215__rlt-maniskill-stage2-12h-seed2026` | failed | — | 2026-07-27T07:02:16.863412Z |
| `20260727-070549__rlt-maniskill-stage2-12h-seed2026` | failed | eval/success_once=0.671875 (64 episodes)<br>eval/reward=0.010207230225205421 (64 episodes)<br>eval/episode_len=211.265625 (64 episodes)<br>global_step=87 | 2026-07-27T07:05:50.276934Z |
| `20260728-080217__libero10-task0-medium-steam-value-smoke-2gpu` | failed | — | 2026-07-28T08:02:17.251867Z |
| `20260728-080517__libero10-task0-medium-steam-value-smoke-2gpu` | completed | — | 2026-07-28T08:05:18.917781Z |
| `20260728-093657__libero10-task0-medium-steam-seed1-2gpu` | failed | — | 2026-07-28T09:36:58.527145Z |
| `20260728-094321__libero10-task0-medium-steam-seed1-2gpu` | completed | baseline_success_rate=0.4 (100 episodes)<br>steam_step500_success_rate=0.51 (100 episodes)<br>steam_step1000_success_rate=0.66 (100 episodes) | 2026-07-28T09:43:21.784990Z |
| `historical__libero10-task0-medium` | completed | baseline_success_rate=0.35 (100 episodes)<br>recap_step1000_success_rate=0.6 (100 episodes)<br>steam_step500_success_rate=0.55 (100 episodes) | unknown |
| `historical__libero10-task0-mvp` | completed | baseline_success_rate=0.32 (100 episodes)<br>recap_success_rate=0.09 (100 episodes)<br>steam_success_rate=0.14 (100 episodes) | unknown |
<!-- lab:results:end -->

## 资源与恢复

medium 的 W&B 可观测阶段合计约 34 GPU·小时。该聚合实验跨 baseline、value、CFG、
evaluation 和迁移恢复阶段，`run.json` 保留四个已知代码 revision 与九个 W&B URL，
不声称存在单一 revision。

## 证据边界与下一步

正向结果来自单任务、单训练 seed、每配置 100 回合；baseline 与 policy eval 固定使用
eval seed 0。它支持继续研究 medium 配置，但不是论文级统计结论。当前第二个 seed 的
step 1000 优于 step 500，后续仍应扩展训练 seed 与 benchmark，并同时保留两档 checkpoint。
当前两卡转入 RL Token；STEAM 不继续消耗本轮预算。
