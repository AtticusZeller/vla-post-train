# TacXense RLT 理解笔记

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

这不是 actor-takeover gate（后者在 `TDConfig.takeover` 上，按 actor 更新次数计数，语义完全不同，见下文"易混淆点"）。

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

### 易混淆点：另一个同名字符串 "warmup_updates"

`OnlineRunner` 里还有一处把字符串字面量 `"warmup_updates"` 作为 actor-takeover 的 skip 原因（`online_runner.py:1117`）：

```python
elif self.actor_update_step < takeover.min_actor_updates:
    reason = "warmup_updates"
```

这是 `TDConfig.takeover.min_actor_updates`（`TakeoverConfig`，控制 actor 何时允许接管执行）在门控日志里用的原因码，和 `rlt_schedule.warmup_min_units`（控制 critic/actor **训练预算**何时开始累积）是两个完全独立的配置项、独立的机制，只是都叫"warmup"、字符串又长得像，读日志或搜代码时容易把两者当成同一个变量。

### 未验证事项

以上结论转述自本工作区对 `methods/tacxense`（`feature/rlt-test` 分支）源码与 YAML 的阅读，本工作区未实际运行 phase two online RL，未观察过 warmup 阈值在真实 rollout 中触发/resume 拒绝的运行时行为。
