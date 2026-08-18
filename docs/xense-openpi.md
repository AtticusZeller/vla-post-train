# xense-openpi 模块

> `methods/xense-openpi/` 是 Xense 平台的 openpi fork（工作区角色 `framework`）。
> 本文件记录根仓库视角下、跨会话需要复用的结构性结论，避免重复探查代码。
> 需要改动方法内代码时，先读方法自身的 `CLAUDE.md`。

## 定位与边界

| 项 | 值 |
|---|---|
| origin（用户 fork） | `https://github.com/AtticusZeller/xense-openpi.git` |
| 工作区登记 upstream | `https://github.com/XenseRobotics-AI/xense-openpi.git`（[lab.py:62](../scripts/lab.py#L62)） |
| 分支 / 当前 pin | `main` / `045ca400` |
| 上游本体 | Physical-Intelligence/openpi |
| 许可证 | Apache-2.0 |

这个 fork 只做**模型侧**：训练配置、模型实现、norm stats、策略服务端，以及真机
推理客户端。数据采集、机器人驱动、遥操作在 [lerobot-xense](lerobot-xense.md)，
两者通过 LeRobotDataset 和一份 recipe 格式相接。

相对官方 openpi 的差异集中在四处：删掉 ALOHA / LIBERO 依赖只保留 DROID 与 Xense
平台；新增 `bi_flexiv` / `xense_flare` 两个平台 policy；新增 YAML 训练配置系统
取代集中式 `_CONFIGS`；把异步推理客户端拆成独立包 `packages/xense-client`。

**远端归属待确认：** 方法 README 的 clone 指令写的是 `Vertax42/xense-openpi`，而
工作区登记的 upstream 是 `XenseRobotics-AI/xense-openpi`。两个远端当前都可访问
（`git ls-remote` 通过）。接 upstream 前需要确认哪个是权威镜像，否则
`lab method sync` 拉到的可能不是 fork 真正的父仓库。

## 事实修正：当前 pin 没有 `third_party/` 嵌套 submodule

[docs/log.md](log.md) 2026-08-17 条目记「含 5 个 `third_party/*` 嵌套 submodule，
已递归初始化」，[docs/cognitive-debt.md](cognitive-debt.md) 的「待理解内容」也把
ARX5 / XGripper / Elite SDK 归给本仓库。**当前 pin 不是这样**：`045ca400` 的仓库根
没有 `.gitmodules`，`git submodule status` 输出为空。

这些依赖历史上存在过，被两次提交移除：`21ece9c Remove ALOHA and LIBERO
third-party dependencies` 删依赖，`6061181 Remove unused configuration and lock
files` 删 `.gitmodules`。硬件 SDK 的嵌套 submodule 现在全部在 lerobot-xense
（7 个直接 + `libpyflexiv/flexiv_rdk` 1 个嵌套）。因此那条认知债的待理解项应改指
lerobot-xense，本仓库这边没有嵌套依赖要理解。

## 环境约束

- Python ≥ 3.12；NVIDIA GPU + CUDA 12（JAX cuda12 + PyTorch cu128）；仅 Ubuntu 22.04+。
- 显存下限：推理 / LoRA 微调 24 GB（RTX 4090），全量微调 70 GB+（A100 80G / H100）。
- 多卡只支持**单机 FSDP**（`fsdp_devices`），不支持多节点。
- checkpoint 默认从 `gs://openpi-assets` 下载并缓存到 `~/.cache/openpi`，可用
  `OPENPI_DATA_HOME` 改写。正式 run 必须改到 `/mnt/data/atticux/vla-post-train/`
  下，否则大文件落在容器盘上。

**环境与 lerobot-xense 共用，不是独立闭包。** 安装顺序是先 `mamba activate
lerobot-xense`，再 `pip install -e packages/xense-client`，再 `pip install -e .`。
这与根 CLAUDE.md「方法环境保持隔离」的一般约定相反，是这两个方法特有的耦合；
将来写 `experiments/xense-openpi/runbook.md` 时必须显式写明这一点，否则会有人
按惯例去建独立环境然后装不上。

## 代码结构

- [`src/openpi/models/`](../methods/xense-openpi/src/openpi/models) —— JAX 模型：
  `pi0.py`、`pi0_fast.py`、`gemma.py`、`siglip.py`，以及本 fork 新增的
  `pi0_tactile.py` / `pi0_tactile_config.py`。
- [`src/openpi/models_pytorch/`](../methods/xense-openpi/src/openpi/models_pytorch) ——
  PyTorch 实现。`transformers==5.3.0` 起 Pi0 专有行为放在
  `transformers_compat/` 子类里，旧的 `transformers_replace/` + `cp` 流程已删除。
- [`src/openpi/policies/`](../methods/xense-openpi/src/openpi/policies) ——
  平台适配层：`bi_flexiv_policy.py`、`xense_flare_policy.py`、`droid_policy.py`、
  `aloha_policy.py` / `aloha_tactile_policy.py`（后两者是 ALOHA 清理的残留）。
- [`src/openpi/training/`](../methods/xense-openpi/src/openpi/training) ——
  `config.py`（`DataConfig` / `TrainConfig` / 遗留 `_CONFIGS`）、`yaml_loader.py`、
  `registry.py`、`data_loader.py`、`weight_loaders.py`、`optimizer.py`、`sharding.py`。
- [`src/openpi/serving/websocket_policy_server.py`](../methods/xense-openpi/src/openpi/serving/websocket_policy_server.py) ——
  策略服务端（唯一一个文件）。
- [`packages/xense-client/`](../methods/xense-openpi/packages/xense-client) ——
  独立安装的异步推理客户端包，机器人端装它、不装 openpi 本体。
- [`examples/bi_flexiv_rizon4_rt/`](../methods/xense-openpi/examples/bi_flexiv_rizon4_rt) ——
  双臂 Flexiv 真机推理客户端（`main.py` / `real_env.py` / `recipe.py` / `intervention.py`）。
- [`examples/dewu_video_switch/`](../methods/xense-openpi/examples/dewu_video_switch) ——
  得物鞋垫 demo 的检测 + 视频切换 app，跑在独立的播放笔记本上，与算法无关。
- [`configs/`](../methods/xense-openpi/configs) —— 每任务一个 YAML；只有
  `_examples/` 进 git，`configs/*.yaml` 被 gitignore（个人在跑的实验）。

## 训练配置系统（改动最大的地方）

`get_config(name)` 有三级查找，先命中先用，见
[config.py:966](../methods/xense-openpi/src/openpi/training/config.py#L966)：

1. `configs/<name>.yaml`（本机私有，gitignore）
2. `configs/_examples/<name>.yaml`（共享模板，进 git）
3. `_CONFIGS_DICT[name]`（遗留 Python 注册表，[config.py:929](../methods/xense-openpi/src/openpi/training/config.py#L929)）

YAML 里 `type:` 字段通过 [registry.py](../methods/xense-openpi/src/openpi/training/registry.py)
反查类：`MODELS` 只有 `Pi0Config` / `Pi0FASTConfig` / `Pi0TactileConfig`；
`DATA_CONFIGS` 惰性填充以打破与 `config.py` 的循环 import。带 lambda 或
`flax.nnx` freeze filter 的老配置**故意不注册**，只能留在 `_CONFIGS`。

LoRA 是唯一的特殊处理：YAML 里把 `paligemma_variant` / `action_expert_variant`
写成含 `lora` 的值，loader 会自己从 `Pi0Config.get_freeze_filter()` 推出 freeze
filter（[yaml_loader.py:108](../methods/xense-openpi/src/openpi/training/yaml_loader.py#L108)），
不需要也无法在 YAML 里手写 flax filter tree。

数据侧的 factory 是 Xense 专有的两个：
[`LeRobotXenseFlareDataConfig`](../methods/xense-openpi/src/openpi/training/config.py#L390)（单臂 10D）
和 [`LeRobotBiFlexivDataConfig`](../methods/xense-openpi/src/openpi/training/config.py#L443)（双臂 20D）。

## 数据接口：20D 状态与 6D 旋转

双臂 Flexiv 的状态和动作都是 20 维，定义在
[bi_flexiv_policy.py:13](../methods/xense-openpi/src/openpi/policies/bi_flexiv_policy.py#L13)：

```
left_tcp{x,y,z,r1..r6} (9D) + left_gripper.pos (1D)
right_tcp{x,y,z,r1..r6} (9D) + right_gripper.pos (1D)
```

`r1..r6` 是旋转矩阵的前两列（6D 旋转表示），连续、无欧拉角 ±180° 跳变、无四元数
双覆盖问题，因此 policy 层**不做任何编解码**，dataset 维度直通模型维度。单臂
`xense_flare` 是同一套表示的 10D 版本。

相机侧 `bi_flexiv` 只认三路：`head`、`left_wrist`、`right_wrist`，分别映射到模型的
`base_0_rgb` / `left_wrist_0_rgb` / `right_wrist_0_rgb`；缺路用黑图补齐并把
`image_mask` 置 False，多出来的相机名直接抛错。**触觉图不在这条链路里**——
`bi_flexiv` 的正式训练管线目前是纯视觉 + 本体感的。

## Pi0Tactile：触觉分支目前是未接线的原型

[`pi0_tactile.py`](../methods/xense-openpi/src/openpi/models/pi0_tactile.py) 的设计
意图是：3 路视觉相机走预训练 SigLIP，2 路触觉（`left_tactile_0_rgb`、
`right_tactile_0_rgb`）走另建的 SigLIP `So400m/14`（`pool_type="none"`，从头训），
两支 token 拼接后再进 LLM；对应 `ModelType.PI0_TACTILE` / `PI05_TACTILE`。

但按现在的代码，它跑不起来，用之前必须先修：

- 类声明是 [`class Pi0Tactile(nnx.Module)`](../methods/xense-openpi/src/openpi/models/pi0_tactile.py#L25)，
  却在 `__init__` 里调 `super().__init__(config, rngs)` —— 父类是 `nnx.Module`，
  不接这两个参数。
- `embed_prefix` 直接用 `self.PaliGemma.img` 和 `self.PaliGemma.llm`，但 `PaliGemma`
  是 `Pi0` 的属性，这个类既不继承 `Pi0` 也没自己建它。
- 全文件仅 115 行，只实现了 `__init__` 和 `embed_prefix`，没有 `compute_loss` /
  `sample_actions`。
- 仓库里没有任何 config（YAML 或 `_CONFIGS`）引用 `Pi0TactileConfig`，也没有
  `pi0_tactile` 的测试。

结论：**「xense-openpi 已支持触觉输入」这个说法目前不成立**，它只有一个骨架。
真要做触觉 VLA，这里是从零补齐，不是调参。

## 部署链路

服务端 / 客户端分离，两端跑在不同机器上：

```bash
# GPU 机
python scripts/serve_policy.py policy:checkpoint \
    --policy.config=<config_name> --policy.dir=<checkpoint_dir>

# 机器人机（lerobot-xense 环境）
python -m examples.bi_flexiv_rizon4_rt.main \
    --args.robot-recipe forward-05 --args.host 10.142.1.1 --args.port 8000
```

三个必须知道的约束，见
[examples/bi_flexiv_rizon4_rt/README.md](../methods/xense-openpi/examples/bi_flexiv_rizon4_rt/README.md)：

- **双物理网卡是硬性要求**：机械臂 FastDDS 是 1 kHz 时延敏感链路，与推理大包共用
  网卡会 stall。文档里的分工是板载网口走机械臂，USB-C 网卡（`10.142.1.2/24`）
  直连策略服务器（`10.142.1.1/24`）。
- `--args.robot-recipe` 必填，指向本仓库 `examples/bi_flexiv_rizon4_rt/recipes/`
  下的 bench 名，也接受路径 —— 可以直接指 lerobot-xense 那边的 recipe 文件。它
  取代了原来的 `--bi_mount_type`（上游 `3b964bc6` 删掉了 lerobot 里的 `stations/` 表）。
- **优先级与 lerobot 那边相反**：bench 硬件来自 recipe，运行调参**完全归 CLI**，
  每个调参 flag 都有默认值并且总是覆盖 recipe 里的同名键（loader 会打日志）。

`xense-client` 的分层（README 已是中文，细节见
[packages/xense-client/README.md](../methods/xense-openpi/packages/xense-client/README.md)）：
`Runtime` → `PolicyAgent` → `RTCActionChunkBroker` → `WebsocketClientPolicy`。
关键设计是 RTC broker 用后台线程 + 动作队列做异步推理，队列剩余长度低于
`action_queue_size_to_get_new_actions`（默认 20）就发起下一次远端推理，控制环路
永远不等推理；序列化用 msgpack + numpy 零拷贝而非 pickle。

## 当前接入状态与缺口

已完成：fork + submodule 接入、`lab` 注册、README 角色表、模块索引。

未完成，需要时补：

- 没有 `methods/xense-openpi/AGENTS.md`。工作区规则要求改方法前读它，现在只有
  一份从上游继承的 `CLAUDE.md`（讲的是官方 openpi，不含 Xense fork 的约定）。
- 没有 `experiments/xense-openpi/`，因此没有 runbook、没有配置、没有 run 证据。
- [cmd.md](../cmd.md) 的接入验证块仍是 Pending。
- 认知债 2026-08-17 条目 Open，且其「待理解内容」需按本文「事实修正」一节改写。
