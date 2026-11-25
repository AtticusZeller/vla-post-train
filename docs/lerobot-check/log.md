# lerobot-check Log

## 2026-11-25 · 第二期：分布、标定与补采改为 viewer 原生面板

- **背景与目的：** 用户试用第一期后认为 HTML 报告和 agent 文字建议太长，真正需要的是能在现场执行的补采清单（物体放哪、
  朝哪），并能区分"数据少"和"覆盖窄、背轨迹"。分析全部改成 viewer 内的可视化，补采位置画回头部相机画面。
- **实现思路：** lerobot-check 只产出机器可读的 JSON（`distribution`、`suggest`、`calibrate`），viewer 负责显示和交互，
  两边通过 `.xense-viewer/` 下的文件衔接（见[概览](overview.md)）。删除精细窗口、速度检查、两两相对位移、`mix`、HTML 报告
  和 `advice.md`。头部相机外参按臂与工具点偏移联合求解，用户在 viewer 中点选指尖。补采面板在用户画的多边形内优先抽空白、
  其次稀疏的格子，并生成密集 / 边缘 / 空白三类测试点，用于补采前后在同一批点上对比真机成功率。
- **组件变化：**
  - lerobot-check 新增 `distribution`、`suggest`、`calib-frames`、`calibrate`、`exemplars`，删除 `report`、`mix`。
  - viewer 新增 DISTRIBUTION、CALIBRATION、COLLECTION 三个标签页，删除报告 iframe；保存 Subtask 标注后自动重算分布。
  - Subtask 面板增加"标记本 episode 已复核"。
  - 标定页增加离群"复查"标记、"换一帧"，跳过帧默认收起。
- **主要文件：**
  - lerobot-check：`src/lerobot_check/analysis.py`（分布与指标）、`calib.py`（选帧与标定）、`suggest.py`、`render.py`
    （含 `exemplars`）、`docs/distribution.md`（JSON 字段说明）、`docs/annotate.md`（agent 标注流程）。
  - viewer：`src/components/{distribution,calibration,collection}-*.tsx`、`src/utils/distributionMetrics.ts`
    （按 episode 选择重算指标）、`src/lib/lerobot-check-runner.ts`（调用 CLI）。
- **任务变化：** `pack_iphone_box_1119` 的 `close_lid` 拆为 `move_lid` / `flip_lid` / `close_lid`，任务变为 5 个 subtask，
  名称与 prompt 见概览（用户确认，2026-11-25）。分界规则改为"最后一次松开且放稳"，`flip_lid` 例外，写进 task spec 注释。
  agent 第一版 5 条的分界有系统性偏差：`flip_lid` 平均晚 1.7 s，个别抓放段早结束 2–3 s。用户复核改正后作为分界样例
  （`exemplars`），由 agent 精标前对照。
- **验证：**
  - 分布指标：鸡蛋盒全量 121 条 `distribution` 用时 4 s；viewer 端重算的指标与 CLI 对同一 episode 选择的输出最大差 8.9e-16。
  - 标定解算：合成相机（偏移 18 cm、点选噪声 2 px）下标定 RMS 1.6–1.8 px，偏移误差 < 4 mm。
  - 补采采样：合成标定下补采位置 40/40 落在多边形内。
  - 用户实测标定：右臂 RMS 2.7 px、留一 4.5 px；左臂内点 4.0 px、留一 6.8 px，达到 ≤ 5 / 8 px 的验收线，用户确认可用。
  - 测试：lerobot-check 89 项，viewer 721 项。
  - 试用中修复的问题：
    - 标定页切帧时 seek 卡死，点击会记在旧画面上；
    - 标定与分布的位置原用法兰 TCP，有标定时改为工具点；
    - Overlay 与 Parquet 跳转把全局行号当成文件内行号，只有第一个数据文件里的 episode 正确；
    - 最后一段终点改为空值后，viewer 拒读 `distribution.json`，原因是 viewer 的测试样例没有跟 lerobot-check 同步。

## 2026-11-24 · 第一期：标注表、agent 标注与 N 段 prompt 重标

- **背景与目的：** 多阶段长程任务改用 subtask prompt 训练（用户决定，2026-11-23），需要一张逐 episode、逐 subtask 的
  标注表作为分界的唯一来源，并据此重标 prompt 和分析补录。分析依赖不能进与 `xense-openpi` 共用环境的 `lerobot-xense`，
  所以新建独立仓库 `AtticusZeller/lerobot-check`。
- **实现思路：** 标注表为人可编辑的 CSV，半开区间、首尾相连，`lerobot-check validate` 是唯一的格式校验。agent 由粗到细看图
  标注：单路相机约 1 s 间隔粗扫，再在分界 ±1 s 内细看；夹爪开度信号不可靠，`propose` 只作提示。subtask 以物体被松开并
  放稳为界，松开后的回撤归下一段。人工复核在 viewer 的 Subtask 面板完成，保存时只把改动的行记为 `human`。
- **组件变化：** lerobot-check 的 `info`、`propose`、`render`、`validate`、`relabel`、`verify-relabel`；
  viewer fork 登记为 `methods/xense-lerobot-viewer`，新增 Subtask 面板。
- **主要文件：** lerobot-check `src/lerobot_check/schema.py`（标注表与 task spec 契约）、`relabel.py`（逐帧写 `task_index`，
  视频硬链接）、`docs/annotate.md`；viewer `src/components/subtask-panel.tsx`、`src/utils/subtaskCsv.ts`。
- **验证：**
  - `relabel` 回归：与旧两段 `relabel.py` 在鸡蛋盒 121 个 episode、337238 帧上逐帧 `task_index`、`tasks.parquet`、非 task 列与
    245 个视频硬链接零差异。
  - agent 盲标鸡蛋盒 5 条，分界误差 −3 / −39 / +9 / −21 / −9 帧，只有 3/5 在 15 帧以内。偏差来自参考值 `cuts.csv` 的 1 s 量化
    和落点定义不同，用户据此定下"松开放稳"规则后按原因已查明验收。
  - viewer 跳帧原先偏一帧，改为跳到帧区间中点后，与 lerobot-check 解码的同一帧逐像素一致。
