# lerobot-xense Plan

## `pack_iphone_box` 单 subtask 补采与合并

属于根仓分支 `AtticusZeller/subtask-pack-iphone-box` 的 subtask 线；前置是 `docs/lerobot-check/plan.md` 的重标数据集，
方法依据见 `docs/xense-openpi/subtask-prompt-spec.md`。补采哪几段、每段多少条由用户定。

### Task: 按 subtask 录制补采数据集

**Change**

- 每个要补的 subtask 录一个数据集：`lerobot-record` 用装盒任务的 Flexiv 录制配置，`--dataset.single_task` 取该 subtask
  的 prompt（与 task spec 逐字一致），场景摆成该 subtask 开始时的状态。录制由用户在采集机上执行。
- lerobot-check 为补采数据集写单行标注（整段属于该 subtask），`validate` 通过。

**Verification**

1. 补采数据集的 `tasks.parquet` 只有一句 prompt，与重标数据集中对应的 prompt 逐字相同。
2. 所有 mp4 的编码与重标数据集相同（H.264）。

**Done**

- 每个补采数据集的 episode 数达到用户定的数量，`validate` 通过。

### Task: 合并成训练数据集

**Change**

- 官方 `merge_datasets` 默认参数，把重标数据集与各补采数据集合并；坏 episode 只改元数据删除，不重编码视频。
- 合并与下游 `xense-openpi` 训练必须使用同一工具 TCP（`taccap-rs00`）下的数据集（旧数据需先经 `lerobot-check retarget-tcp` 转换，如 `pack_iphone_box_1119_taccap_rs00_subtask`），且训练前必须在转换/合并后的新数据集上重新计算 `norm_stats.json`，禁止复用旧 `xenseflare` TCP 的归一化统计。

**Verification**

1. 合并后逐帧核对：每个来源抽 2 条 episode，图像、state、action 与来源一致。
2. 合并后 `tasks.parquet` 仍是 5 句 prompt，补采 episode 的 `task_index` 指向对应 prompt。

**Done**

- 合并数据集的 episode 数与帧数等于各来源之和；上面两项核对无差异。
