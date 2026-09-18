# TacXense Plan

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
数值待按 VLA norm stats 重新推导。工作区已改，未 commit；上游 `architecture.md` § 4.47。

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
