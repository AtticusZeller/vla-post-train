# xense-openpi 实验记录

按时间倒序记录外部启动的实验。每节依次保留原始记录、结果分析和下一步；观测、推断与未验证猜想分开。
训练契约见 [rlt-spec.md](rlt-spec.md)，已确认工作见 [plan.md](plan.md)。

## 2026-10-10 · pi05_base_bi_flexiv_insert_ethernet_0928_h100/test1010-2 — corrected 局部对准与人工切回 VLA

### 1 原始记录

#### 任务边界、身份与取证截止

- **W&B：** <https://wandb.ai/XenseRobotics/xense-openpi-hubo/runs/o8ifks0z>；project `XenseRobotics/xense-openpi-hubo`，run `o8ifks0z`，group 未设置。
- **用户定义的阶段任务：** 从离插入口稍有距离的位置开始，actor 调整到正确插入位置，稍微插入即结束示教；评测时对准/浅插后由用户手动关闭窗口，让 VLA 接管后续插入。actor 不承担完整插入，也没有自动判断阶段成功的切换器。
- **用户假设：** Q 可能没有多少作用，因此只采成功人工示教；担心加入完整插入数据会影响对准能力。两条均是研究假设，未由本次对照验证。
- **代码版本：** W&B metadata 与远端 HEAD 均为 `84113a489240e8b221f7f9617c756ea7c1d25fe6`，标题 `chore(rlt): set ethernet 0928 token checkpoint and 20-step chunks`；远端分支 `feature/rlt-jax`。启动时分支未单独记录。与第一次 `68dbe8f` 比较，代码增加 `input_reference` 选择，并设置 `corrected`；另有配置/测试及机器人端 main 的变化，不将所有行为差异归到单一代码行。
  本机 method 仍为 `rl-exp / 7464fec`，根仓 `4c517089312c9fafe88b1cbf25c14dbe70c4df0f` 有既有未提交工作；本 run 在远端裸脚本启动，不是根仓 `lab` 实验。
- **硬件与权重：** `xense-inference`，RTX 5090；VLA `/home/li/hubo/xense-openpi/checkpoints/ehernet_insertion`，VLA 权重 step 未确认；token `/home/li/hubo/xense-openpi/checkpoints/ehernet_insertion/token_encoder/60000`。没有重跑 phase one。
- **归一化身份：** 与第一次相同，`checkpoints/ehernet_insertion/assets/Xense/insert-ethernet-above-desk-0916/norm_stats.json`，SHA256 `00789e9879f3cb6f66d6c2c02ec7352f99f03897b0aed448c4da7b4323a8d2ea`。
- **精度与 seed：** token 配置 `bfloat16`，参数/残差/loss 为 `float32`；phase-two MLP 未显式指定低精度 dtype，未实测权重 dtype；`seed=42`。
- **状态与截止：** 2026-10-10 约 17:08（北京时间）拉取，W&B 为 `running`；14:35:53 启动，最后完整轮为第 139 轮（16:02:42），16:02:49 机器人断连后等待重连。取证时服务进程仍在；W&B 最后日志 runtime 约 `5208 s`，不等于取证时进程墙钟时长。未确认是否已结束机器人侧操作，不将这次写成已完成的 300 轮运行。
- **统计子集：** history 17,957 行，含 139 个 round、13,040 个 update、4,778 个 chunk；完整轮累计 4,702 个 chunk。第 62 轮号下有 76 个未提交尝试的额外 chunk，不能混入完整轮任务统计。
- **证据位置：** 远端 `checkpoints_rlt/pi05_base_bi_flexiv_insert_ethernet_0928_h100/test1010-2/`；取证时最后保存 checkpoint 为 `rl/130`，已检查全部 39 个非空 `transitions/round_*.npz`。本机分析缓存 `/tmp/o8ifks0z-analysis/` 为临时缓存；既定数据挂载当前不可写，未在仓库保存大文件。

#### 影响训练的配置

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

#### 训练数据、指标与人工观察

| 观测 | 本次值 |
|---|---|
| 已入库成功阶段 | **39 段**，各有人工介入；failure 0；2,608 条 transition，39 个 terminal reward 为 1 |
| 采集口径 | 日志出现 40 次 success 标记，其中一段未留在最终入库数据；已提交阶段累计 5,917 执行步。完整轮累计 discard 操作 53 次，不等于 53 个任务失败 |
| 人工数据占比 | 重叠窗口内人工动作 50,181 / 52,160 = **96.206%**；actor 1,702、VLA 277。这不是去重后的真实步占比 |
| 真实执行 | 完整轮 99,720 步，其中人工 10,785 步；总 recording 步 23,219，包括未入库窗口 |
| Warm-up 与更新 | 第 32 轮开始训练；累计 critic **13,040**、actor **6,520**；`2608 × 5 = 13040`，`13040 / 2 = 6520`，无预算欠账 |
| 数据停止增长 | 最后一次训练为第 110 轮；第 111–139 轮无新行、无更新。139 轮中 100 轮无入库行，warm-up 后其中 77 轮无新行 |
| Critic loss | 首次 `0.04851` → 最后 `1.325e-5`；末 500 critic 更新中位数 `1.677e-5`，非单调下降 |
| BC loss | 首次 `0.11734` → 最后 `2.243e-5`；末 500 actor 更新中位数 `2.152e-5`，非单调下降 |
| Q | `q_data` 首次 `−0.03802` → 最后 `0.32650`；`q_pi` 首次 `−0.30562` → 最后 `0.32887`；末段两者约 `0.32`，非单调 |
| Critic 目标与分歧 | 末 500 更新 target std 中位数 `0.16037`；双 Q 差首次 `0.25075` → 最后 `0.003357` |
| BC/Q 梯度 | 末 500 actor 更新加权范数中位数 `0.03307 / 0.02367`；逐次范数比中位数 **1.398**；cosine 中位数 **−0.732**，97.8% 为负 |
| 执行动作与 VLA 的差异 | actor 路由 chunk 844 个；位置残差均值之中位数 **3.558 mm**，末 50 个中位数 `3.988 mm`；完整轮中的 actor 路由 chunk 为 834，差额来自未提交尝试 |
| 工程健康 | dump 的动作/proprio/reference/z_rl 无非有限值；844 actor、3,934 shadow chunk 的 nonfinite 全为 0；完整轮 rot6d fallback 为 0 |
| 裁剪/投影 | 完整轮 out-of-range 元素 42,243、物理 gripper clip 元素 62,161；末 500 actor 更新 projection absolute mean 中位数 `0.14915`。不是失败次数或饱和率 |

**（用户报告的人工评估）** 初期对准成功率估计 `<10%`；示教中后期开始分批手动评测，后期估计 `70–80%`。用户澄清此前“约 60–100 次示教”来自把 W&B 的 100 多个 round 误当成示教次数，应以实际 39 段已入库示教为准。
两阶段评估的精确成功数/总试验数、对应 checkpoint、起始距离分布、是否无人工纠正，均未登记；不能给出置信区间或 Fisher 检验。
这些百分比不由 W&B 的 39 个 success 标签计算，也不能从 phase-positive 数据推导完整插入成功率。

**视频参考：** [Feishu20261010-170700.mp4](/home/atticuszz/Downloads/Feishu20261010-170700.mp4)，时长 `5.667 s`，`540×960`；SHA256 `868257ed1546ae94409b3760a8ec4ff727dd123cfda36c2646681e3b70045093`。
已提取每 0.5 秒代表帧查看，可见两侧夹具握持插头与接口并局部相对移动；用户指定为成功参考，并确认通过手动关闭窗口让 VLA 接管。
视频没有策略来源/窗口状态叠加，不能由画面独立确认切换时刻、是否全程无人纠正或机械完全插入/锁止。

### 2 结果分析

以下源码位置均指 `84113a4` 的 `src/openpi/rlt/` 旧布局。

#### 对准后退出是这次的目标边界，不应按 actor 未完成整段插入判失败

**用户定义：** actor 是有一定起始距离下的局部对准策略；浅插后人工切回 VLA。与第一次讨论的持续接管插入不同，这次主动限定 actor 职责。

**推断：** 在此边界下，对准/浅插 terminal reward 为 1 与阶段任务一致；不能再要求 actor 自主完成剩余插入来判断它是否有效。
但当前是“人工判定阶段完成并关闭窗口”的系统，尚未验证自主切换，端到端插入还依赖 VLA 和切换时机。
依据：`collector.py:73–89,135–152`，actor 仅在开窗且 warmed-up 后使用，关窗后走 VLA。

#### corrected 拟合得更好，但训练 loss 不能证明部署时对准更强

**源码事实：** `td.py:81–100` 用人工替换后的 `bc_target` 同时作为 actor 条件 reference 和 BC 目标；dropout 只随机清零条件 reference，目标不变。部署时输入仍为 VLA reference。

| 可比训练摘要 | 第一次 proposal | 第二次 corrected |
|---|---:|---:|
| 已入库阶段 / transition | 43 / 2,123 | 39 / 2,608 |
| 人工动作位置占比 | 97.569% | 96.206% |
| Actor 更新数 | 5,307 | 6,520 |
| 末 500 actor 更新 BC loss 中位数 | `1.743e-4` | `2.152e-5` |
| 末段 BC/Q 梯度范数比中位数 | 1.845 | 1.398 |

**观测：** 第二次末段 BC loss 约为第一次的 1/8.1。**推断：** 这与 corrected 的输入更容易预测自身目标相容，也与更多更新、更长示教阶段及采集方式改变相容。
仅凭 BC loss 不能证明策略在“原始 VLA reference + 新起始距离”的部署输入上更好；人工估计的改善提供方向性证据，尚无固定条件的受控评测。

- [ ] **未验证**：corrected 本身导致对准改善。验证方式：同一 replay、同一更新预算训练 corrected/proposal，冻结后在相同距离与误差分组下盲测或随机顺序评测。当前还同时改变了示教采集与手动切换流程，不能做模式因果归因。

#### Q 没有关闭，日志也没有证明 Q 对性能没贡献

**观测：** `q_weight=0.1`；末段加权 Q 梯度范数中位数 `0.02367`，BC 为 `0.03307`；cosine `−0.732`，97.8% 为负。
依据：`td.py:98–100` 的 actor loss 与 `learner.py:172–190` 的分项梯度。

**推断：** Q 确实参与且经常与 BC 拉扯；“全是正例示教”不等于“纯 BC 算法”。梯度非零不能证明它有益，梯度冲突也不能证明它无益。

每个 terminal window 的 TD target 应为 `0.99^19 = 0.82617`；非终止 bootstrap 系数 `0.99^20 = 0.81791`。
剔除作废阶段后，按 39 段实际长度与 anchors 计算已记录行为到终点的折扣回报，2,608 个窗口的均值 `0.44947`、标准差 `0.18921`、范围 `0.04954–0.82617`。
末段 Q 约 `0.32`；TD RMSE/target std 约 **2.55%**，说明 critic 对当前目标的拟合误差较小。
bootstrap 跟随的是 next actor 而不是未来人工动作，因此行为回报与 Q 的差值不是直接的 critic 校准误差；Q 描述局部阶段的奖励，不是完整插入价值。

- [ ] **未验证**：只靠 BC 可达到同样对准表现。验证方式：固定数据/预算比较 `q_weight=0` 与 `0.1`，按 actor 自主对准和交接后 VLA 完成率分别统计；不能用当前纯正例 run 单独证明。

#### 70–80% 是有价值的人工观察，但不是 W&B 可复算成功率

**观测：** 用户报告 `<10% → 70–80%`；全部 39 段已入库阶段都含人工介入。没有独立 evaluation stream，也没有记录失败试次分母。

**推断：** 可以记录局部技能看起来有改善，不能写成“39/39 自主成功”或量化算法提升。139 是 round，不是示教数，也不是评测样本量。
100 轮没有新行包含评测、作废或未标窗口，日志不足以给这些轮逐一分配实验用途。111–139 轮权重没有新更新，可以成为固定权重观察片段，但缺少成功/失败与接管记录，不能事后当作完整评测集。

#### 插入数据会削弱对准能力，目前只保留为用户假设

**（用户提出）** 不希望 AC 学习插入，因为完整插入数据可能影响它的对准能力；采用对准/浅插示教与分阶段切换。

**推断：** 缩小任务边界有助于让示教覆盖与考核目标一致。是否存在对准与插入之间的容量冲突、数据分布冲突或监督混淆，本次没有“加入插入数据”的对照，不能据此断言。

- [ ] **未验证**：加入完整插入数据会损害对准。若以后需要检验，只比较固定对准数据与“对准数据 + 插入数据”，对准和插入分开评测；不要将此假设当成当前流程已证明的机制。

### 3 下一步

候选项，不修改 `plan.md`，不启动实验。

- [ ] **先把局部对准和人工交接后的结果分别量化。** 固定 actor checkpoint，按起始距离、横向/角度误差分组；每次记录 actor 无人工纠正的对准/浅插结果、手动关窗时刻，以及 VLA 后续是否完成插入。
  证据：人工估计有明显改善但分母未登记。判据：每组给成功数/总试次及区间，比较时使用 Fisher 检验；人工纠正试次单列。风险：操作员看到结果后选择何时切换会影响端到端表现，需预先固定阶段完成标准。
- [ ] **检验 Q 的贡献，再决定是否改成纯 BC。** 同一 replay、更新预算与 seed，对比 Q 权重 `0` 和 `0.1`。
  证据：Q 梯度不小且常与 BC 冲突，当前没有消融。判据：在同条件下比较自主对准、输出稳定性与交接后插入完成；若纯 BC 等效，才支持省去 Q。风险：训练 loss 可能降低却部署泛化变差，必须看独立试次。
- [ ] **若要归因 corrected，固定数据和训练量再比较 proposal。** 不同时改变起始距离分布、示教终点或交接规则。
  证据：本次 loss 更低但 actor 更新更多、示教采集和任务边界也变了。判据：matched 条件下 corrected 仍提高对准率，并保持交接后完成率；风险：corrected 的复制捷径可能掩盖 reference 输入失配。
- [ ] **保留成功视频，同时给下一次视频叠加策略来源和窗口状态。** 证据：本视频无法独立定位切换时刻。判据：能对应到固定 checkpoint、trial 编号、actor 结束与 VLA 开始；风险：一段成功视频仍是个例，不能替代失败与总次数记录。

#### 暂不处理

- 不要求 actor 一直接管到完全插入，不把对准后退出视为本次阶段任务的失败。
- 不把“完整插入数据损害对准”写成已验证结论，也不自动扩大 actor 的任务范围。
- 不把全部成功示教标签当成独立评测成功率，不为缺失分母编造统计显著性。
- 不将持续等待重连的服务写成已完成实验；此次结论截止上述快照。
- 不修改训练代码、配置、已有计划或第一次实验记录；不提交、不推送、不启动消融或评测。

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
