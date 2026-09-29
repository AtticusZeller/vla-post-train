# xense-openpi Plan

## RLT（JAX）真机验证

`feature/rlt-jax` 的接入、审查与修复已完成并记入 [log.md](log.md)；代码层面只有 CPU 单测与假机器人，下面这项只能由用户
在真机上执行。机器人端与训练服务器都要用 `feature/rlt-jax`（协议 `openpi-rlt/1` 与 tacxense 不兼容）。

### Task: 标签挂起时按 A 不丢关键阶段，窗口内不换驾驶者

**Change**

- 无代码改动。

**Verification**（用户执行）

1. [ ] 机器人端 `--args.rlt --args.pico4-intervention`，服务器 `scripts/rlt/train_rl.py`：一轮内按 B 开窗、按 Y 标失败后
       立刻按 A。
2. [ ] warm_up 之后，在机器人停着等下一个 chunk 时按 B 开窗。

**Done**

- [ ] 第 1 项：机器人跑满当前单元才归位，服务器终端出现 "Failure labeled: … +N transitions"，轮末摘要
      `data : +N transitions` 中 N > 0。
- [ ] 第 2 项：该窗口的每个 chunk 在服务器日志 / W&B chunk 轴上都是 actor（`use_actor=True`），没有先 VLA 后 actor。
