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

它只管训练预算，与 actor 能否执行无关。actor 曾有按更新次数计数的接管门槛（`TDConfig.takeover.min_actor_updates`），2026-09-18 已删除，现在只由键盘 `a` 手动切换。

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

- b 进入关键阶段，从下一个 chunk 起算；Warmup / Online 由 `a` 手动切换，从下一个 chunk 起生效。
- 按下 Pico 运动键（SDK `grip`）只是待命；手柄动到阈值、且两只手的扳机夹爪与机器人夹爪开/闭一致才接管，
  不一致只打 warning；接管后按相对运动控制。松开运动键即结束介入，丢弃剩余动作并重新推理；松开时仍在动或
  夹爪在翻转会打 warning。没有单独的进入 / 退出介入按键。
- anchor 取原 policy chunk 起点、人类介入中每 C 步、重启起点；每个 anchor 取 C 步，窗口可以重叠。
- Success / Failure 按下后，当前单元跑满才结束；最后一个窗口带 reward，`done = True`。
- 上游旧条目（§ 4.43 等）与图冲突时，以图为准。RTC 不在范围内。
