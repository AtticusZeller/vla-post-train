# UniVTAC · N0-VTLA 实验报告

## 当前状态

- 云端 H20 推理环境与发布 checkpoint 已部署；
- 同机 ZMQ 推理 smoke 已通过；
- UniVTAC adapter 已通过 fake-task 端到端验证，完整执行 50×8 动作 chunk；
- 实验室 RTX 4090 已通过 SSH 隧道调用 H20 服务，并以 WebRTC 完成 5-episode
  `insert_hole` 跨机闭环仿真验证。

## 结果索引

<!-- lab:results:begin -->
| Run | 状态 | 主要指标 | 开始时间 |
| --- | --- | --- | --- |
| — | 无记录 | — | — |
<!-- lab:results:end -->

## 已有工程证据

| 验证 | 结果 | 边界 |
| --- | --- | --- |
| checkpoint 完整性 | Hugging Face 5/5 文件通过 | 固定 revision `73a514c...` |
| H20 模型加载 | 通过，约占用 8.7 GiB | 不涉及 Isaac Sim |
| 同机 ZMQ 推理 | `(50, 32)`，约 684 ms roundtrip | 合成视觉/触觉输入 |
| UniVTAC adapter | 完整执行 `(50, 8)` | fake task，不是实际仿真 |
| 4090 闭环仿真 | 用户观察 5/5 成功，run exit code 0 | 单任务、5 episodes、非正式评测 |
| WebRTC 视频 | 22.27 秒、VP8、4096×2560 | 可见末次插孔过程连续运动与完成阶段 |

## 4090 闭环结果与证据边界

用户在 2026-08-03 观察五个 episode 全部成功。返回的控制台片段直接保存了：

```text
[2026-08-03 09:22:35] [4  ] Seed 1000003 success after 52.25 s.
steps: 662, actions: 207.
Total 4/4(100.00%) success.
Setting seed: 1000004
```

片段随后记录第五个 episode 执行至 step 568，并进入 Kit 关闭阶段；根摘要记录
`local_exit_code=0` 和 `status=completed`。但原生脚本的最终 `Final Result` 没有进入保存的
日志，根汇总器也没有方法专属 parser，因此 `primary_metrics` 和 `results` 仍为空。

据此，本次可以确认跨机 ZMQ 推理、4090 UniVTAC 仿真和 WebRTC 观察的工程闭环已完成；
“5/5”保留为用户观察到的方向性 smoke 结果。机器文本可直接复核到 4/4 和第五回合已运行，
不能把空 `results` 改写成机器解析的正式 100% 指标。本次也不构成真机 WebSocket 验证或
模型质量结论。
