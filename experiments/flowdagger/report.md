# FlowDAgger 实验汇总

## 当前结论

MetaWorld Assembly、seed 42 上，batch 16 已完成 smoke、100-step short 和
4,000-step full。batch 64 在首次 BC update 失败。full 的 25-episode success rate
从 step 0 的 0.64 上升到 step 1500 的 1.00，最终 step 4000 为 0.80，曲线并不单调。

## 结果索引

<!-- lab:results:begin -->
| Run | 状态 | 主要指标 | 开始时间 |
| --- | --- | --- | --- |
| `20260721-110029__exp-01-smoke` | completed | success_rate=0.0 (1 episodes) | 2026-07-21T11:00:29Z |
| `20260721-111301__exp-02-short-b64` | failed | pre_update_success_rate=0.8 (5 episodes) | 2026-07-21T11:13:01Z |
| `20260721-111611__exp-02-short-b16` | completed | success_rate=0.8 (5 episodes) | 2026-07-21T11:16:11Z |
| `20260721-113655__exp-03-default-b16` | completed | final_success_rate=0.8 (25 episodes)<br>peak_success_rate=1.0 (25 episodes) | 2026-07-21T11:36:55Z |
<!-- lab:results:end -->

## 实现与资源

- 旧代码基线：FlowDAgger `d2e60b5bf5d39538783f1e73d460394b21eb0f28`，
  nested OpenPI `4c5df220f794ec604d88baef386751dd36d8429f`。
- full 用时 53 分 48 秒，单张 H20；历史证据位于
  `/mnt/data/atticux/FlowDAgger/`。
- 新运行统一写入 `/mnt/data/atticux/vla-post-train/flowdagger/`。

## 证据边界与下一步

结果只覆盖一个 MetaWorld 任务和一个 seed。25 回合的单次 checkpoint 评测不足以支持
跨任务或论文级结论；intervention rate 也不是泛化指标。若继续投入，应先增加 seed，
并明确 batch 16 与官方默认 batch 256 的比较口径。
