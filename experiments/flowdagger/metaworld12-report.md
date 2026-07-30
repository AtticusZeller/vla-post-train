# FlowDAgger MetaWorld-12 实验汇总

- 协议：`metaworld12-v1`
- 进度：5/36 个正式运行
- 正式结论门槛：12 tasks × 3 seeds 全部完成。

| Task | Seeds | Base SR | Final SR | Δ SR |
| --- | ---: | ---: | ---: | ---: |
| `metaworld_assembly` | 3/3 | 0.680 | 0.800 | 0.120 |
| `metaworld_bin_picking` | 2/3 | 0.540 | 0.100 | -0.440 |
| `metaworld_box_close` | 0/3 | — | — | — |
| `metaworld_coffee_pull` | 0/3 | — | — | — |
| `metaworld_dial_turn` | 0/3 | — | — | — |
| `metaworld_door_lock` | 0/3 | — | — | — |
| `metaworld_hammer` | 0/3 | — | — | — |
| `metaworld_hand_insert` | 0/3 | — | — | — |
| `metaworld_lever_pull` | 0/3 | — | — | — |
| `metaworld_pick_place` | 0/3 | — | — | — |
| `metaworld_soccer` | 0/3 | — | — | — |
| `metaworld_stick_push` | 0/3 | — | — | — |

## 证据边界

- 未完成三 seed 的任务只显示进度性均值，不进入正式 macro average。
- 每个任务独立训练 steering policy；这不是联合多任务 steering policy。
- 本地稳定配置使用 `bc_batch_size=16`，不声称与论文全部超参数完全一致。
