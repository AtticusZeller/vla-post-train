# lerobot-check 概览

## 定位

长程多阶段任务改用 subtask prompt 训练后，需要一张逐 episode、逐 subtask 的标注表，并据此判断补采什么。两个仓库分工：

- `methods/lerobot-check`（`AtticusZeller/lerobot-check`，公开）：Python CLI。读 LeRobot v3.0 数据集，负责标注表校验、
  agent 标注辅助（`info`、按分界找帧的 `window-sheet`、结束帧拼图 `boundary-sheet`、`render`、`exemplars`）、N 段 prompt 重标（`relabel`）、物体层分割（`object-poses`）、分布计算（`distribution`）、头部相机标定
  （`calib-frames`、`calibrate`）、补采建议与轮廓计划（`suggest`、`mask-template`、`mask-overlays`、`collection-plan`）。一次性 TCP 转换工具（`retarget-tcp`、`verify-tcp`）仅保留在独立分支 `AtticusZeller/tcp-retarget`，不合入 `main`（用户决定，2026-11-26）。
- `methods/xense-lerobot-viewer`（fork `AtticusZeller/xense-lerobot-viewer`）：人工界面。Subtask 面板改分界，DISTRIBUTION、
  CALIBRATION、COLLECTION 三个标签页分别显示两层分布（物体层 / 末端层切换）、点选标定、画目标区域并生成/审核/导出补采计划。界面通过环境变量 `LEROBOT_CHECK_DIR`
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
| `object-poses/<org>__<name>@<rev>.json` | `object-poses` | 第 0 帧头图物体轮廓、反投位姿与跳过记录（侧车） |
| `distribution/<org>__<name>@<rev>.json` | `distribution` | 帧占比、物体两层初始位姿与覆盖（末端层及可选 `object_layer`）、各 subtask 轨迹与指标 |
| `suggestions/<org>__<name>@<rev>.json` | `suggest` | 补采摆放与密集 / 边缘 / 空白三类测试点 |
| `mask-templates/<org>__<name>@<rev>/<obj>.json` | `mask-template` | 已审核的物体轮廓模板或拒绝模板（含 `anchor_layer`） |
| `plans/<org>__<name>@<rev>.json` | `collection-plan` | 按轮补采计划、目标轮廓与采集进度 |

`<rev>` 取数据集 `.cache/huggingface/trees/<sha>.json` 的 sha，没有时为 `local`。字段说明以 lerobot-check 的
`docs/distribution.md`、`docs/collection-plan.md` 为准；agent 标注流程以 `docs/annotate.md` 为准。

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
- **两层分布（物体层 / 末端层）**：每个物体在 `distribution.json` 中可同时保存两层初始位姿。**末端层**（`poses`）取抓取或
  释放事件帧的夹爪位姿：有标定时用工具点 $p_{tcp} + R_{tcp}\,o$（补偿录制 TCP 到指尖中点的偏移；例如 `pack_iphone_box_1119` 原
  `xenseflare` TCP 残余偏移约 38–41 mm，转换到 `taccap-rs00` 后收缩到约 3–7 mm），否则用原始 TCP，
  `provenance.position_point` 标明种类，`suggest` 拒绝混用。**物体层**（`object_layer`）由 `object-poses` 从每条 episode
  第 0 帧头图按 `layout_box` 分割后反投到 `plane_z_m` 得到，取轮廓质心与最小外接矩形长轴朝向，按
  `min(yaw_symmetry_deg, 180°)` 折叠、不分头尾。补采建议、补采计划和轮廓模板默认使用物体层（缺失时报错，不静默回退），
  末端层保留展示。
- **标定**：$\pi\big(K,\ T_{cam\leftarrow base}\,(p_{tcp} + R_{tcp}\,o)\big) \approx (u, v)$，每条臂单独求解（solvePnP 初始化，
  鲁棒最小二乘）；残差 > max(3 × 中位数, 15 px) 判为离群。`calib-frames` 只选夹爪闭合（开度 ≤ 0.05，0 为闭合）且 TCP 速度
  ≤ 0.03 m/s 的帧，降低运动模糊和时间错位的影响。
- **补采与测试点**：目标多边形画在头部画面上，可以比现有数据覆盖更大。"数据少"还是"覆盖窄、背轨迹"由真机测试区分：
  补采前后用同一批三类测试点对比成功率。

## 当前数据集：`Xense/pack_iphone_box_1119`（与 `taccap-rs00` 转换版）

原始录制集 `Xense/pack_iphone_box_1119`（`v3.0` → `3a8b398b`，`bi_flexiv_rizon4_rt`，121 个 episode，274,083 帧，30 fps）使用了错误的 `xenseflare` 工具 TCP。已于 2026-11-26 通过 `lerobot-check retarget-tcp` 转换到现役 `taccap-rs00` TCP 并公开上传至 Hub：

- 原始单任务转换版：`Xense/pack_iphone_box_1119_taccap_rs00`（`v3.0` → `5c9229b2`）
- 5 段 subtask 重标转换版：`Xense/pack_iphone_box_1119_taccap_rs00_subtask`（`v3.0` → `b017a723`）

5 个 subtask（用户确认，2026-11-25），全部两臂参与：

| subtask | prompt |
| --- | --- |
| `place_insert` | `Place the paper insert into the box.` |
| `place_phone` | `Place the iPhone into the box with the camera facing up.` |
| `move_lid` | `Place the box lid next to the box.` |
| `flip_lid` | `Flip the box lid onto the box.` |
| `close_lid` | `Close the box lid.` |

头部相机为 RealSense D435（序列号 `346522071766`），640×480，$f_x = 606.016113$、$f_y = 605.505737$、$c_x = 323.207703$、
$c_y = 244.806580$，畸变全 0。截至 2026-11-26：全部 121 条 episode 共 605 行标注完成并通过 `validate`（`human` 86 行、`agent` 519 行），已完成 5 段 prompt 重标与 `taccap-rs00` TCP 转换；物体层 483/484 个物体实例识别成功（仅 ep43 `box_lid` 因第 0 帧手腕遮挡跳过），4 个物体（含 `box_base`）均已按物体层建立轮廓模板。`Xense/pack_iphone_box_1119_taccap_rs00` 标定结果（`head.json`）：左臂 15/15 内点，RMS 2.10 px、留一误差 3.22 px、`tool_offset` 2.9 mm；右臂 13/13 内点，RMS 1.49 px、留一误差 2.58 px、`tool_offset` 7.3 mm。
