# Command Reference

> 项目常用命令与用户侧验证入口。命令应可直接复制执行。

## 常用命令

```bash
cd /root/vla-post-train
uv sync --python 3.12 --all-groups

./lab doctor
./lab method status
./lab config validate --all

./lab experiment dry-run \
  experiments/flowdagger/configs/metaworld_assembly_smoke_b16_seed42.yaml
./lab experiment dry-run \
  experiments/dsrl-pi0/configs/libero90_task57_smoke_seed0.yaml
./lab experiment dry-run \
  experiments/rlinf/configs/libero10_task0_medium_seed0.yaml

uv run ruff format --check .
uv run ruff check .
uv run ty check scripts tests
uv run pytest
```

## 待用户验证

- **Status:** Pending（2026-08-02；云端修复已停止，等待 Ubuntu 本地机验证）
- **Purpose:** 从远端恢复 UniVTAC `dev@a206692`（安装器基线 `0876043`），在本地
  RTX 4060 Laptop GPU 上完成依赖安装、最小 GPU smoke 与 GUI 启动。
- **Prerequisites:** GitHub 私有仓库访问权限、Conda、可用 NVIDIA 驱动和至少约 50 GB
  空间。Isaac Sim 4.5 官方只列出 Ubuntu 20.04/22.04，最低内存为 32 GB；当前
  Ubuntu 24.04、16 GB RAM 和 8 GB VRAM 属于未覆盖/最低边缘配置，首次验证时关闭其他
  高内存程序，并避免 4K 多相机或大规模并行场景。
- **Commands:**

```bash
git clone --recurse-submodules \
  https://github.com/AtticusZeller/vla-post-train.git
cd vla-post-train

git -C methods/univtac status --short --branch
git -C methods/univtac remote -v

set -o pipefail
bash methods/univtac/scripts/install.sh 2>&1 | tee "$HOME/univtac-install.log"

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate UniVTAC
python -m pip check
# 阅读并接受 NVIDIA Omniverse EULA 后再设置：
export ACCEPT_EULA=Y
bash methods/univtac/scripts/install.sh --gpu-smoke \
  2>&1 | tee "$HOME/univtac-gpu-smoke.log"

# GPU smoke 通过后再验证 GUI；关闭窗口即可结束。
isaacsim

# 可选：单环境 TacEx 可视化，不先跑 UniVTAC 数据采集或 512-env 训练。
cd methods/univtac/third_party/TacEx
python scripts/demos/tactile_sim_approaches/check_taxim_sim.py --debug_vis
```

- **Pass criteria:** UniVTAC revision 以 `a206692` 开头且工作树干净；安装命令以
  exit code 0 结束；`pip check` 无 broken requirements；
  `--gpu-smoke` 能创建并关闭 Isaac Sim、导入 `tacex` 与 `tacex_uipc`；`isaacsim`
  出现可交互窗口；可选 TacEx demo 能显示单环境触觉可视化，且无 CUDA OOM 或崩溃。
- **Return on failure:** 返回 `$HOME/univtac-install.log` 或
  `$HOME/univtac-gpu-smoke.log`；若 GUI 失败，附终端末尾 200 行、`nvidia-smi`、
  `free -h` 与是否使用 Wayland。如果首错是 tinygltf `unexpected hash`，不要直接采用
  控制台 `Actual` 值或盲目重跑；先保留归档、验证 gzip/源码内容/tar commit，并参考
  `docs/bug.md` 的 2026-08-02 条目。失败 manifest 的 build cache 会让下一次重跑表现为
  Eigen3 缺失。不要在失败后直接启动数据采集。

## 最近用户验证

- **状态**：Passed（2026-07-30，用户确认 `corner` 视角与 640×480 清晰度可用）
- **目的**：人工确认 FlowDAgger MetaWorld-12 冒烟运行生成的视频可播放，
  且画面确实是 Assembly 任务而非黑屏、静帧或错误任务。
- **前置条件**：可在 Codex 桌面端播放本次回复中的视频，或本机可使用 `ffplay`。
- **命令**：

```bash
ffplay -autoexit \
  /mnt/data/atticux/vla-post-train/flowdagger/20260730-035402__metaworld12-assembly-smoke-seed42/mw12-assembly-smoke_2026_07_30_11_54_14_0000--s-42/videos/eval_step0_rollout0.mp4

ffplay -autoexit \
  /mnt/data/atticux/vla-post-train/flowdagger/20260730-035402__metaworld12-assembly-smoke-seed42/mw12-assembly-smoke_2026_07_30_11_54_14_0000--s-42/videos/eval_step1_rollout0.mp4
```

- **通过标准**：两段视频都能完整播放约 10 秒；可见 MetaWorld Assembly 场景和机械臂
  连续运动；无黑屏、静帧、花屏或截断。Smoke 成功率不作为本次视觉验收标准。
- **失败时返回**：失败视频名、播放器报错，或能说明异常的时间戳/截图。

## 历史验证记录

STEAM medium 两卡复现、RLToken 无墙钟长跑和 RLToken progressive 中等预算三项
用户侧验证均已 Passed，命令、通过标准和实际结果记录在 [`docs/log.md`](docs/log.md)
对应条目中，不在本文件重复保留。

## RLToken 运行与汇总

```bash
cd /root/vla-post-train

./lab config validate \
  experiments/rlinf/configs/rlt_maniskill_stage2_progressive_seed2026.yaml
./lab experiment dry-run \
  experiments/rlinf/configs/rlt_maniskill_stage2_progressive_seed2026.yaml

./lab experiment status 20260729-021706__rlt-maniskill-stage2-progressive-seed2026
```

汇总某个 run 前，需要先把该 run 的 W&B URL 临时写入配置的 `tracking.run_urls`
（`primary_metrics` 同理），再执行下面两条命令，完成后按惯例把配置还原为空模板：

```bash
./lab experiment summarize <run-id>
./lab report build rlinf
```
