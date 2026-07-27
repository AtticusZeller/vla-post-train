# DSRL π0 实验汇总

## 当前结论

LIBERO-90 task 57、seed 0 上，Pixel SAC steering 已完成 smoke、10k 和 500k。
10k 从 step 0 的 2/10 提升到 5/10；500k 最终为 10/10。另保留一次未进入 update 的
初始化失败记录，未知时间、revision 和退出码均未推测补齐。

## 结果索引

<!-- lab:results:begin -->
| Run | 状态 | 主要指标 | 开始时间 |
| --- | --- | --- | --- |
| `20260714-134147__smoke` | completed | success_rate=0.0 (1 episodes) | unknown |
| `20260714-142003__10k` | completed | baseline_success_rate=0.2 (10 episodes)<br>final_success_rate=0.5 (10 episodes) | unknown |
| `20260714-152044__500k` | completed | baseline_success_rate=0.2 (10 episodes)<br>final_success_rate=1.0 (10 episodes) | 2026-07-14T07:20:52Z |
| `historical__500k-initialization-failure` | failed | — | unknown |
<!-- lab:results:end -->

## 资源与实现

- 500k：500,200 optimizer updates、494,089 env steps、18:52:05、
  75.47 GPU·小时。
- 历史产物：`/mnt/data/atticux/dsrl_pi0/`；新产物：
  `/mnt/data/atticux/vla-post-train/dsrl-pi0/`。
- 500k 基线 revision：
  `7f48937d4553e95244cd81c79236a3256df80597`。

## 证据边界与下一步

所有性能结果仅覆盖一个 task、一个 seed；每次正式评测只有 10 回合。下一步若继续研究，
应先补多 seed 和更多 LIBERO task，而不是将 10/10 外推为 suite 级结论。
