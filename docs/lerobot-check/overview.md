# lerobot-check 概览

## 定位

长程多阶段任务改用 subtask prompt 训练后，需要一张逐 episode、逐 subtask 的标注表，并据此判断补采什么。两个仓库分工：

- `methods/lerobot-check`（`AtticusZeller/lerobot-check`，公开）：Python CLI。读 LeRobot v3.0 数据集，负责标注表校验、
  agent 标注辅助（`info`、`render`、`exemplars`）、N 段 prompt 重标（`relabel`）、分布计算（`distribution`）、头部相机标定
  （`calib-frames`、`calibrate`）和补采建议（`suggest`）。
- `methods/xense-lerobot-viewer`（fork `AtticusZeller/xense-lerobot-viewer`）：人工界面。Subtask 面板改分界，DISTRIBUTION、
  CALIBRATION、COLLECTION 三个标签页显示分布、点选标定、画目标区域并导出补采清单。界面通过环境变量 `LEROBOT_CHECK_DIR`
  调用 lerobot-check；未设置时只显示可复制的命令。

训练和推理在 `xense-openpi`，采集在 `lerobot-xense`。各仓库之间通过 LeRobotDataset 和下面这些文件衔接。

## 文件约定

所有标注与分析文件放在本地 LeRobot 根目录的 `.xense-viewer/` 下（默认 `~/.cache/huggingface/lerobot/.xense-viewer/`），
属于数据，不进任何仓库：

| 文件 | 写入方 | 内容 |
| --- | --- | --- |
| `subtasks/<org>__<name>@<rev>.csv` | agent（CLI）、viewer Subtask 面板 | 标注表 |
| `subtasks/<org>__<name>.task_spec.yaml` | 人工 | subtask、prompt、相机、参与臂、物体、覆盖网格参数；分界规则写在各 subtask 上方的注释里 |
| `calib/<org>__<name>.intrinsics.json` | 人工 | 头部相机内参 |
| `calib/<org>__<name>.frames.json` | `calib-frames` | 待点选帧（episode、帧号、臂、TCP、新帧带 `speed_mps`） |
| `calib/<org>__<name>.points.json` | viewer 标定页 | 像素点或 `skipped` |
| `calib/<org>__<name>.head.json` | `calibrate` | 每条臂的外参、工具点偏移、RMS、留一误差、离群点 |
| `targets/<org>__<name>.json` | viewer 补采页 | 头部图像上的目标多边形 |
| `distribution/<org>__<name>@<rev>.json` | `distribution` | 帧占比、物体初始位姿与覆盖、各 subtask 轨迹与指标 |
| `suggestions/<org>__<name>@<rev>.json` | `suggest` | 补采摆放与密集 / 边缘 / 空白三类测试点 |

`<rev>` 取数据集 `.cache/huggingface/trees/<sha>.json` 的 sha，没有时为 `local`。字段说明以 lerobot-check 的
`docs/distribution.md` 为准；agent 标注流程以 `docs/annotate.md` 为准。

**标注表**列为 `repo_id, revision, episode_index, subtask, start, end, contact, grasp, success, annotator, note`。区间半开，
每个 episode 的行首尾相连并覆盖整条 episode，subtask 顺序与 task spec 一致（允许只含连续的一段，对应单阶段补录）。
`contact` 不再标注；`grasp` 保留，物体初始位置取这一帧。`annotator` 为 `agent` / `human` / `converted`；viewer 中改过或
标记"已复核"的行为 `human`。

## 关键约定

- **分界**：抓放类 subtask 在该物体最后一次松开、完全放稳时结束，之后接近下一个物体的运动属于下一段；移动不单独成段。
  有特殊规则的 subtask 在 task spec 注释里写明（如 `flip_lid` 在盖子刚落到盒上时结束，之后的对准与按压归 `close_lid`）。
- **分界样例**：两侧都是 `human` 的分界会成为 `exemplars` 的样例。agent 精标前先看样例，样例与文字规则冲突时以样例为准。
- **轨迹起终点**：只用于可视化与指标。起点取 `grasp` 帧（没有时取首帧），终点取 `end − 1`，最后一个 subtask 不计终点；
  训练用的分界仍包含接近运动。
- **位置**：有标定时用工具点 $p_{tcp} + R_{tcp}\,o$（Flexiv 的 TCP 是法兰，比指尖高约 18 cm），否则用原始 TCP，
  `distribution.json` 的 `provenance.position_point` 标明是哪一种；`suggest` 拒绝混用。
- **标定**：$\pi\big(K,\ T_{cam\leftarrow base}\,(p_{tcp} + R_{tcp}\,o)\big) \approx (u, v)$，每条臂单独求解（solvePnP 初始化，
  鲁棒最小二乘）；残差 > max(3 × 中位数, 15 px) 判为离群。`calib-frames` 只选夹爪闭合（开度 ≤ 0.05，0 为闭合）且 TCP 速度
  ≤ 0.03 m/s 的帧，降低运动模糊和时间错位的影响。
- **补采与测试点**：目标多边形画在头部画面上，可以比现有数据覆盖更大。"数据少"还是"覆盖窄、背轨迹"由真机测试区分：
  补采前后用同一批三类测试点对比成功率。

## 当前数据集：`Xense/pack_iphone_box_1119`

`v3.0` → `3a8b398b`，`bi_flexiv_rizon4_rt`，121 个 episode，30 fps。5 个 subtask（用户确认，2026-11-25），全部两臂参与：

| subtask | prompt |
| --- | --- |
| `place_insert` | `Place the paper insert into the box.` |
| `place_phone` | `Place the iPhone into the box with the camera facing up.` |
| `move_lid` | `Place the box lid next to the box.` |
| `flip_lid` | `Flip the box lid onto the box.` |
| `close_lid` | `Close the box lid.` |

头部相机为 RealSense D435（序列号 `346522071766`），640×480，$f_x = 606.016113$、$f_y = 605.505737$、$c_x = 323.207703$、
$c_y = 244.806580$，畸变全 0。截至 2026-11-25：episode 0 / 15 / 30 / 45 / 60 / 75 / 90 / 100 / 110 / 120 共 50 行，全部由用户复核（`human`）。
标定结果（`head.json`）：右臂 11 点 RMS 2.7 px、留一误差 4.5 px；左臂 15 点中 13 个内点，内点 RMS 4.0 px、留一误差 6.8 px。
