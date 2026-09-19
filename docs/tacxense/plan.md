# TacXense Plan

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
