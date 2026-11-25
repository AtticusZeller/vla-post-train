# lerobot-check Plan

## 第一期：subtask 标注表、数据分布分析与 N 段 prompt 重标

多阶段长程任务改用 subtask prompt 训练（用户决定（2026-11-23）），难的阶段单独补录。补录前要知道：各阶段和精细接触
窗口的帧占比、接触阶段是否真的放慢、物体初始位置和轨迹覆盖到哪里、补多少条后比例变成多少。这些分析和 prompt 重标都
从同一张逐 episode、逐 subtask 的标注表派生，所以新建独立仓库 `AtticusZeller/lerobot-check`（公开，用户决定（2026-11-23）），
登记为 `methods/lerobot-check`。

边界：

- 独立仓库，不写进 `lerobot-xense`：后者是团队共用的采集驱动 fork，且与 `xense-openpi` 共用环境，分析依赖会污染它。
  本仓库用自己的 uv 环境，依赖 PyPI 上能读 v3.0 数据集的 `lerobot` 固定版本，不依赖 `lerobot-xense` 和硬件 SDK。
- 第一期只用本体数据（TCP 位姿、夹爪开度），不用触觉图像（用户决定（2026-11-23））。head 相机标定和 SAM3 分割放第二期。
- TCP 位姿在各自机械臂基座坐标系下；两臂之间没有外参，所以图按臂分开画。
- subtask 以"松开物体"为界划分，抓起和放下属于同一个 subtask（用户决定（2026-11-23））。
- 补录 episode 的结尾在 subtask prompt 下语义一致，不裁尾；补充比例靠采集条数控制，openpi loader 不改（用户决定（2026-11-23））。
- 标注文件和报告是数据，不进公开仓库：CLI 用参数指定路径，仓库 `.gitignore` 忽略默认输出目录。
- 4 阶段任务的数据集 repo id、subtask 列表和 prompt 由用户后续提供；第一期用本地已缓存的
  `Xense/bi_elite_cs66_rt_egg_carton_to_tray_1016_fixed`（122 个 episode，30 fps，两个 subtask）开发和验收。

### 契约

**标注表**（CSV，一个数据集 revision 一个文件，人可直接编辑）：

| 列 | 含义 |
| --- | --- |
| `repo_id`, `revision` | 数据集与其 revision |
| `episode_index` | 数据集内 episode 编号 |
| `subtask` | task spec 中的 subtask 名 |
| `start`, `end` | episode 内帧号，半开区间 `[start, end)` |
| `contact`, `grasp` | 可空；夹爪接触物体、完成夹持的帧 |
| `success` | 该 subtask 是否成功 |
| `annotator` | `agent` / `human` / `converted`（由旧格式转换） |
| `note` | 可空 |

校验规则：每个 episode 的行按 `start` 排序后首尾相连、覆盖全部帧（第一行 `start=0`，`start_{k+1}=end_k`，最后一行
`end=episode 长度`）；`contact`、`grasp` 若存在须满足 `start ≤ contact ≤ grasp < end`；`subtask` 必须在 task spec 中；
一个 episode 内 subtask 顺序与 task spec 顺序一致（允许只含其中连续的一段，对应单阶段补录）。prompt 在 `end_k` 处切换。
标注表可以不含某些 episode：分析命令跳过并在输出中列出；`relabel` 要求每个 episode 都有标注，否则报错。

**task spec**（YAML，每个任务一个）：

- `subtasks`：有序列表，每项 `name` 和 `prompt`（逐字等于训练和客户端使用的字符串）。
- `objects`：每项 `name`、`subtask`、`event`（`grasp` 取 `grasp` 帧、`release` 取 `end - 1` 帧的 TCP 位姿）、`arm`
  （`left` / `right`）、`yaw_symmetry_deg`（如 360 / 180 / 90，yaw 按此折叠）。
- `fine_window_s`：精细窗口长度 Δ，默认 1.0 s。精细窗口定义为 $[\max(start, contact-\Delta), grasp]\ \cup\ [\max(start, end-\Delta), end)$，
  无 `contact`/`grasp` 时只取后一段。
- 覆盖网格参数：xy 格子边长（默认 5 cm）、yaw 分箱（默认 30°）、稀疏阈值。

### Task T1：仓库骨架与标注 CLI

**Change**

- [x] uv 项目（Python ≥ 3.12），包名 `lerobot_check`，CLI 入口 `lerobot-check`；仓库 `AGENTS.md`（英文）写明环境、测试命令、
      数据不进仓库；`README.md`（中文）。
- [x] 标注表与 task spec 的读写和校验，按上面的契约实现；task spec 附鸡蛋盒示例（两个 prompt 取自
      `xense-openpi` 分支 `feat/egg-carton-subtask` 的 `scripts/egg_carton_two_stage/egg_prompts.py`）。
- [x] `propose`：从 `observation.state` 的夹爪开度检测每臂的闭合 / 张开事件（阈值加迟滞，避免抖动产生成串事件），从 TCP
      xyz 差分得到线速度并找出低速段；输出每个 episode 的候选事件表。
      **审查修正（2026-11-24）：** 绝对阈值（闭合 ≤ 0.5、张开 ≥ 0.7）在鸡蛋盒数据上漏掉夹蛋阶段的全部夹取：episode 0
      左夹爪先夹起一个夹子工具，之后在 0.24–0.40 之间往复，从不回到 0.7 以上。改为两类信号：按相对幅度的迟滞检测开合动作
      （从上一个极值变化 ≥ δ 才算一次闭合 / 张开，不依赖绝对开度）；以及 action 与 state 的夹爪差持续为负的"挤压"区间
      （指令已闭合、被物体挡住，例如 episode 0 帧 1380–1490 action 0.00、state 0.26）。两者都只是候选，由标注 agent 看图确认。
      **用户决定（2026-11-24）：** 夹爪开合不可靠，标注以 agent 按自选帧率直接看图为主，`propose` 降为可选提示，不再为它调参。
      标注流程改为由粗到细：先用单路相机、约 1 s 间隔扫完整个 episode，定位各分界、接触和夹持的大致位置；再在每个位置
      ±1 s 内用三路相机、1–3 帧间隔精确定位。`render` 增加网格排布（单路相机多帧按行列排），降低粗扫的 token 消耗。
- [x] `validate` 对照数据集实际 revision：标注表的 `revision` 与本地检测到的 commit 不一致时报违规，检测不到时给出警告
      （审查补充（2026-11-24）：原实现不检查 revision，数据集被重写后旧标注会静默通过）。6D 旋转的约定从 `lerobot-xense` 写数据的代码确认，
      写进 docstring。
- [x] `render`：给定 episode 和帧号列表（或候选事件 ± 窗口、步长），把 head 与两个腕部相机的图像拼成带帧号的 PNG，供
      agent 查看后判断；尺寸可调以控制 token。
- [x] `validate`：对照数据集元数据中的 episode 长度检查标注表，逐条打印违规并以非零退出。
- [x] `docs/annotate.md`（英文，面向标注 agent）：用 `propose` → `render` → 写标注表 → `validate` 的流程和判定准则。
- [x] `examples/egg_carton/`：鸡蛋盒 task spec，以及 `cuts.csv` → 标注表的转换脚本（输入为原 122 个 episode 的数据集，
      `cuts.csv` 用删除 episode 108 之前的编号，`cut_frame = round(cut_s × 30)`；108 不写入；`grasp` 取每个 subtask 内 `propose`
      报出的第一次夹爪闭合帧，`annotator=converted`）。T3、T4 共用。

**Verification**

1. [x] 单测覆盖校验规则的每一条违规（缺帧、重叠、越界、`contact > grasp`、未知 subtask、顺序颠倒），以及单阶段补录 episode 合法。
2. [x] 单测：构造夹爪开度序列（含阈值附近抖动），`propose` 每次真实开合只报一个事件。
3. [x] 在鸡蛋盒数据集上实跑 `propose` 和 `render`（至少 2 个 episode）。

**Done**

- [x] 上述测试在本仓库 uv 环境中通过；`ruff` 与类型检查对新代码无报错。
- [x] 鸡蛋盒 episode 的 `render` PNG 中能看到三路相机和正确帧号（coordinator 抽看 ep0 事件图、1 s 粗扫网格；2026-11-24 合入本地 main `45e3019`，37 项测试通过）。

### Task T2：agent 标注小样本准确度

**Change**

- [ ] 按 `docs/annotate.md` 由 agent 为鸡蛋盒数据集 5 个 episode 标注两个 subtask 的分界（不标其余 episode，正式使用时再放开，
      用户决定（2026-11-23））。

**Verification**

1. [ ] 与 `cuts.csv`（注意它用删除 episode 108 之前的编号，`cut_frame = round(cut_s × 30)`）对比，报告每个 episode 的分界误差帧数。

**Done**

- [ ] 误差表写进 `docs/lerobot-check/log.md`；5 个中至少 4 个误差 ≤ 15 帧（0.5 s）。不达标时记录原因，不调阈值凑数。

**结果（2026-11-24）：未达标，3/5。** agent 盲标 episode 0 / 30 / 60 / 90 / 120 得 897 / 411 / 369 / 579 / 381，`cuts.csv` 为
900 / 450 / 360 / 600 / 390，误差 −3 / −39 / +9 / −21 / −9 帧；5 条共看 20 张图（每条粗扫 2 张、细看 2 张）。

- agent 的分界都落在盒盖平放到桌面后约 6 帧；`cuts.csv` 全是整数秒（自身就有 ±15 帧量化误差），且落点不一：episode 0 / 60
  在盖子落平附近，episode 30 / 90 在右臂收回之后。coordinator 看了 episode 30 帧 399–459：盖子约在 411 落平，411–459 是右臂
  从盖子旁收回，人工 450 对应收回结束。误差来自两边对"分界"的落点定义不同，以及参考值的 1 s 分辨率（Agent 推断，基于这 5 条）。
- 暴露的流程问题：没有查看 revision 和 episode 长度的 CLI；`--frames a:b:s` 含右端点，与标注表的半开区间不一致；
  `annotate.md` 没说清松开后的回撤动作归哪个 subtask、双臂时以哪条臂为准；粗扫时不需要看完整条 episode 的所有图。


**用户决定（2026-11-24）：** 分界定在 subtask 的物体被松开并放稳的那一刻（开盒即盒盖躺平），松开后的回撤归下一个 subtask。
agent 的落点符合这条规则，T2 按"原因已查明"接受，不再重测；`cuts.csv` 只作旧参考。

### Task T3：分析报告

**Change**

- [x] `report`：输入一个或多个（数据集, 标注表），输出一个静态 HTML，多数据集叠加时按数据集着色（用于对比完整数据与单阶段补录）：
  - 帧占比：每个 subtask 的帧数和占比，以及精细窗口帧数和占比；
  - 速度：每个 episode 精细窗口与其余帧的 TCP 线速度中位数，比值超过阈值的 episode 列为"未放慢"；
  - 物体初始位置：按 task spec 的 `objects` 取事件帧 TCP 位姿，画 xy 散点和 yaw 分布，并画物体两两相对位移；
  - 轨迹：每个 subtask、每条臂在基座坐标系下的 3D TCP 轨迹，按归一化时间着色；有 `grasp` 的 subtask 再画以 `grasp`
    帧 TCP 为原点的轨迹，图注写明它只反映接近方向的多样性；
  - 覆盖：每个物体的 xy 格子 × yaw 分箱计数，列出低于稀疏阈值的格子。
- [x] `mix`：输入若干（数据集, 标注表, 重复次数），输出合并后各 subtask 与精细窗口的帧数和占比（不写数据集）。
- [x] `suggest`：从稀疏格子中为每个物体独立抽样，输出下一批 N 条的摆放清单（xy、yaw）。物体间的碰撞不处理，在输出里注明。

**Verification**

1. [x] 单测：手算的小标注表上帧占比、精细窗口（含与 `start` 截断、无 `contact` 的情况）、`mix` 重复次数结果一致。
2. [x] 单测：yaw 折叠（180° 对称时 170° 与 −10° 归同一箱）。
3. [x] 用由 `cuts.csv` 转换的标注表（只含分界，无 `contact`/`grasp`；episode 108 不在其中）在鸡蛋盒数据上实跑 `report`、`mix`、`suggest`。

**Done**

- [x] 测试通过；鸡蛋盒报告 HTML 能在浏览器离线打开，五类图都有内容；`mix` 对"原数据 ×1 + 原数据 ×1"给出的占比与单份相同、帧数翻倍。

**结果（2026-11-24）：** 分支 `1cf78f3`，与 T4 的 `cli.py` 冲突由 coordinator 手工合并（`b4496fb`），合并后 57 项测试、ruff、ty 通过。
鸡蛋盒报告 `/tmp/lerobot-check-t3/egg_carton_report.html`（14 MB，内嵌 plotly，无外部链接）。帧占比：`open_carton` 18.70%、
`place_eggs` 81.30%；精细窗口共 2.15%。`mix` 同一数据 ×1+×1 占比不变、帧数翻倍。

- 示例 task spec 把 `egg_carton` 配给左臂，实际开盒时是右臂推盖（episode 0 开盒阶段右臂移动 0.73 m、夹爪不闭合），左臂在拿夹子；
  已改为右臂（`e516b2b`）。
- 契约限制：每个 subtask 只有一组 `contact` / `grasp`。`place_eggs` 里有多次夹蛋，精细窗口和物体位置只覆盖第一次。
  4 阶段任务每个 subtask 只抓放一个物体，不受影响（Agent 推断）。

### Task T4：N 段 prompt 重标

**Change**

- [x] 把 `feat/egg-carton-subtask` 的 `relabel.py` / `verify_relabel.py`（两段、读 `cuts.csv`）移植为 `relabel` / `verify-relabel`
      命令：读标注表与 task spec，支持 N 个 subtask，逐帧写 `task_index`；`tasks.parquet` 行顺序等于 `task_index`；只改 task 相关
      字段，视频硬链接不重编码。保留原脚本的输入检查（缺行、越界等报错且不写出文件）。

**Verification**

1. [x] 回归：在同一输入数据集上，把 `cuts.csv` 转成标注表后运行新 `relabel`，与原 `relabel.py` 的输出逐帧 `task_index`、`tasks.parquet`
      完全一致（含 episode 108 的处理方式与原流程相同）。
2. [x] 单测：3 个及以上 subtask、单阶段补录 episode、标注表非法时不写出文件。
3. [x] `verify-relabel` 在新输出上为 `OK`，对人为改坏一个非 task 字段的副本报错。

**Done**

- [x] 回归比对零差异；单测通过；在鸡蛋盒数据上抽查分界帧前后各 1 帧的 prompt 正确。


**结果（2026-11-24）：** 合入本地 main `ccb9b4c`，48 项测试通过。回归：旧流程（删 108 + 旧 `relabel.py`）与新 `relabel` 在同一份
121 个 episode 的数据上，337238 帧的 `task_index`、`tasks.parquet`、全部非 task 列与元数据、245 个视频硬链接零差异。coordinator
补测：全部 122 个 episode 只标 `place_eggs`（模拟单阶段补录数据集）时，`relabel` 与 `verify-relabel` 正常，`LeRobotDataset` 读出的
prompt 正确；`tasks.parquet` 仍保留未使用的 `Open the egg carton.` 行（0 帧），官方合并按字符串去重，不影响训练。

### Task T5：按 subtask 选相机、中文报告、数据建议、真实数据集分析

用户试用后的反馈（2026-11-24）：agent 切完分界后没有给人复核调整的环节，报告就直接出了；不同 subtask 要看的相机不同（有的看
左腕、有的看右腕，head 有时看不出来），拼三路图应是可选项；报告要以中文为主；希望 agent 根据分析结果给出补数据建议。另外第一期
验收用的是原始数据 `1016_fixed`，实际训练用的是重标后合并了开盒补录的 `Xense/bi_elite_cs66_rt_egg_carton_relabeled_plus_open_1103`
（`v3.0` tag 指向 `fd0f68ff`，174 个 episode，1.63 GB）。工具正确性不受影响（T4 回归必须从原始数据复现旧流程），但真实分析应在训练
用的数据集上做，它的 53 条开盒补录正好检验"完整数据 vs 单阶段补录"的对比。人工复核界面放到 xense-lerobot-viewer（T6），不在本仓库
做静态 HTML（用户决定（2026-11-24））。
**目标数据集更正（用户，2026-11-24）：** 要标注和分析的是 4 阶段装盒任务 `Xense/pack_iphone_box_1119`，不是鸡蛋盒重标数据集；
因此去掉"从逐帧 `task_index` 导出标注表"一项。全局 prompt 为 `Place the paper insert into the box. Place the iPhone into the box
with the camera facing up. Close the box lid.`
任务共 3 个阶段（用户，2026-11-24）：`place_insert`（`Place the paper insert into the box.`）、`place_phone`（`Place the iPhone into
the box with the camera facing up.`）、`close_lid`（`Close the box lid.`），prompt 取自全局 prompt 的三句。

**Change**

- [x] task spec 每个 subtask 增加 `cameras`（标注时看哪几路，如只看右腕）；`render` 在给定 `--subtask` 时默认用它，多路拼接为可选。
- [x] `annotate.md` 写入分界规则（T2 的用户决定）、按 subtask 选相机、粗扫只看到定位所需的图为止。
- [x] `info` 命令：打印 repo_id、revision、fps、episode 数与每个 episode 长度。`--frames a:b:s` 改为半开区间 `[a, b)`。
- [x] 标注表默认位置与 T6 共用：`<数据集根目录的上两级>/.xense-viewer/subtasks/<org>__<name>@<revision>.csv`（即本地
      LeRobot 根目录下），该数据集使用的 task spec 放在同目录 `<org>__<name>.task_spec.yaml`；CLI 不传 `--annotations` /
      `--task-spec` 时读写这里，显式传参仍可用。revision 规则沿用 T1：唯一的 `.cache/huggingface/trees/<sha>.json` 给出 sha，否则为 `local`。
- [x] `report` 以中文为主（标题、说明、图注、表头）；页首列出标注来源统计（`agent` / `human` / `converted` 行数），存在未经人工复核的
      `agent` 行时给出醒目提示；支持按 episode 分组着色（例如原数据与补录数据），分组来自参数而非猜测。
- [x] `report` 同时写出 `summary.json`：帧占比、精细窗口占比、速度检查、物体位置与覆盖、稀疏格子，字段有文档说明。
- [x] `docs/advise.md`（英文，面向 agent）：读 `summary.json`（可附用户提供的各阶段真机成功率）写中文 `advice.md`，内容为补哪个
      subtask、建议条数（用 `mix` 算出补后占比）、摆放（来自 `suggest`）、采集注意（如接触阶段放慢），每条建议写明依据的数字。
      `report --advice advice.md` 把它嵌入页面，并标为"Agent 建议"。
- [x] 报告与 `summary.json` 默认写到 `.xense-viewer/reports/<org>__<name>@<revision>/`，供 T6 读取。

**Verification**

1. [x] 单测：`--frames` 半开区间；按 subtask 选相机；从 `task_index` 导出标注表（含单 subtask 的补录 episode、未知 prompt 报错）；
       报告中文表头、来源统计与未复核提示；`summary.json` 字段齐全。
2. [x] 下载 `Xense/pack_iphone_box_1119`（`v3.0` → `3a8b398b`，`bi_flexiv_rizon4_rt`，121 个 episode，274083 帧），`info` 输出正确；
       确认 Flexiv 的 6D 旋转约定与 state 中两个夹爪排在最后两维时的臂解析。
3. [x] agent 起草该任务的 task spec（以松开物体为界划分 subtask，每段 prompt、相机、物体），**由用户确认后**再标注 episode 0 / 30 / 60 /
       90 / 120，`validate`，跑 `report`，按 `advise.md` 写 `advice.md` 并嵌入报告。

**Done**

- [x] `pack_iphone_box_1119` 的 task spec 经用户确认；5 个 episode 的 agent 标注通过 `validate`。
- [x] 该数据集的中文报告能离线打开，页首显示"5/121 个 episode 已标注、均为未复核的 agent 标注"；Agent 建议中的每个数字能在
      `summary.json` 中找到。

**结果（2026-11-24）：** 合入本地 main `ad5fee8`，67 项测试、ruff、ty 通过。Flexiv 的 6D 约定与 Elite 相同（`quaternion_to_rotation_6d`
取旋转矩阵前两列），夹爪排在最后两维的特征顺序有测试覆盖。`pack_iphone_box_1119` 的 task spec 按用户确认装到约定路径；agent 标注
episode 0 / 30 / 60 / 90 / 120 共 15 行，`validate` 通过；报告页为中文，页首显示 5/121 已标注、15 行未复核 agent 标注。鸡蛋盒报告已用
新版重新生成，`lang="zh-CN"`。5 条样本的帧占比：`place_insert` 18.79%、`place_phone` 25.41%、`close_lid` 55.81%，精细窗口合计 11.84%。

审查意见（已由 2026-11-24 第二期决定取代：速度检查和 `advice.md` 删除）：
- 速度检查对每条臂的所有精细窗口都算，不看这条臂在该阶段是否参与。`pack_iphone_box` 中左臂多数时间停着，报告得出"左臂全部放慢"
  （中位比值 0.097），这是停着造成的，不能说明放慢了。右臂"3/5 未放慢"经 coordinator 抽查 episode 60 属实：右臂在放纸托的接触窗口中位
  速度 0.040 m/s、松开窗口 0.047 m/s，高于整条 0.028 m/s。
- `advice.md` 的方案 C 以"三阶段帧占比均衡"为目标，这个目标没有依据；建议已写明以真机评测为前提，但 `advise.md` 应要求不以均衡占比
  作为默认目标。


### Task T6：xense-lerobot-viewer 的 Subtask 标注面板与数据分布页

fork `AtticusZeller/xense-lerobot-viewer`（上游 `XenseRobotics-AI/xense-lerobot-viewer`，Next.js + bun），登记为
`methods/xense-lerobot-viewer`（用户决定（2026-11-24））。它已有本地 v3.0 读取、多路相机同步播放、state/action 曲线、中文界面，以及
"标注只读展示、结论写在数据集之外"的 TacFlow 先例。标注表契约以本计划为准，格式校验以 `lerobot-check validate` 为准。

**Change**

- [x] episode 页新增"Subtask"面板：读取 `.xense-viewer/subtasks/<org>__<name>@<revision>.csv`（revision 规则与 lerobot-check 一致）
      与 task spec，在进度条上按 subtask 分色显示各段，标出 `contact`、`grasp`。
- [x] 逐帧前后移动（快捷键），把当前帧设为某行的 `start` / `end`（相邻行的分界联动，保持首尾相连）/ `contact` / `grasp`，切换
      `success`，可新增或删除分界；保存时原子写回 CSV，被改的行 `annotator=human`；保存前做首尾相连、区间与 subtask 顺序的轻量检查
      并在界面上提示。没有标注文件的 episode 可从 task spec 新建。
- [x] 数据集页新增"数据分布"标签：内嵌 `.xense-viewer/reports/<org>__<name>@<revision>/` 下的报告 HTML（含 Agent 建议）；不存在时
      提示运行 `lerobot-check report` 的命令。
- [x] 中英文文案进 `i18n/messages`。

**Verification**

1. [x] `bun run format && bun run validate` 通过；新增单测覆盖 CSV 解析与写回（往返不变）、分界联动、轻量检查、`annotator` 改写。
2. [x] 用 T1 的鸡蛋盒转换标注表放到约定路径，`bun dev` 打开 episode 页能看到分段；改一处保存后 `lerobot-check validate` 通过。
3. [x] 用户在浏览器中完成一次调整并确认操作顺手（用户执行；2026-11-24 用户确认可用。当时"数据分布"页显示的鸡蛋盒报告是英文，由 T3
       版 `report` 生成；中文版属于 T5，合入后重新生成）。

**Done**

- [x] 保存后的 CSV 通过 `lerobot-check validate`，只有被改的行变为 `annotator=human`，其余行逐字节不变。
- [ ] ~~"数据分布"标签能显示 T5 生成的报告~~（由 T9 的原生面板取代，用户决定（2026-11-24））。

**结果（2026-11-24）：** 合入 fork 本地 main `03a44ac`，`bun run validate` 677 项通过。coordinator 补测：备注含逗号、引号、换行的
CSV 原样保存逐字节不变；移动分界只把相邻两行改为 `human`，Python `load_annotations` 能读回；越界被保存前检查拦下。审查发现帧号可能
偏一帧，worker 实测证实：episode 4（`file-002.mp4`，`from_timestamp = 3221/30`）跳到 `N/fps` 时 Chromium 把 `currentTime` 截到微秒，落在
第 N 帧 PTS 前 1 µs，显示的是第 N−1 帧；改为跳到帧区间中点 `(N+0.5)/fps`、读回用 `floor`，与 lerobot-check 解码的同帧逐像素比对后
episode 0 / 2 / 4 全部对上。数据集不在 `LOCAL_DATASET_ROOT` 下时，viewer 与 lerobot-check 推算的 `.xense-viewer/` 位置可能不同，此时
CLI 需显式传路径。

## 第二期：分布分析改为 viewer 原生面板，补采落到相机画面

用户试用 T5 / T6 后的决定（2026-11-24）：标注工作流（T1、T4、T5 的标注部分、T6 的 Subtask 面板）保留并收尾；分布分析重做。
分析的产出是能在现场执行的补采清单（物体放哪、朝哪、补几条），画在头部相机画面上；图表只是中间产物。具体决定：

- 不再生成独立 HTML 报告和 agent 文字建议，全部做成 viewer 内的可视化功能块，文字只用于标题、图注和指标名。
- 删除：精细窗口（`fine_window_s`）、速度检查、两两相对位移、`mix`、`advice.md` 与 `docs/advise.md`、HTML 报告、viewer 内嵌报告的 iframe。
- 标注表契约不变；`contact` 不再标注（留空合法），`grasp` 保留，物体初始位置取这一帧的 TCP。
- 保留并迁入 viewer：按 subtask 的帧占比、物体初始位置（xy + yaw）、按 subtask 的 TCP 轨迹（可选 episode 分组）、覆盖网格。
- 头部相机外参标定提前到本期；目标区域由用户在头部画面上画多边形，倾向覆盖比现有数据更大的泛化区域。
- "数据少"还是"覆盖窄导致背轨迹"由真机测试点区分：补采面板同时生成密集区、边缘、空白区三类测试点，补采前后用同一批点对比。

头部相机（用户提供，2026-11-24 实读）：RealSense D435，序列号 `346522071766`，RGB8 640×480 30 fps，
$f_x = 606.016113$、$f_y = 605.505737$、$c_x = 323.207703$、$c_y = 244.806580$，畸变模型 `inverse_brown_conrady`，系数全 0。
与数据集 `observation.images.head`（640×480）一致。腕部相机本期不用。

### 契约（第二期新增）

文件都放在 `.xense-viewer/` 下，与标注表同一根目录，不进仓库：

| 文件 | 写入方 | 内容 |
| --- | --- | --- |
| `calib/<org>__<name>.intrinsics.json` | 用户提供（coordinator 写入） | 头部相机内参，`pack_iphone_box_1119` 已写入上面的实读值 |
| `calib/<org>__<name>.frames.json` | lerobot-check `calib-frames` | 待点选的帧：episode、帧号、臂、该帧 TCP 位姿 |
| `calib/<org>__<name>.points.json` | viewer 标定面板 | 在上一文件基础上加像素坐标 `(u, v)` 或 `skipped` |
| `calib/<org>__<name>.head.json` | lerobot-check `calibrate` | 内参、每条臂的外参（基座 → 头部相机）、工具点偏移、重投影误差、所用点数 |
| `targets/<org>__<name>.json` | viewer 补采面板 | 目标多边形（头部图像像素坐标） |
| `distribution/<org>__<name>@<revision>.json` | lerobot-check `distribution` | 见 T7，字段有文档说明 |
| `suggestions/<org>__<name>@<revision>.json` | lerobot-check `suggest` | 补采摆放与三类测试点（基座坐标、yaw、像素坐标与朝向箭头端点） |

task spec 的 subtask 新增可选字段 `arms`（参与的臂）；不写时取该 subtask 物体的臂。轨迹与起终点只统计参与臂，避免停着的臂干扰。

TCP 所指的物理点（法兰还是指尖）由 Flexiv 控制器的工具设置决定，代码里查不到。标定时点选两指尖中点，把工具坐标系下的
常量偏移 $o$ 与外参一起求解：$\pi\big(K,\ T_{cam\leftarrow base}\,(p_{tcp} + R_{tcp}\,o)\big) \approx (u, v)$。

### Task T7：lerobot-check 精简与 `distribution`

**Change**

- [ ] 删除 `report`、`mix`、速度检查、精细窗口、两两相对位移、`advice` 相关代码、文档与测试；task spec 中 `fine_window_s` 视为过时字段
      （读到时警告，不报错，已有 spec 仍能加载）。
- [ ] 新增 `distribution` 命令，写出 `distribution.json`：
  - 每个 subtask 的帧数与占比；
  - 每个 episode、每个物体的初始位姿（xyz、折叠后的 yaw、所用事件帧和臂）；
  - 每个 episode、每个 subtask、每条参与的臂（task spec 中该 subtask 物体的臂）的起点与终点位姿（xyz、yaw），以及按进度 0→1
    重采样的轨迹（xyz + yaw，默认 50 点）；
  - 每个物体的覆盖网格（xy 5 cm × yaw 30°，计数）；
  - 每个 subtask、每条参与臂的指标：起点覆盖与终点覆盖（占用格子数、yaw 跨度），轨迹离散度（同一进度下各轨迹位置标准差的平均，cm）。
  支持 `--episodes` 过滤（用于与 viewer 计算结果对齐），未标注的 episode 跳过并列出。
- [ ] `suggest` 改为：读取 `targets/*.json` 的多边形，用标定把多边形投回每个物体的平面（z 取该物体事件帧 TCP z 的中位数），在多边形内
      优先空白、其次稀疏的格子 × yaw 档抽样 N 个补采摆放；另生成三类测试点（密集、边缘、空白，每类数量可配），全部附带像素坐标
      与朝向。输出写进 `suggestions/*.json`，也可导出 CSV。没有多边形时用现有数据包围盒外扩 5 cm。
- [ ] 文档（`README.md`、`docs/annotate.md`）同步：`contact` 不再标注。

**Verification**

1. [ ] 单测：手算小标注表上的帧占比、起终点覆盖、轨迹离散度、`--episodes` 过滤；多边形回投与点在多边形内判定；三类测试点落在对应格子。
2. [ ] 在 `pack_iphone_box_1119` 上实跑 `distribution`（5 个已标注 episode），字段齐全。

**Done**

- [ ] 测试、ruff、ty 通过；`lerobot-check --help` 不再出现被删除的命令；`distribution.json` 字段文档与实际输出一致。

**进展（2026-11-24 夜）：** worker 交付 `c907d5c`、`36b3964`，72 项测试、ruff、ty 通过；`report`、`mix` 已删。coordinator 补测：鸡蛋盒全量
121 条 `distribution` 4 s、内存 1.3 GB、JSON 3.8 MB；用真实 `frames.json` 的 TCP 姿态加合成相机（工具偏移 18 cm、点选噪声 2 px）跑
`calibrate`，RMS 1.6–1.8 px、留一 2.3–2.8 px，偏移误差 < 4 mm。审查退回一处：位置用的是原始 TCP，若 TCP 是法兰，物体位置和补采标记
会比指尖高约 18 cm，投到头部画面有明显视差；已要求有标定时一律用工具点 $p_{tcp} + R_{tcp}\,o$。
修正后合入本地 main `47a5048`（另含 `calib-frames` 覆盖保护 `3ec6a0d`），76 项测试通过；coordinator 手算 episode 0 帧 325 的工具点与输出一致。
T8 viewer 标定面板合入 fork 本地 main `6b3ec69`（690 项测试）；审查退回并修正：重新生成待点选帧后旧点击会挂到另一帧。
T9 合入 fork 本地 main `4f48a52`（698 项测试）；前端对 episode {0, 30, 60} 重算的指标与 `distribution --episodes 0,30,60` 最大差 8.9e-16；
保存标注后自动重算并刷新已实测。coordinator 补测 episode 范围解析（闭区间、半开区间、倒序、非法输入）。
T10 合入 fork 本地 main `8995495`（703 项测试）；用临时合成标定实跑：画多边形、每物体 10 个补采位置与 36 个测试点，40/40 落在多边形内，
导出 PNG 与 CSV；临时文件已清除，缓存中的 `distribution.json` 恢复为 `tcp`。T8、T10 的真实验收等用户点选标定。

用户确认（2026-11-25）：移动到下一个物体属于该 subtask 的开头，不单独拆 subtask。起终点定义待用户确认：现在"起点 / 终点"取 subtask 的首帧和末帧。第一个 subtask 的起点都是 home（鸡蛋盒 `open_carton` 起点 121 条只占
2 格、yaw 跨 0.1°；装盒 `place_insert` 5 条占 1 格），最后一个 subtask 的终点含回撤，也是 home，这两个指标没有信息量。建议改为：
起点取 `grasp` 帧（物体被拿起的位置，没有 `grasp` 时取首帧），终点取 `end − 1`（松开放稳的位置）；最后一个 subtask 的终点暂不统计。
参与臂：5 条样本中左臂在三个阶段的路径长度中位数为 0.67 / 0.77 / 1.87 m，右臂 0.98 / 1.08 / 2.54 m，两臂都在动，建议 `arms` 都写两臂，
随 `close_lid` 拆分一起改。

### Task T8：头部相机外参标定

**Change**

- [ ] lerobot-check `calib-frames`：从已标注或未标注的 episode 中按 TCP 位置与姿态的最远点采样选帧（每条臂默认 15 帧），写 `frames.json`。
- [ ] lerobot-check `calibrate`：读 `points.json` 与内参，每条臂先用 solvePnP 初始化，再与工具点偏移 $o$ 联合最小二乘；输出 `head.json`
      （含每点残差、RMS、留一误差）。内参从 `intrinsics.json` 读，默认值不写死在代码里。
- [ ] viewer 新增"标定"面板：按 `frames.json` 显示头部画面，点选两指尖中点或跳过，可要求补帧；保存 `points.json`；调用 `calibrate`；
      结果页把 TCP 轨迹投影到头部视频上叠加播放，供人眼检查。

**Verification**

1. [ ] 单测：用已知外参与偏移合成像素点（加 1 px 噪声），`calibrate` 恢复的外参平移误差 < 5 mm、偏移误差 < 5 mm。
2. [ ] 用户在 `pack_iphone_box_1119` 上点选两条臂（用户执行）。

**Done**

- [ ] 每条臂重投影 RMS ≤ 5 px，留一误差 ≤ 8 px；叠加播放中投影点跟随夹爪（用户确认）。

### Task T9：viewer 分布面板（取代报告 iframe）

**Change**

- [ ] 删除"数据分布"标签的 iframe 与报告路由，改为原生面板，数据来自 `distribution.json`：
  - 帧占比：一张表；
  - 物体初始位置：每个物体一张俯视图（散点、朝向箭头、覆盖格子着色），有标定时再显示投影到头部画面的版本；
  - Subtask 轨迹：每个 subtask、每条参与臂一张图，可切换俯视与 3D；默认只画起终点和朝向箭头，可打开整条轨迹（沿轨迹画朝向箭头）；
    起点与终点 yaw 的极坐标直方图；旁边显示三个指标；
  - episode 选择：输入范围或列表，可建多个分组并分色，指标按当前选择重算。
- [ ] 保存 Subtask 标注后自动调用 `lerobot-check distribution` 重算并刷新面板；lerobot-check 的位置由环境变量配置，未配置时提示命令。
- [ ] viewer 原有的 Spatial Trajectory 不改。

**Verification**

1. [ ] `bun run format && bun run validate` 通过；单测覆盖 JSON 解析、按选择重算的指标与 `lerobot-check distribution --episodes` 对同一选择的输出一致。
2. [ ] 在 `pack_iphone_box_1119` 上打开面板，改一处标注保存后面板数值更新。

**Done**

- [ ] 用户在浏览器中确认四个功能块可用、比原报告简洁（用户执行）。

### Task T10：补采面板

**Change**

- [ ] viewer 在头部画面上画、改、保存目标多边形（`targets/*.json`），调用 `suggest`；在头部画面上显示带编号的补采位置与朝向箭头、三类测试点；
      导出 PNG 与 CSV 带到现场。实时相机叠加不在本期（需要连机器人 SDK，以后在采集端另开任务）。

**Verification**

1. [ ] `bun run validate` 通过；在 `pack_iphone_box_1119` 上画多边形生成 10 个补采位置，标记全部落在多边形内。

**Done**

- [ ] 用户在现场按导出图摆放一次物体，确认位置与朝向能看懂（用户执行）。

### `close_lid` 拆成三个 subtask（用户确认（2026-11-25））

用户（2026-11-24）：关盒是很长的复杂动作，至少包含三段：把盒盖拿起放到盒子旁边；左臂把盒盖转一定角度扶住、右臂夹住、左臂
松开、右臂翻过来扣到盒子上；按扣合情况推长边、轻扣头尾，最后整体按死。coordinator 看了 episode 0 的 head 画面（帧 989–2341，
1.5 s 间隔）与此一致：约 989–1250 右臂移盖到盒旁，约 1260–1950 双臂翻盖并扣上，约 1950–2341 扣合按压与回撤。

用户确认（2026-11-25）名称、prompt 与参与臂如下表（prompt 是训练与客户端逐字使用的字符串）；三个 subtask 全部写两臂。

| subtask | prompt 草案 | 结束于 | 参与臂 |
| --- | --- | --- | --- |
| `move_lid` | `Place the box lid next to the box.` | 盒盖放在盒旁、右夹爪松开且盖子放稳 | 左、右 |
| `flip_lid` | `Flip the box lid onto the box.` | 盒盖翻过来、刚落到盒子上的那一帧（用户决定（2026-11-24）） | 左、右 |
| `close_lid` | `Close the box lid.` | episode 结束（最后一个 subtask 含回撤） | 左、右 |

用户（2026-11-24）：最后一段不能叫 press，它先要左右精细对准扣上长边和头尾，对不准就按不下去，按压只是最后一步。coordinator 建议
沿用原来的 `close_lid` 与 `Close the box lid.`："关上"同时包含对准和按压，且与原数据的 prompt 一致。
`flip_lid` 的分界不沿用"松开放稳"规则：盖子落到盒子上之后手可能还扶着，之后的调整都归 `close_lid`。

影响：任务变为 5 个 subtask；已有标注中的 `close_lid` 行（含用户已调整的 episode 0）按新分界拆分，拆出的行记为 `agent` 待复核；
物体表中 `box_lid` 的事件改为 `move_lid` 的 `grasp`。T7 的代码不依赖 subtask 数量，不受影响。

**结果（2026-11-25）：** task spec 已改为 5 段（每段两臂，分界规则写在 subtask 上方的注释里；旧 spec 与 CSV 已备份）。agent 按腕部相机重切
5 条样本的 `close_lid`，看图 29 张；`validate` 通过（25 行），其余行逐字节不变；`annotate.md` 补充"subtask 可在 spec 中自带结束规则"（`579a220`，已推送）。
`move_lid` 结束帧比只看 head 时早约 1.3 s（右腕可见夹爪松开）。`flip_lid` 落盖帧从图上难以精确判断，需用户在 viewer 中复核。

### 执行方式

T1 由一个 Orca antigravity worker 完成，合入 `main` 后 T2、T3、T4 各派一个 worker 并行（各自分支）。coordinator（Claude）负责任务说明和审查：用能运行的边界用例验证，不只读 diff。

第二期：lerobot-check 一个 worker 依次做 T7 与 T8 的 CLI 部分（避免 `cli.py` 冲突）；viewer 一个 worker 同时按上面的文件契约做 T8 标定面板，
随后做 T9、T10。
