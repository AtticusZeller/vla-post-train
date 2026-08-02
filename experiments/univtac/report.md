# UniVTAC · N0-VTLA 实验报告

## 当前状态

- 云端 H20 推理环境与发布 checkpoint 已部署；
- 同机 ZMQ 推理 smoke 已通过；
- UniVTAC adapter 已通过 fake-task 端到端验证，完整执行 50×8 动作 chunk；
- 本地 RTX 4060 的 5-episode `insert_hole` 闭环验证待用户执行。

## 已有工程证据

| 验证 | 结果 | 边界 |
| --- | --- | --- |
| checkpoint 完整性 | Hugging Face 5/5 文件通过 | 固定 revision `73a514c...` |
| H20 模型加载 | 通过，约占用 8.7 GiB | 不涉及 Isaac Sim |
| 同机 ZMQ 推理 | `(50, 32)`，约 684 ms roundtrip | 合成视觉/触觉输入 |
| UniVTAC adapter | 完整执行 `(50, 8)` | fake task，不是实际仿真 |

实际任务成功率必须等本地 5-episode run 完成后填写。
