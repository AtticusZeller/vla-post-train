# xense-openpi Commands

## RL 单测（共享层、RLT 与机器人端）

用途：改动 `src/openpi/rl/` 或 `examples/bi_flexiv_rizon4_rt/rlt_mode.py` 后回归。

前提：`methods/xense-openpi/.venv` 已由 `GIT_LFS_SKIP_SMUDGE=1 uv sync` 建好；`methods/tacxense` 已检出（数值对照用例
从这里导入 tacxense）。

```bash
cd methods/xense-openpi
JAX_PLATFORMS=cpu TACXENSE_ROOT=$(realpath ../tacxense) \
  .venv/bin/python -m pytest -q -rs -p no:cacheprovider \
  src/openpi/rl examples/bi_flexiv_rizon4_rt \
  --deselect src/openpi/rl/algos/rlt/features_test.py
```

预期：全部通过；`-rs` 里只有 `token_model_test` 找不到 RLinf 参照的 2 个 skip。出现 "TacXense reference not found"
说明 `TACXENSE_ROOT` 没生效，对照用例没有真正运行。`features_test` 跑真实 pi0 前向，本机不跑。


## rlt-jax 选择 actor 训练参考输入

前提：使用已支持 `input_reference` 的 `feature/rlt-jax`。在实验 YAML 的 `rl` 段设置：

```yaml
rl:
  input_reference: corrected # 原方案；proposal 使用原始 VLA reference
```

预期：`corrected` 在人工步使用人工替换后的 reference 作为 actor 训练输入；两种模式的 BC target 相同。
省略该项时使用 `corrected`。对照测试使用不同实验名从相同初始权重开始，不恢复另一方案的训练 checkpoint；
旧 checkpoint 缺少此字段，也会被训练条件检查拒绝。

## RECAP 价值模型（`feature/pi-star-0.6`）

下面的命令都在 `methods/xense-openpi` 下运行。方法定义见 [pi-star-06-spec.md](pi-star-06-spec.md)，文件与模块见
[codebase.md](codebase.md)。

### 安装 gemma 依赖

用途：价值模型的语言骨干 Gemma3-270M 来自 `gemma` 包，它在可选依赖组 `recap` 里，默认环境不装。

前提：已有能跑 openpi 的环境。在共享服务器上不要装进共享环境，先克隆一份自己的再装，例如
`conda create --prefix <env> --clone <共享环境>`；根分区空间小时把 `TMPDIR` 指到数据盘。

```bash
pip install -e ".[recap]"
```

预期：`python -c "from gemma import gm; gm.nn.Gemma3_270M"` 不报错，`pip check` 干净。若 pip 顺带升级了 `packaging` 或
`setuptools` 导致 `pip check` 报 lerobot 的约束，把这两个包装回原版本。

### 下载 Gemma3-270M 权重与 tokenizer

用途：训练脚本只读本地副本。两个地址是 `src/openpi/recap/gemma3.py` 里的 `PARAMS_PATH` 与 `TOKENIZER_PATH`。

前提：能访问 Google Cloud Storage 的公开桶；有 `gsutil`，或用 `gcsfs` 等价下载（下面的 `gsutil` 写法没有实际跑过）。

```bash
gsutil -m cp -r gs://gemma-data/checkpoints/gemma3-270m-pt <ckpt_dir>/
gsutil cp gs://gemma-data/tokenizers/tokenizer_gemma3.model <ckpt_dir>/
```

预期：`<ckpt_dir>/gemma3-270m-pt` 约 400 MB，`<ckpt_dir>/tokenizer_gemma3.model` 存在。SigLIP 权重取自 `pi05_base`，训练时
由 openpi 自己下载到 `~/.cache/openpi`。

### 算 return 标签

用途：给 LeRobot v3.0 数据集算逐帧归一化 return，写到数据集外的旁路 parquet，不改原数据集。

前提：`<dataset_root>` 下有 `meta/episodes`；只读元数据，不需要视频和 GPU。数据集有成功 / 失败列时加
`--success-column <列名>`，否则全部按成功处理。

```bash
python scripts/recap/compute_returns.py --dataset-root <dataset_root> --output <returns.parquet>
```

预期：日志报告行数、episode 数、每个任务的 `l_max` 与最小 return；行数等于数据集总帧数，全部成功时最小 return 不低于
$-0.5$。

### 训练价值模型

用途：在一个或多个数据集上训练价值模型，每个数据集按 episode 留出 10% 做验证。

前提：上面三步已完成；数据集已在 `HF_LEROBOT_HOME` 下或用 `--dataset-root` 指定；GPU 空闲。在 `xense-train-01` 上还要
`export HF_ENDPOINT=https://huggingface.co`（tmux 会继承镜像地址，走代理时被拒），以及
`export HF_DATASETS_CACHE=<大盘上的目录>`（默认写到只有 30G 的根盘，每加载一个数据集几十到几百 MB；画图同样需要）。

```bash
XLA_PYTHON_CLIENT_MEM_FRACTION=0.9 python scripts/recap/train_value.py \
  --repo-id <repo_id> --returns <returns.parquet> \
  --gemma-params <ckpt_dir>/gemma3-270m-pt --gemma-tokenizer <ckpt_dir>/tokenizer_gemma3.model \
  --output-dir <runs_dir> --exp-name <run> \
  --best-metric mae --patience 3
```

多个数据集时 `--repo-id` 与 `--returns` 各给多个值，顺序一一对应：各数据集按相同概率采样，验证指标取各数据集的平均，
日志里另有每个数据集一行。从已有权重出发（例如从预训练的 $V_{\mathrm{pre}}$ 微调）加 `--init-params <runs_dir>/<run>/params`，
此时不再载入 SigLIP 与 Gemma3 的预训练权重。留出 episode 很长时用 `--final-episodes <n>` 限制结尾整段预测的 episode 数。

预期：每 250 步打印一次留出集的 `val_loss`、`val_mae`、`val_corr`；`--best-metric` 指定的指标（`mae` 或 `loss`）创新低时
覆盖写 `<runs_dir>/<run>/params`；连续 `--patience` 次验证没有新低就早停。结束时写
`<runs_dir>/<run>/heldout_predictions.parquet`，是最优权重在留出 episode 上的逐帧预测。启动后要等所有 data worker 起来
才出第一条训练日志。

只用已有权重做预测、不训练：`--init-params <runs_dir>/<run>/params --num-train-steps 0`，换一个 `--exp-name`。加
`--final-train-episodes <n>` 时另对每个数据集前 n 个训练 episode 整段预测，写 `train_predictions.parquet`。

### 画带优势标签的 $V$ 曲线

用途：把训练写出的预测画成每个 episode 一张图：上排是等间隔的 head 相机帧，中间是 return 与预测值，背景按优势标签
着色（positive 绿、negative 红），下栏是优势与阈值线。优势往后看 `--advantage-horizon` 帧（默认 50），阈值在预测文件里
该数据集的全部帧上取，使 `--positive-fraction`（默认 0.4）的帧为 positive。

前提：训练已写出 `heldout_predictions.parquet`；环境里有 matplotlib；能读到同一个数据集的视频。不需要 GPU，可加
`JAX_PLATFORMS=cpu`。

```bash
python scripts/recap/plot_value.py --predictions <runs_dir>/<run>/heldout_predictions.parquet \
  --repo-id <repo_id> --output-dir <plots_dir>
```

预期：日志打印一行 `threshold=… advantage_std=… flips_per_second=… median_positive_run=…s`；`<plots_dir>` 下每个
episode 一张 `value_episode_XXXX.png`，标题里有该 episode 的 MAE 与 positive 帧的比例。只画部分 episode 时加
`--episodes 42 71`（阈值仍在全部 episode 上取）。数据集不在 LeRobot 默认缓存位置时加 `--dataset-root <数据集根目录>`。
预测文件要含整条 episode，换成 `train_predictions.parquet` 即画训练 episode。

加 `--videos` 时每个 episode 另写一个同名的 `value_episode_XXXX.mp4`（H.264）：画面边框是该帧标签的颜色，左上角是
帧号与优势，底部是整条 episode 的标签时间轴和当前位置的光标。要解码整条 episode，一条 1400 帧的约 30 秒、1.6 MB。

### 训练前检查数据集

用途：找出元数据与数据不一致、相机视频缺失，以及需要人看的可疑 episode（超长、多数时间静止、开头或结尾长时间静止）。
只读，不删任何东西。

前提：数据集在本地，LeRobot v3.0。不需要 GPU，可加 `JAX_PLATFORMS=cpu`。

```bash
python scripts/recap/check_dataset.py --dataset-root <数据集根目录> \
  [--sheet-dir <图目录>] [--output <报告.json>]
```

预期：不一致打印 `PROBLEM …`，可疑 episode 每条一行 `SUSPECT episode N: <原因> | 时长、静止帧比例、开头与结尾静止秒数`，
最后一行是问题数与可疑数。加 `--sheet-dir` 时给每条可疑 episode 存一张 6 帧的 head 相机图（要解码视频，也要设
`HF_DATASETS_CACHE`）；有 `PROBLEM` 时不出图，退出码为 1。阈值见 `--help`。

### 删 episode 并核对

用途：按检查清单删掉指定的 episode，产出重新编号的新副本。只改元数据，不重编码视频（视频硬链接到源文件）；源数据集
不动。

前提：LeRobot v3.0 数据集在本地；`<新目录>` 还不存在，并与源数据集在同一个文件系统上（硬链接）。两条命令都在
`scripts/recap/` 下运行。

```bash
python drop_episodes.py --src <数据集根目录> --dst <新目录> --episodes 0 70
python verify_drop.py --src <数据集根目录> --dst <新目录> --episodes 0 70
```

预期：`verify_drop.py` 最后一行报 OK。新副本再过一遍 `check_dataset.py`，并重算 return（episode 数与 $L_{\max}$ 都变了）；
训练与画图时用 `--dataset-root <新目录>`。

### 把价值模型权重传到 COS

用途：把一次运行的最优权重存到团队的 COS 桶，供别的机器取用。

前提：在 `xense-train-01` 上，`/root/coscli` 与 `/root/.cos.yaml` 已配置。目录约定是
`xense_checkpoints/pi06_recap_value_checkpoints/<运行名>/<最优步>/`。

```bash
/root/coscli --disable-log cp <runs_dir>/<run>/ \
  cos://data-1460349206/xense_checkpoints/pi06_recap_value_checkpoints/<run>/<step>/ \
  -r --process-log=false --fail-output=false
```

预期：`coscli ls <目标> -r` 列出 `params/` 下的全部文件与 `heldout_predictions.parquet`，大小与本地一致。源路径末尾的
`/` 不能省，否则目录本身会被嵌进目标里多一层。
