# TacWAM 模块说明

## 定位

`methods/tacwam` 是触觉感知机器人操作的世界动作模型（WAM）method。2026-09-02 曾接入又与
Cosmos-Framework 一并移出工作区；本次（2026-09-03）重新接入，仓库架构已实质变化——不再是
Cosmos3-Edge/`cosmos-framework` 外部依赖，而是从 [[docs/fastwam.md]] 迁移模型代码并统一
改名得到的 **基于 Wan2.2-TI2V-5B 的视频—动作联合世界模型**，同时引入了仿 xense-openpi 风格的
`TrainConfig`/`get_config()` 完整 YAML 配置系统。`src/`、`configs/` 中均已不含 Cosmos 引用。

## 来源与版本

- 协作仓库（`origin` 与 `upstream` 同一 URL）：`https://github.com/Hubo1231/TacWAM.git`
- 分支：`main`
- 当前 pin：`ba42007cfa310ec51291359245474887cdba8f27`
- GitHub 状态：非 fork；用户是该仓库的联合开发者，因此本工作区直接使用原仓库作为
  `origin`，不创建个人 fork；为兼容根仓 method registry，`scripts/lab.py` 的 `upstream`
  字段也指向同一 URL——沿用 2026-09-02 首次接入时确认过的理由
- 上次接入的 pin 为 `d42ff465a673b151482d6efb6d1cc4ab74b5faf6`；本次固定的 `ba42007` 是其
  后代，中间新增的关键提交：`af24ac7`（用 Wan2.2/TacWAM 模型替换 Cosmos3-Edge 并引入配置
  系统）、`7ccee80`（LeRobot normalization statistics 工具）、`e8688b9`（训练启动脚本）、
  `b409c18`（LeRobot DataLoader 与 mamba 环境）、`ba42007`（改用 mamba 环境清单）
- 许可证：仓库当前没有 LICENSE 文件或 GitHub license metadata；未经项目成员确认，不对外
  推断其授权范围
- 嵌套 submodule：无

## 当前实现范围

- 模型代码位于 `src/tacwam/models/wan22/`，四个变体：`TacWAM`（uncond）、`TacWAMJoint`
  （动作 token 可关注全部视频 latent token）、`TacWAMIDM`（带 inverse dynamics model
  条件）、`TacWAMOptionalIDM`（训练/推理时可选 IDM 条件）；对应 Hydra 模型配置在
  `configs/model/`，通过 `tacwam.model_factory` 创建实例。
- `src/tacwam/training/config.py` 提供仿 xense-openpi 风格的冻结 dataclass 配置系统
  （`TrainConfig`、`DataConfig`、`get_config()`、`all_configs()`、Tyro CLI 覆盖），示例见
  `configs/_examples/tacwam_bi_flexiv.yaml`；`configs/README.md` 有详细说明。
- `src/tacwam/training/data_loader.py` 已实现单个 LeRobot 数据集的 DataLoader 构造
  （项目固定 `lerobot[dataset]==0.6.0`，惰性导入，FakeDataset 与轻量配置测试不在模块导入阶段
  加载 LeRobot/PyTorch）；混合数据集仍未实现。
- `scripts/compute_norm_stats.py` 计算 LeRobot 数据集的 normalization statistics，默认只读
  `data/**/*.parquet`，不解码图片/视频；支持 `--hub-data-meta-only` 只下载统计所需文件。
- `scripts/train.py` 初始化 Accelerate/DeepSpeed、随机种子、checkpoint 目录、W&B，解析校验
  数据配置并构建 DataLoader；脚本在实例化模型之前结束，训练循环本身仍未实现。

## 环境安装（未在本机跑完）

上游 README 记录环境为 Python 3.12 + `torch==2.11.0+cu128` + `torchvision==0.26.0+cu128` +
Transformers 5.4/5.5 + CUDA 12.8，用仓库根目录的 `conda_enviroment.yaml` 创建 `tacwam`
mamba 环境：

```bash
mamba env create -f conda_enviroment.yaml
mamba activate tacwam
```

默认从 ModelScope 下载 Wan 权重；设置 `DIFFSYNTH_DOWNLOAD_SOURCE=huggingface` 可改用
Hugging Face。本次接入未创建该环境，未下载权重，未运行训练或推理。

`pyproject.toml` 已把 `torch==2.11.0`、`torchvision==0.26.0`、`lerobot[dataset]==0.6.0`
列为正式（非 test-extra）依赖，因此即便只想跑"轻量" config/transform 测试，也必须先装完整
PyTorch/LeRobot 依赖栈——没有不装重量依赖就能跑测试的路径。本机 2026-09-03 尝试用 uv 代替
mamba 安装（root 环境没有 mamba，只有 conda function）：

```bash
cd methods/tacwam
UV_EXTRA_INDEX_URL="https://download.pytorch.org/whl/cu128" \
  uv sync --extra test --python 3.12 --index-strategy unsafe-best-match
```

按用户要求中途手动停止（"环境配置不用你装，命令给我就行"），未装完；本机磁盘当时只剩
23G 可用（594G 分区已用 96%），过程中 `~/.cache/uv` 从 34G 涨到 38G（约缓存了 4G，主要是
`torch==2.11.0+cu128` 单 wheel 782MiB 以及部分 nvidia-* CUDA 依赖），根仓与 submodule 检出
均已确认恢复干净（无残留 `.venv`/`uv.lock`）。真正跑通环境安装留给用户在 `cmd.md` 或直接用
上述命令自行执行。

## Agent 指南与文档已过时（已在 `docs/sync-agents-guide` 分支修复，待合并）

`methods/tacwam/AGENTS.md` 原先仍描述已被 `af24ac7` 替换/删除的 Cosmos3-Edge BiFlexiv 架构与
`cosmos-framework` 外部 editable 依赖，与当前 Wan2.2 实现不符；其记录的测试命令
`uv run --no-project --with pytest --with numpy pytest` 在当前代码上因未安装本地包而报
`ModuleNotFoundError: No module named 'tacwam'`（`tests/` 下 5 个测试模块全部导入失败，实测于
2026-09-03）。

2026-09-03 已在协作仓库 `Hubo1231/TacWAM` 上开新分支 `docs/sync-agents-guide`（从 `main`
`ba42007` 分出，提交 `6e5cd18`）重写整份 `AGENTS.md`：Structure 改为对照 `src/tacwam` 实际
目录、Commands 改为 `uv run --with-editable . --with pytest pytest` 并注明 torch/lerobot
已是硬依赖、无免安装测试路径，Boundaries 补上"不重新引入 cosmos-framework 依赖"。已推送到
`https://github.com/Hubo1231/TacWAM/tree/docs/sync-agents-guide`，PR 尚未开，`main` 尚未合并
该修复；根仓 `.gitmodules`/`scripts/lab.py` 仍按约定跟踪 `main`，pin 未变。

## 与 FastWAM 的关系

TacWAM 的 Wan2.2 骨干、ActionDiT 动作头及权重加载/转换代码直接从 [[docs/fastwam.md]]
迁移而来（改名 `FastWAM → TacWAM`、`fastwam → tacwam`），但训练/数据加载/配置系统已经
独立演化（新增仿 xense-openpi 的配置系统与 LeRobot DataLoader，FastWAM 一侧没有）。两者
在根仓 `focus.yaml` 的 `xense` profile 中并列为 WAM 对照实现。

## 接入边界

2026-09-03 首次接入只做 submodule 接入、根仓登记与文档，未改 TacWAM 代码。同日的后续
`docs/sync-agents-guide` 分支修改了 `methods/tacwam/AGENTS.md` 并推送到协作仓库，但仍未
创建 `experiments/tacwam/`、配置、launcher 或 runbook，未安装环境、未下载数据集或权重，
未运行任何训练、推理或评测；`main` 分支与根仓 pin 均未变。

## 验证边界

Agent 侧只验证了 submodule remote/branch/revision 与根仓登记的一致性（`./lab doctor`、
`./lab method status`），`AGENTS.md` 测试命令的失败模式，以及 `docs/sync-agents-guide`
分支已成功推送到远端（`git ls-remote` 确认）；没有可用的训练、推理或真机证据，`main`
上是否合并该分支待用户/协作者决定。
