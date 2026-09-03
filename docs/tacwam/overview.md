# TacWAM 概览
## 定位

TacWAM 是面向触觉机器人操作的 world action model。当前架构从 FastWAM 的 Wan2.2 视频骨干
与 ActionDiT 动作头演化而来，并增加了面向 LeRobot 数据的配置、数据加载和统计链路；它不再
依赖早期讨论中的 Cosmos3-Edge 方案。

模型保留直接动作、联合视频—动作、IDM 条件和可选 IDM 条件等方向。与 FastWAM 相比，主要
差异不是骨干本身，而是独立演化的训练配置与数据接口。

## 当前边界

当前固定版本具备 YAML 驱动的 typed configuration、单个 LeRobot dataset 加载和 normalization
statistics 工具，但混合数据集尚未形成已验证能力。工作区没有 TacWAM 实验配置、训练记录、
推理结果或真机证据；现有代码能力不能被表述为已经完成端到端训练验收。

仓库目前没有明确许可证文件，因此工作区不推断其对外分发边界。
