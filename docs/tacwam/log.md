# TacWAM Log

已验收的事务按 `plan.md` 的原格式整体归档于此，保留 Change / Verification / Done 三段，
以便在不翻分支的情况下复原当时的判断依据。

## 2026-09-04 · 上游合并推理端并修正两处训练/推理不一致

- **背景与目的：** `feat/inference-serving` 经 PR #2 合并为 `7c314ce`。协作者随后对照缓存数据集、
  模型 forward 与 `scripts/serve_policy.py` 复查，发现两处本工作区未能发现的静默偏差
  （`ea4fbfe`，作者 博 胡）。本工作区据此更新 pin 与文档。
- **两处不一致：** 其一，训练把 50 步动作块补零到 52 token，ActionDiT 始终在 52 个位置上注意，
  而服务端只采样 50；现要求 `model.action_horizon` 等于 `(video_num_frames - 1) *
  video_frame_stride`，loader 直接读 52 步，`TacWAMVideoInputs` 不再补零。其二，训练从 480x640
  原图直接缩放到 224x320，而机体端默认先 letterbox 成 224x224、服务端再缩一次，实测像素均值
  绝对差约 40、95% 像素改变；现由 data config 记录 `camera_image_size`，训练与服务两侧都校验
  帧尺寸后再用共享的 `resize_uint8_image` 缩放。
- **对本工作区的影响：** 机体侧启动命令必须追加
  `--args.render-height 480 --args.render-width 640 --args.action-horizon 52`——`examples/` 是上游
  原样拷贝、不改默认值，因此每次启动都要带。已同步进 `cmd.md`。
- **顺带关闭的待办：** `transforms._resize_uint8_image` 已被提升为公开 `resize_uint8_image`，
  正是此前记录的开放项；`plan.md` 中该条已移除。
- **教训：** 这两处都在全绿测试下存在，印证了当时写明的边界——对假 model 的测试证明接线正确，
  不证明数值行为正确。真实数据与真实 forward 的对照是不可替代的一步。

## 2026-09-04 · 与上游对齐推理端的图像与 transform 契约

推理端已接入并有测试覆盖（见下一条），但当时的基线落后 `origin/main` 两个提交。上游
`46f1b70 Add video-window training inputs` 改变了训练侧的图像契约，使现有服务端无法驱动真实
checkpoint。本事务把服务端对齐到该契约。

**两处不一致（外部 review 指出，已逐条核实）**

- **布局**：服务端的 `build_input_image` 是从 FastWAM `deploy_policy.py` 移植的，而那份对应
  FastWAM 数据集的 `concat_multi_camera="robotwin"` 模式——RoboTwin benchmark 的特例（上 256x320
  加下方两路 128x160，合成 384x320）。FastWAM 的通用模式是 `horizontal`/`vertical`，上游
  `TacWAMVideoInputs` 走的正是通用路径：三路相机各 `video_size: [224, 320]`，`camera_layout:
  horizontal`，拼成 224x960。布局是 per-config 的，因此必须从 data config 派生而非硬编码。
  值域两侧一致（`[-1, 1]`），错的只是尺寸与拼接方向。
- **transform 列表**：上游把 `TacWAMVideoInputs` 加进了 `model_transforms.inputs`。它要求
  `num_frames=5` 帧图像和 `actions`，而在线请求只有单帧观测、没有动作。同步上游后，服务端整体
  复用该列表会让每次 `infer()` 在模型推理前直接报错。

**Change**

- [x] 把 `methods/tacwam` 同步到 `origin/main`（当时落后 `46f1b70`、`f100900` 两个提交），
      并复核迁移目录与 xense-openpi 的 `diff -r` 仍只有既定差异
- [x] `build_input_image` 改为从 data config 读取 `video_size` 与 `camera_layout` 拼接单帧，
      删除硬编码的 `_HEAD_SIZE_WH` / `_WRIST_SIZE_WH` / `_MOSAIC_SIZE_HW` 及其失效注释
- [x] 服务端不再整体复用 `data_config.model_transforms.inputs`，只取在线适用的部分
      （`InjectDefaultPrompt` 等），排除需要多帧与 actions 的 `TacWAMVideoInputs`
- [x] 复核上游对 `BiFlexivInputs` 的改动（新增 pad 键、`[T,C,H,W]` 分支）与服务端契约仍兼容

**Verification**

1. [x] 同步后运行全量 `pytest`，确认既有用例不回归
2. [x] 新增测试：给定一份 `video_size`/`camera_layout` 与默认值不同的 data config，
      断言 `build_input_image` 的输出尺寸随之改变——锁住"布局来自配置"而非硬编码
3. [x] 断言服务端构造出的输入 transform 链中不含 `TacWAMVideoInputs`

**Done**

- [x] `build_input_image` 在默认配置下输出 `[1, 3, 224, 960]`，且值域仍为 `[-1, 1]`
- [x] 改配置里的 `camera_layout` 或 `video_size` 后，输出尺寸随之变化，代码无需改动
      （horizontal 224x960 / vertical 672x320 / video_size 128x160 时 128x480 三组）
- [x] 用 fake model 走完整 `create_trained_policy` → `infer` 路径不再触发多帧/actions 相关报错

**补充记录**：同步后全量 88 passed（含上游新增用例）。ty 另外抓到一处 ruff 无法发现的问题——
`video_size` / `camera_layout` 定义在具体 data config 而非 `DataConfigFactory` 基类上，直接取
属性对其他 data config 会裸 `AttributeError`，已改为经 `_serving_geometry` 显式校验并给出可读报错。

## 2026-09-04 · 完善 TacWAM 推理端口

把 TacWAM 接入现成的 BiFlexiv 双臂实时控制链路。机体侧控制代码与模型无关——它只通过 websocket
交换 `infer(obs) -> {actions}`，不感知背后是 pi0 还是 TacWAM——因此逐字迁移、不做改动；TacWAM
侧只补"加载 policy + 启动服务"这一层。

**环境边界**：机体侧沿用现成的 `lerobot-xense` mamba 环境，不新建环境、不安装 tacwam；服务端用
`tacwam` mamba 环境。两者 torch 约束互斥（lerobot-xense `<2.11.0` vs tacwam `==2.11.0`），机体侧
依赖不得写入 `pyproject.toml` 的 `[project.dependencies]`，否则冲突立即复现。

**推进顺序**：Task 1-3 先交付与 policy 实现无关的部分——服务端骨架、CLI、以及一个待接入的 policy
构建调用点，使传输契约可以独立验证；Task 4 同步文档。Task 5 再补 policy 本身，相机通道数等属于
policy 层的约定也在那里一并定下。

**RTC 本次不可用**：RTC 不是纯客户端机制——它要求服务端在去噪循环内把动作前缀冻结为已执行的动作，
且模型需以相同语义训练过（openpi 侧的 `enable_training_time_rtc`）。TacWAM 两者都不具备。服务端
只透传 `__rtc_kwargs__`、不做处理，因此本次无需额外实现；机体侧不要启用 `--args.rtc-enabled`。

### Task 1: 机体侧控制代码可在 tacwam 仓库内直接启动

**Change**

- [x] 复制 `xense-openpi/examples/bi_flexiv_rizon4_rt/`（`main.py`、`env.py`、`real_env.py`、
      `recipe.py`、`recorder.py`、`subscribe.py` 与 `recipes/`）到 `methods/tacwam/examples/`，
      逐字不改，内部模块一个不删
- [x] 一并复制单臂版 `xense-openpi/examples/flexiv_rizon4_rt/`（含 `recipes/default.yaml`）
- [x] 一并复制隐藏依赖 `examples/flexiv_recipe.py` 与 `examples/flexiv_recipe_test.py`——双臂与单臂的
      `recipe.py` 都直接 import 前者，漏掉会在启动时 ImportError
- [x] 不迁移与 TacWAM 无关的部分：`bi_arx5_real/`、`droid/`、`dewu_video_switch/`、`simple_client/`、
      `convert_jax_model_to_pytorch.py` 及两个 notebook
- [x] `examples/` 保持为仓库顶层可运行目录（`python -m examples....`），不打包进 wheel

**Verification**

1. [x] `diff -r` 对比迁移后目录与 xense-openpi 源目录
2. [x] `grep -rn "^from openpi\|^import openpi\|^from tacwam\|^import tacwam"` 扫描迁移后的 `examples/`

**Done**

- [x] `diff -r` 无输出，两侧逐字一致，后续可直接 diff 同步上游修复
- [x] grep 无命中，确认机体侧不依赖任何模型侧代码
- [x] `methods/tacwam/pyproject.toml` 的 `[project.dependencies]` 未新增 lerobot 或其他机体侧依赖

### Task 2: TacWAM 可以加载 policy 并对外提供 websocket 服务

**Change**

- [x] 新增 `src/tacwam/serving/websocket_policy_server.py`，从 xense-openpi 同名文件逐字迁移。该文件
      与 policy 实现无关：只要求传入对象满足 `BasePolicy`，仅依赖 `xense_client` 的 `base_policy`
      与 `msgpack_numpy`
- [x] 完整复制 `xense-openpi/packages/xense-client/` 到 `methods/tacwam/packages/xense-client/`。它是
      workspace 内的本地包、不在 PyPI 上；机体侧与服务端共用同一套 msgpack 序列化，除下面一处外
      保持与上游逐字一致，否则协议漂移会表现为难以定位的反序列化错误
- [x] 消除该包对 lerobot 的未声明依赖：其中三个模块从 lerobot-xense 导入 `get_logger`，而该函数只
      存在于那个 fork，在 TacWAM 环境里必然 ImportError。把 `get_logger` 及其支撑代码完整迁入
      `xense_client/logger.py` 并注明出处，其余模块改为从本地导入。保留原有的 spdlog 实现而不改写成
      stdlib logging，以维持两侧日志行为一致；`spdlog` 声明进该包自己的 `pyproject.toml`，因为它现在
      确实是本包的依赖——上游把 lerobot 当依赖用却不声明，正是这次要修掉的问题。这是本包相对上游
      唯一允许的差异
- [x] 新增 `scripts/serve_policy.py`：tyro CLI，只负责"加载 policy + 启动服务"两件事，对齐
      xense-openpi 的 `scripts/serve_policy.py` 职责
- [x] policy 构建收敛为脚本内的单一函数调用点，并在该处写 TODO 注明待落地的内容：预期签名、
      输入输出契约、以及哪些约定（相机通道、动作空间、RTC 支持与否）属于 policy 层
- [x] 在 `docs/tacwam/overview.md` 记录 RTC 不可用的原因与边界；新增 `docs/tacwam/cmd.md`，写入环境
      准备与服务启动命令，并标注机体侧不要启用 `--args.rtc-enabled`
- [x] 在 `conda_enviroment.yaml` 的 pip 段加 `-e packages/xense-client`，与现有 `-e .[test]` 并排，使
      `mamba env create` 一次装完、无需额外说明

**Verification**

1. [x] 在 `tacwam` 环境中导入 `xense_client` 的全部模块，确认无 lerobot ImportError
2. [x] `diff -r` 对比复制后的 `packages/xense-client/` 与 xense-openpi 源目录

不把 `ruff check` 作为验收项：TacWAM 自身没有 ruff 配置，根仓的 ruff 配置又明确排除了
`methods/`；用根配置扫描会报出数百条既有问题，覆盖大部分现有文件。补一份 method 级 lint 基线
是独立事务。

**Done**

- [x] `scripts/serve_policy.py --help` 打印出 checkpoint 与端口参数
- [x] 传入任意满足 `BasePolicy` 的对象即可起服务，脚本内不含 policy 实现细节
- [x] 待接入的 policy 构建点集中在一处并带 TODO，接口确定后只需改动该处
- [x] `packages/xense-client/` 的 `diff -r` 只输出 logger 迁移涉及的文件，其余逐字一致
- [x] 卸载 spdlog 后单独 `pip install -e packages/xense-client` 能把它重新拉回，证明依赖声明有效
- [x] `docs/tacwam/cmd.md` 含可复制的环境创建与服务启动命令，并写明 RTC 不可用；其中不含
      xense-client 的单独安装步骤

### Task 3: 无 GPU、无真机即可验证 websocket 契约

**Change**

- [x] 新增回环测试：假 policy 固定返回 `[50, 20]`，启动真实 `WebsocketPolicyServer`，用真实
      `WebsocketClientPolicy` 发送一帧 BiFlexiv 观测（20 维 state + 图像 + prompt）
- [x] 断言 msgpack 往返后 dtype 与 shape 不变
- [x] 断言 `ActionChunkBroker` 每拍切出一个 20 维向量，连续 50 拍只触发一次推理，第 51 拍触发新推理

**Verification**

1. [x] 先 `mamba env update -f conda_enviroment.yaml`，再在 `tacwam` 开发环境中运行该测试文件

**Done**

- [x] 测试在 `tacwam` 环境通过（当时全量 48 passed），全程不加载 torch、不连接机械臂、不需要
      checkpoint、不依赖尚未落地的 policy

### Task 4: README 覆盖推理链路

`README.md` 当时只讲到训练启动脚本，读者无法从中知道推理怎么跑。仓库自身的 README 是上游协作者的
入口，不能只靠工作区 `docs/` 承载这部分信息。

**Change**

- [x] 在 `README.md` 的环境安装一节补充：`conda_enviroment.yaml` 现在同时安装 `packages/xense-client`；
      说明机体侧不用这个环境，而是沿用 lerobot-xense 环境
- [x] 新增推理章节，覆盖两侧：GPU 机用 `scripts/serve_policy.py` 起服务，机体机用
      `python -m examples.bi_flexiv_rizon4_rt.main` 连上去，并给出 `--args.dry-run` 的干跑用法
- [x] 说明 `examples/` 与 `packages/xense-client/` 的来源是 xense-openpi，以及 `xense-client` 相对
      上游的唯一差异，便于后续同步上游修复
- [x] 标注 RTC 不可用及原因，与 `docs/tacwam/overview.md` 保持一致
- [x] 标注 policy 构建当时尚未接入

**Verification**

1. [x] 按 README 的推理章节逐条核对命令与仓库现状（脚本路径、参数名、环境名）一致
2. [x] 确认 README 未与 `docs/tacwam/cmd.md`、`overview.md` 产生互相矛盾的说法

**Done**

- [x] 读者只看 `README.md` 就能装出环境、起推理服务、并在机体侧连上
- [x] README 中每条命令的脚本路径与参数都能在仓库里找到对应实现

**核对时发现的错误**：RTC 的 CLI flag 实为 `--args.rtc-enabled`（tyro 把下划线转为连字符），
四处文档原先都写成 `--args.rtc_enabled`，已全部更正。

### Task 5: 实现 policy 并接上 `serve_policy.py` 的待接入点

**参考关系与收敛结论**

逐层对照 openpi 的四层职责，TacWAM 只保留其中两层：

- `openpi/policies/policy.py` 的 `Policy` —— 把 `xense_client` 的 `BasePolicy` 实例化，持有已建好的
  model，串起「输入 transform → 采样 → 输出 transform」。**保留**，但删掉 JAX/PyTorch 双路
  （`is_pytorch` 分支、`module_jit`、rng split）和 `Observation.from_dict` 抽象——TacWAM 纯 PyTorch，
  且 `infer_action` 是平铺关键字参数，没有 Observation 概念。
- `openpi/policies/bi_flexiv_policy.py` 的输入输出适配 —— **已存在**同名文件，复用，不重写。
- `openpi/policies/policy_config.py` 的 `create_trained_policy` —— 加载权重与统计量、组装 transform
  链、返回 `Policy`。**保留函数但与 `Policy` 同文件**：删掉 checkpoint 格式探测和 `gs://` 下载后
  它只剩十几行，不值得单独成文件。
- `openpi/scripts/serve_policy.py` 的 `EnvMode` 与 `DEFAULT_CHECKPOINT` —— **删除**。openpi 要服务
  aloha/droid/libero 多平台默认权重，TacWAM 只有 BiFlexiv。

落到两个文件：新增 `src/tacwam/policies/policy.py`（`TacWAMPolicy` + `create_trained_policy`），
以及已有的 `scripts/serve_policy.py`。不并进 `scripts/` 是因为该目录是入口层，policy 构建后续会被
评测脚本复用。

**配置来源**

checkpoint 里另有 `metadata.pt` 记录训练配置，但那部分做法仍在演进，本任务不依赖它。
`serve_policy.py` 用显式的 `--config <name>` 经 `get_config()` 取 `TrainConfig`，与 openpi 的
`create_trained_policy(train_config, checkpoint_dir)` 一致。normalization statistics 优先读
`checkpoint_dir/assets/<asset_id>/norm_stats.json`——这是 openpi 刻意的选择，保证服务用的统计量就是
训练时那份——读取走已有的 `utils/normalize.py:load`，只依赖该路径约定，不解析 `metadata.pt`。

**训练配置与推理需求的冲突，及其解决**

这是本任务唯一的实质设计问题。训练配置是 `load_text_encoder: false` + `use_text_embed_cache: true`，
靠 `precompute_text_embeds.py` 预先编码数据集里的 task；而服务时 prompt 由机体侧实时传入，
`LoadCachedTextEmbedding` 查不到缓存会抛 `FileNotFoundError`，足以在 episode 中途打断控制。

解决方式是服务端加载文本编码器，由模型自己 `encode_prompt`，接受任意 prompt。需要**三处配套改动**，
缺任何一处都会失败：

1. 派生 serving 版模型配置：`dataclasses.replace(config.model, load_text_encoder=True)` 后再 `create`。
   `load_text_encoder` 是构造参数而非架构开关，只决定要不要一并加载 T5，YAML 文件不改。
2. 派生 serving 版数据配置，使 transform 链里不含 `LoadCachedTextEmbedding`。`ModelTransformFactory`
   按 `text_embed_cache_dir is not None` 决定是否插入它，因此
   `dataclasses.replace(train_config.data, use_text_embed_cache=False)` 即可，无需手工拼链。
   **只做第 1 步的话请求仍会在 transform 阶段抛 `FileNotFoundError`，模型的编码器根本没机会被
   调用**。`InjectDefaultPrompt` 保留作兜底。
3. 由 policy 自己调 `model.encode_prompt(prompt)` 并按 prompt 记忆化，再把结果作为
   `context=`/`context_mask=` 传给 `infer_action`，而不是直接传 `prompt=`。若传 `prompt=`，
   `infer_action` 每次调用都会重跑一遍 T5——prompt 在一个 episode 内通常不变，那是纯浪费，而且
   落在每次 chunk 推理的关键路径上。`encode_prompt` 返回的 `(prompt_emb, mask)` 正是 context 路径
   期望的那一对，两条路径互斥且必须二选一。

这样做不引入训练/推理偏移：T5 是预训练冻结的，训练时因 `load_text_encoder: false` 压根没进模型、
没进 optimizer；而 `precompute_text_embeds.py` 生成缓存用的是同一个 `load_wan22_text_encoder`，
model_id 与 tokenizer 都相同。服务端只是把查表换成现算，产出的 embedding 与缓存一致。
代价是 T5 常驻显存，因此该行为在 `serve_policy.py` 上留一个默认开启的开关。

**图像适配契约**

`infer_action` 与训练的 `build_inputs` 是两条独立路径，推理不需要训练阶段的 `sample["video"]`。
但 `_encode_input_image_latents_tensor` 把 `input_image` 原样交给 VAE，不做任何归一化，因此值域与
布局仍需明确，而当时仓库里没有一处写明。依据 FastWAM 的 `deploy_policy.py`——它跑的是同一条
`infer_action` 路径，且 TacWAM 的模型代码本就是 FastWAM 改名而来——取值域 `image * (2.0/255.0) - 1.0`
即 `[-1, 1]`，并沿用其三路相机空间拼接的做法。

（后续证明这一步选错了分支：该 helper 对应 FastWAM 数据集的 `concat_multi_camera="robotwin"` 模式，
是 RoboTwin benchmark 的特例；值域正确，布局不正确。修正见上一条事务。）

**Change**

- [x] 在 `src/tacwam/transforms.py` 新增 `Unnormalize`。逻辑与 openpi
      `src/openpi/transforms.py` 的同名类一致，直接搬运，只沿用 TacWAM 已简化的按 key 遍历口径，
      不引入 `apply_tree` / `pad_to_dim`；反向公式复用与 `Normalize` 完全相同的 epsilon，否则往返
      留残差。不改动 `Normalize` 任何一行
- [x] 新增 `src/tacwam/policies/policy.py`，其中 `TacWAMPolicy` 实现 `BasePolicy`：`infer(obs)` 依次
      跑输入 transform、调模型、跑输出 transform，返回 `{"actions": [action_horizon, 20]}`
- [x] 调用 `TacWAM.infer_action` 而非 `infer_joint`：后者附带视频扩散，延迟不适用于实时控制
- [x] 图像适配收敛为单个函数：拼接三路相机后做 `[-1, 1]` 归一化，输出 `[1, 3, H, W]` 的 device
      tensor。函数注明布局待训练侧对齐
- [x] 自行处理 batch 维度。openpi 的 `Policy` 统一加 `[None, ...]` 再剥 `[0, ...]`，而 `infer_action`
      自己接受 `[3, H, W]` 或 `[1, 3, H, W]` 且返回时已剥掉 batch，不能照搬
- [x] `TacWAMPolicy` 不持有影响输出的状态：动作分块的缓存由机体侧 `ActionChunkBroker` 负责
      （见 `xense_client/action_chunk_broker.py`），服务端再放一层队列会造成双重缓冲。FastWAM 的
      `WorldActionRobotWinPolicy` 内有 `pending_actions` 队列，那是因为 RoboTwin 逐步调用它、
      没有 broker，不能照搬
- [x] `create_trained_policy` 构造后立即 `model.eval()`。这不是可选优化而是记忆化的前置条件：
      `WanTextEncoder` 含 `Dropout(0.1)`，而 `infer_action` 开头那句 `self.eval()` 管不到 policy
      在它之外调用的 `encode_prompt`——若未先 eval，首次编码会带着 dropout 噪声被缓存并一直复用，
      且因只算一次而不会自我暴露。openpi 的 `Policy` 同样在构造时 eval
- [x] 同文件内实现 `create_trained_policy(train_config, checkpoint_dir)`：加载权重、读取
      normalization statistics、组装输入输出 transform 链、返回 `TacWAMPolicy`
- [x] 在 `create_trained_policy` 内落实上述文本编码器三处改动。跳过 `LoadCachedTextEmbedding` 采用
      `dataclasses.replace(train_config.data, use_text_embed_cache=False)` 而非手工拼链
- [x] serving 链不含 `data_config.repack_transforms`：它把 LeRobot 数据集列名映射成 policy 格式，
      而机体侧送来的观测已经是 policy 格式，套用会找不到 `observation.state`。openpi 链里那个
      `repack_transforms` 同样是调用方参数而非 data config 里的那份
- [x] 输出链包含 `AbsoluteActions` 与 `Unnormalize`，把模型输出从 delta、归一化空间还原成机体侧
      可直接执行的绝对动作
- [x] 把 `scripts/serve_policy.py` 的 `create_policy` 改为调用 `create_trained_policy`，删除其中的
      TODO 与 `NotImplementedError`

**Verification**

1. [x] 新增 `tests/test_transforms.py` 覆盖 `Unnormalize`，在 `tacwam` 环境运行
2. [x] 用假 model 构造 `TacWAMPolicy`，直接调 `infer` 验证 transform 链与返回契约，不需要 checkpoint
3. [x] 复用现有 `tests/test_serve_websocket.py` 的回环，确认真 policy 也满足 `BasePolicy`
4. [x] 运行全量 `pytest`，确认既有用例不回归

**Done**

- [x] `Unnormalize` 测试同时有绝对值断言与往返断言：只有往返断言时，正反两侧同样写错也能互相抵消
      而通过，因此必须另有一组手算期望值锁住公式本身；往返测试先断言归一化结果确实不等于原值，
      避免两个空实现也能通过
- [x] `Unnormalize` 覆盖 z-score 与 quantile 两条分支、缺失 key、宽度不匹配、`norm_stats=None`、
      float32 dtype 保持，以及 quantile 模式缺少 q01/q99 时报错
- [x] 假 model 下 `infer(obs)` 返回 `[action_horizon, 20]`，且连续两次调用结果一致——证明 policy
      不持有影响输出的状态
- [x] 输出经过 `Unnormalize` 与 `AbsoluteActions`：给定已知统计量与已知模型输出，动作值等于手算的
      绝对值，而不是归一化空间里的数。测试走完整的 delta 链，并覆盖「`norm_stats` 含 `state` 键」
      这一隐含前提——`AbsoluteActions` 要的是物理单位的 state，靠 `Unnormalize` 顺带还原
- [x] 未预先缓存的 prompt 不再触发 `FileNotFoundError`
- [x] prompt 不变时 `encode_prompt` 只被调用一次：以计数用的假 model 连续多次 `infer`，断言编码次数
      为 1；换一个 prompt 后增加到 2
- [x] 断言 `create_trained_policy` 返回时模型已处于 eval 模式，锁住上述 dropout 前置条件
- [x] 图像适配函数的输出形状与值域 `[-1, 1]` 受测，且全黑与全白输入分别映射到 -1 与 +1——锁住
      归一化方向，避免反了也看不出来
- [x] `scripts/serve_policy.py` 中不再有 `NotImplementedError`

**补充记录**：验收时全量 69 passed。测试当场暴露一条隐含约束——serving 走的是 quantile 归一化
（`create_base_config` 内 `use_quantile_norm=True`），因此 checkpoint 携带的统计量必须含 q01/q99，
否则 `Normalize` 构造即抛 `ValueError`；`compute_norm_stats` 会写这两个字段，真实路径不受影响。
