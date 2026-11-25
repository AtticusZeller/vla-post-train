# lerobot-check Plan

## `pack_iphone_box_1119` 全量标注与 5 段 prompt 重标

整条 subtask 线（标注 → 重标 → 补采 → 训练 → 推理）在根仓分支 `AtticusZeller/subtask-pack-iphone-box` 上推进；补采见
`docs/lerobot-xense/plan.md`，训练与推理见 `docs/xense-openpi/plan.md`，方法依据见 `docs/xense-openpi/subtask-prompt-spec.md`。

### Task: agent 并行标完剩余 111 条

**Change**

- 4 个 agent 并行，按 `docs/annotate.md`（含 `exemplars` 步骤）标注，episode 分组：1–28、29–58、59–88、89–119
  （跳过已复核的 0 / 15 / 30 / 45 / 60 / 75 / 90 / 100 / 110 / 120）。
- 每个 agent 只写自己的文件 `~/.cache/huggingface/lerobot/.xense-viewer/annotate-batch/pack_iphone_box_1119/part-<k>.csv`，
  渲染输出也各用各的目录；`exemplars` 只读共享标注表。
- 全部完成后合并进共享标注表，已有 50 行 `human` 不动。

**Verification**

1. 每个 part 文件 `lerobot-check validate --annotations <part>` 通过，且恰好覆盖本组 episode。
2. 合并前备份共享表；合并后 `validate` 通过，原有 50 行逐字节不变。
3. 重算 `distribution`，viewer 分布页能读。

**Done**

- `validate` 输出 `605 rows covering 121/121 episodes`。
- 由下一项的结束帧拼图验收。

### Task: 结束帧拼图与 agent 自查闭环

用户的验收方式是看前 4 个 subtask 的最后一帧：夹爪已松开、回到物体上方空中为对；手还压在物体上为早，已回撤去够下一个
物体为晚。腕部视角常比头部看得清（用户定，2026-11-25）。

**Change**

- lerobot-check 新增 `boundary-sheet`：每个 subtask 一组拼图，每条 episode 一格，格内并排头部（可裁剪）和两个腕部
  在 `end − 1` 的画面，标 episode、帧号、`human`；可只渲染指定 episode，可分页。
- `annotate.md` 与 task spec 注释写明上面的结束帧标准（`flip_lid` 仍按"盖子刚落到盒上"）和自查闭环：出全量拼图 →
  标出不合格的格 → 只改 agent 行的 `end`（同时改下一行 `start`）→ 只重渲染改过的 episode → 直到全部合格。
  `human` 行只报告不改。
- 4 个 agent 各负责一个分界，各在自己的标注表副本上改；我把每个分界的改动合并回共享表。

**Verification**

1. 单测：选帧（`end − 1`、episode 过滤、跳过最后一个 subtask）、格子布局与分页、`human` 标记、裁剪参数解析。
2. 在真实数据上对 ep20 `place_insert` 出图，能看出右臂已回撤到手机旁。
3. 合并后 `validate` 通过，只有 `end` / 下一行 `start` 变化，`human` 行不变。

**Done**

- 每个分界一张完整拼图，用户看完认可。

### Task: 重标出 5 段 prompt 的训练数据集

**Change**

- `lerobot-check relabel` 按共享标注表逐帧写 `task_index`，输出新数据集 `Xense/pack_iphone_box_1119_subtask`（用户定，2026-11-25）。`grasp` 统一取夹爪在物体上闭合的那一帧（用户定，2026-11-25），不影响重标。

**Verification**

1. `verify-relabel` 通过：帧数、非 task 列、视频与原数据集一致。
2. 抽查 3 条 episode，每个分界帧前后各一帧的 `task` 与标注表一致。

**Done**

- 新数据集的 `tasks.parquet` 恰好是概览里的 5 句 prompt，按 task spec 顺序排列。
