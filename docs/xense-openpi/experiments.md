# xense-openpi 实验记录

按时间倒序记录外部启动的实验。每节依次保留原始记录、结果分析和下一步；观测、推断与未验证猜想分开。
训练契约见 [rlt-spec.md](rlt-spec.md)，已确认工作见 [plan.md](plan.md)。

## 2026-10-10 · pi05_base_bi_flexiv_insert_ethernet_0928_h100/test1010-2 — 用成功示教学局部对准，再交给 VLA 插入

### 1 原始记录

#### 用户的实验思路：先把对准与插入分开

**以下是用户的设计理由与分析判断，不是从训练指标倒推出来的解释。**

首先限定小 AC 网络的职责：**actor 从离插入口稍有距离的位置，调整到正确的插入位置；VLA 负责后续完整插入。** 本次想考察的是局部对准能力。

按这个分工设计示教：起点与插入口保持稍许距离，给 actor 学习“如何调整到位”的空间；对准并稍微插入就结束示教，不继续教完整插入。用户担心**完整插入数据可能影响小 AC 网络的对准能力**，因此主动缩小示教范围。这个担心是设计假设，本次没有加入插入数据的对照。

同时，用户暂时假设 **Q 的作用可能不大，先看成功人工示教能否让 actor 学会对准**，所以只采成功示教，没有刻意加入失败或错误示教。这里的“纯成功示教”描述数据选择，不表示实际训练已经关闭 Q。

第二次采用 **corrected 默认条件输入模式**。评测遵循同一个阶段边界：actor 对准或浅插后，由用户**手动关闭窗口**，让 VLA 接管；不要求 actor 一直驾驶到完全插入。

因此，本次想验证的是：**用专门针对对准阶段的成功示教训练小 actor，再在对准后切回 VLA，这种分工是否可行，对准能力是否改善。**

#### 用户的现场观察：对准能力看起来有明显改善

用户在示教中后期开始分批手动评测，估计对准成功率从初期 **低于 10%** 提升到后期 **70–80%**。这支持用户对上述分工的初步判断，但还没有登记准确的成功数/试次总数、checkpoint 和起始距离分布，不能给出置信区间或显著性检验。

用户随后澄清：“约 60–100 次示教”是把 W&B 的 100 多个 round 误当成示教次数。应区分 **round、已入库示教段数、手动评测试次**；本次日志不能还原手动评测的准确分母。

[成功参考视频：Feishu20261010-170700.mp4](/home/atticuszz/Downloads/Feishu20261010-170700.mp4) 为用户提供的行为个例，时长 5.667 秒。已查看代表帧；画面没有策略来源标记，交接方式依据用户确认的“手动关闭窗口”，不由视频推断切换时刻。

#### 云端数据：只保留与上述判断直接相关的证据

以下沿用 **2026-10-10 约 17:08 的取证快照**，不是本次重写时重新拉取的实时状态。

| 要回答的问题 | 已核对的事实 |
|---|---|
| 用了多少成功示教？ | 入库 **39 段**，全部含人工介入；failure 为 0；形成 2,608 条重叠 transition，人工动作位置占比 96.206% |
| 训练是否实际发生？ | Critic 更新 13,040 次，actor 更新 6,520 次；第 32 轮开始训练，最后一次更新在第 110 轮；与 UTD=5、critic/actor 更新比 2 一致 |
| 是否在拟合示教目标？ | BC loss 首次 `0.11734` → 最后 `2.243e-5`；末 500 actor 更新中位数 `2.152e-5`，非单调下降 |
| 是否有数值异常？ | Critic loss 首次 `0.04851` → 最后 `1.325e-5`；已检查的 replay 特征/动作与 actor 输出未发现非有限值，完整轮 rot6d fallback 为 0 |
| Q 是否实际上关闭？ | 没有；`q_weight=0.1`。末 500 actor 更新的加权 BC/Q 梯度范数中位数为 `0.03307 / 0.02367`；逐次范数比中位数 1.398 |
| 能否复算 70–80%？ | 不能。已入库的 39 个 success 是含人工介入的采集标签，不是 39 次自主评测；139 个 round 也不是评测分母 |

<details>
<summary>取证身份与训练配置</summary>

- **W&B：** <https://wandb.ai/XenseRobotics/xense-openpi-hubo/runs/o8ifks0z>；project `XenseRobotics/xense-openpi-hubo`，run `o8ifks0z`，group 未设置。
- **代码版本：** W&B metadata 与远端 HEAD 均为 `84113a489240e8b221f7f9617c756ea7c1d25fe6`，标题 `chore(rlt): set ethernet 0928 token checkpoint and 20-step chunks`；远端分支 `feature/rlt-jax`。启动时分支未单独记录。与第一次 `68dbe8f` 比较，代码增加 `input_reference` 选择，并设置 `corrected`；另有配置/测试及机器人端 main 的变化，不将所有行为差异归到单一代码行。
  本机 method 仍为 `rl-exp / 7464fec`，根仓 `4c517089312c9fafe88b1cbf25c14dbe70c4df0f` 有既有未提交工作；本 run 在远端裸脚本启动，不是根仓 `lab` 实验。
- **硬件与权重：** `xense-inference`，RTX 5090；VLA `/home/li/hubo/xense-openpi/checkpoints/ehernet_insertion`，VLA 权重 step 未确认；token `/home/li/hubo/xense-openpi/checkpoints/ehernet_insertion/token_encoder/60000`。没有重跑 phase one。
- **归一化身份：** 与第一次相同，`checkpoints/ehernet_insertion/assets/Xense/insert-ethernet-above-desk-0916/norm_stats.json`，SHA256 `00789e9879f3cb6f66d6c2c02ec7352f99f03897b0aed448c4da7b4323a8d2ea`。
- **精度与 seed：** token 配置 `bfloat16`，参数/残差/loss 为 `float32`；phase-two MLP 未显式指定低精度 dtype，未实测权重 dtype；`seed=42`。
- **状态与截止：** 2026-10-10 约 17:08（北京时间）拉取，W&B 为 `running`；14:35:53 启动，最后完整轮为第 139 轮（16:02:42），16:02:49 机器人断连后等待重连。取证时服务进程仍在；W&B 最后日志 runtime 约 `5208 s`，不等于取证时进程墙钟时长。未确认是否已结束机器人侧操作，不将这次写成已完成的 300 轮运行。
- **统计子集：** history 17,957 行，含 139 个 round、13,040 个 update、4,778 个 chunk；完整轮累计 4,702 个 chunk。第 62 轮号下有 76 个未提交尝试的额外 chunk，不能混入完整轮任务统计。
- **证据位置：** 远端 `checkpoints_rlt/pi05_base_bi_flexiv_insert_ethernet_0928_h100/test1010-2/`；取证时最后保存 checkpoint 为 `rl/130`，已检查全部 39 个非空 `transitions/round_*.npz`。本机分析缓存 `/tmp/o8ifks0z-analysis/` 为临时缓存；既定数据挂载当前不可写，未在仓库保存大文件。

权威来源：本 run 的 W&B config 与 `84113a4` 的 YAML/源码。对比第一次，除实验名外，W&B 中已有数值配置均相同；明确新增且不同的条件输入模式加粗。

| 组 | 参数 | 值 |
|---|---|---|
| 条件输入 | `input_reference` | **`corrected`，第一次源码固定为 proposal** |
| Actor 目标 | `q_weight / bc_weight / reference_dropout_prob` | `0.1 / 5 / 0.5`；Q 未关闭 |
| 优化 | `actor_lr / critic_lr / max_grad_norm` | `3e-4 / 3e-4 / 10` |
| 动作与 TD | `num_action_chunks / ref_num_action_chunks / replay_stride` | `20 / 50 / 2` |
| Critic / 探索 | `gamma / tau / fixed_std` | `0.99 / 0.005 / 0.002` |
| 数据 | `warm_up / batch_size / buffer_size` | `600 / 256 / 6000`，容量单位为 transition |
| 预算 | `utd / critic_actor_ratio / total_rounds` | `5 / 2 / 300` |

结构沿用第一次：actor/critic `(256,256)`，两个 Q head，actor LayerNorm 关闭、critic LayerNorm 开启；token 结构、接管阈值、VLA 去噪步数和保存周期见运行 config，没有把这些遗漏当成关闭。

</details>

### 2 结果分析

#### 当前最有依据的判断：这套分工有可行性，对准改善主要由现场观察支持

**（用户判断）** corrected 模式下，针对局部对准采成功示教，actor 对准后手动切回 VLA，这套分工看起来可行，且对准能力明显改善。

**数据支撑：** 39 段示教确实进入训练，BC loss 明显下降，未发现数值发散。这说明训练路径有效、actor 在拟合所给目标。用户观察到的 `<10% → 70–80%` 才是行为改善的主要证据；训练 loss 不能替代对准评测。

**任务解释：** 对准后退出符合本次职责。不能因为 actor 没独立插到底就判定本次失败；也不能把人工切换后的系统行为等同于自主判断何时切换。此处依据用户定义和 `84113a4` 的 `collector.py:73–89,135–152`。

#### 本次还不能把改善归因到 corrected、Q 或示教范围中的某一项

三条判断应分别保留，不能混成一个“已证明的原因”：

- [ ] **未验证：corrected 本身带来改善。** 本次还改变了示教起始条件、阶段边界与交接流程。`84113a4` 的 `td.py:81–100` 确认 corrected 将人工替换后的 reference 同时作为条件输入和 BC 目标；这也使训练拟合更容易。应固定 replay 和更新预算再比较 corrected/proposal，观察部署时的自主对准结果。
- [ ] **未验证：Q 对对准没什么贡献。** 当前 Q 仍有非零加权梯度，说明参与更新；参与不等于有益。应在相同数据/预算下比较 `q_weight=0` 与 `0.1`，看对准行为是否变化，而不是只比较 loss。分项梯度依据 `learner.py` 的 actor 更新实现。
- [ ] **未验证：完整插入数据会影响对准能力。** 本次仅验证了用户选择的局部示教方案，没有完整插入数据对照。若以后检验，应固定对准数据，比较是否加入插入数据，并单独考核对准阶段。

### 3 下一步

当前最需要补的是**把用户已经观察到的对准改善记录成可复核的评测结果**。以下为候选验证，不进入 `plan.md`。

- [ ] 固定 checkpoint 与起始距离/误差分组，记录每次 actor 自主对准是否成功、有无人工纠正、何时手动关窗，以及 VLA 后续是否插入完成。**判据：** 分别报告局部对准和交接后完成的成功数/总次数；人工纠正试次单列。**风险：** 操作员改变切换标准会混入系统表现，应先固定标准。
- [ ] 若需要解释改善来源，再分别做 corrected/proposal、Q 开/关、加入插入数据的对照，每次只改变一个因素。**判据：** 在相同评测条件下，对准表现的差异能重复；取得实际计数后再做区间和显著性检验。**风险：** 同时改变数据、模式与任务终点将无法归因。

#### 暂不处理

- 保持用户定义的“actor 对准、VLA 插入”边界，不自动扩大 actor 职责或加入完整插入示教。
- 不把人工估计变成精确成功率，不把成功采集标签当成自主评测。
- 不因“Q 作用可能不大”的假设自动关闭 Q；不因复制捷径的可能性否定用户看到的行为改善。
- 本次只重写记录；不刷新运行数据、不改技能、代码、配置或计划，也不启动对照实验。

## 2026-10-10 · pi05_base_bi_flexiv_insert_ethernet_0928_h100/test1010 — 人工对准示教下的 proposal actor 训练

### 1 原始记录

#### 身份、权重与结束状态

- **W&B：** <https://wandb.ai/XenseRobotics/xense-openpi-hubo/runs/x7dxhn3g>；project `XenseRobotics/xense-openpi-hubo`，run `x7dxhn3g`，group 未设置。
- **方法与任务：** RLToken 第二阶段在线 actor/critic；插网线。服务器 `xense-inference`，RTX 5090；运行目录 `/home/li/hubo/xense-openpi`。
- **启动代码：** W&B metadata 记录 `68dbe8fb6768ebf52d20cb83d40a0383ce4bb1d9`，标题 `chore(rlt): set ethernet 0928 token checkpoint and 20-step chunks`；该提交位于远端 `feature/rlt-jax`。启动时分支名称未被 metadata 记录。
  取证时远端工作树已切到 `main / 6b9a30f`，因此所有运行语义均用 `git show 68dbe8f:<path>` 核对。
  本机 method 为 `rl-exp / 7464fec`；根仓为 `4c517089312c9fafe88b1cbf25c14dbe70c4df0f`，已有未提交工作，与这次外部启动运行不构成同一代码快照。
- **VLA：** `/home/li/hubo/xense-openpi/checkpoints/ehernet_insertion`；VLA 权重训练 step 未从本次证据确认。
- **Token：** `/home/li/hubo/xense-openpi/checkpoints/ehernet_insertion/token_encoder/60000`，step `60000`。本 run 的 token-training 配置写 `20000`，但本次加载已有 `60000` 权重，没有重新执行第一阶段训练。
- **归一化：** `checkpoints/ehernet_insertion/assets/Xense/insert-ethernet-above-desk-0916/norm_stats.json`；SHA256 `00789e9879f3cb6f66d6c2c02ec7352f99f03897b0aed448c4da7b4323a8d2ea`。state/actions 均没有 `q99-q01 <= 1e-6` 的维度。
- **精度与 seed：** token 矩阵计算配置为 `bfloat16`，token 参数、残差和 loss 保持 `float32`；phase-two MLP 未显式配置低精度 dtype，不应把 token dtype 当成 actor/critic dtype 的实测值。`seed=42`。
- **状态与截止：** 2026-10-10 约 14:18（北京时间）拉取 W&B；API 状态 `finished`，runtime `11570 s`（3 小时 12 分 50 秒）。运行 10:30 启动，86 个完整 round 的末尾为 11:36:42，11:37 机器人断连并等待重连，13:43:24 保存最终 `rl/86`；用户确认主动结束，未跑满配置的 300 轮。
- **统计子集：** 缓存 history 为 13,394 行，包含 86 个 round 记录、10,615 个 update 记录和 2,693 个 chunk 记录。完整轮累计 chunk 为 2,657；额外 36 个来自第 4 轮号下未提交尝试（该轮号共记录 67 个 chunk，完成尝试计 31 个），不能混入已完成轮的任务统计。末尾 chunk 轮号仍为 86，不能把这 36 个误归到最后断连的一轮。
- **产物与取证：** 远端 `checkpoints_rlt/pi05_base_bi_flexiv_insert_ethernet_0928_h100/test1010/` 下保留 `rl/86` 与 `transitions/round_*.npz`。已检查全部 43 个非空 transition dump。
  本机规定的 `/mnt/data/atticux/agent-workspace/` 挂载不可写，分析缓存临时放在 `/tmp/x7dxhn3g-analysis/`，该缓存不是长期证据存档；未将完整日志、pickle 或 checkpoint 写入仓库。

#### 影响训练的配置

没有选定且核验上一轮对照配置，因此不标注“相对上一轮改动”。权威来源为本 run `config.json` 和启动提交的 `configs/rlt/pi05_base_bi_flexiv_insert_ethernet_0928_h100.yaml`。

| 组 | 参数 | 值 |
|---|---|---|
| Actor 语义 | 条件输入 / 输出 | `proposal`：原始 VLA reference / `direct`，由源码确认，并非 config 中的模式字段 |
| 动作与 TD | `num_action_chunks / ref_num_action_chunks / replay_stride` | `20 / 50 / 2` |
| 优化 | `actor_lr / critic_lr / max_grad_norm` | `3e-4 / 3e-4 / 10` |
| Actor 目标 | `q_weight / bc_weight / reference_dropout_prob` | `0.1 / 5 / 0.5` |
| 探索 | `fixed_std` | `0.002`，归一化动作空间 Gaussian 标准差 |
| Critic | `gamma / tau` | `0.99 / 0.005`；gamma 按执行步计 |
| 数据与预算 | `warm_up / batch_size / buffer_size` | `600 / 256 / 6000`，warm-up 和容量单位为 replay transition |
| 更新 | `utd / critic_actor_ratio` | `5 / 2` |
| 采集 | `total_rounds / num_steps` | `300 / 10`；后者为 VLA 去噪步数 |

结构设置未作为本轮调参项：actor/critic 均为 `(256,256)`，critic 两个 Q head，actor LayerNorm 关闭、critic LayerNorm 开启；token 的层数、维度、head 与 prefix 长度，以及接管阈值、保存周期，见上述运行 config。

#### 标签、数据与训练观测

**用户说明：** 本次没有独立评测；未考虑 failure 和错误示教。人工示教主要到对准或浅插，即使没有完成插入也按 success 结束窗口。
用户观察到 actor 接管时停留在对准位置、不继续插入；计划再测试 `corrected`。这是机器人定性观察，不是量化评测结果。

| 观测 | 数值及边界 |
|---|---|
| 已入库阶段 | 43 个，全为 success；failure 0 个 |
| 已入库 transition | 2,123；43 个 terminal，各自最后一步 reward 为 `1`；其余 reward 为 `0` |
| 人工占比 | replay 的重叠窗口中 41,428 / 42,460 个动作位置，即 **97.569%**；VLA 219，actor 813。这不是去重后的真实执行步占比 |
| 真实采集长度 | 已提交阶段累计 5,018 步；阶段长度 40–304 步。完整轮总执行 64,219 步，人工 14,476 步，含未入库时段 |
| Warm-up / 更新 | 第 23 轮达到 684 行并开始训练；最终 critic 10,615、actor 5,307 次；最后一次训练在第 84 轮；85、86 轮没有新行，也没有更新 |
| 更新预算核对 | `2123 × 5 = 10615`，`floor(10615 / 2) = 5307`；没有欠账。2,123 行来自 stride 2 的重叠窗口，不代表 2,123 段独立示教 |
| Critic loss | 首次 `0.07150` → 最后 `6.70e-6`；末 500 critic 更新中位数 `7.37e-6`；非单调下降 |
| BC loss | 首次 actor 更新 `0.11750` → 最后 `1.878e-4`；末 500 actor 更新中位数 `1.743e-4`；非单调下降 |
| Q | `q_data` 首次 `−0.03983` → 最后 `0.30997`；`q_pi` 首次 `−0.32090` → 最后 `0.32023`；末段 `q_target` 约 `0.319`，非单调 |
| Q 分歧 / 目标离散度 | 双 Q 平均差首次 `0.3020` → 最后 `0.002856`；末 500 critic 更新的 `q_target_std` 中位数 `0.17014` |
| 两项梯度 | 末 500 actor 更新加权 BC/Q 梯度范数中位数分别 `0.02604 / 0.01416`；逐次范数比中位数 **1.845**；cosine 中位数 **−0.549**，96.4% 为负 |
| Actor 与 VLA 的动作差异 | 281 个 actor 路由 chunk 的双臂位置差均值之中位数 `4.665 mm`，末 50 个中位数 `5.350 mm`；此值无方向，不能据此判断沿插入轴后拉 |
| 工程健康 | dump 的 actions/proprio/reference/z_rl 无非有限数；actor 281、shadow 2412 个 chunk 的 nonfinite 都为 0；完整轮累计 rot6d fallback 为 0 |
| 裁剪与投影 | 完整轮累计 out-of-range 元素 26,501、物理 gripper clip 元素 39,582；末 500 actor 更新 projection absolute mean 中位数 `0.17109`。这是元素/幅度统计，不是失败次数或动作饱和率 |

W&B summary 会保留以前非空字段：第 86 轮没有更新，summary 中的 `round/train_*` 实际来自第 84 轮，不能称为“第 86 轮训练结果”。history 的缺失值对应分开的日志流和隔次 actor 更新，不当成训练产生 NaN。

**任务指标：** 没有完整插入判据、失败标签或冻结策略评测，不能计算任务成功率，也不进行成功/失败 Fisher 检验。43 个正标签只能描述采集方式，不能作为 100% 插入成功率。pre-warmup 也是人工对准示教，不是自主 VLA 评测基线。

### 2 结果分析

以下源码位置均指启动提交 `68dbe8f` 的旧路径，而非本机 `rl-exp` 的新布局。

#### 训练确实在学习，但学习目标止于对准或浅插

**观测：** 用户确认对准/浅插即 success；dump 43 个 terminal reward 全为 1；97.569% 的 replay 动作位置来自人工；BC loss 降到约 `1.7e-4`。

**推断：** actor 在人工 mask 位置被要求模仿这些动作，critic 被要求给它们结束的状态正价值。系统没有获得“继续插到位才成功”的区别信号。
这两条监督与“停在对准附近”相容；将其归因于网络学死或数值炸掉，当前没有证据。
依据：`td.py:29–38,82–96` 的 BC target，以及 `collector.py:195–225` 的 terminal reward。

**（用户提出）** 示教不完成插入，actor 学会纠正 VLA 后，可能反而把 VLA 限制在对准位置。

- [ ] **未验证**：actor 在同一状态下是否削弱了 VLA 沿插入轴的推进。需对同一观测、同一 VLA reference 比较 actor/VLA 的轴向位移及末端推进轨迹；当前 4.665 mm 的无方向差值不能证明“后拉”。也需排除 VLA 自身不能插入、接触阻力或控制器接管规则。

#### proposal 更直接学习人工修正，corrected 仍使用相同的目标和奖励

**源码事实：** 本 run 的 actor 输入一直是原始 VLA reference；BC target 在人工位置换成人工动作。
它学习的是“VLA 建议 → 人工纠正”，不是只复制已纠正的输入。reference dropout 为 0.5。
依据：`td.py:82–96`；本机 spec 的研究性选项与此一致。

**推断：** 若人工常把 VLA 的推进改成对准/浅插，proposal 能直接把这种修正迁移到部署输入，因而可能更容易表现为抑制推进。
`corrected` 的训练条件输入则是人工替换后的 reference，但 BC target 和 terminal reward 不变；部署时仍没有未来人工 reference。
所以 corrected 的复制捷径或训练/部署输入差异可能改变行为，却不能补上完整插入的成功定义。

- [ ] **未验证**：停滞主要来自 proposal 条件方式还是来自示教/奖励终点。只改变条件输入、固定数据与其余超参的对照才能区分；若换模式同时换示教与标签，无法归因。

#### Critic 拟合自己的 TD 目标良好，不等于在评价完整插入

本次 TD 目标为：

$$
y=\sum_{i=0}^{19}\gamma^i r_i+(1-d)\gamma^{20}\min_j Q'_j(s',a'),\qquad \gamma=0.99.
$$

单个 terminal 窗口的目标应为 `0.99^19 = 0.82617`；非 terminal 的 bootstrap 系数是 `0.99^20 = 0.81791`。
依据：`td.py:51–58`；奖励位于最后一执行步，不能把每个窗口的目标都当成 1。

**观测：** 按 43 段实际长度、stride 2 和 terminal anchor，给每个保存窗口计算跟随已记录示教直至其终点的折扣回报；均值 `0.48403`、标准差 `0.20537`、范围 `0.04758–0.82617`。
末 500 critic 更新的 Q/target 均值约 `0.319`；`sqrt(median TD loss) / median target std ≈ 1.60%`，表明当前 TD 目标拟合误差小。

**推断：** critic 没有停止更新，也不是目标完全没变化。它已较好拟合当前 bootstrap 目标，但其正价值指向人工定义的对准/浅插终点。
示教折扣回报 `0.484` 只是行为轨迹参照；bootstrap 用下一状态的 actor，而不是下一段人工示教，因此与 Q `0.319` 的差值不能直接当成 critic 校准误差或算法失败。

#### BC 与 Q 梯度在拉扯，不能只按 loss 数值决定减小 BC 权重

**观测：** 末 500 actor 更新的加权 BC loss 中位数 `0.0008715`，加权 Q 值 `0.03238`，后者绝对值较大；但 BC/Q 梯度范数比中位数为 `1.845`，cosine 中位数 `−0.549`，96.4% 为负。

**推断：** BC 对参数更新的约束仍较强，两项经常冲突。Q 值大小与其动作梯度大小不同，不能因为 BC loss 小就认定 BC 不影响 actor。
依据：`learner.py:172–190` 分别对加权 BC 与负加权 Q 求梯度。当前还不知道冲突是否集中在插入轴，也没有证据证明降低 BC 权重就能插入。
缺少任务完成监督时，加强 Q 可能只是更积极地优化错误终点或外推 Q。

#### 数据覆盖窄，actor 自主停滞没有形成新的纠错监督

**观测：** replay 只有 43 段已标正例，且人工占比 97.569%。完整轮一半没有入库数据；warm-up 后 32 轮没有新行。第 85、86 轮有执行但没有更新。

**推断：** 没有标签的窗口会丢弃，失败标签没有自动补上（`collector.py:102–149`）。actor 停住后若该窗口未标注或未提交，它不会仅凭“停住了”获得负信号。
没有 failure 并不意味着所有示教动作都正确，也不意味着必须惩罚所有人工接管；应将对准纠正、插入完成和真实失败按任务标准区分。

### 3 下一步

以下为候选验证，不修改 `plan.md`，不启动训练或评测。

- [ ] **先区分训练终点与完整任务终点。** 若最终目标是完整插入，补充到位的正确示教，并使任务 success 对应完整插入；对准/浅插可以是明确的阶段目标，但不能当作完整任务已结束。
  支持证据：43 个 terminal 全部正奖励，用户确认标准止于对准/浅插。观测判据：在固定起始状态下，完整示教覆盖插入轴推进和终点；actor 推进深度与到位判据改善而非只停在对准。风险：同时换数据与标签会混淆两者作用，需分别记录。
- [ ] **按用户意向测试 corrected，作为条件输入的对照。** 保持示教、标签标准、VLA/token、C、seed、训练预算和其他超参一致；优先用已保存 replay 离线训练两种条件输入模式后做同观测动作比较，再决定真机对照。
  支持证据：本次明确为 proposal，人工 target 占比极高。观测判据：corrected 是否减弱同状态下对 VLA 轴向推进的抑制；同时报告 BC、梯度比、动作幅度和任务终点。风险：corrected 在人工位置存在复制捷径，部署条件输入不同；模式改变有效不代表标签标准正确。
- [ ] **单独验证“actor 拽住 VLA”。** 在安全、可重复的对准状态，冻结当前 actor，比较窗口内 VLA 与 actor 的有符号插入轴位移、实际推进深度及人工接管位置。
  支持证据：用户定性观察及 actor/VLA 有毫米级动作差异。观测判据：同一 reference 下 VLA 给正向推进而 actor 给接近零或反向动作，且真实轨迹重复出现；若两者都不推进，应转查 VLA 或控制器。风险：不同起始状态、接触条件和人工操作会混入差异。
- [ ] **审查示教与裁剪的任务影响后再调权重。** 查看正确对准、停止、浅插、完整插入等片段，以及插入轴与 gripper 上的 clip/projection；不要把所有人工动作天然当成正确修正。
  支持证据：高人工占比、投影幅度 `0.171` 和累计裁剪元素。观测判据：能定位被截断或错误停止的具体动作，并在保持数据/标签不变的对照中验证影响；不能用累计裁剪次数替代这个检查。风险：直接减 BC 会削弱安全约束，Q 当前也不代表完整插入质量。

#### 暂不处理

- 本轮没有独立评测，不补造成功率、不把 43 个正标签当成策略改善证据。
- 不把本次 proposal 运行当成 `rl-exp` 真机试跑计划的验收证据；代码快照不同。
- 不调整网络容量、学习率或 Q/BC 权重；当前优先问题是目标语义和数据覆盖，尚无容量不足或数值发散证据。
- 不将本次归一化问题与 H100 圆柱堆叠训练混同：这里没有退化分位区间，RL 动作空间有 clip。
- 不改源码、配置、计划或既有日志；不提交、不推送、不启动 corrected 实验。
