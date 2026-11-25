# lerobot-check Plan

## 第二期验收余项

已完成部分见 [log.md](log.md)，文件约定与规则见 [overview.md](overview.md)。

### Task：检验分界样例能否消除 agent 的系统性偏差

用户复核 episode 0 / 30 / 60 / 90 / 120 后确认（2026-11-25）：agent 参照这些人工分界样例（`exemplars`）标几条新 episode，再由
用户复核，比较分界误差。第一版的对照误差（agent 第一版对比用户改后，单位秒，取绝对值的平均）如下：

| 分界 | 第一版误差 | 偏差规律 |
| --- | --- | --- |
| `place_insert` → `place_phone` | 1.1 | episode 60 / 120 早结束 2–3 s（放下后的调整被划给下一段） |
| `place_phone` → `move_lid` | 1.2 | episode 30 晚 5.4 s |
| `move_lid` → `flip_lid` | 0 | — |
| `flip_lid` → `close_lid` | 1.7 | 5 条全部偏晚 1.4–2.2 s（落盖后的对准算进了 `flip_lid`） |

**Change**

- [ ] worker 按 `docs/annotate.md`（含 `exemplars`）标注 episode 15 / 45 / 75 / 100 / 110，写入共享标注表（`annotator=agent`），
      并把原始 25 行另存一份用于对比（2026-11-25 已派出）。
- [ ] 用户在 viewer 中复核这 5 条。

**Verification**

1. [ ] 对每个分界计算 agent 原始结果与用户复核结果的帧差，按分界类型汇总，与上表对照。

**Done**

- [ ] 误差表与结论写进 log.md。结论要说明 `flip_lid` 偏晚和抓放段早结束这两类偏差是否消失；仍存在的偏差写明原因，
      不改规则凑数。

### Task：补采面板的现场使用

**Change**

- [ ] 用户在 COLLECTION 页画目标多边形，用真实标定生成补采位置与三类测试点，导出 PNG / CSV 带到现场。

**Verification**

1. [ ] 用户按导出图摆放一次物体（用户执行）。

**Done**

- [ ] 用户确认位置与朝向能看懂、按图摆放可行。

### Task：用户确认分布面板

**Verification**

1. [ ] 用户在 DISTRIBUTION 页查看 5 条复核后的数据：帧占比、物体初始位置、各 subtask 轨迹与指标、episode 分组（用户执行）。

**Done**

- [ ] 用户确认四个功能块可用、比原 HTML 报告简洁。
