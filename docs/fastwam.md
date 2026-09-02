# FastWAM 模块说明

## 定位

`methods/fastwam` 是 Fast-WAM 论文的官方实现，属于 world action model（WAM）方向的
method。核心问题是"WAM 在测试时是否必须先想象未来"：模型用 Wan2.2-TI2V-5B 视频骨干
配 ActionDiT 动作头，既可以先生成未来视频再推动作（IDM），也可以跳过想象直接从当前
观测出动作（first-frame，即 Fast-WAM）。基准是 LIBERO 与 RoboTwin 2.0。

接入它的用途是作为 `methods/tacwam` 的 WAM 对照实现：TacWAM 走 Cosmos3-Edge 触觉
路线，FastWAM 是同一问题域里已发表、有公开 checkpoint 和数值的参照系。

## 来源与版本

- 官方仓库（`upstream`）：`https://github.com/yuantianyuan01/FastWAM.git`
- 工作区 fork（`origin`）：`https://github.com/AtticusZeller/FastWAM.git`
- 分支：`workspace`，从 upstream `main` 的 `7faa711` 创建
- 当前 pin：`f109f8f863feb49575cbcae9e6e069d38d7c5df0`（= upstream `7faa711` + 一条本仓
  Agent 指南 commit）
- 论文：arXiv:2603.16666；项目页 `https://yuantianyuan01.github.io/FastWAM/`
- 许可证：MIT
- 嵌套 submodule：无。`third_party/RoboTwin/` 是 vendored 的 RoboTwin 评测代码副本，
  `src/fastwam/datasets/lerobot/` 与 `datasets/lerobot3/` 也是 LeRobot v2.1 / v3.0 读取
  逻辑的副本，不是 upstream `lerobot` 包。

upstream 除 `main` 外只有 `dev/fix_gpu_oom`（停在 2026-04）和 `web_pages`（项目主页），
没有可直接用的干净集成分支，因此按工作区惯例新建 `workspace`。

## 代码结构

- [src/fastwam/models/wan22/](../methods/fastwam/src/fastwam/models/wan22/) 是四个模型
  变体：`fastwam.py`（uncond，直接出动作）、`fastwam_idm.py`（先想象再出动作）、
  `fastwam_joint.py`（视频-动作联合）、`fastwam_optional_idm.py`（同一权重支持两种推理
  模式）。
- [src/fastwam/runtime.py](../methods/fastwam/src/fastwam/runtime.py) 提供
  `create_fastwam*` 工厂，`configs/model/*.yaml` 的 Hydra `_target_` 指向它们。
- [src/fastwam/trainer.py](../methods/fastwam/src/fastwam/trainer.py) 是训练循环，入口为
  `scripts/train.py` 与 `scripts/train_zero1.sh`（DeepSpeed ZeRO-1）。
- `configs/` 是 Hydra 分层：`task/` 选训练任务、`model/` 选架构、`data/` 选数据布局，
  外加 `train.yaml`、`sim_libero.yaml`、`sim_robotwin.yaml`。
- `experiments/libero/run_libero_manager.py` 与
  `experiments/robotwin/run_robotwin_manager.py` 是评测管理器。

## 运行前提（尚未在本机验证）

- 环境：Python 3.10 + `torch==2.7.1+cu128`，与本仓根环境（3.12 + uv）相互独立。
- 训练与推理都要先用 `scripts/preprocess_action_dit_backbone.py` 从 Wan22 DiT 插值出
  ActionDiT 骨干；训练前还要跑 `scripts/precompute_text_embeds.py` 生成 T5 缓存。
- 默认并行度是 LIBERO 8 卡、RoboTwin 64 卡，小机器必须显式传 `MULTIRUN.num_gpus`。
- LIBERO 评测需要官方 LIBERO 环境和 `mujoco==3.3.2`；RoboTwin 评测需要官方 RoboTwin
  安装、资产，以及 `third_party/RoboTwin/policy/fastwam_policy` 符号链接。
- 数据集与 checkpoint 在 Hugging Face（`yuanty/fastwam`、`yuanty/LIBERO-fastwam`、
  `yuanty/robotwin2.0-fastwam`），体积较大，按工作区规则落在
  `/mnt/data/atticux/vla-post-train/` 下，不写入 checkout。

## 数值对照的两个陷阱

- **sigma shift**：action scheduler shift 现在默认 `1.0`；评测早期发布的 checkpoint 必须
  设 `EVALUATION.sigma_shift=5.0` 才能复现原始数值。任何成功率都要连同 shift 一起报告。
- **instruction type**：`EVALUATION.instruction_type` 决定 RoboTwin 用 seen 还是 unseen
  指令，upstream README 明确说这会差一两个点。

upstream 自报的 LIBERO 全量结果（40 任务 × 50 episodes，optional-IDM checkpoint，
shift 1.0）：IDM 模式平均 98.55%，first-frame 模式平均 97.75%。这是上游声明值，本工作区
尚未复现。

## 接入边界

本次只完成 fork、submodule 接入、method Agent 指南和根仓登记。**没有**创建
`experiments/fastwam/`、配置、launcher、runbook 或结果报告，也没有安装环境、下载数据集
或运行任何训练与评测。所有运行前提均来自 upstream README，未在本机执行验证。
