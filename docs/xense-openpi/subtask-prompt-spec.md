# 长程任务按 subtask 切分 prompt

适用范围：一个 episode 里先后出现几段动作分布差别很大的阶段，并且只训练一个 pi05 模型。第一个实例是双臂 Elite
"打开鸡蛋盒 → 取蛋装盘"。代码在 xense-openpi fork 分支 `feat/egg-carton-subtask`，实现细节见该分支的
`scripts/egg_carton_two_stage/README.md`。

## 问题

鸡蛋盒任务一个 episode 约 60–90 秒，包含两段：打开盒子，以及把鸡蛋逐个夹到蛋托。夹蛋占大部分时间。整段只用一个
prompt 训练时，模型夹蛋学得较好，开盒学得差（用户判断（2026-11-06））。

## 方法

1. **逐帧 subtask prompt。** 人工为每个 episode 标出阶段分界秒数 $t_{cut}$，按 $f_{cut} = \mathrm{round}(t_{cut} \cdot \mathrm{fps})$
   切分：帧号 $< f_{cut}$ 的帧用阶段 A 的 prompt，其余用阶段 B 的 prompt。一个 episode 里允许出现多个 subtask。
   - A：`Open the egg carton.`
   - B：`Take out the eggs one by one and place them in the egg tray.`
2. **给难的阶段补数据。** 单独采集只有阶段 A 的数据集（task 只有 A 的 prompt），与切分后的数据合并成一个数据集，训练
   一个模型。哪个阶段难就补哪个阶段。
3. **真机按键切换。** 客户端启动时用 A 的 prompt。操作者按 `1` / `2` 选择 A / B，控制线程在下一步发现 prompt 变化，
   清掉缓存的 action chunk 后用新 prompt 推理。RTC 模式下会重新做 warmup。

训练和推理服务端不需要改代码：LeRobot 按 `task_index` 逐帧取 `task` 作为 `prompt`，服务端直接使用 observation 里的
`prompt`。数据上的硬约束是 `tasks.parquet` 的行顺序必须等于 `task_index`，两端 prompt 字符串必须逐字一致。

## 数据规则

- 坏 episode 只改元数据删除，视频不重编码。官方 `delete_episodes` 会把 H.264 视频重编码成 AV1，导致官方 merge 拼接失败，
  或写出无法解码的视频。
- 合并用官方 `merge_datasets` 默认参数。合并前所有 mp4 必须是同一编码。
- 每次删除或合并后，都逐帧核对图像和 state/action，并检查分界帧前后送进模型的 prompt。

## 实验

| 项目 | 内容 |
| --- | --- |
| 数据 | 原数据 `Xense/bi_elite_cs66_rt_egg_carton_to_tray_1016_fixed` 去掉错误的 episode 108 后切分（121 个 episode，A 63060 帧 / B 274178 帧），合并开盒数据 `Xense/bi_elite_cs66_rt_open_egg_carton_1103`（53 个 episode，32426 帧），共 174 个 episode、369664 帧 |
| 模型 | pi05_base 全量微调，config `pi05_base_bi_elite_egg_carton_relabeled_plus_open_1103_h100`，batch 256，40000 步 |
| 训练 | W&B [`pyi79tmz`](https://wandb.ai/XenseRobotics/xense-openpi-hubo/runs/pyi79tmz)，最终 loss 0.0010 |
| 部署 | checkpoint 39999 部署在 03 推理服务器；elite 客户端按键切换 prompt |

**结果：** 真机按键切换响应快，切换时没有明显卡顿。按 subtask 切分后，整个任务的成功率提升了很多（用户结论
（2026-11-06））。没有记录成功率数字。

## 讨论

- 训练数据中的分界点完全靠人工标注。部署时由操作者判断何时进入下一阶段，所以这套方案还不是自主完成长程任务。
- 合并后右夹爪 state 第 19 维的 q01/q99 几乎相同。开盒数据里 1e-4 级的抖动经分位数归一化和离散化后，会变成 prompt
  里 state token 的大幅跳动。用户决定保持现状，训练出现异常再处理（用户决定（2026-11-04））。这次训练没有出现异常。
- 没有和"同样的数据、只用一个 prompt"做对照训练。成功率提升与补充开盒数据、切分 prompt 各自贡献多少，没有分开测过。
