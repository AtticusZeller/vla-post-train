# lerobot-check Log

## 2026-11-26 · 分布增加物体层、补采与轮廓改用物体层、viewer 支持两层切换

- **背景与目的：** 原有分布只记录夹爪抓取或释放事件帧处的工具点位姿（末端层）。未被抓取的物体（如 `box_base` 借用
  `place_insert` 释放插片的点）缺乏稳定锚点，轮廓投影偏约 10 px、15°，只能写拒绝模板、无法进入多物体补采轮次。
  用户决定（2026-11-26）将分布拆为**物体层**（第 0 帧头图分割得到的物体本身初始位姿）与**末端层**（原有事件帧工具点位姿，
  保留展示）；补采建议、补采计划和轮廓模板默认改用物体层，矩形朝向按 180° 折叠不分头尾；viewer 的 DISTRIBUTION 页同步支持
  两层切换。
- **实现思路：**
  - **物体层计算（[lerobot-check#12](https://github.com/AtticusZeller/lerobot-check/issues/12)）：** 在 `task_spec.yaml` 中
    为物体配置第 0 帧头图固定布局框 `layout_box`（可选 `object_plane_z_m`，默认取末端层 `median_z_m`）。`object-poses`
    每帧做一次 SAM 2.1 图像编码，用框内正点网格与多掩码筛选提取不触框边界的单物体掩码（不依赖亮度阈值，可复用到其他固定布局
    任务），反投到对应臂基座平面 `z = plane_z_m`，取轮廓质心和最小外接矩形长轴朝向，折叠周期为
    `yaw_period_deg = min(yaw_symmetry_deg, 180)`（要求对称周期 `>= 180` 或整除 `180`）。支持
    `--prompt-box EP:OBJECT=x0,y0,x1,y1` 覆盖个别偏离固定布局的 episode，支持 `--sheet` 输出复核拼图，并输出物体坐标系下的
    末端抓取偏移统计。`distribution` 自动读取侧车写出 `object_layer` 与 `provenance.object_poses_sha256`；无侧车时输出逐字节
    不变。
  - **下游改用物体层（[lerobot-check#13](https://github.com/AtticusZeller/lerobot-check/issues/13)）：** `suggest`、
    `collection-plan generate`、`mask-template` 默认 `--layer object`（可用 `--layer tool` 显式切回末端层）。缺少
    `object_layer` 时直接报错，不静默回退；模板记录 `anchor_layer`、计划记录 `layer`，`mask-overlays` 与 `collection-plan`
    拒绝跨层混用。
  - **viewer 两层切换（[xense-lerobot-viewer#8](https://github.com/AtticusZeller/xense-lerobot-viewer/issues/8)）：**
    DISTRIBUTION 页存在 `object_layer` 时默认展示物体层，可在物体层与末端层间切换，切换数据集时重置选择；单个物体缺少物体层
    时该卡片回退展示末端层并提示；180° 周期的物体层朝向以无箭头线段绘制，末端层保持箭头；不含物体层的旧分布文件卡片渲染保持
    逐字节不变。
- **组件变化：**
  - lerobot-check 新增 `object-poses` 命令与 `object-poses/<org>__<name>@<rev>.json` 侧车；`distribution` 增加可选
    `object_layer`；`suggest`、`collection-plan`、`mask-template` 新增 `--layer object|tool` 并默认 `object`。
  - viewer 的 DISTRIBUTION 页新增两层切换控件、无箭头轴向绘制与物体层跳过列表。
- **主要文件：**
  - lerobot-check：`src/lerobot_check/object_pose.py`（第 0 帧分割、反投与偏移统计）、`segmentation.py`、`analysis.py`、
    `suggest.py`、`masks.py`、`collection_planner.py`、`docs/distribution.md`、`docs/collection-plan.md`。
  - viewer：`src/utils/distributionData.ts`、`distributionMetrics.ts`、`src/components/distribution-panel.tsx`、
    `distribution-object-card.tsx`。
  - 本地数据：`.xense-viewer/object-poses/`、`.xense-viewer/distribution/`、
    `.xense-viewer/mask-templates/Xense__pack_iphone_box_1119@3a8b398b…/`（4 个物体按物体层重建，含 `box_base` 真实轮廓；
    原末端层模板与未采的旧末端层计划备份于 `annotate-batch/pack_iphone_box_1119/`）。
- **验证：**
  - 单元测试与静态检查：lerobot-check 327 项 pytest、ruff、ty 全部通过，无侧车 `distribution.json` 与改前逐字节一致；
    viewer `bun run validate` 742 项测试通过，无物体层老文件卡片渲染逐字节一致。
  - 真实数据 `Xense/pack_iphone_box_1119`（121 条，CUDA 约 58 s，5 条偏离布局 episode 共 9 处 `--prompt-box`）：
    484 个物体实例中 483 个识别成功，唯一跳过为 ep43 `box_lid`（第 0 帧被右手腕遮挡，可见尺寸 16.6×13.4 cm 偏离中位数
    20.2×9.5 cm）。用户审阅 11 页审核拼图与 4 物体模板预览后认可（2026-11-26）。
  - `box_base` 物体层模板（39 顶点）投影至 15 条其他 episode：轮廓平均误差 0.64 px（最大 1.37 px）、平均 IoU 0.964
    （最小 0.912）、质心差 0.15 px、朝向差 +0.17°。试生成 25 轮 × 每轮 2 物体的补采计划，`box_base` 进入 13 轮且所有目标
    均带轮廓。
  - 物体坐标系下末端抓取点偏移标准差：`paper_insert` 0.83 / 0.94 cm、`iphone` 0.71 / 2.03 cm、`box_lid` 1.90 / 1.28 cm。
    后两项超过原定 1 cm 指标，系人工抓取位置变化及个别 episode 抓前碰动所致，不能衡量物体层测量精度，用户认可收尾
    （2026-11-26）。

## 2026-11-26 · `pack_iphone_box_1119` 全量标注、结束帧拼图自查与 5 段 prompt 重标

- **背景与目的：** subtask prompt 训练需要 121 条 episode 全部标注。原流程每个分界都要细看，agent 标得慢；用户实际
  验收只看前 4 段的最后一帧（夹爪已松开、回到物体上方空中为对），所以把精度交给"结束帧拼图 + agent 自查"，粗扫只求快。
- **实现思路：**
  - 4 个 agent 按 episode 分组并行初标，各写各的文件，合并时只覆盖 `agent` 行。
  - 新增 `boundary-sheet`：每个分界一张拼图，每条 episode 一格（头部裁剪 + 两个腕部的 `end − 1`）。4 个 agent 各管
    一个分界，循环"看图 → 改 `agent` 行 `end` → 只重渲染改过的 episode"，共改 237 处；`human` 行只报告不改。
    用户看完整拼图后分三轮改了 13 处，最终相对 agent 结果：`place_insert` 只有 ep80 提前 0.5 s（另 6 条改后又改回），
    `place_phone` ep50 / 75 / 120 推后 3 / 0.5 / 0.5 s，`move_lid` ep2 提前 1.3 s、ep3 / 65 推后 0.7 s；`flip_lid` 无改动。
  - 新增 `window-sheet`，粗扫改为按分界、由粗到细的窗口搜索：每个分界一个 agent，按经验窗口第一轮 4 s 一格、第二轮
    约 0.5 s 一格，8 条 episode 拼一张图，只判断"这一段在这一帧是否已结束"。
  - `grasp` 取夹爪在物体上闭合的那一帧，只在 task spec 有 `event: grasp` 物体的 subtask 上标。
  - 盲测暴露的规则歧义写进 task spec 注释（用户定）：`place_phone` 在右夹爪松开抬起时结束，之后左夹爪的按压归
    `move_lid`；`flip_lid` 在盖子第一次碰到盒子（边缘先碰也算）时结束。
- **组件变化：** lerobot-check 新增 `boundary-sheet`、`window-sheet` 两个命令；`docs/annotate.md` 改为四步：窗口搜索初标 →
  组装标注表 → 结束帧拼图自查 → `validate`。逐分界细看、`exemplars`、`propose` 降为可选工具。
- **主要文件：** lerobot-check `src/lerobot_check/render.py`（拼图）、`docs/annotate.md`（流程）；标注表
  `.xense-viewer/subtasks/Xense__pack_iphone_box_1119@3a8b398b….csv`；重标数据集
  `~/.cache/huggingface/lerobot/Xense/pack_iphone_box_1119_subtask`。
- **验证：**
  - 标注表 `validate` 输出 `605 rows covering 121/121 episodes`；重标后 5 个 task 帧数为
    66061 / 65267 / 22348 / 67798 / 52609（共 274083 帧），`verify-relabel` 通过。
  - `window-sheet` 盲测：10 条人工复核 episode，只看画面、不读标注表，与人工 `end` 误差在 1 s 内的条数为 `place_insert`
    8/10、`place_phone` 8/10、`move_lid` 10/10、`flip_lid` 8/10，每个分界约 10 分钟，多数 episode 2–3 轮出图。
    6 条超差中 3 条是搜索误判（含夹爪抬起后又回压，已在 `annotate.md` 加 2 s 后复查一帧），3 条是上面两条规则的歧义。
    未达计划的 9/10，用户认可此精度后收尾。
  - 限制：自查循环曾按"左夹爪仍在按压"推后部分 `place_phone` 结束帧（ep89–119 中多条推后 30–75 帧），按新规则可能
    偏晚；用户看过整张拼图后只改了 ep50 / 75 / 120，其余未逐条回查。

## 2026-11-25 · 分界样例消除了 agent 标注的系统性偏差

- **背景与目的：** agent 第一版标注 `pack_iphone_box_1119` 的 5 条 episode，分界平均偏约 1 s，而且偏差有规律：
  `flip_lid` 结束平均晚 1.7 s（落盖后的对准被算进去），个别抓放段早结束 2–3 s（放下后的调整被划给下一段）。
  需要验证：用户复核过的分界做样例（`exemplars`）后，agent 能否对上用户的标准。
- **实现思路：** agent 按 `docs/annotate.md` 标注新的 episode 15 / 45 / 75 / 100 / 110，每放一个分界或 `grasp` 前，
  先看用户复核过的 3 个样例；样例与文字规则冲突时以样例为准。另存 agent 的原始输出，再与用户复核后的结果逐行比较。
- **组件变化：** 无代码改动。`annotate.md` 补充：凡是夹持物体的 subtask 都要标 `grasp`（包括 task spec 没有对应物体的
  `flip_lid`），因为它同时决定轨迹起点。
- **主要文件：** lerobot-check `docs/annotate.md`；标注表 `.xense-viewer/subtasks/Xense__pack_iphone_box_1119@3a8b398b….csv`
  现有 10 条 episode、50 行，全部由用户复核。
- **验证：**

  | 分界 | 第一轮平均误差（s） | 第二轮平均误差（s） |
  | --- | --- | --- |
  | `place_insert` → `place_phone` | 1.1 | 0 |
  | `place_phone` → `move_lid` | 1.2 | 0.08（只有 episode 45 一处：晚 12 帧，手机还没完全落进盒里） |
  | `move_lid` → `flip_lid` | 0 | 0 |
  | `flip_lid` → `close_lid` | 1.7 | 0 |

  其余 19 个分界与 20 个 `grasp` 用户都未改动。agent 标 5 条 episode 用了 21 分钟（含看 8 组样例）。
  结论：两类系统性偏差都消失了。规则写成文字容易有歧义，样例可以消除这种歧义（Agent 推断，基于 5 条样本）。

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
  - 用户验收（2026-11-25）：DISTRIBUTION 页在 10 条复核数据上"基本 ok"。COLLECTION 页作为补采参考可用，但现场对着导出图片
    肉眼摆放不实用；改为"目标物体 mask 叠加到实时相机画面"另立
    [xense-lerobot-viewer#1](https://github.com/AtticusZeller/xense-lerobot-viewer/issues/1)。
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
