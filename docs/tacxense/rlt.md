# TacXense RLT 理解笔记

## Phase two MLP 输入输出 contract

RLT phase two 只使用一套表示：proprio 保留“当前绝对状态”的语义，手臂 action 在相对当前
state 的 delta space 中学习，夹爪 action 保留 absolute opening。三者的数值尺度由 frozen VLA
checkpoint 自带的 quantile stats 固定，不从在线 replay 重新估计。

```text
state_raw ──state q01/q99 ──clamp[-1, 1]────────────────→ proprio
VLA absolute ref ──DeltaActions(state_raw)─────────────→ action representation
                 ──action q01/q99 ──clamp[-1, 1]──────→ ref_chunk

actor input  = concat[z_rl, proprio, flatten(ref_chunk[:C])]
actor mean   = MLP 最后一层的线性输出 mu
train action = clip(mu + sigma * epsilon, -1, 1)
infer action = clip(mu, -1, 1)

normalized action ──inverse action q01/q99─────────────→ physical delta / gripper opening
                  ──delta dims add state_raw───────────→ absolute executable chunk
                  ──rot6d/gripper projection──────────→ controller
```

具体语义：

- `state_raw` 是 20D 当前绝对 TCP pose + gripper state，只供 action delta 编解码、rot6d fallback、
  物理量日志与控制器适配；Actor/Critic 使用其 quantile-normalized `proprio`，不直接读取 raw state。
- action mask 只决定是否减当前 state，不决定是否归一化：前 18D TCP position/rot6d 为 delta，
  后 2D gripper 为 absolute opening；20D 随后都用 `norm_stats["actions"]` 做 quantile normalization。
- normalized proprio、reference、replay action 与 BC target 都 clamp 到 `[-1, 1]`，和 Actor 输出同一范围
  （2026-09-19 用户决定）；越界只以计数留下，离线审计用 `audit_action_range.py`。夹爪先限到物理 [0, 1]
  再归一化。代价是 proprio 与 VLA 自己看到的不同（VLA 不 clip），超出 q01/q99 的人工纠正被截断。
- 训练采集使用 fixed-std Gaussian sample；确定性评估与部署直接使用网络均值。二者都在最后 clip。
- inverse norm 后的前 18D 是 physical delta，后 2D 是 physical gripper opening。本仓控制器接口接收
  absolute target，所以 codec 必须给 delta 维加回本次 observation 的 `state_raw`；这一步是接口适配，
  不改变 MLP 在 delta action space 学习的语义。
- phase-one `z_rl` encoder 与 prefix 路径不变，已有匹配 VLA 的 token checkpoint 可复用；旧
  stage-two Actor/Critic、optimizer 与 replay 的 tensor 含义不同，不能 resume 或 serving。

## Phase two MLP 网络结构 baseline

2026-09-20 确认的唯一结构规格，完整理由见 TacXense `docs/architecture.md` § 4.51。

| 项目 | 配置 |
|---|---|
| 输入 | `[z_rl, proprio, ref_chunk[:C]]` 直接 concat |
| Actor 主干 | 2 × 256 |
| Critic 主干 | Twin-Q，每个 Q 网络 2 × 256 |
| 激活函数 | ReLU |
| Actor LayerNorm | 默认关闭，训练不稳再开 |
| Critic LayerNorm | 默认开启 |
| Actor 输出 | 线性均值 → Gaussian 采样 → clip[-1, 1] → denorm |
| Critic 输出 | 线性标量 Q，不加激活 |

```text
actor:  [z_rl, s_prop, a_ref] → Linear(256) → ReLU → Linear(256) → ReLU → Linear(C*d)
critic: [z_rl, s_prop, a]     → Linear(256) → LayerNorm → ReLU
                              → Linear(256) → LayerNorm → ReLU → Linear(1)
```

配置字段：`model.mlp_activation`（默认 `relu`）、`model.actor_layer_norm`（默认 `false`）、
`model.critic_layer_norm`（默认 `true`）、`actor_hidden_dims` / `critic_hidden_dims`（都写
`[256, 256]`）。原来把激活、LayerNorm、初始化绑在一起的 `model.mlp_backbone` 已删除。

初始化：actor 隐层正交 init（gain √2）、输出头 0.01·√2 小正交 init，让第一批动作落在归一化零点
附近；critic 隐层 Xavier（relu gain）、输出头 `N(0, 0.02)`。

## Replay transition contract

一条 replay row 是一个完整 C-step chunk。`curr_obs.ref_chunk` 始终保留 VLA 原始 reference；人工
接管不会在采集时改写它。实际执行的 normalized action 存在 `actions`，逐步人工位置存在
`intervention_mask`，训练时统一组合：

```text
ã_train = where(intervention_mask, actions, curr_obs.ref_chunk[:C])

actor input = [z_rl, proprio, ã_train]
BC target   = ã_train
critic data = [z_rl, proprio, actions]
```

公式覆盖完整 chunk。RTC 的 `committed_len` 只把 Q 输入拼成
`[executed committed zone | actor execution zone]`，不改变 Actor 条件输入或 BC target。
`next_obs.ref_chunk` 是 next state 的原始 VLA reference，bootstrap 不使用当前 transition 的人工 mask。

主要字段：

| 字段 | 含义 |
|---|---|
| `curr_obs` / `next_obs` | `z_rl`、raw `state`、normalized `proprio`、raw VLA `ref_chunk` |
| `actions` / `chunk_rewards` | normalized 实际执行 chunk / 逐步 reward |
| `intervention_mask` / `intervene_flags` | 逐步人工 mask / 其 `any()` 派生值 |
| `action_source` / `source` | 逐步 VLA/RL/HUMAN；chunk 级 VLA/RL/HUMAN/MIXED |
| `episode_id` / `round_id` / `rollout_unit_id` | 关键阶段尝试 / 操作轮次 / 训练预算单元 |
| `timestamp` / `is_critical` / `actor_enabled` | 日志对齐与采集状态 |
| `terminated` / `truncated` / `dones` | 终止、截断与 bootstrap 信息 |
| `valid_action_mask` / `executed_length` | 固定长度完整性校验 |
| `end_reason` / `window_outcome` | 边界原因与成功/失败标签 |
| `next_committed` | 仅 RTC；bootstrap state 已在途的 committed plan |

实际下发的 absolute `executed_actions` 不进 replay，只留在 transition dump 供物理量审计。字段集合变化
对应 `transition_schema_version = 4`；schema 1–3 不允许恢复，必须使用新 `exp_name`。

## Rollout warmup（`rlt_schedule.warmup_min_units`）

### 定义与语义

`RLTScheduleConfig`（`src/tacxense/rlt/config.py:261`）是 phase two（online RL）的采集/更新节奏配置，`warmup_min_units` 是其中一个字段，默认值 `2`：

```python
warmup_min_units: int = 2
chunks_per_rollout_unit: int = 30
updates_per_unit: int = 8
max_updates_per_train_step: int = 0
```

语义：committed chunk 按 `chunks_per_rollout_unit` 累积成 rollout unit，只有完整 unit 才进入 replay buffer。每个 flush 的 unit 从第 `warmup_min_units` 个开始才贡献 critic 更新预算，前 `warmup_min_units - 1` 个 unit 不产生任何更新预算：

```text
earned = updates_per_unit * max(0, units_committed - warmup_min_units + 1)
```

它只管训练预算。2026-09-21 起同一个 warmup 判据也决定 actor 是否执行：关键阶段内 replay 达到 `warm_up`
就由 actor 驾驶，关窗即退回 VLA，没有按键也没有更新次数门槛（§ 4.48）。`TDConfig.takeover` 整体已删除。

### YAML 来源

字段来自 `config/rlt/<name>.yaml` 的 `rl.algorithm.rlt_schedule.warmup_min_units`。目前仓库内 5 个配置全部显式写 `2`（与 dataclass 默认值相同，均带相同注释，像是复制默认值而非按需覆盖）：

- `config/rlt/rlt_test.yaml:105`
- `config/rlt/rlt_fast.yaml:122`
- `config/rlt/rlt_0916.yaml:116`
- `config/rlt/rlt_rtc_test.yaml:88`
- `config/rlt/insert_ethernet_0917.yaml:127`

### 加载路径（YAML → dataclass）

`rlt/config.py` 不用第三方 YAML→dataclass 库，是自写的递归构造器：

1. CLI 传入 `--config <name>` → `rlt_config.get_config(name)` 在 `config/rlt/<name>.yaml` 找文件 → `load()`。
2. `load()` 用 `OmegaConf.load` 读原始 dict，交给 `_build_config(name, raw)`。
3. `_build_config` 按 `RLTConfig` 的字段注解逐key `_coerce`；`rl` 字段类型是 `OnlineRLConfig`，走 `_construct` 递归下去。
4. `OnlineRLConfig.algorithm: TDConfig | PPOConfig` 是多态字段（Union of 2+ dataclass），走 `_build_polymorphic`，按 YAML 里的 `type: TD` key 分派到 `TDConfig`。
5. `TDConfig.rlt_schedule: RLTScheduleConfig` 是单一 dataclass 字段（非多态），`_coerce` 直接 `_construct(RLTScheduleConfig, {...})`，`warmup_min_units` 在此被赋值。
6. 任何未知 key 在 `_construct`/`_build_config` 里直接抛 `ValueError`（"a typo fails the parse"），不会静默吞掉写错的字段名。

最终形状：`RLTConfig.rl.algorithm.rlt_schedule.warmup_min_units`（`rl.algorithm` 在运行时已确定是 `TDConfig` 实例）。

### 校验

- `RLTScheduleConfig.__post_init__`（`config.py:283`）：`warmup_min_units < 1` 直接拒绝。
- `TDConfig.__post_init__`（`config.py:453`）：`replay_window_units < rlt_schedule.warmup_min_units` 拒绝——replay 窗口必须至少能装下 warmup 需要的 unit 数，否则 warmup 永远打不到。

### 运行时传递与消费（`OnlineRunner`）

`scripts/rlt/train_rl.py` 用 `dataclasses.replace(rlt_config.get_config(args.config), exp_name=..., resume=...)` 拿到最终 `RLTConfig`，传给 `OnlineRunner(config, ...)`。`OnlineRunner.__init__`（`online_runner.py:799`）把 `self.algo = config.rl.algorithm`，此后所有消费点都经 `self.algo.rlt_schedule.warmup_min_units` 读取，不再直接碰 `config`：

- `_updates_pending()`（`online_runner.py:1929`）：按上面的 `earned` 公式算未消耗的 critic 更新预算，供状态展示和 `_updates_to_run()` 使用。
- `_updates_to_run()`（`online_runner.py:1935`）：先判断 `len(online_buffer) < warmup_min_units * chunks_per_rollout_unit` 直接返回 0（replay 还没攒够 warmup 阈值，本轮不训练），够了才应用 `_updates_pending()` 并按 `max_updates_per_train_step` 截断。此函数被 `_train_if_ready`（三处调用：`online_runner.py:1326`、`:1595`、`:1749`，对应不同的 round-end/window-end 时机）驱动实际训练循环。
- `_status()` 的 `replay_ready` 字段（`online_runner.py:2113`）：同样的阈值判断，暴露给状态上报（`env.report_status`）。
- `_train_if_ready` 在 `total <= 0` 时发 `train_skip` 事件并带上 `warmup_min_units=...`（`online_runner.py:2166`），方便从日志/诊断流里看出"这轮没训练是因为还在 warmup"。
- `_log_episode_summary`（`online_runner.py:1062`）：本 episode 没有任何更新时，日志明确写"first update needs {warmup_min_units} full units of {unit_size} chunks"。
- `load_checkpoint()`（`online_runner.py:2276`）：resume 时用 checkpoint `metadata["config"]["rl"]["algorithm"]["rlt_schedule"]` 里保存的 `warmup_min_units`（连同 `chunks_per_rollout_unit`、`updates_per_unit`）与当前 config 逐字段比对，任何一个不一致就拒绝 resume（"Resume cannot reinterpret rlt_schedule.{key}; start a new stage2 run."）——改这几个字段等于改变了已训练模型的更新预算语义，不允许在同一次 run 里静默切换。

### 未验证事项

以上结论转述自本工作区对 `methods/tacxense`（`feature/rlt-test` 分支）源码与 YAML 的阅读，本工作区未实际运行 phase two online RL，未观察过 warmup 阈值在真实 rollout 中触发/resume 拒绝的运行时行为。

## Phase two 关键阶段采集工作流

唯一规格是上游 `methods/tacxense/docs/architecture.md` § 4.49 的状态图。图的主体由用户 2026-09-18 给出，
`◆` 是 2026-09-19 问答中确认的补充。这里不另存副本，避免两份内容以后各自改动、出现分歧；要改流程，
先改那张图并经用户确认。

要点（完整内容以图为准）：

- b 进入关键阶段，从下一个 chunk 起算；Warmup / Online 不由操作员切换，replay 达到 `warm_up` 即由 actor
  执行（§ 4.48）。replay 只在轮末提交，所以切换落在轮边界。
- 按下 Pico 运动键（SDK `grip`）只是待命；手柄动到阈值、且两只手的扳机夹爪与机器人夹爪开/闭一致才接管，
  不一致只打 warning；接管后按相对运动控制。松开运动键即结束介入，丢弃剩余动作并重新推理；松开时仍在动或
  夹爪在翻转会打 warning。没有单独的进入 / 退出介入按键。
- anchor 取原 policy chunk 起点、人类介入中每 C 步、重启起点；每个 anchor 取 C 步，窗口可以重叠。
- Success / Failure 按下后，当前单元跑满才结束；最后一个窗口带 reward，`done = True`。
- 上游旧条目（§ 4.43 等）与图冲突时，以图为准。RTC 不在范围内。
