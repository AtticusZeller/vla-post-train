# TacXense Plan

## Actor 执行改由 warm_up 自动决定，操作员只用手柄

2026-09-21 用户指出 TacXense `docs/architecture.md` § 4.48 记错了历史：`takeover.auto_enable` 是
`d2aa4fb`（2026-09-10）引入并在四个配置里默认开启的既定行为，`58b1f1d`（2026-09-19）删掉它之后把它写
成了"被否的方案"，同时把 actor 挪到键盘 `a` 上，破坏了"所有操作都在手柄上完成"。用户确认恢复自动启用、
不要 `min_actor_updates` 那类更新次数门槛，并要求 actor 的启用/退出完全不经按键：关键阶段内 warm_up
结束即自动启用，成功/失败标记关窗即自动退出。结构与语义的唯一真相是 § 4.48。

判据：`use_actor = recording_enabled and len(online_buffer) >= rlt_schedule.warm_up`，与 critic 更新
预算共用 `OnlineRunner._warmup_done()`。非目标：不改 § 4.49 的状态图（标记后当前单元仍跑满 C 步）、
不改 § 4.53 的 UTD/stride、不给 `auto_enable` 留配置字段、不验证 RTC（用户 2026-09-21 明确 RTC 先不管，
本事务只让 RTC 路径跟着改字段以免 KeyError）。

### Task: actor 判定与控制链

**Change**

- [x] sync 与 RTC 三处判定改用 `_warmup_done()`；`replay_ready` 复用同一函数。
- [x] 删除键盘 `a`、`KeyboardSignals._actor_enabled` 与 controls 里的 `actor_enabled`；
      `sync_controls` 只剩 `recording_enabled`；同步协议 v6→v7、RTC v5→v8。
- [x] 状态 `reason` 由 `manual_switch_on/off` 改为 `warmup_done` / `warmup_pending`。

**Verification**

1. [x] 单测：replay 短于 warm_up 时开窗仍跑 VLA；跨过 warm_up 后下一轮自动跑 actor 且
       `update_step == actor_update_step == 0`；`begin_chunk` 不再返回 `actor_enabled`；
       按 `a` 不改变任何控制；旧协议版本握手被拒。
2. [x] 全量 `pytest tests/`：3 failed / 1106 passed，失败全部是既有的
       `test_rtc_sampler_guard.py` 三条，与基线一致。
3. [x] 改动文件 `ruff check --statistics` 与 HEAD worktree 逐文件对比无新增发现。

**Done**

- [x] 代码里不存在操作员可切换 actor 的路径；Pico 四枚面键覆盖全部操作。
- [ ] 真机验收待做：新 `exp_name` 跑一轮，确认第一轮全程 VLA、replay 过 `warm_up` 后的下一轮开窗即
      由 actor 驾驶、关窗立即退回 VLA。

### Task: 删掉整套键盘路径，手柄成为唯一输入

2026-09-21 用户在上一个 Task 交付后确认：键盘整个删掉，纳入本次改动，只跑相关测试。

**Change**

- [x] `keyboard_signals.py` → `operator_signals.py`、`KeyboardSignals` → `OperatorSignals`；
      删除 pynput 监听、`on_key`、按键去抖（`DEBOUNCE_S`/`_accept_press`）、`stop()`、
      stdin 回车门控与 `enable_keyboard` 参数；`wait_reset` 的 `poll` 改为必填。
- [x] 删除 `--args.rlt-keyboard-enabled`；`rlt_mode` 与 `train_rl` 本地模式在启动时要求
      `--pico4-intervention`（否则 reset 门控会等一个永远不会到来的按键）。
- [x] `pynput` 移出 `conda_enviroment.yaml`；测试文件改名 `test_rlt_operator_signals.py`，
      删掉键盘去抖、stdin 门控与键盘镜像用例，其余改用面键按压。

**Verification**

1. [x] `pytest` 相关用例（operator signals、pico monitor/takeover、window transactions、
       online runner、remote env、rtc、takeover safety、action contract、replay、config）：
       262 passed。按用户要求本次不跑全量。
2. [x] 新增回归：hub 不再有 `on_key` 属性，`begin_chunk` 的键集恰为 `{"recording_enabled"}`。
3. [x] 改动文件 `ruff check --statistics` 与 HEAD worktree 对比无新增（测试文件 14 → 9）。

**Done**

- [x] 仓库里不存在任何键盘输入路径；Pico4 A/B/X/Y 是唯一操作员输入。
- [ ] 真机验收待做：确认无键盘时四键可完整走完一轮（开窗、标记、丢弃、结束/开下一轮）。

### Task: 文档纠正

**Change**

- [x] § 4.48 重写，并把 `auto_enable` 的真实历史与"手柄完备性被打破"这个未记录的代价写回去。
- [x] § 4.42 / § 4.49 / § 4.45、`CHANGELOG.md`、`docs/current_state.md`、`docs/rlt-fast-training.md`、
      根仓库 `docs/tacxense/rlt.md` 同步。
- [x] § 4.42 补记键盘删除的决定、代价与被否的"留键盘做 fallback"；`docs/rlt-intervention-fixes.md`
      里那条 `--args.no-rlt-keyboard-enabled` 的旧建议标为 superseded。

**Done**

- [x] 仓库里不再有"actor 由操作员手动切换"的说法。

## Replay transition 条目结构对齐 RLT 规格

2026-09-20 用户确认：replay 中永久保留 VLA 原始 `a_ref`、实际执行的归一化 `a_exec` 与
`intervention_mask`，训练时再组合
`ã_train = where(m_human, a_exec, a_ref)`。同一份 `ã_train` 同时作为 Actor 条件输入和 BC target；
Critic 继续读取真实执行动作、逐步 reward、next state 与 next state 的原始 VLA reference。
`docs/architecture.md` § 4.52 是字段和训练语义的唯一真相。

字段事务同时包含：`window_id → episode_id`、`recording_enabled → is_critical`，新增
`round_id` / `timestamp` / chunk 级 `source`；`executed_actions` 移出 replay、只保留在 transition
dump；`transition_schema_version` 与 `diagnostic_schema_version` 升为 4。非目标：不改变 step 如何构成
anchor 窗口、不改变 critic TD target、不调整 warmup / buffer size / overlapping subsampling。

2026-09-20 外部 review 发现一个 P1：RTC 分支把 committed zone 的 BC target 恢复成 raw VLA
reference，而已批准公式对完整 chunk 生效。这个例外还造成同一步的 Actor 条件输入是人工动作、BC
target 却是 VLA。确认按规格修复：`committed_len` 只控制 Q 输入的 committed/action splice，不改变
`ã_train` 或 BC target。

### Task: replay 保存可追溯的原始 reference 与执行来源

**Change**

- [x] 同步与 RTC row 都不再覆盖 `curr_obs.ref_chunk`；人工执行动作只保存在 normalized `actions`，
      由 `intervention_mask` 标出。
- [x] `TransitionBuffer` 使用 § 4.52 的字段集合；chunk 级 `source` 从逐步 `action_source` 归约，任意
      两种来源共存即 `MIXED`；绝对物理 `executed_actions` 只留在 dump。
- [x] schema 4 拒绝 schema 1–3 与旧 replay 字段集合。

**Verification**

1. [x] replay save/load 逐位一致；四类 `source` 归约可辨别；人工介入后 replay 的 `a_ref` 仍与 VLA
       原值逐位相同，`a_exec` 可由 `actions + intervention_mask` 直接读出。
2. [x] transition dump 保留实际下发的绝对动作，并使用 schema 4 与新 metadata 名称。

**Done**

- [x] 一条 transition 能同时回答“VLA 建议了什么、机器人实际执行了什么、哪些步来自人工”。

### Task: Actor 输入与 BC target 共用完整 chunk 的 ã_train

**Change**

- [x] `td.training_reference` 是唯一组合函数；Actor loss 与 actor-output logging 共用它。
- [x] 同步与 RTC 都把完整 chunk 的 `ã_train` 同时用于 Actor 条件输入和 BC target；RTC 的
      `committed_len` 只作用于 Q 输入 splice，不对 BC target 增加例外。
- [x] `next_obs.ref_chunk` 始终是 next state 的原始 VLA reference，bootstrap 不套用当前 transition
      的人工 mask。

**Verification**

1. [x] 人工 mask 分别落在 RTC committed zone 与 execution zone 时，Actor 输入和 BC target 对应步
       都等于 normalized human action；未介入步等于 VLA reference。
2. [x] mutation：禁用 reference 组合、让 Actor 使用 raw reference、或恢复 committed-zone BC 例外，
       相应测试必须失败。

**Done**

- [x] `ã_train` 逐元素等于批准公式，且 Actor 条件输入与 BC target 没有模式或分区差异。

### Task: review、全量验证与文档同步

**Change**

- [x] 核验外部 review；确认项回写计划并修复。P1 committed-zone BC 冲突已确认。
- [x] 同步 `CHANGELOG.md`、`docs/current_state.md`、根仓库 `docs/tacxense/rlt.md` 与 § 4.52。

**Verification**

1. [x] touched-file ruff / format / ty 与基线相比无新增发现。
2. [x] 全量 `pytest tests/` 无新增失败；三条既有 `test_rtc_sampler_guard.py` 失败单独记录。
3. [x] 搜索确认 replay 不残留 `executed_actions`、`window_id` 或 row-level `recording_enabled` 读者；
       协议层 `recording_enabled` 与 dump row 的临时 `executed_actions` 继续保留。

**Done**

- [ ] 自动证据满足 § 4.52；真机只保留“新 `exp_name` 检查 replay/dump 字段与行为”的用户验收。

## Phase two MLP 网络结构收敛到 2×256 ReLU baseline

2026-09-20 用户给出 baseline 规格并要求"先写文档后实现"。结构的唯一真相写在 TacXense
`docs/architecture.md` § 4.51，本事务只负责让代码、配置、测试与它一致。这一步是调 warmup 等
训练超参之前的前置项：先把网络固定成一个参数最少、最容易排查的参照点，再去调节奏参数。

目标结构（§ 4.51 表格的等价形式）：

```text
actor:  [z_rl, s_prop, a_ref] → Linear(256) → ReLU → Linear(256) → ReLU → Linear(C*d)
critic: [z_rl, s_prop, a]     → Linear(256) → LayerNorm → ReLU
                              → Linear(256) → LayerNorm → ReLU → Linear(1)
```

与当前代码的差距，逐项：

| 项目 | 现状 | 目标 |
|---|---|---|
| 隐层 | 三个真机配置都是 `[256, 256, 256]`，dataclass 默认 `(512, 512)` | 都写 `[256, 256]` |
| 激活 | `mlp_backbone: rlinf` ⇒ tanh | ReLU |
| Actor LayerNorm | 无开关，预设永远关 | `actor_layer_norm`，默认 `false` |
| Critic LayerNorm | 跟随 `mlp_backbone == "rlinf"` | `critic_layer_norm`，默认 `true` |
| 初始化 | RLinf init，critic Xavier 用 tanh gain | 形状不变，critic Xavier 换 relu gain |
| Actor / Critic 输出 | 已经是线性均值 / 线性标量 | 不变 |

2026-09-20 用户决策（`AskUserQuestion`）：

- `model.mlp_backbone` **删除**，换成 `mlp_activation` / `actor_layer_norm` / `critic_layer_norm`
  三个正交字段。被否的方案是"加第三个预设"和"预设 + 显式覆盖"：前者下次想单独开 actor
  LayerNorm 还得再加预设，后者让 checkpoint 校验要同时比对预设和覆盖值。删除不留兼容值的
  代价是旧 `rlinf` 预设的 checkpoint 无法加载——但 § 4.50 的 `mlp_io_version` 已经让所有
  stage-two checkpoint 必须重建，实际没有可复用的权重。
- 初始化**保留 RLinf 的形状，gain 换 ReLU**：actor 隐层正交 √2 + 输出头 0.01·√2 小 init，critic
  隐层 Xavier(relu gain) + 输出头 `N(0, 0.02)`。被否的方案是全用 PyTorch 默认（代码更少，但初始
  `mu` 的量级由 fan_in 决定，真机第一次打开 actor 会直接下发 O(0.1~1) 的随机归一化动作）。

非目标：不动 § 4.50 的 I/O contract、不动 twin-Q 数量与 TD 目标、不动 `fixed_std`、不动 warmup
与任何训练节奏参数（那是下一个事务）、不引入新的网络族（残差、dropout、spectral norm 等）。

### Task: 结构规格进入网络架构文档

**Change**

- [x] TacXense `docs/architecture.md` 新增 § 4.51：baseline 表格、结构图、选 ReLU 与只给 critic
      加 LayerNorm 的理由、删预设换正交开关的理由、初始化决定、代价与推翻条件。
- [x] 根仓库 `docs/tacxense/rlt.md` 在 phase two contract 之后补结构 baseline 与配置字段名。
- [x] TacXense `CLAUDE.md` 不变量表加一行指向 § 4.51，让每次会话都看到这个唯一真相。

**Verification**

1. [x] 文档里的字段名、默认值与结构图，和本事务要实现的代码一一对应，没有第二处描述网络结构。

**Done**

- [x] 任何人只读 § 4.51 就能写出 actor/critic 的每一层，包括 LayerNorm 的位置和初始化。

### Task: 配置层用三个正交字段描述网络

**Change**

- [x] `RLTModelConfig` 删除 `mlp_backbone`，新增 `mlp_activation: Literal["relu", "tanh"] = "relu"`、
      `actor_layer_norm: bool = False`、`critic_layer_norm: bool = True`；`__post_init__` 拒绝未知激活。
- [x] `config/rlt/*.yaml`（`rlt_fast`、`rlt_0916`、`insert_ethernet_0917`）删掉 `mlp_backbone`，
      hidden dims 改 `[256, 256]`，注释指向 § 4.51。
- [x] `checkpoint_binding.validate_mlp_architecture` 的字段列表把 `mlp_backbone` 换成三个新字段；
      旧 checkpoint 没有这些键时不再用 legacy 默认值放行，而是明确拒绝。

**Verification**

1. [x] 配置单测：默认值就是 baseline；`mlp_backbone` 这个键出现在 YAML 里时解析失败（未知键）。
2. [x] binding 单测：改任一新字段都能被拒绝并指名字段；缺字段的旧 checkpoint 被拒绝。

**Done**

- [x] `config/rlt/*.yaml` 只用这三个字段 + hidden dims 就能唯一确定网络结构。

### Task: `mlp_policy` 按新字段构网，初始化换 ReLU gain

**Change**

- [x] `RLTActor` / `TwinQ` 的 `backbone` 参数换成 `activation` + `layer_norm`；`_make_mlp` 不变。
- [x] 初始化不再由预设名触发：actor 永远用正交 √2 隐层 + 0.01·√2 输出头，critic 永远用
      Xavier(relu gain) 隐层 + `N(0, 0.02)` 输出头；`_init_rlinf_critic` 的 gain 改为按激活函数取。
- [x] `RLTActorCritic.build` 从新字段读取，`actor_hidden_dims or mlp_hidden_dims` 的兜底保留。

**Verification**

1. [x] 单测断言 actor 无 LayerNorm、critic 每个隐层前有 LayerNorm、两者激活都是 ReLU、
      层数等于 hidden dims 长度。
2. [x] 单测断言 `actor_layer_norm: true` 时 actor 也长出 LayerNorm，且 critic 不受影响。
3. [x] 单测断言初始输出量级：默认初始化下 actor 的 `mu` 绝对值均值远小于 1（小输出头生效）。
4. [x] `pytest tests/` 全绿（除已知的 `tests/test_rtc_sampler_guard.py` 三条既有失败）。

**Done**

- [x] 从 YAML 到 `nn.Module` 的每一层都能对上 § 4.51 的结构图。

### Task: 复核、静态检查与文档同步

**Change**

- [x] 外部 reviewer 对照 § 4.51 审 diff；确认的发现回写成新条目再实现。
- [x] `CHANGELOG.md` 记一条 Changed（删 `mlp_backbone`、新三字段、baseline 结构）。
- [x] `docs/current_state.md` 更新 phase two 网络现状；真机未验证的部分标 pending。
- [x] 逐项核对 `docs/2026-09-15-rlt-stage2-rlinf-tacxense-comparison.md` 中受影响的行，标注
      baseline 与 RLinf 的已知差异，而不是让那份对照表继续声称"已对齐"。

**Verification**

1. [x] 改动文件的 `ruff check` / `ruff format --check` 与 base 结果一致；`uvx ty` 无新增发现。
2. [x] 全量 `pytest tests/` 与基线对比无新增失败。

**Done**

- [x] 仓库里不存在 `mlp_backbone` 的残留引用（代码、配置、测试、文档除历史记录外）。

## RLT phase two MLP 输入输出统一为 quantile-normalized delta contract

2026-09-19 用户确认并要求执行。任务从根仓库 `ad7509e`、TacXense `5a77e1d`
建立独立 worktree 与 `codex/rlt-actor-io-standard` 分支；原工作区正在进行的 Pico 接管与
critical-trace 改动不进入本事务。2026-09-19 按用户决定，未提交改动迁到已推送的根仓库 `283dba3`、TacXense
`c52aca0`（含 Pico 接管与 anchor 窗口）之上继续；本事务的决策条目编号顺延为 § 4.50。

目标是把 phase two 的 MLP I/O 收敛成唯一标准，不再让 raw/execution、canonical、direct、
reference-residual 等模式并存。约束如下：

```text
state_raw ──quantile norm──────────────────────────────→ proprio
VLA absolute ref ──delta mask(state_raw)──quantile norm→ ref_chunk

actor input  = concat[z_rl, proprio, flatten(ref_chunk[:C])]
actor output = Linear mean → fixed-std Gaussian sample → clip[-1, 1]

clipped normalized action ──inverse quantile──→ physical delta/action
                         ──state rebase────────→ absolute executable chunk
                         ──rot6d/gripper projection──→ current controller
```

- `state_raw` 保留绝对当前状态，只供 delta 编解码、rot6d fallback、物理量日志与控制器适配；
  actor/critic 不读取 raw state。
- `proprio` 使用同一 VLA checkpoint 的 `norm_stats["state"]`；`ref_chunk`、replay action 与
  actor output 使用 `norm_stats["actions"]`。前 18 个 action 维先按 VLA `DeltaActions` mask
  减当前 state，夹爪保持 absolute opening，再对全部 20 维应用同一种 quantile 公式。
- ~~输入归一化不 clip~~ **2026-09-19 用户改为**：归一化后的 proprio 与动作类输入（ref_chunk、replay
  执行动作 / critic 输入、BC target）也 clamp 到 `[-1, 1]`，与 actor 输出同一范围；夹爪先做物理
  `[0, 1]` 投影再归一化。越界不再留在张量里，只保留计数审计（`codec_out_of_range`、离线
  `audit_action_range.py` 读未 clamp 的原始动作）。actor 的 Gaussian mean/sample 仍在交给 critic 或
  inverse norm 前 `clip[-1, 1]`。代价：proprio 与 VLA 自己看到的（不 clip）不同；超出 q01/q99 的人工
  纠正在 BC target 里被截断。
- 机器人端 `send_action` 接口要求 absolute TCP/gripper target，所以“physical delta → controller”
  在本仓必须经过 state rebase；不改变远程协议、机器人驱动或控制器 action schema。
- `z_rl`、phase-one token 网络及其 prefix 路径不变；匹配同一 VLA identity 的 token checkpoint
  可以复用。旧 stage-two actor/critic/optimizer/replay 的 I/O 含义不同，明确拒绝 resume/serving，
  必须使用新的 `exp_name`。
- 本事务不包含 Pico 接管、critical trace、奖励归属、UTD、RTC cadence 或算法目标调整；不带入
  原工作区未提交改动，不提交或推送，除非用户另行要求。

### Task: 文档先固定唯一 MLP I/O contract

**Change**

- [x] 在 `docs/tacxense/rlt.md` 写清 raw state、normalized proprio、normalized delta action、
      actor clip、inverse norm、state rebase 与 absolute controller target 的顺序和职责。
- [x] 在 TacXense `docs/architecture.md` 增加决策条目，说明为何移除 execution action、
      reference-residual、gripper 特殊 sigmoid/clamp 与 `action_scale` 运行时分支；同步
      `docs/current_state.md`，但在代码验证前标为 pending。

**Verification**

1. [x] 对照 VLA transform 顺序确认公式与 `DeltaActions → Normalize` 一致；对照
       `RealEnv.send_action` 确认文档最终输出为 absolute executable target。
2. [x] 逐项检查后续代码、测试与配置都能追溯到上面的唯一 contract，没有第二套 action space。

**Done**

- [x] 文档能唯一回答 actor/critic 每个输入字段和 action tensor 所处的表示空间、是否 clip、
      使用哪份统计量，以及 controller 最终收到 absolute 还是 delta。

### Task: 固定统计量预处理同时产出 raw state 与 normalized MLP observation

**Change**

- [x] 让 `ActionCodec` 从 VLA checkpoint 同时绑定 `state` 与 `actions` 的 q01/q99，并提供
      `normalize_proprio(state_raw)`；缺少 quantile stats、维度不匹配或非有限统计量时启动即失败。
- [x] action encode 统一为“delta mask → 全维 quantile norm → clamp[-1, 1]”（用户 2026-09-19 改），
      返回 clamp 前的逐维 q01/q99 越界审计；`normalize_proprio` 同样 clamp；decode 统一为“inverse quantile → delta state rebase →
      rot6d 投影/physical gripper clamp”。
- [x] `FeatureExtractor` 和 replay observation 显式保存 `state`（raw）与 `proprio`（normalized）；
      actor/critic 只拼 `proprio`，codec 和物理量指标只读 `state`。

**Verification**

1. [x] 用人工 q01/q99 验证 state/action 公式逐元素等于 `utils.transforms.Normalize` /
       `Unnormalize`，包括 18D delta 与 2D absolute gripper。
2. [x] 覆盖 ref/human / proprio 超出 q01/q99 时被 clamp 且越界被计数，以及 actor 范围内 action 的
       encode/decode roundtrip、rot6d fallback、gripper physical clamp。
3. [x] replay sample 同时返回 raw `state` 与 normalized `proprio`，保存/恢复保持逐位一致。

**Done**

- [x] 同一个 raw observation 在 online runner 与 RLT serving 中产生相同 `proprio` / `ref_chunk`；
      改变 raw-state 数值不会绕过 fixed stats 直接进入 MLP。

### Task: Actor/Critic 只保留 direct normalized-delta Gaussian contract

**Change**

- [x] Actor 输入顺序固定为 `[z_rl | proprio | normalized ref_chunk]`；reference dropout 只清零
      actor 的 ref 输入，BC target 不变。Critic 输入固定为
      `[z_rl | proprio | normalized action_chunk]`。
- [x] Actor 最后一层保持线性；确定性路径 clip mean，采样路径先加 fixed-std Gaussian 再 clip，
      所有 action 维统一 `[-1, 1]`，不再按 gripper 选择 sigmoid。
- [x] 删除 `actor_output_mode` / `actor_residual_bound` / `execution_gripper_activation` /
      `action_space` / `action_scale` 的运行时分支与 shipped YAML 键；人工干预 transition 始终把
      BC target 换成对应的 normalized executed action。
- [x] checkpoint 元数据增加新的 MLP-I/O / replay schema version；旧 stage-two checkpoint 给出
      明确的不兼容错误，phase-one token checkpoint 仍按 prefix/VLA identity 规则复用。
      实现：`mlp_io_version = "quantile-delta-v1"`；phase one 只把 codec 参数写进元数据、不参与 z_rl，
      token 校验因此不再比较 codec 块，norm stats 由 `vla_identity` 覆盖。
- [x] 2026-09-19 用户决定：`scripts/rlt/calibrate_action_scale.py` 去掉 `action_scale` 推荐与
      `--write-scale`，只保留 reference / human 动作逐维 q01/q99 越界统计与退出码，改名
      `scripts/rlt/audit_action_range.py`；`rl.dump_transitions_dir` 保留为它的输入。

**Verification**

1. [x] 单测锁定 concat 顺序、reference dropout、linear mean、Gaussian-before-clip、确定性 clip、
       全维 `[-1, 1]` 与饱和区梯度行为。
2. [x] TD target、actor loss、BC/human target、同步与 RTC 执行、serving 都只消费同一 normalized
       action contract；测试中没有 raw action 或 raw state 进入 actor/critic。
3. [x] 所有 `config/rlt/*.yaml` 解析后只有一个 MLP I/O contract；旧字段作为 unknown key 失败。

**Done**

- [x] 给定同一 `z_rl + raw observation + VLA ref`，训练采集与 serving 的 actor normalized chunk
      和最终 absolute executable chunk 一致；旧 stage-two checkpoint 不会被静默重解释。

### Task: 按计划复核、验证并同步文档

**Change**

- [x] 用独立 reviewer session 按本计划审查 diff；逐条复现并处理确认的问题，任何需要改变上述
      contract 的发现先回到用户确认并更新计划。
- [x] 验证完成后同步 TacXense `CHANGELOG.md`、`docs/architecture.md`、`docs/current_state.md`、
      `docs/rlt-fast-training.md` 与本工作区 `docs/tacxense/rlt.md`；不把未跑的真机结果写成已验证。

**Verification**

1. [x] `pytest tests/`；对修改文件运行 `ruff check`、`ruff format --check` 与 `ty check`。
2. [x] 运行不依赖真实权重的 synthetic checkpoint / serving 集成测试；检查 final diff 和两层仓库
       `git status`，确认不含原任务改动。
3. [ ] 若本机没有匹配的 VLA/token checkpoint，则把真机启动验收保留为用户项：新 `exp_name`
       启动后 metadata 显示新 I/O schema，第一条 actor chunk 的 normalized 值全在 `[-1, 1]`，
       controller 收到 finite absolute target。

独立 review（2026-09-19）结论：无 blocking finding。确认并处理的问题：

- [x] 没有 `metadata.pt` 且开 `allow_legacy_checkpoints` 时，serving 会静默加载旧 actor（旧 actor 输入宽度与新的
      相同，strict load 能过）。复现后修正：缺 metadata 也按 `mlp_io_version` 不符拒绝，补测试
      `test_serving_rejects_checkpoint_without_metadata_even_when_legacy_allowed`。
- [x] Done 项"采集与 serving 一致"缺直接证据：补 `test_collection_and_serving_agree_on_features_and_executed_chunk`
      （runner 存 checkpoint、serving 加载，同一 obs 的 features 与绝对 chunk 逐位相等；让 serving 用 proprio
      decode 的变异会使其失败）。
- [x] `encode` 在归一化前把夹爪投影到物理 [0, 1]，与原 Task 2 "输入路径不 clip" 字面不一致。用户 2026-09-19
      决定改 contract：归一化后的 proprio 与动作类输入都 clamp 到 [-1, 1]，夹爪物理投影保留（统计量
      超出 [0, 1] 时它仍起作用）。
- 未处理：`docs/rlt-integration-acceptance.md`、`docs/rlt-calibration-openpi-review.md` 仍写着旧的
  `action_scale` 校准步骤，属于历史报告，按维护者规则不改。

自动证据（改为输入 clamp 之后重跑）：全量 `tests/` 1058 passed、3 failed（`test_rtc_sampler_guard.py`，改动前同样失败）；改动文件
ruff check / format 无新增问题（改动前已不合规的文件未整体重排）；`ty check` 相对基线无新增诊断。

**Done**

- [x] 自动检查通过，reviewer 没有未处理的 blocking finding；文档把自动证据与待真机验证分开，
      且两层 worktree 只包含本事务文件。

## Pico 接管的夹爪一致性与操作失误告警

2026-09-19 用户要求并确认（夹爪一致按开/闭判定）。已提交 `58b1f1d`，未推送；全量 `tests/` 1090 passed、3 failed
（`test_rtc_sampler_guard.py`，改动前同样失败）。真机验证见"关键阶段采集重构"事务末尾的第 4、5 条。

用户的规格：运动键（SDK `grip`）握住后才检测手柄运动；夹爪键（SDK `trigger`）的变化不算接管依据。
接管前夹爪状态必须和机器人一致——要开就开、要关就关——再加上手柄的相对运动，才算真正开始
intervention；不能出现"机器人夹爪闭着，一接管就突然张开"。松开运动键时，手柄姿态与夹爪都应该相对
静止。这些操作失误要打 warning。

事实依据：

- lerobot-xense `Pico4.get_action` 的夹爪目标是按扳机**绝对映射**的：`1 − trigger × gripper_width`
  （1 = 开、0 = 闭），而且每帧都更新，不管运动键有没有握住。接管那一帧起，两只手的夹爪都直接跟随各自
  的扳机，和机器人当前夹爪无关，这就是用户说的突然张开。
- 机器人读回的夹爪位置同为 [0, 1]、1 = 开（`gripper.get_gripper_position`）。但夹住物体时实测停在物体
  宽度上（命令 0，实测可能 0.4），所以比较对象取**最近一次下发的夹爪命令**，而不是实测位置。

### Task: 接管 = 运动键 + 夹爪一致 + 手柄运动

**Change**

- [x] 去掉接管条件里的扳机变化（`rl.intervention.takeover_trigger` 删除）。接管条件改为：运动键已握住，
      任一手柄相对按下时刻位移 ≥ 5 mm 或转角 ≥ 3°，**且**两只手的扳机映射夹爪 `1 − trigger × width`
      与最近一次下发的夹爪命令开/闭一致（以 0.5 为界，≥ 0.5 为开；用户决定只看开/闭，不看差值）。
- [x] 运动已达阈值但夹爪不一致：不接管，policy 继续执行；打 warning，写明哪只手、扳机映射值、机器人命令值、
      该往开还是往闭调。同一次按住运动键只提示一次，直到一致或松开。
- [x] 最近一次下发的夹爪命令由 `RealEnvAdapter` 从它发出的 20 维动作里取（第 18、19 维），传给控制器。
      回位后尚未下发时退回机器人实测夹爪。

**Verification**

1. [x] 单测：运动达阈值但一只手夹爪开/闭不一致 → 不接管、恰好一条 warning；调成一致 → 接管。
2. [x] 单测：夹住物体（命令 0、实测 0.4）、扳机捏紧 → 接管，不被实测值拦住。
3. [x] 单测：扳机单独变化、手柄不动 → 不接管。
4. [x] 单测 `test_takeover_check_sees_the_gripper_last_sent_to_the_robot`：控制器每一步收到的夹爪参照值
       等于上一步实际下发动作的最后两维；尚未下发时为 None（退回实测）。
5. [x] 变异：去掉夹爪检查 → 2 条失败；只用实测夹爪 → 1 条失败；不记录下发的夹爪命令 → 1 条失败。

**Done**

- [x] 夹爪不一致时不会发生接管，因此也不会出现接管瞬间夹爪跳变。**更正**：计划写"单测断言接管前没有
      调用 `get_override_action`"，实际断言的是不一致时 `poll_and_decide` 返回 False、`reset_to_pose` 未被
      调用；`step_chunk` 只在它返回 True 时才调用 `get_override_action`。
- [x] § 4.49 状态图与 `rl.intervention` 同步更新（YAML 删除 `takeover_trigger`）。

### Task: 松开运动键时不静止就告警

**Change**

- [x] 控制器保留接管期间最近约 0.2 s（6 个控制周期）的手柄读数。松开那一帧，如果这段时间内手柄位移
      ≥ 5 mm、转角 ≥ 3°，或任一只手扳机映射夹爪的开/闭翻转过，打 warning（"松开时仍在移动 / 夹爪在变"）。
      只告警，不改变行为：运动键一松机器人就不再跟随，policy 照常重启。

**Verification**

1. [x] 单测：松开前持续移动 → 一条 warning；夹爪开/闭翻转 → 一条 warning；静止松开 → 无 warning；
       三种情况 release 事件都照常产生。
2. [x] 变异：去掉松开检查 → 2 条失败。

**Done**

- [x] warning 不影响 release：`consume_release_event()` 在三种情况下都为 True。

## § 4.49 状态图作为唯一规格，删除与之冲突的旧文档

2026-09-19 用户要求：用户给出的采集状态图是"唯一真相"，防止后面走偏；与它冲突的旧内容应当删除，只留在
git 记录里，免得污染上下文。CHANGELOG 与带日期的报告（如 2026-09-16 对齐清单、2026-09-10 训练复盘）属于
历史记录，按用户决定保留不动。已提交 `58b1f1d`（上游文档）与本仓库本次提交（工作区 `rlt.md`）。

### Task: 状态图原样进入上游 `architecture.md`，并在每次会话都被看到

**Change**

- [x] 上游 § 4.49 改为"RLT phase two 同步采集工作流（唯一规格）"：用户原图全文 + `◆` 标出的问答补充，
      其后是实现对应、被否方案、范围、代价。开头声明冲突时以图为准，发现冲突就删掉旧内容而不是并列保留。
- [x] 工作区 `docs/tacxense/rlt.md` 删掉图的副本，只留指向 § 4.49 的指针和要点，避免两份内容各自演化。
- [x] 上游 `CLAUDE.md` 的 Invariants 表加一行指向 § 4.49：`architecture.md` 不会自动进入会话上下文，
      `CLAUDE.md` 会。
- [x] 按用户措辞修正图中表述："没有真正接管"写成"运动没达到阈值（或夹爪不一致）"；按键统一写成
      运动键（SDK `grip`）/ 夹爪键（SDK `trigger`）；补入"松开即结束、不设单独的进入 / 退出按键"。

**Verification**

1. [x] 用户原图逐行在 § 4.49 中都能找到（脚本逐行 `grep -F`，缺失 0 行）；上游与工作区两份图 diff 后只差
       一行措辞，之后工作区副本删除。

**Done**

- [x] 状态图只存在于上游 § 4.49 一处；`CLAUDE.md` Invariants 表有对应行。

### Task: 删除"当前真相"文档里与规格冲突的旧内容

**Change**

- [x] `architecture.md`：§ 4.43 改写为只描述 RTC 仍在用的终局写回规则；§ 4.44 / 4.46 / 4.47 删掉对旧门控、
      旧截断的引用；§ 4.45、§ 4.48 只写当前决策与被否方案，删掉"曾经怎样、后来撤销"的叙述。
- [x] `current_state.md` 的 RLT 状态段与已知缺口 § 8、`rlt-fast-training.md` 的指标说明 / 定长约束 /
      中断语义段，按 § 4.49 重写为只写现状。
- [x] `CHANGELOG.md` 只改 `[Unreleased]` 顶部几条描述中间状态的条目（`min_actor_updates`、门控值日志、
      终局截断回写）；其余历史条目保留。

**Verification**

1. [x] 在 `architecture.md`、`current_state.md`、`rlt-fast-training.md`、`CLAUDE.md` 中检索 `min_actor_updates`、
       `auto_enable`、`TakeoverConfig`、`actor_gate`、`gate_passed`、`actor_off`、`握住即接管` 等旧概念，剩余
       命中只在 RTC 仍成立的 § 4.43 规则与 RLinf 对照说明里。

**Done**

- [x] 当前真相文档里不再有与 § 4.49 冲突的描述；旧内容只在 git 历史、CHANGELOG 历史条目与带日期报告中。

## RLT phase two 关键阶段采集重构：运动门控的人类介入与 anchor 重叠窗口

2026-09-19 用户给出目标工作流，唯一规格是上游 `architecture.md` § 4.49 的状态图（`rlt.md` 只留指针）。本事务按它重构
同步模式的采集与 replay 构造。D1、D2、D3 与范围已由用户确认（2026-09-19）。代码、测试与上游文档已完成，
已提交 `feature/rlt-test` 的 `58b1f1d`（CHANGELOG 指针 `c52aca0`），未推送；剩下真机验证（本节末）。全量 `tests/`：1084 passed、3 failed（`test_rtc_sampler_guard.py`，改动前同样失败）。

**规格以本次对话为准。** 用户明确：上游 `docs/`（如 `architecture.md` § 4.43）与此前的约定凡与本工作流
冲突者一律作废，文档同步时按本工作流改写，而不是保留旧说法。

依据：

- openpi-RLT（`~/DevSpace/openpi-RLT`，`c1e40ac`）的 chunk replay 模式就是这套流程：执行时间轴连续；
  anchor 取每个执行 chunk 起点，再加上人松手后 policy 重新推理的起点（`policy_anchor_offsets`）；每个
  anchor 取 `chunk_len` 步构成窗口，允许重叠；窗口末端观测在 episode 结束后补做特征提取。它每步都采
  观测，没有运动门控。
- RLinf（`origin/main`）的 SpaceMouse / Gello 只有检测到运动时才算 `driving`
  （`norm(arm) > MOVEMENT_EPSILON` 或夹爪按下）；它的 Pico 只要握着就算介入。
- lerobot-xense `Pico4.get_action`：位置按 `start + (cur − ref) × sens` 映射，姿态按接管时刻算出的
  offset 映射，两者的参考都在 `reset_to_pose` 之后第一次 `get_action` 时设定。因此只要把
  `reset_to_pose`（对齐到机器人实际 TCP）从"握住"挪到"检测到运动"，就是以接管时刻为起点的相对运动
  控制，**不需要改 lerobot-xense**。它没有死区，`filter_window_size=1`，手柄抖动会原样进入命令，
  所以"是否在动"只能用阈值判断。

现状与目标的差距（同步模式）：

| 目标 | 现状 |
|---|---|
| 握住后 policy 继续执行，检测到相对运动才接管 | 握住那一刻就暂停 policy，机器人原地保持 |
| （2026-09-19 用户决定不做）介入中的静止帧过滤 | 静止帧照常记成人类 step，保持不变 |
| 松手后的 P' 补满前一个 MIXED 窗口，窗口可重叠 | 被松手截断的 chunk 长度不足 C，整条丢弃并标 `collection_gap` |
| 窗口末端可能落在 chunk 中途（例中 s10） | 只在 chunk 或 segment 结束时采观测 |
| 按标签后当前 chunk 跑完，最后窗口带 terminal reward | 按标签立即截断，reward 写回上一条 transition（上游 `architecture.md` § 4.43） |

边界：

- 只改同步模式，RTC 先不管（用户决定）。控制器"握住待命、检测到运动才接管"是两种模式共用的代码，
  RTC 会随之改变，但不在本事务验证范围内。
- Warmup / Online 仍由键盘 `a` 手动切换（用户决定）。
- 不改 lerobot-xense。改动都在 `methods/tacxense` 的 `feature/rlt-test`，commit / push 等用户要求再做。
- replay 行的字段不变。窗口重叠会让同样的采集时长产生更多行，rollout unit 攒得更快；每个 unit 的
  更新预算不变，所以单位真实时间内的更新次数会变多。

规格：

- **D1 标签的结束时机（已确认）。** s/f 不再截断。关键阶段在"当前执行单元"结束时结束：policy chunk 是 C 步；
  人类段也是 C 步。如果单元被松手提前结束，重启的 P' 仍属于关键阶段，P' 跑完
  C 步时结束。terminal 窗口就是最后这个单元的 anchor 窗口：最后一步 reward 为 1（success）或
  0（failure），`done = True`。这推翻上游 § 4.43 的截断语义。`e`、`x`、步数上限、`b` 关窗仍立即
  生效，未标注的数据照旧丢弃。
- **D2 接管阈值与配置位置（已确认；不做静止帧过滤）。** 放进 RLT YAML 的新块 `rl.intervention`，由服务器经 `configure_collection`
  下发到机器人端，同时记进 W&B config。初始值（待真机标定）：
  - 接管：任一手柄相对"握住时刻"的位移 ≥ 5 mm、转角 ≥ 3°，或扳机读数变化 ≥ 0.1；
    **更正（2026-09-19）**：扳机变化不再算接管依据，改为"运动 + 两只手夹爪开/闭一致"，见"Pico 接管的夹爪
    一致性"事务。
- **D3 中途关 actor 不再丢弃任何数据（已确认，撤销上一事务的这条规则）。** 按 `a` 关 actor 只让下一个
  chunk 起改用 BASE，已采数据照常入库。同步与 RTC 里上一事务加的丢弃逻辑与 `actor_off_chunks_dropped` 一并删除。

### Task: 握住 Pico 只是待命，检测到相对运动才接管

**Change**

- [x] `Pico4InterventionController` 分成两个状态：握住但没动是"待命"，`poll_and_decide` 返回
      False，policy 照常执行；手柄相对握住时刻的位移、转角或扳机变化超过 D2 阈值时才转为"接管"。
      接管那一帧对齐到当时机器人的实际 TCP（`reset_to_pose`），之后下发相对运动。松手：只有接管过才
      产生 release 事件，只待命过则不触发重新推理。
- [x] 手柄原始位姿直接从 `xrt.get_*_controller_pose()` 读，不在待命期调用 `get_action`。否则
      `Pico4` 会在握住时刻就设定参考点，接管时机器人会跳回握住时的位姿。

**Verification**

1. [x] 假 xrt / teleop 单测：握住不动的若干帧，env 收到 policy 动作，`reset_to_pose` 未被调用；
       手柄移动 6 mm 的那一帧转为接管，`reset_to_pose` 收到的是这一帧的机器人 TCP，而不是握住那一帧的；
       只待命就松手时，`consume_release_event()` 为 False。
       （`tests/test_pico_takeover_motion.py`。**更正**：单测断言的是 `poll_and_decide` 在待命期返回 False；
       "env 收到 policy 动作"由 `step_chunk` 按该返回值选动作的既有逻辑保证，没有另写 env 级断言。）

**Done**

- [x] 上述单测在"握住即接管"的旧逻辑下会失败（变异验证）。把 `_decide_takeover` 改成握住即返回 True 后，9 条中 8 条失败。

### Task: 关键阶段按 anchor 构造可重叠的 C 步窗口

**Change**

- [x] 服务器端同步 `_run_episode` 维护关键阶段的连续 step 轨迹（执行动作、reward、来源、人类标记），
      替换"一个 chunk 一行、不足 C 步丢弃"的做法。anchor：每个 policy chunk 起点（松手后的重启也是
      一次新的 `step_chunk`，天然是 anchor）；人类段起点（机器人端每满 C 步切一段，现有逻辑）。
      窗口 `[a, a+C)` 在轨迹达到 a+C、且那一步的观测特征已有时生成一行；next_obs 取 s_{a+C}。
- [x] 窗口末端落在 chunk 中途时（例中 s10 在 P' 里），服务器下发 P' 时就知道偏移 k，经 `step_chunk`
      新增的 `capture_at=[k]` 让机器人在执行第 k 步后额外采一次观测。采到的观测在返回后做特征提取。
      这样不需要每步都把图像传回服务器。remote 协议两端（`remote_env.py`、`rlt_mode.py`）同步加这个字段。
- [x] 删除针对"不足 C 步的 chunk"的 `collection_gap` 与截断标签逻辑；关键阶段结束时仍未补满的窗口
      直接丢弃。

**Verification**

1. [x] 单测复现 § 4.49 状态图的 C=10 例子：第 3 步接管、第 8 步松手，得到 A 的来源是
       `[P P P H H H H H P' P']`，next_obs 来自 `capture_at=[2]` 采到的观测；B 覆盖第 8～17 步；
       两者重叠。
2. [x] 单测：第 3 步接管、第 23 步松手（跨两个 chunk 以上），anchor 为 0、10、20、23，窗口为 [0,10)、
       [10,20)、[20,30)、[23,33)。
3. [x] `tests/test_rlt_*.py` 全绿。受影响的旧测试（partial chunk、`collection_gap`、4.43 截断）按新
       语义改写，每条改写在计划里注明原因。
       删除：`test_only_full_chunks_enter_replay`、`test_interrupted_human_window_labels_the_last_complete_chunk`、
       `test_label_at_segment_boundary_updates_last_real_transition`、`test_skipped_chunk_keeps_history_*`、
       `test_success_reward_collection_diagnostics`、`test_terminal_truncated_chunk_labels_preceding_transition`、
       `test_terminal_truncation_never_labels_across_a_real_collection_gap`、`test_truncated_terminal_keeps_row_boundary_observation`、
       `test_real_adapter_records_actual_mid_chunk_override_and_success`——都在断言被推翻的 4.43 截断 / 不足 C 步丢弃语义。
       新增：`test_release_restart_overlaps_the_mixed_window`、`test_label_must_close_a_full_unit`、
       `test_label_mid_chunk_runs_the_chunk_out_*`、`test_label_before_release_is_reported_by_the_restarted_chunk`、
       `test_human_hold_release_and_label_build_overlapping_windows`、`test_takeover_thresholds_reach_the_robot_before_reset`、
       `tests/test_rlt_critical_trace.py`。`test_transition_recording_and_done_at_episode_boundary` 的 reward 断言改为
       failure 标签让 terminal 最后一步 reward 为 0（D1）。协议版本相关断言 v4 → v6。
       变异验证：`capture_offsets` 恒返回空 → 5 条失败；标签在不足 C 步的单元上报告 → 2 条失败；
       按下那一步保留 reward → 1 条失败。

**Done**

- [x] 例子中的 A 行进入 replay，而现状下它会作为 partial chunk 被丢弃（对照旧代码跑同一脚本）。
      HEAD（`5a77e1d`）worktree 上同一脚本只产出 1 行（P'，全 VLA 来源）；新代码产出 A、B 两行。

### Task: 标签在当前执行单元结束后才结束关键阶段（D1）

**Change**

- [x] s/f 改为挂起：当前单元跑完才结束关键阶段；单元被松手提前结束时，经重启的 P' 跑完再结束。
      最后一个单元的 anchor 窗口是 terminal：最后一步 reward 为 1/0，`terminated=True`。

**Verification**

1. [x] 单测：policy chunk 第 4 步按 s，机器人仍执行满 C 步，terminal 行 reward 在第 C 步。
2. [x] 单测：人类段中按 s、随后松手，P' 仍执行，terminal 在 P' 末尾。

**Done**

- [x] 所有被接受的窗口里恰有一行 `terminated=True`，且它是按时间最后的窗口。

### Task: 文档

**Change**

- [x] 上游 `CHANGELOG.md`、`docs/architecture.md` 新增决策条目（推翻 § 4.43，说明运动门控与重叠窗口）、
      `docs/current_state.md`、`docs/rlt-fast-training.md` 操作说明同步。状态图作为唯一规格写入上游 § 4.49，本仓库 `rlt.md` 只留指针（2026-09-19 用户要求）。

**Verification**

1. [x] 文档里的阈值、键位与代码默认值一致。

**Done**

- [x] `rg "4.43"` 的引用处都标注已被新条目取代。**更正**：只在 § 4.43 标题与 `current_state.md`
      已知缺口处标注；`CHANGELOG.md` 历史条目与 § 4.44 / § 4.46 里的历史引用保持原样。代码里唯一的引用在 RTC
      路径，仍然成立。**更正（2026-09-19）**：被"§ 4.49 状态图作为唯一规格"事务取代，§ 4.43 已改写为只描述
      RTC，不再保留"已取代"的标注。

### 真机验证（用户执行）

1. [ ] 握住不动时 policy 照常执行、不误触发接管；轻微移动能触发接管。D2 阈值不合适就按实测调整。
2. [ ] 接管瞬间机器人不跳变；`capture_at` 那一步的控制周期超时不超过 1 个周期。
3. [x] 按键：用户确认握住的 SDK `grip` 就是运动键，`trigger` 控夹爪（2026-09-19）。
4. [ ] 夹爪不一致时终端出现 warning 且不接管；按提示松开 / 捏紧扳机后能正常接管，接管瞬间夹爪不跳变。
5. [ ] 松开运动键前手还在动时出现 warning。

2026-09-19 用户决定：介入保持"按下运动键 + 轻微运动 → 接管，松开 → 结束并重新推理"，不加单独的
进入 / 退出介入按键（Critical phase 中通常不需要松手换姿势）。

## RLT actor 改为纯手动、键盘去抖

已提交 `58b1f1d`，未推送。2026-09-18 用户要求：`min_actor_updates` 没有必要（RLinf 真机也没有）；接管按键要有冷却，防止一次按下被
识别成两次。用户决定连同 `auto_enable` 删掉整个 `TakeoverConfig`：actor 阶段一定是手动控制。依据：
RLinf 真机 `RealworldRLTRoute` 只看 `rlt_switch_flags`，更新次数门槛只存在于仿真路由的 `warmup_updates`；
所有真机 YAML 原先都开着 `auto_enable`，删门槛后若保留它，未训练的 actor 会在录制窗口一开就下发。上游
§ 4.48。

核验结论（未改动的现有行为）：chunk 中途按 `a` 打开 actor，从下一个 chunk 起生效；`b` 关窗、`e` / `x`
在 chunk 中途按下时当前数据按规格丢弃。

### Task: actor 只由 `a` 手动打开，没有更新次数门槛

**Change**

- [x] 删除 `TakeoverConfig` 与 `_actor_takeover_ready`、原因 `warmup_updates`、指标
      `actor_requests_below_update_gate`、状态字段 `actor_gate_min_actor_updates` / `actor_takeover_ready`；
      `gate_passed` 改名 `manual_switch_on`；6 个 YAML 删除 `takeover:` 块。
- [x] ~~chunk 中途用 `a` 关 actor：该 chunk 跑完但不入库~~：同日实现后被"关键阶段采集重构"事务的 D3 撤销，
      丢弃逻辑与 `actor_off_chunks_dropped` 已删除。

**Verification**

1. [x] `test_manual_actor_switch_alone_routes_the_actor`：`actor_update_step == 0` 时按下 `a`，录制窗口内
       即由 actor 执行。依赖门槛的旧测试改写为无门槛语义。

**Done**

- [x] `rg "min_actor_updates|auto_enable|TakeoverConfig"` 在 `src/ scripts/ config/ examples/` 下无结果。

### Task: 键盘按键 0.2 s 去抖

**Change**

- [x] `KeyboardSignals.DEBOUNCE_S = 0.2`，同一键 0.2 s 内的重复按下丢弃，每个键单独计时，作用于所有键盘
      按键（RLinf `KeyboardSession.DEBOUNCE_S`）。放在 pynput 回调层，`on_key` 保持语义入口，现有测试不受影响。

**Verification**

1. [x] `test_listener_debounces_repeat_presses_of_the_same_key`：用假 pynput `Listener` 与可控时钟，0.1 s 内
       第二次按 `a` 被忽略，另一个键不受影响，超过冷却后再按生效。

**Done**

- [x] 一次物理按下不会把 `a` / `b` 切两次（上述单测锁住）。

### 真机验证（用户执行）

1. [ ] 按 `a` 开关各一次，确认没有被识别成两次，终端显示 `manual_switch_on/off`。

## RLT phase two 在线训练接入 W&B 训练日志

2026-09-18 用户确认并要求实现。代码与离线验证已完成，已推送 `feature/rlt-test`（`213563f`、
`412492d`），**待用户在训练机真机跑一轮验收**，验收后移入 `log.md`。

phase two（`scripts/rlt/train_rl.py` → `OnlineRunner`）现在的运行情况几乎只能从终端看。代码里
已有 W&B 接线，但实际从未生效：

- `train_rl.py` 只在 `config.wandb_enabled` 为真时调用 `wandb.init(config=dataclasses.asdict(config))`，
  而 `RLTConfig.wandb_enabled` 默认 `False`，`config/rlt/` 下的 YAML 都没有写这个字段。
- 即使打开，`OnlineRunner.run()` 也只在每个 episode 末 `log(metrics, step=episodes_completed)`
  一次；每次 `_update()` 的 loss / Q / grad norm 只取 episode 均值，逐 chunk 的 actor 输出、gate
  检查值和 VLA 参考动作全都不进 W&B。
- 逐 update、逐 chunk 的明细目前只在 `rl.dump_transitions_dir` 打开时写本地
  `events.jsonl` / `transitions_ep*.npz`，需要事后离线读。

W&B 打开后默认会抓取进程的 stdout/stderr 到 run 的 Logs 页（`wandb.Settings(console=...)` 默认
开启），所以终端里的 episode summary、`RLT training: ...` 状态行不需要另外转写，只需要把**可画
曲线的数值**结构化上传。

边界：

- 改动全部在 `methods/tacxense`（官方仓库直连，`feature/rlt-test`）。按上游 `CLAUDE.md` 同步
  `CHANGELOG.md`。commit / push 等用户要求时再做。
- W&B 只做观测：任何日志代码不能改变机器人收到的动作、replay 内容、训练更新或 checkpoint 格式。
  写日志失败不能中断在线控制循环。
- 不改 phase one（`train_token*.py`）和 serving 路径。phase one 读同一个 `wandb_enabled`，
  YAML 打开后它原有的 loss 日志也会上传。
- `--resume` 现在用 `resume="allow"` 但不传 run id，按 W&B 语义会新开一个 run；本事务不改这一点，
  只加 `group` 让同一 exp 的多段 run 聚在一起。

### Task: 每次 phase two 启动都在 W&B 上留下完整可复现的配置记录

**Change**

- [x] `config/rlt/` 下 YAML 都显式写 `wandb_enabled: true`（用户决定：开关放 YAML，不加 CLI
      flag）。`RLTConfig` 的 dataclass 默认值保持 `False`。**更正**：计划写的是 5 个，实际有 6 个
      （漏数了 `rlt_insert_ethernet_rtc_0914.yaml`），6 个都改了。
- [x] `wandb.init` 增加 `group=<config.name>/<exp_name>`、`job_type="rlt_stage2"`。
- [x] runner 构造后 `run.config.update({"runtime": ...})`：CLI 参数、token checkpoint 路径、
      `ActionCodec.params_dict()`、`preprocessing_binding`、env 拓扑（local / remote）。前三项由
      新增的 `OnlineRunner.runtime_config()` 提供。
- [x] `run.save()` 上传 YAML 原文件。W&B 默认记录 git commit，这里不重复实现。

**Verification**

1. [x] 单测 `test_runtime_config_is_serializable`：`runtime_config()` 可 JSON 序列化且含 codec。
       `train_rl.py` 本身要加载真 VLA，无法在单测里跑；它的 `init / save / config.update` 调用由
       下一条冒烟按原样复现。
2. [x] 临时环境 offline 冒烟：真实 `wandb.init(mode="offline", config=asdict(insert_ethernet_0917))`
       + `run.save(YAML)` + `config.update(runtime)` + 假 env 跑 6 轮，读回 `.wandb` 事务日志。

**Done**

- [x] offline run 的 config 记录里有 `rl.algorithm.rlt_schedule.warmup_min_units=2`、`runtime` 下
      有 `cli / codec / env_topology / preprocessing_binding / token_checkpoint`；`files/` 下有
      `insert_ethernet_0917.yaml`。offline 模式不生成 `config.yaml`，改为解析 `run-*.wandb` 验证。
- [x] `test_shipped_rlt_configs_enable_wandb`：6 个 YAML 解析后 `wandb_enabled is True`。
      `wandb_run=None` 时现有 RLT 测试全绿。

### Task: 每个 update step 上传训练曲线，并能看出 MLP 输出和残差怎么变

用户决定（2026-09-18）：不看训练 batch 的输入统计；关注 MLP 输出动作均值的变化和它相对 VLA 参考
学到的残差。这些都是纯观测量。

**Change**

- [x] 新模块 `src/tacxense/rlt/run_logger.py`（`RunLogger`）用 `define_metric` 分三条 x 轴，不给
      `log()` 传 `step=`：`episode/*` ← `episode/index`，`update/*` ← `update/critic_step`，
      `chunk/*` ← `chunk/index`。episode 指标加前缀上传；`metrics` 字典本身的键不变。
- [x] 每次 `_update()` 末尾把它已有的 info 上传到 `update/*`，actor 相关键只在 actor 更新步出现。
- [x] **MLP 输出均值**：actor 更新步在同一 batch 上额外做一次 `no_grad`、`deterministic=True`、
      无 reference dropout 的前向（在 optimizer step 之后，反映更新后的 actor），按 codec 的
      position / rotation / gripper 分组记 `update/actor_output/<group>_mean|_std`。
- [x] **残差**：同一次前向，把输出和 batch 的 `ref_chunk` 都 decode 到执行空间，记
      `residual_position_mm_*`、`residual_rotation_rad_*`、`residual_gripper_*`（mean / max）。
      计算函数 `actor_output_metrics` 与 chunk 级共用。`_check_actor_chunk` 里的位置分块与 rot6d
      夹角两个内部函数提升为模块级，供两处复用，行为不变。
- [x] 额外前向放在 runner 的 `_update()` 里，不改 `td.actor_loss`，且只在有 W&B run 时计算。
- [x] warmup 期间可见性：episode 行附带 `replay_ready` 与 `warmup_min_units`，结合已有的
      `rollout_units_committed` 看得出为什么还没训练。没有逐次上传 `train_skip` 事件：RTC 模式下它每个
      segment 都会触发，信息与 episode 行重复。

**Verification**

1. [x] `test_wandb_logs_every_update_with_actor_output`：88 条 update 行，`critic_step` 为 1..88，
       actor 输出/残差键恰好出现在 22 个 actor 更新步。
2. [x] `test_wandb_logging_is_observation_only`（正常与 `log` 抛异常两种）：有无 W&B 时 env 收到的
       动作、replay 的 actions / ref_chunk / rewards、update 计数、模型全部参数逐位相同。把额外前向
       改成 `rsample` 或加 reference dropout 时，该测试会失败（已做变异验证）。

**Done**

- [x] offline 冒烟读回：update 行 88 条 = `update_step`，其中 22 条带 `actor_output/*`。
- [x] `test_residual_metric_starts_at_zero_and_grows_for_residual_head`：reference_residual 零初始化头
      的残差为 0（1e-6 内），在人工干预作为 BC 目标的数据上更新 40 步后 > 1 mm；direct 头随机初始化
      即 > 1 mm。**更正**：计划写"单调变大"，测试只检查起点为 0、训练后变大，不检查逐步单调。

### Task: 在线执行按 chunk 上传 AC 输入输出，能定位异常发生在哪一个 chunk

**Change**

- [x] 同步路径 `_run_episode` 每个 chunk 记一条 `chunk/*`：`recording`、`actor_requested`、
      `use_actor`、`deferred_segment`、实际执行长度、人工干预步数、reward、codec clip 数、
      执行耗时、feature 耗时，加上 actor 提议的输出均值 / 残差 / 门控值（`gate_ok`、
      `gate_position_step`、`gate_rotation_step`、`gate_degenerate`）。
- [x] RTC 路径（**更正**：计划写在 `_rtc_decide` 里记，实际在每次 `rtc_push` 之后记，不给决策加延迟）
      每个推送的决策记一行：该边界刚上报的 segment（长度、干预、reward、underrun）+ 本次决策的
      actor 提议，残差只算执行区 `[n, 2n)`。终局 segment 在推送前就结束本轮，它的结果只进 episode 行。
      RTC 行没有 codec clip 与耗时字段。
- [x] actor 没有被评估（warmup、开关关闭）的新决策跑一次 **deterministic 影子推理**，记在
      `chunk/shadow/*`，不进动作、replay、episode tally 与 `actor_gate_rejections_*`。被评估但被门控
      拒绝的 chunk 记在 `chunk/actor/*`，`gate_ok=0`。同步路径的影子推理在 `step_chunk` 之后算。
- [x] 只记标量统计，不上传直方图和原始 npz（用户决定）。本地 `dump_transitions_dir` 行为不变。
- [x] 所有 `log` 走 `RunLogger`：无 run 时空操作；异常只 warning 一次，不向控制循环抛出。

**Verification**

1. [x] 同步：`test_wandb_logs_every_chunk_with_actor_or_shadow`（12 行，`chunk/index` 1..12，5 行
       actor、7 行 shadow）。RTC：`test_rtc_logs_one_chunk_row_per_pushed_decision`（行数 = push 数，
       segment 字段正确）与 `test_rtc_gated_actor_is_logged_as_shadow`。
2. [x] `test_wandb_logging_is_observation_only[True]`：`log` 每次抛异常，episode 照常结束且结果逐位相同。
3. [x] 同上一 Task 的逐位相同测试覆盖影子推理。
4. [ ] **用户真机**：`python scripts/rlt/train_rl.py --config <yaml> --exp-name <run>` 跑 1 轮。
       通过标准：W&B run 在 `<config>/<exp>` group 下，Files 有 YAML，Logs 页有终端输出；
       同步模式下 `chunk/*` 行数与终端 `RLT chunk=` 行数一致；warmup 期的行带 `chunk/shadow/*`。

**Done**

- [x] `test_wandb_rejected_chunk_is_logged_and_shadow_never_counts`：门控拒绝的 chunk 记为
      `chunk/actor/gate_ok=0`、`chunk/use_actor=0`；`actor_gate_rejections_pose_step` 只等于真实评估的
      行数，影子推理不计入。
- [x] warmup 期（actor 未过门控）的 chunk 带 `chunk/shadow/*`（同步与 RTC 测试都覆盖）。
- [x] 临时环境 `tests/test_rlt_*.py` 411 passed。全量 `tests/` 1063 passed、3 failed，失败项都在
      `test_rtc_sampler_guard.py`，在未改动的 `39c4fa1` 上同样失败，与本改动无关。
- [x] ruff：新模块、`train_rl.py` 新增部分、测试新增部分无新发现；改动文件里已有的 ruff / format 问题
      是上游积压，未顺手清理。ty：改动前后同为 23 条既有诊断，没有新增。

### 验证环境

本机没有 `tacxense` conda 环境。在 scratchpad 用 uv 建了临时 venv（`uv pip install -e
methods/tacxense`，实际装的是 torch 2.10.0+cu128、wandb 0.24.2），跑测试与 offline W&B 冒烟。
真机环境的 wandb 版本以 `tacxense` 环境为准（`pyproject` 下限 0.19.1）。

## 删除 phase two 的 actor 执行门控与 holdout 验证

2026-09-18 已推送 `feature/rlt-test`（`a4f5ff0`、`48bb7b9`），待用户真机验收。实现后发现上游
`docs/current_state.md` § 8 记录 2026-09-17 真机 run 门控实测 `position_step` 达 0.55 m（主要是实测位姿
→ chunk 首点的跳变），上游原计划是加强门控；已向用户说明，用户确认仍删除、不做 actor 输出的防御性验证。
上游 `architecture.md` § 4.45 记录该决策与代价。

用户要求（2026-09-18）：actor 过了接管条件后，其动作块应直接执行，不再逐块做位姿跳变检查；
holdout 验证一并删除（用户决定 Q3）。改动在 `methods/tacxense` 的 `feature/rlt-test`。

依据：

- 参考实现 `~/DevSpace/openpi-RLT`（`rlt_online_rl/src/rlt_online_rl/inference.py`
  `_policy_planner`）：actor 返回的 `refined_chunk` 直接作为 `action_chunk` 下发；只在 actor 服务
  调用抛异常时退回 `ref_chunk`（`safe_fallback_to_ref`）。`safe_action_filter` 与机器人端
  `--action_delta_limits` 都是默认关闭的可选钩子，没有逐块拒绝，也没有 holdout 验证。它保留的接管
  条件是 `min_online_actor_version`，对应 TacXense 的 `takeover.min_actor_updates`。
- RL Token 论文 IV 节只描述高斯 actor + BC 正则 + reference dropout，没有执行门控。
- TacXense 自己的 serving 路径 `policies/rlt_policy.py` 已经不做门控：decode 后直接下发，
  rot6d 退化只打 warning（codec 逐行回退到当前姿态）。
- NaN/Inf（用户决定 Q1：原样下发）：本仓库策略动作路径上没有有限值检查（只有 Pico 人工动作有）。
  `lerobot-xense` 的 `FlexivRizon4RT` docstring 写明 C++ RT 线程负责 "NaN check, jump clamp,
  500 ms timeout"；该线程源码不在工作区，属驱动自述，未在本工作区验证。

保留不动：录制窗口要求、`auto_enable` / `a` 请求、`min_actor_updates`、Pico 人工接管、codec 自身的
rot6d 回退（仍计入 `rot6d_fallbacks`）与夹爪 [0,1] 裁剪、`reference_residual` 的 `actor_residual_bound`。

### Task: actor 过接管条件后，其采样动作块原样执行

**Change**

- [x] 删除 `_check_actor_chunk` 及同步 `_run_episode`、RTC `_rtc_decide` 里的调用、非有限值 / rot6d
      退化判断与"整块退回参考"分支；reason `current_chunk_rejected`、`actor_rejected` 状态上报删除。
- [x] 删除 `actor_gate_rejections_*` 计数、episode tally 的 `gate_checks / gate_max`、episode 指标
      `gate_max_*` 与 `actor_gate_rejections_*`、摘要里的 `actor gate` 行与 `max ...` 行、`_status` 对应字段。
- [x] 删除 holdout 验证：`_validate_actor`、`_holdout`、保留验证轮、`_takeover_validation` 与计数、
      `_update` 里"验证未过则 q_weight=0"、`_actor_takeover_ready` 的验证分支（只剩 `min_actor_updates`）、
      reason `validation_pending_or_failed`、`_status` 的 `validation_*` / `takeover/*` 字段。
- [x] `TakeoverConfig` 只保留 `auto_enable`、`min_actor_updates`；删除全部 `max_*`、`validation_*`、
      `holdout_size`、`min_validation_samples`、`required_validation_passes`（用户决定 Q2：连同早已无人
      读取的 4 个阈值）。同步删除 `config/rlt/*.yaml` 里这些键——配置解析对未知键报错。
- [x] 上位机 `examples/bi_flexiv_rizon4_rt/rlt_mode.py` 的状态行去掉 validation 字样。
- [x] W&B：`chunk/actor|shadow/gate_*` 删除；影子推理只记输出均值与残差。
- [x] 上游 `CHANGELOG.md`（Removed）、`docs/architecture.md` § 4.45（新增决策条目，原先没有门控条目）、
      `docs/current_state.md` 已知缺口 § 8 与 `docs/rlt-fast-training.md` 同步。

**Verification**

1. [x] 删除/改写 `tests/` 中针对门控与 holdout 验证的用例；新增：接管就绪后 env 收到的动作等于
       actor 采样 decode 的结果，即使单步位移 1 m。
2. [x] 全部 `config/rlt/*.yaml` 解析通过；`tests/test_rlt_*.py` 全绿；ruff / ty 在新增行上无新发现。
3. [ ] 用户真机：先用小 `min_actor_updates` 跑一轮，确认 actor 接管后的执行情况，并留意驱动端
       NaN / jump clamp 告警。

**Done**

- [x] `grep -rn "_check_actor_chunk\|max_position_step\|actor_gate_rejections\|validation_enabled\|_validate_actor"`
      在 `src/ scripts/ config/ examples/` 下无结果。
- [x] 1 m 位移测试里，接管就绪时 env 收到的正是这 1 m 位移的动作，`use_actor=1`。

## `rlt_fast` 与 `insert_ethernet_0917` 改用 canonical 动作空间

用户决定（2026-09-18）。execution 空间下 direct 头初始输出 ≈0 即基座原点的绝对位姿；canonical 下 MLP
输出是 VLA 自己的模型空间（18 维 TCP 为 `action − state` 按 VLA norm stats 归一化并 tanh，夹爪 sigmoid），
≈0 即"停在当前位姿附近"。0917 的残差界原为米 / rot6d 分量单位，在 canonical 下含义改变，先置 `null`，
数值待按 VLA norm stats 重新推导。已提交 `08fa3a6`；上游 `architecture.md` § 4.47。

- [x] 两个 YAML 改 `action_space: canonical`；0917 `actor_residual_bound: null`，smooth 权重注释标明需复核。
- [x] `tests/test_rlt_mlp_policy.py::test_fresh_direct_head_starts_near_state_only_in_canonical_space`：
      rlt_fast 真实 20 维配置、新初始化 direct 头，canonical 下 decode 后离当前 TCP < 1 cm，execution 下不是。
- [x] `tests/test_rlt_config.py` 固定两个配置的 canonical 与 0917 残差界为空；`tests/test_rlt_*.py` 全绿。
- [ ] 需新 `exp_name` 开 stage2（RL checkpoint 绑定 codec 参数）；token checkpoint 可复用。

## warmup 对齐 openpi-RLT

现状：`rlt_schedule` 只在 replay 攒够 `warmup_min_units`（2 × 30 chunk）后按每 unit 8 次发更新预算；
`rlt_fast` 在第一批 8 次 critic / 2 次 actor 更新后即可接管，0917 在约 32 次 critic 更新后接管。
TacXense 曾有 `warmup_min_size` / `warmup_post_collect_updates`，2026-09-16 为对齐 RLinf 删除
（`tests/test_rlt_config.py` 现在拒绝这两个键）。

openpi-RLT（`rlt_online_rl/src/rlt_online_rl/trainer.py`，`configs/tasks/agilex_ethernet/online_rl.yaml`，
同一网线插入任务）：

- replay 第一次达到 `warmup_min_size: 600` 时锁存，之后一次性要求 `warmup_post_collect_updates: 20000`
  次更新；此后每新增一条 transition 再给 `grad_updates_per_cycle: 5` 次。
- `global_step < warmup_required_updates` 期间 actor 用 `warmup_bc_weight: 10` / `warmup_q_weight: 0.1`，
  之后 `online_bc_weight: 5` / `online_q_weight: 0.1`；`actor_update_period: 2`。
- 机器人端 `_wait_until_online_ready` 等到 learner 的 `ready_for_online`（replay ≥ 600 且 warmup 更新做完）
  才让 actor 上机。
- 数据门槛量级相近（600 条 stride-2 样本 ≈ 24 s，TacXense 60 chunk ≈ 40 s），差距在更新次数：20000 对 8~32。

实测：本机 CPU 上 rlt_fast 维度（canonical，batch 256）单次 `_update` 28.8 ms，20000 次约 9.6 min，
5000 次约 2.4 min；本机 CUDA 驱动不可用，训练机 GPU 耗时未测。

用户决定（2026-09-18，替代上面"一次性 N 次"的草案）：数据门槛 ×10、达标时补齐已有数据的预算、
critic:actor 改 2:1、BC/Q 权重保持固定 5 / 0.1、补齐的更新在达标那一轮轮末一次跑完。

### Task: warmup 门槛放大到 600 chunk，达标时按全部已提交数据补齐更新

**Change**

- [x] `RLTScheduleConfig` 新增 `warmup_catch_up: bool = False`。为真时预算为
      `updates_per_unit × units_committed`（达到 `warmup_min_units` 之前为 0），即达标那一轮把前面每个 unit
      的预算一起补上——对应 openpi-RLT 不设 `warmup_post_collect_updates` 时的
      `adds_total × grad_updates_per_cycle`。为假时保持现有公式，其他配置行为不变。
- [x] resume 校验把 `warmup_catch_up` 与现有三个 rlt_schedule 字段同样对待：改了就拒绝恢复。
- [x] `rlt_fast`、`insert_ethernet_0917`：`warmup_min_units: 20`（600 chunk，对齐 openpi `warmup_min_size: 600`）、
      `warmup_catch_up: true`、`critic_actor_ratio: 2`（openpi `actor_update_period: 2`）。达标那一轮补 160 次
      critic / 80 次 actor 更新，低于现有 `max_updates_per_train_step: 600`，当轮跑完，无需改上限。
      `replay_window_units: 200` 足以容纳门槛。BC/Q 权重不动。
- [x] 上游 `CHANGELOG.md`、`docs/architecture.md` 决策条目、`rlt-fast-training.md` 同步。

**Verification**

1. [x] 单测：`warmup_catch_up=False` 时现有预算测试不变；为真时达标前 0 次，达标那一轮 = 每 unit 预算 × 已提交
       unit 数，之后每 unit 照常增加。
2. [x] 单测：resume 时改 `warmup_catch_up` 被拒绝。
3. [x] 两个 YAML 解析后取值正确；`tests/test_rlt_*.py` 全绿。
4. [ ] 用户真机：约 6.7 分钟标注数据后第一次训练，W&B `update/critic_step` 在那一轮跳到 160。

**Done**

- [ ] （真机）rlt_fast 配置下，第 20 个 unit 提交的那一轮 `update_step` 从 0 变为 160、`actor_update_step` 为 80。

## 标签后的停顿：sliding replay 特征改为批量前向

现象（2026-09-22，真机评测）：人类介入之后、或打完标签重新开始时有较长停顿。用户判断介入本身不是
原因——重新推理只有几百毫秒——怀疑卡在打标签那一下。

定位结论（代码分析，非真机测量）：同步采集里正 stride 的特征物化全部压在**按下成功/失败的那一
刻**。`_materialize_sliding_features` 对每个缺失索引单独调一次 `Policy.infer`，而 `Policy.infer` 的
输入管线写死 `[None, ...]`，batch 恒为 1，于是一次标签要串行跑几十次 2B VLA 前向（每次还含
`num_steps` 步 flow-matching 去噪）。`C=10`/`stride=2`/一段 150 步的 phase 需要 61 次。关键阶段越
长停得越久，这与"介入后卡"的体感一致——因为用户通常介入结束就立刻打标签。

这条与 § "wandb 上报不得阻塞训练循环" 是两个独立的停顿源：那条发生在 drain 期间，这条发生在标签
按下到下一轮之间。删除 `max_updates_per_train_step` 之后 drain 停顿只会更长，两条都需要真机计时
才能分清。

已完成（tacxense `7361225`，决策见 `architecture.md` § 4.53）：

- [x] `Policy.infer_batch`：同一套 input/output transform 与 sampler，中间的前向合并成一次。
- [x] `FeatureExtractor.extract_batch`：逐样本快照 `last_ref_exec`，保留 § 4.52 要求的原始 reference。
- [x] 新配置 `rl.replay_feature_batch_size`（默认 16），纯墙钟旋钮，不进 checkpoint 校验。
- [x] 索引去重与"同一次 forward 同时取 z_rl 与 ref_chunk"——本来就已成立，只是写进了文档。
- [x] CPU 单测：批量 == 逐样本（含 prefix）、任意 batch size 产生相同 replay 行、CUDA OOM 不被
      误当成"不支持批量"而退回串行。
- [x] 删除 `max_updates_per_train_step`，每次 drain 跑满 UTD 欠账。
- [x] 三个真机配置统一到 `C=10`。

**真机验收（待用户执行）**

1. [ ] 日志新增的 `RLT sliding features materialized: indices=… batch_size=… forwards=… elapsed_s=…`
       一行即可读出标签停顿的真实时长与前向次数。记录一段典型 phase 的数值。
2. [ ] 对比 `replay_feature_batch_size: 1` 与 `16` 的 `elapsed_s`，确认加速比与前向次数之比相当；
       若不相当，说明瓶颈不在 batch 而在别处（相机解码、CPU 侧 transform）。
3. [ ] 确认 16 不会 OOM；显存有余量就继续调大，直到停顿可接受或显存拒绝。
4. [ ] 分别记录标签停顿（上面这行）与回合末 drain 停顿（`pending_updates` + drain 耗时），确认
       "介入后卡很久"到底属于哪一个；drain 现已不封顶，预期变长。

**不做（2026-09-22 决定）**

- 异步 learner / replay builder 拆分 + actor snapshot 发布。方案本身成立（允许 stale actor 是前提
  而非缺陷），但改动面覆盖整个 runner 的所有权模型，而批量化之后同步时延已可接受。只有在
  `replay_feature_batch_size` 吃满显存后停顿仍不可接受时才重新考虑。
