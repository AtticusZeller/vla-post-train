# xense-openpi Commands

## RECAP 价值模型（`feature/pi-star-0.6`）

下面的命令都在 `methods/xense-openpi` 下运行。方法定义见 [pi-star-06-spec.md](pi-star-06-spec.md)，文件与模块见
[codebase.md](codebase.md)。

### 打优势标签

用途：给数据集的每一帧打二值优势标签，作为一次尝试写到数据集外的文件，不改数据集。`round = 0` 的帧（初始示范）与
`is_intervention` 的帧（人接管）一律 positive；其余帧往后看 `--advantage-horizon` 帧（默认 50）算优势，高于阈值的
为 positive。阈值使 `--positive-fraction`（默认 0.4）的帧为 positive，取在哪些帧上由 `--threshold-frames` 定：
`rollout`（默认）只取按优势打标签的那些帧，`all` 取全部帧。数据集缺这三列时报错：rollout 要用采集模式录，初始
示范先按「给初始示范补标记并与 rollout 合并」补上。

前提：return 文件已算出；$V$ 的预测覆盖数据集的每一帧——`heldout_predictions.parquet` 只有留出 episode，训练
episode 要用 `--final-train-episodes <训练 episode 数>` 另写 `train_predictions.parquet`，两个文件一起传。不需要
视频和 GPU。

```bash
python scripts/recap/label_advantage.py --dataset-root <数据集根目录> --returns <returns.parquet> \
  --predictions <runs_dir>/<run>/heldout_predictions.parquet <runs_dir>/<run>/train_predictions.parquet \
  --output <labels_dir>/<尝试名>.parquet
```

预期：写出 `<尝试名>.parquet`（每帧一行：`episode_index`、`frame_index`、`return`、`value`、`advantage`、
`positive`、`source`，`source` 取 `initial`、`intervention`、`value`）和同名的 `.json`（参数、阈值、各来源的帧数与
positive 占比、输入文件的路径）。各来源帧数之和等于数据集总帧数；`rollout` 做法下 `value` 来源的 positive 占比
等于 `--positive-fraction`。预测少一帧、多一帧或与 return 文件对不上都报错，不写文件。预测文件含多个数据集时加
`--repo-id <repo_id>` 选出本数据集的行。

### 画优势标签的门禁图

用途：把一次打标签尝试画成每个 episode 一张图，供人判断这份标签能不能用：上排是等间隔的 head 相机帧，中间是
return 与预测值，下栏是优势与阈值线。颜色全部来自标签文件，图上看到的就是写回后训练要用的那一份：绿是按优势
positive，红是 negative，青是按规则强制 positive（初始示范与介入帧）。

前提：「打优势标签」生成的标签 parquet 与同名 `.json`；环境里有 matplotlib；能读到同一个数据集的视频。不需要 GPU，可加
`JAX_PLATFORMS=cpu`。

```bash
python scripts/recap/plot_value.py --labels <labels_dir>/<尝试名>.parquet \
  --repo-id <repo_id> --output-dir <plots_dir>
```

预期：日志打印一行 `threshold=…（阈值做法、N、比例） advantage_std=… flips_per_second=… median_positive_run=…s`；
`<plots_dir>` 下每个 episode 一张 `value_episode_XXXX.png`，标题里有该 episode 的 MAE 与 positive 帧的比例。只画部分
episode 时加 `--episodes 42 71`。数据集不在 LeRobot 默认缓存位置时加 `--dataset-root <数据集根目录>`。要换 $N$、比例
或阈值做法，重新运行「打优势标签」。

加 `--videos` 时每个 episode 另写一个同名的 `value_episode_XXXX.mp4`（H.264）：画面边框是该帧标签的颜色，左上角是
帧号与优势，底部是整条 episode 的标签时间轴和当前位置的光标。要解码整条 episode，一条 1400 帧的约 30 秒、1.6 MB。

### 把认可的标签写回数据集

用途：把门禁通过的那一次尝试写成数据集的一列 `advantage_positive`，产出带标签的新副本；策略训练读这一列。
源数据集不动。

前提：标签文件是给同一份数据集打的；`<带标签的新目录>` 不存在；磁盘够放一份完整副本（官方的 `modify_features`
会把视频整份复制）。不需要 GPU。

```bash
python scripts/recap/write_advantage_labels.py --src <数据集根目录> --labels <labels_dir>/<尝试名>.parquet \
  --dst <带标签的新目录>
```

预期：日志一行报告帧数、positive 占比与打标签的参数；新副本的 `meta/info.json` 里有 `advantage_positive`，
`meta/advantage_labels.json` 是这次尝试的 `.json`。标签文件与数据集的帧对不上时报错，不产出副本。

### 用带标签的数据集训练策略

用途：第 $k\ge1$ 轮的策略训练，每一帧按自己的优势标签带 `Advantage: positive` 或 `Advantage: negative`。

前提：配置的 `model.advantage_conditioned: true`，数据集是「把认可的标签写回数据集」产出的带标签副本，已对它算过 norm stats。示例配置
`configs/_examples/pi05_base_bi_flexiv_cylinder_stack_recap_round_h100.yaml`，其中 `repo_id` 是占位，要改成本轮的
数据集并重新扫 prompt 的 token 长度。

```bash
env -u LD_LIBRARY_PATH XLA_PYTHON_CLIENT_MEM_FRACTION=0.9 OPENPI_LEROBOT_DATASET_ROOT=<带标签的新目录> \
  python scripts/train.py <配置名> --exp-name=<实验名>
```

预期：训练开始时日志有一行以 `Advantage condition:` 开头，报告标签取自哪个数据集的 `advantage_positive` 列、
positive 帧的占比与总帧数，占比与写回时报告的一致。数据集没有这一列时这一行写的是 `every frame is trained as
positive`，即第 0 轮的行为；选错数据集时从这一行看出来。

### 采集带标记的 rollout

用途：在 bi_flexiv 上让策略执行任务并录成 LeRobot 数据集，人可以随时接管；每帧另录 `is_intervention`、
`episode_success`、`round` 三列，供优势标签和训练使用。

前提：机器人主机（`lerobot-xense` 环境），策略服务已在 `<host>:<port>` 上；Pico4 已连接。只能用同步运行方式，不能加
`--args.rtc-enabled` 或 `--args.action-hz`。`--args.record-round` 是本轮的编号 $k\ge1$。视频按 h264 编码，与
bi_flexiv 的示范相同；示范用别的编码时加 `--args.record-vcodec <编码>`，两边编码不同就合并不了。

```bash
mamba run -n lerobot-xense python -m examples.bi_flexiv_rizon4_rt.main \
    --args.robot-recipe forward-05 --args.host <host> --args.port <port> \
    --args.record --args.record-repo-id <repo_id> --args.task "<任务指令>" \
    --args.pico4-intervention --args.record-round <k> --args.num-episodes <n>
```

预期：机械臂归位后日志提示按 A；按 A 开始一条 episode。B 以成功结束，Y 以失败结束，X 或中途按 A 作废；握住任一
grip 并移动手柄超过 5 mm 或 3° 才接管，松开后策略重新推理。按下 B / Y 的那一帧是最后一帧，之后的归位不录。没有标签
就结束的 episode（X、A、到步数上限、Ctrl+C）不保存，但仍计入 `--args.num-episodes`。Ctrl+C 按一次是停下并归位；
归位时再按一次是立刻退出、不等归位，已保存的 episode 仍然读得出。录完后用「训练前检查数据集」中的脚本看
每轮的 episode 数、失败数与介入帧占比。

### 给初始示范补标记并与 rollout 合并

用途：把示范做成能与 rollout 合并的副本，再合成一轮训练用的累计数据集。LeRobot 只合并 features 完全相同的数据集：
示范要补上三列（全部成功、无介入、`round = 0`），并去掉 rollout 没有录的视频流。源数据集都不动。

前提：示范与 rollout 的相机分辨率、fps、视频编码相同；两个新目录都不存在；磁盘够放保留下来的视频各一份。不需要
GPU。bi_flexiv 的示范要去掉的是四路触觉视频：

```bash
python scripts/recap/mark_initial_dataset.py --src <示范数据集根目录> --dst <补标记的新目录> \
  --remove-features observation.images.left_tactile_left observation.images.left_tactile_right \
  observation.images.right_tactile_left observation.images.right_tactile_right

lerobot-edit-dataset --new_repo_id <合并集的 repo_id> --new_root <合并集的新目录> \
  --operation.type merge \
  --operation.repo_ids "['<示范的 repo_id>', '<rollout 的 repo_id>']" \
  --operation.roots "['<补标记的新目录>', '<rollout 数据集根目录>']"
```

预期：第一条命令的日志报告去掉了哪些 feature，新副本的 `meta/info.json` 里多三列、少四路触觉视频。第二条最后打印
合并集的 episode 数与帧数，等于两边之和；示范排在前面，episode 编号从 0 起。features 有任何不同时第二条在动数据之前
就报错并列出差异。合并后运行「训练前检查数据集」中的脚本，按轮的 episode 数应与各数据集一致。往后每一轮在 `repo_ids` 与 `roots`
里按顺序再加一个 rollout 数据集。

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

### 训练前检查数据集

用途：找出元数据与数据不一致、相机视频缺失，以及需要人看的可疑 episode（超长、多数时间静止、开头或结尾长时间静止）。
只读，不删任何东西。

前提：数据集在本地，LeRobot v3.0。不需要 GPU，可加 `JAX_PLATFORMS=cpu`。

```bash
python scripts/recap/check_dataset.py --dataset-root <数据集根目录> \
  [--sheet-dir <图目录>] [--output <报告.json>]
```

预期：不一致打印 `PROBLEM …`，可疑 episode 每条一行 `SUSPECT episode N: <原因> | 时长、静止帧比例、开头与结尾静止秒数`，
最后一行是问题数与可疑数。数据集带 `is_intervention`、`episode_success`、`round` 三列时另查三列是否齐全、
`episode_success` 与 `round` 在一条 episode 内是否不变、`round = 0` 的 episode 有没有介入帧，并按轮打印 episode 数、
失败数、有介入的 episode 数与介入帧占比。加 `--sheet-dir` 时给每条可疑 episode 存一张 6 帧的 head 相机图（要解码视频，也要设
`HF_DATASETS_CACHE`）；有 `PROBLEM` 时不出图，退出码为 1。阈值见 `--help`。

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

前提：`<dataset_root>` 下有 `meta/episodes` 与 `data/`；不需要视频和 GPU。成功 / 失败读数据集的逐帧列
`episode_success`（采集模式录下，见「采集带标记的 rollout」）；数据集没有这一列时全部按成功处理。

```bash
python scripts/recap/compute_returns.py --dataset-root <dataset_root> --output <returns.parquet>
```

预期：日志报告失败的 episode 数（或"全部按成功"）、行数、episode 数、每个任务的 `l_max` 与最小 return；行数等于
数据集总帧数，全部成功时最小 return 不低于 $-0.5$。

### 训练价值模型

用途：在一个或多个数据集上训练价值模型，每个数据集按 episode 留出 10% 做验证。

前提：已安装 gemma、下载权重和 tokenizer，并算出 return 标签；数据集已在 `HF_LEROBOT_HOME` 下或用 `--dataset-root` 指定；GPU 空闲。在 `xense-train-01` 上还要
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
