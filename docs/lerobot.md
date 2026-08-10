# LeRobot 模块

> `methods/lerobot/` 是 LeRobot framework 的固定 submodule；本文件记录根仓库
> 视角下、跨会话需要复用的代码结构结论，避免重复探查。

## Base + Sync rollout：chunk 消费到重推理的触发方式

`--strategy.type=base --inference.type=sync`（pi05 默认 base rollout）下，是
**当前 chunk 的 `n_action_steps` 步全部执行完（本地动作队列清空）才会重新调用
模型推理**，没有"按百分比提前丢弃剩余动作、提前重新推理"的选项。

触发逻辑是纯计数，见
[`PI05Policy.select_action`](../methods/lerobot/src/lerobot/policies/pi05/modeling_pi05.py#L1021)：

```python
if len(self._action_queue) == 0:
    actions = self.predict_action_chunk(batch)[:, : self.config.n_action_steps]
    self._action_queue.extend(actions.transpose(0, 1))
return self._action_queue.popleft()
```

队列非空时直接 `popleft()`，不看执行进度。`n_action_steps`
（[配置](../methods/lerobot/src/lerobot/policies/pi05/configuration_pi05.py)默认
50，等于 `chunk_size`）是**静态步数**，不是运行时百分比阈值；调小它只会让模型
每次多算一些被切片丢弃的动作，不会让 sync 引擎变成"边执行边监听、按比例提前
重规划"。

真正支持"执行到一半用新观测提前重新推理、拼接新旧 chunk"的是
[`RTCInferenceEngine`](../methods/lerobot/src/lerobot/rollout/inference/rtc.py)
（`--inference.type=rtc`，`execution_horizon` 概念，后台线程持续推理），这是
独立的异步推理后端；
[`SyncInferenceEngine`](../methods/lerobot/src/lerobot/rollout/inference/sync.py)
本身没有对应接口。

结论：想要"消费到某比例就提前重规划"必须切到 RTC，sync 路径下是纯开环、整
chunk 执行完再重推理。

## Rollout 数据管道结构简记

共用基础设施（与具体 policy 无关，所有 policy 走同一套骨架）：

- [`BaseStrategy.run()`](../methods/lerobot/src/lerobot/rollout/strategies/base.py) ——
  控制循环骨架：取观测 → 组帧 → 拿动作 → 插值 → 下发
- [`send_next_action()`](../methods/lerobot/src/lerobot/rollout/strategies/core.py) ——
  组帧、调用推理引擎、动作重排、发给机器人
- [`InferenceEngine`](../methods/lerobot/src/lerobot/rollout/inference/base.py) ABC —
  `start`/`stop`/`reset`/`get_action`/`notify_observation` 接口
  - [`SyncInferenceEngine`](../methods/lerobot/src/lerobot/rollout/inference/sync.py) ——
    每 tick 内联跑一次 pre → policy → post
  - [`RTCInferenceEngine`](../methods/lerobot/src/lerobot/rollout/inference/rtc.py) ——
    后台线程异步跑，支持 `execution_horizon` 提前重规划
- [`prepare_observation_for_inference` / `make_robot_action`](../methods/lerobot/src/lerobot/policies/utils.py)、
  [`build_dataset_frame`](../methods/lerobot/src/lerobot/utils/feature_utils.py) ——
  通用张量搬运 / 组帧 / 重排
- `ActionInterpolator` —— 默认 `multiplier=1`，直通不插值

模型专属（每个 policy 自己定义，唯一随模型变化的部分）：

- [`make_pi05_pre_post_processors()`](../methods/lerobot/src/lerobot/policies/pi05/processor_pi05.py) ——
  pi05 特有 preprocessor/postprocessor 步骤（状态离散化拼 prompt、tokenize 等）
- [`PI05Policy.select_action` / `predict_action_chunk`](../methods/lerobot/src/lerobot/policies/pi05/modeling_pi05.py) ——
  chunk 采样 + 本地队列消费逻辑

即：Strategy、InferenceEngine、组帧/重排等基础设施是所有 policy 共用的骨架；
真正随模型变化的只有 `make_pre_post_processors` 产出的 processor pipeline 和
`select_action`/`predict_action_chunk` 这一层。

**Base strategy 不落盘**：
[`build_rollout_context`](../methods/lerobot/src/lerobot/rollout/context.py)
第 5 步显式判断 `if cfg.dataset is not None and not isinstance(cfg.strategy, BaseStrategyConfig)`，
即 BaseStrategy 天生跳过 `LeRobotDataset` 写入，这是它与 sentry/highlight/
dagger/episodic 几种策略的本质区别。

## `async_inference/`：动作队列聚合逻辑

`methods/lerobot/src/lerobot/async_inference/`（`RobotClient` + `PolicyServer`，
独立的 gRPC CLI）是与上面 `rollout/` 平行的另一套异步推理实现，不要与
`rollout/inference/rtc.py` 的 `RTCInferenceEngine` 混淆——两者都做"提前请求下一个
chunk"，但是不同代码路径。

**触发时机**：本地动作队列剩余占比 `≤ chunk_size_threshold`（默认 0.5）时就提前
向 server 发观测请求新 chunk，而不是等队列清空，见
[`RobotClient._ready_to_send_observation`](../methods/lerobot/src/lerobot/async_inference/robot_client.py#L403-L406)。

因为请求是提前发的、网络+推理有延迟，新 chunk 到达时和本地仍在消费的旧 chunk
在时间轴上会有重叠，需要按 `timestep` 对齐合并：

```
timestep:        0    1    2    3    4    5    6    7    8    9   10   11   12   13   14

已执行(past):     ██   ██   ██   ██   ██                                    latest_action = 4

旧队列(old,        ─    ─    ─    ─    ─    ─────┬─────┬─────┬─────┬─────┬─────┐
仍在 self.action_                                 5     6     7     8     9    10
queue 里的部分)

新 chunk(new,       ─    ─    ─   ─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
server 迟到返回)                        3     4     5     6     7     8     9    10    11   12   13   14
                                        ↑                 ↑                             ↑
                                    已过期,丢弃        重叠区,加权混合                纯未来,直接采纳
                                (≤ latest_action=4)  (aggregate_fn(old, new))     (old 里没有对应项)
```

三种情形对应
[`RobotClient._aggregate_action_queues`](../methods/lerobot/src/lerobot/async_inference/robot_client.py#L224-L263)
里的三个分支：

```python
for new_action in incoming_actions:
    if new_action.get_timestep() <= self.latest_action:
        continue                                    # 已执行 -> 丢弃
    elif new_action.get_timestep() not in current_action_queue:
        future_action_queue.put(new_action)          # 纯未来 -> 直接采纳
    else:
        blended = aggregate_fn(
            current_action_queue[new_action.get_timestep()],
            new_action.get_action(),
        )
        future_action_queue.put(TimedAction(..., action=blended))  # 重叠 -> 加权混合
```

- `self.latest_action`：本地**最后一次真正下发给机器人的动作对应的 timestep**，
  在
  [`RobotClient.control_loop_action`](../methods/lerobot/src/lerobot/async_inference/robot_client.py#L370-L385)
  每弹出并执行一个动作后更新；初始为 `-1`。用它来判断新 chunk 里哪些 timestep
  已经是"过去"，避免用新数据覆盖已经发生的事。
- 重叠区间是**逐 timestep 独立混合**，权重是常数，不是"找一个切换点做渐变/拼接"
  ——重叠区内每一个 timestep 都用同一个固定公式。
- 混合的对象是 `torch.Tensor`（`Action = torch.Tensor`，见
  [`helpers.py`](../methods/lerobot/src/lerobot/async_inference/helpers.py#L41)），
  `0.3*old + 0.7*new` 是逐元素 tensor 算术，不是 list 操作。
- `future_action_queue` 构建完直接整体替换 `self.action_queue`
  （`robot_client.py:262-263`），旧队列里新 chunk 没提到的尾部 timestep 会被丢弃，
  没有"新旧都没提到就保留旧值"的兜底。

**默认聚合权重来自
[`AGGREGATE_FUNCTIONS`](../methods/lerobot/src/lerobot/async_inference/configs.py#L29-L34)**，
是写死的 4 项字典，只能通过 `--aggregate_fn_name` 从中选一个，没有注册扩展点：

```python
AGGREGATE_FUNCTIONS = {
    "weighted_average": lambda old, new: 0.3 * old + 0.7 * new,  # 默认
    "latest_only": lambda old, new: new,
    "average": lambda old, new: 0.5 * old + 0.5 * new,
    "conservative": lambda old, new: 0.7 * old + 0.3 * new,
}
```

注意默认是 `weighted_average`（0.3/0.7），不是 0.5/0.5 —— 0.5 默认值其实是
`chunk_size_threshold`，两者是完全独立的配置项，容易记混。
