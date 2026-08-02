# N0-VTLA 模块说明

## 定位与边界

`methods/n0-vtla/` 是 NeoteAI 官方 N0-VTLA 实现的用户 fork，在本工作区登记为
`method`。N0-VTLA 在 PaliGemma (gemma_2b) 前缀 + Gemma (300m) flow-matching action
expert 上加入潜在触觉 token 通路：冻结的 DINOv2 对 baseline-difference 触觉图编码，
cross-attention predictor 将其蒸馏为 5 个潜在 token，再经 zero-initialized gate 注入
action expert。仓库发布后训练工具链、数据转换、验证脚本和推理服务器，不含大规模
预训练管线。

- 用户 fork：`https://github.com/AtticusZeller/N0-VTLA.git`
- 官方 upstream：`https://github.com/neoteai/N0-VTLA.git`
- 工作分支：`workspace`（追踪 upstream `main`）
- 许可证：仓库原创材料 CC BY-SA 4.0；含 Apache-2.0 第三方组件（OpenPI、HuggingFace
  Transformers 补丁、Big Vision 等，见 `NOTICE`/`LICENSES/`）；模型权重为 Gemma 衍生，
  受 Gemma Terms of Use 约束。

## 环境约束

需要 Python 3.11 与 CUDA GPU。根 Python 3.12 环境只做编排，不安装训练依赖。安装需
独立 Conda 环境：`pip install -r requirements.txt && pip install -e . --no-deps`，
再把 `n0vtla/models_pytorch/transformers_replace/*` 复制进 site-packages 的
transformers（必需补丁）。首次模型加载会从 `gs://big_vision` 拉取 PaliGemma
tokenizer，因此 `gcsfs` 是必需依赖。

## 代码结构

- `n0vtla/`：模型包（N0VTLAPolicy、触觉 encoder/predictor、`transformers_replace`）；
- `n0vtla/policies/`：per-embodiment 输入输出 transform 与 canonical schema；
- `n0vtla/training/`：配置、数据加载、优化器；
- `n0vtla_client/`：机器人侧客户端库；
- `scripts/`：train、serve、convert、verify；
- `docs/`：安装（INSTALL）、后训练（POST_TRAINING）、部署（DEPLOY）说明。

## 当前接入状态

已完成代码版本固定（`workspace@65563a9`）与远端登记。按 add-method 规则，本次只做
method 接入，不创建 `experiments/n0-vtla/`、launcher、配置或 runbook；出现具体实验或
历史迁移需求后再补齐。尚未在本机安装依赖或验证训练/推理路径；首次实验前应在
`experiments/n0-vtla/runbook.md` 记录环境、数据与 GPU 要求。大型数据、checkpoint 和
日志写入 `/mnt/data/atticux/vla-post-train/n0-vtla/`。
