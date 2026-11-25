# lerobot-check Plan

## `pack_iphone_box_1119` 全量标注与 5 段 prompt 重标

整条 subtask 线（标注 → 重标 → 补采 → 训练 → 推理）在根仓分支 `AtticusZeller/subtask-pack-iphone-box` 上推进；补采见
`docs/lerobot-xense/plan.md`，训练与推理见 `docs/xense-openpi/plan.md`，方法依据见 `docs/xense-openpi/subtask-prompt-spec.md`。

### Task: agent 并行标完剩余 111 条

**Change**

- 5 个 agent 并行，按 `docs/annotate.md`（含 `exemplars` 步骤）标注，episode 分组：1–23、24–47、48–70、71–94、95–119
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
- 用户在 viewer 里抽查（约每 5 条看 1 条）后认可，或改正后的行变为 `human`。

### Task: 重标出 5 段 prompt 的训练数据集

**Change**

- `lerobot-check relabel` 按共享标注表逐帧写 `task_index`，输出新数据集（repo id 由用户定）。

**Verification**

1. `verify-relabel` 通过：帧数、非 task 列、视频与原数据集一致。
2. 抽查 3 条 episode，每个分界帧前后各一帧的 `task` 与标注表一致。

**Done**

- 新数据集的 `tasks.parquet` 恰好是概览里的 5 句 prompt，按 task spec 顺序排列。
