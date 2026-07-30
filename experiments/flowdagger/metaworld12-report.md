# FlowDAgger MetaWorld-12 实验汇总

- 协议：`metaworld12-v1`
- 进度：11/36 个正式运行
- 正式结论门槛：12 tasks × 3 seeds 全部完成。

| Task | Seeds | Base SR | Final SR | Δ SR |
| --- | ---: | ---: | ---: | ---: |
| `metaworld_assembly` | 3/3 | 0.680 | 0.800 | 0.120 |
| `metaworld_bin_picking` | 2/3 | 0.540 | 0.100 | -0.440 |
| `metaworld_box_close` | 1/3 | 0.320 | 0.120 | -0.200 |
| `metaworld_coffee_pull` | 1/3 | 0.880 | 0.880 | 0.000 |
| `metaworld_dial_turn` | 1/3 | 0.400 | 0.560 | 0.160 |
| `metaworld_door_lock` | 1/3 | 0.280 | 0.760 | 0.480 |
| `metaworld_hammer` | 1/3 | 0.360 | 0.760 | 0.400 |
| `metaworld_hand_insert` | 1/3 | 0.880 | 0.960 | 0.080 |
| `metaworld_lever_pull` | 0/3 | — | — | — |
| `metaworld_pick_place` | 0/3 | — | — | — |
| `metaworld_soccer` | 0/3 | — | — | — |
| `metaworld_stick_push` | 0/3 | — | — | — |

## 证据边界

- 未完成三 seed 的任务只显示进度性均值，不进入正式 macro average。
- 每个任务独立训练 steering policy；这不是联合多任务 steering policy。
- 本地稳定配置使用 `bc_batch_size=16`，不声称与论文全部超参数完全一致。
