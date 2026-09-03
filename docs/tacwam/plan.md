# TacWAM Plan

## 完善 TacWAM 推理端口

把 TacWAM 接入现成的 BiFlexiv 双臂实时控制链路。机体侧控制代码与模型无关——它只通过 websocket
交换 `infer(obs) -> {actions}`，不感知背后是 pi0 还是 TacWAM——因此逐字迁移、不做改动；TacWAM
侧只补服务端。

**环境边界**：机体侧沿用现成的 `lerobot-xense` mamba 环境，不新建环境、不安装 tacwam；服务端用
`tacwam` mamba 环境。两者 torch 约束互斥（lerobot-xense `<2.11.0` vs tacwam `==2.11.0`），机体侧
依赖不得写入 `pyproject.toml` 的 `[project.dependencies]`，否则冲突立即复现。

**RTC 本次不可用**：RTC 不是纯客户端机制——它要求服务端在去噪循环内把动作前缀冻结为已执行的动作，
且模型需以相同语义训练过（openpi 侧的 `enable_training_time_rtc`）。TacWAM 两者都不具备，本次不
实现；服务端必须显式拒绝带 RTC 参数的请求，否则会静默返回未受前缀约束的 chunk，在 merge 点造成
动作跳变。

**单目边界**：`TacWAM.infer_action()` 目前只接受单张 `[1,3,H,W]`，没有多摄像头概念。第一版服务端
只消费 head 相机，左右腕相机不接入。多摄像头属模型侧改动且需重新训练，不在本事务内。

### Task 1: 机体侧控制代码可在 tacwam 仓库内直接启动

**Change**

- 复制 `xense-openpi/examples/bi_flexiv_rizon4_rt/`（`main.py`、`env.py`、`real_env.py`、`recipe.py`、
  `recorder.py`、`subscribe.py` 与 `recipes/`）到 `methods/tacwam/examples/`，逐字不改，内部模块一个不删
- 一并复制隐藏依赖 `examples/flexiv_recipe.py` 与 `examples/flexiv_recipe_test.py`——`recipe.py` 直接
  import 前者，漏掉会在启动时 ImportError
- 不迁移与 TacWAM 无关的部分：`bi_arx5_real/`、`droid/`、`flexiv_rizon4_rt/`、`dewu_video_switch/`、
  `simple_client/`、`convert_jax_model_to_pytorch.py` 及两个 notebook
- `examples/` 保持为仓库顶层可运行目录（`python -m examples....`），不打包进 wheel

**Verification**

1. `diff -r` 对比迁移后目录与 xense-openpi 源目录
2. `grep -rn "^from openpi\|^import openpi\|^from tacwam\|^import tacwam"` 扫描迁移后的 `examples/`

**Done**

- `diff -r` 无输出，两侧逐字一致，后续可直接 diff 同步上游修复
- grep 无命中，确认机体侧不依赖任何模型侧代码
- `methods/tacwam/pyproject.toml` 的 `[project.dependencies]` 未新增 lerobot 或其他机体侧依赖

### Task 2: TacWAM 通过 websocket 对外提供动作推理

**Change**

- 新增 `src/tacwam/serving/websocket_policy_server.py`，从 xense-openpi 同名文件迁移（仅依赖
  `xense_client` 的 `base_policy` 与 `msgpack_numpy`）
- 新增 `src/tacwam/policies/policy.py`：接 obs dict，经 `BiFlexivInputs` → `TacWAM.infer_action()` →
  `BiFlexivOutputs`，返回 `{"actions": [action_horizon, 20]}`。选 `infer_action` 而非 `infer_joint`，
  后者附带视频扩散，延迟不适用于实时控制
- 新增 `scripts/serve_policy.py`：tyro CLI，经 `tacwam.model_factory` 建模型、包 Policy、起服务
- 请求中出现 `prev_chunk_left_over` 或 `inference_delay` 时抛出说明 RTC 未支持的错误
- `xense-client` 以 editable 方式装进 `tacwam` 环境（源自 xense-openpi 的 `packages/xense-client`），
  仅作为 method 环境依赖，不写入 workspace 的 `pyproject.toml`

**Verification**

1. `ruff check` 与 `ruff format --check` 通过
2. 在无 GPU 条件下导入 `tacwam.serving` 与 `tacwam.policies.policy`，确认重量依赖是惰性的

**Done**

- `scripts/serve_policy.py --help` 打印出 checkpoint 路径与端口参数
- 带 RTC 参数的请求返回可读错误，而非静默降级成无前缀约束的推理

### Task 3: 无 GPU、无真机即可验证 websocket 契约

**Change**

- 新增回环测试：假 policy 固定返回 `[50, 20]`，启动真实 `WebsocketPolicyServer`，用真实
  `WebsocketClientPolicy` 发送一帧 BiFlexiv 观测（20 维 state + head 图像 + prompt）
- 断言 msgpack 往返后 dtype 与 shape 不变
- 断言 `ActionChunkBroker` 每拍切出一个 20 维向量，连续 50 拍只触发一次推理，第 51 拍触发新推理
- 断言服务端拒绝携带 RTC 参数的请求

**Verification**

1. 在 `tacwam` 环境运行该测试文件

**Done**

- 测试通过，全程不加载 torch、不连接机械臂、不需要 checkpoint
