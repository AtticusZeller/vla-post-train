# TacWAM 概览
## 定位

TacWAM 是面向触觉机器人操作的 world action model。当前架构从 FastWAM 的 Wan2.2 视频骨干
与 ActionDiT 动作头演化而来，并增加了面向 LeRobot 数据的配置、数据加载和统计链路；它不再
依赖早期讨论中的 Cosmos3-Edge 方案。

模型保留直接动作、联合视频—动作、IDM 条件和可选 IDM 条件等方向。与 FastWAM 相比，主要
差异不是骨干本身，而是独立演化的训练配置与数据接口。

## 推理端口

推理沿用 xense-openpi 已有的双机形态：机体侧控制进程与模型无关，只通过 websocket 交换
`infer(obs) -> {actions}`，因此同一份机体代码可指向任意策略服务。TacWAM 侧提供 `WebsocketPolicyServer`、
`scripts/serve_policy.py`（只负责"构建 policy、启动服务"）以及 `policies/policy.py` 中的
`TacWAMPolicy` 与 `create_trained_policy`。相机通道、动作布局等约定属于 policy 层，不在服务脚本内。

分层参照 openpi 但做了裁剪：`Policy` 与 `create_trained_policy` 合在一个文件，因为去掉
JAX/PyTorch 双路（`is_pytorch` 分支、`module_jit`、rng split）、checkpoint 格式探测和
`gs://` 下载之后，构建函数只剩十几行；openpi 的 `EnvMode` 与 `DEFAULT_CHECKPOINT` 表整个删除，
它们是为服务 aloha/droid/libero 多平台默认权重而存在，TacWAM 只有 BiFlexiv。`Observation`
抽象也不需要——`infer_action` 是平铺关键字参数。构建逻辑不并进 `scripts/`，是因为那是入口层，
后续评测脚本还要复用。

另一处与 openpi 的实质差异是 batch 维度：openpi 的 `Policy` 统一给输入加 `[None, ...]`、
从输出剥 `[0, ...]`，而 `infer_action` 自己接受 `[3, H, W]` 或 `[1, 3, H, W]` 且返回时已剥掉
batch，不能照搬。

policy 层的两个设计要点：动作分块的缓存只在机体侧 `ActionChunkBroker` 中进行，服务端不再放一层
队列，否则双重缓冲；prompt→embedding 做记忆化，因此模型必须在构造时即 `eval()`——文本编码器含
dropout，而 `infer_action` 内部那句 `eval()` 管不到 policy 在其之外调用的 `encode_prompt`，
否则首次编码会带着 dropout 噪声被缓存并一直复用。

服务端加载文本编码器、并跳过训练用的 `LoadCachedTextEmbedding`：训练靠预计算缓存，而服务时
prompt 由机体侧实时传入，缓存未命中会在 episode 中途抛 `FileNotFoundError`。T5 是预训练冻结的，
预计算脚本用的也是同一个加载函数，因此现算与查表结果一致，不引入训练/推理偏移。

两侧环境不可合并：机体侧需要 lerobot-xense fork（`torch<2.11.0`），TacWAM 需要
`torch==2.11.0`。仓库内 `packages/xense-client` 是上游副本，唯一的差异是 `get_logger`：上游经
`logger.py` 从 lerobot-xense 再导出，使整个包绑死在那个 fork 上，而它装不进 TacWAM 环境。该函数
已连同支撑代码迁入本地 `logger.py` 并注明出处，保留原有 spdlog 实现以维持两侧日志行为一致，因此
整包在 TacWAM 环境可完整导入。

**RTC 不可用。** RTC 并非纯客户端机制：它要求服务端在去噪循环内把动作前缀冻结为已执行的动作，
且模型需以相同语义训练过（openpi 侧的 `enable_training_time_rtc`）。TacWAM 两者都不具备。
服务端只把 `__rtc_kwargs__` 原样透传给 policy，不做处理，因此启用 RTC 会得到未受前缀约束的
动作块，在 merge 点造成跳变——机体侧不要启用 `--args.rtc-enabled`。

## 当前边界

当前固定版本具备 YAML 驱动的 typed configuration、单个 LeRobot dataset 加载和 normalization
statistics 工具，但混合数据集尚未形成已验证能力。工作区没有 TacWAM 实验配置、训练记录、
推理结果或真机证据；现有代码能力不能被表述为已经完成端到端训练验收。

推理服务已具备完整调用链并与训练契约同源，但**尚无真实权重、GPU 或真机证据**——已验证的是
websocket 传输契约、action chunk 消费、20 维动作还原、prompt 记忆化与相机几何，全部基于
fake model。

图像契约上有两条不能省的约束。其一，相机几何必须取自训练配置：`TacWAMVideoInputs` 按
`video_size` 与 `camera_layout` 把三路相机拼成一张图（默认各 224x320 横向拼成 224x960），
服务端复用同一份配置和同一个重采样函数，改配置即同步生效。早期版本曾硬编码 FastWAM
`deploy_policy.py` 的布局，那实际是其数据集 `concat_multi_camera="robotwin"` 模式——RoboTwin
benchmark 的特例，而非通用约定；FastWAM 的通用模式同样是 `horizontal`/`vertical`。

其二，`TacWAMVideoInputs` 本身不能进服务链路：它要求 5 帧窗口和动作块，而在线请求只有单帧、
没有动作。服务端从 `model_transforms.inputs` 中排除它，保留其余在线适用的部分，并自行拼出单帧。

仓库目前没有明确许可证文件，因此工作区不推断其对外分发边界。
