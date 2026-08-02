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

- **Status:** Passed（2026-08-02，用户确认最终 gitlink、分支、远端与 CLI/测试均通过）
- **Purpose:** 确认 UniVTAC gitlink 已固定撤销个人 Agent 文件后的 fork
  `dev@1e9272afca41`，且根 CLI 能识别其预期分支与官方 upstream。
- **Prerequisites:** 可访问 GitHub；无需安装 Isaac Sim、Isaac Lab、TacEx 或下载数据。
- **Commands:**

```bash
cd /root/vla-post-train
git submodule update --init methods/univtac
git -C methods/univtac status --short --branch
git -C methods/univtac remote -v
./lab doctor
./lab method status
uv run pytest tests/test_cli.py
```

- **Pass criteria:** UniVTAC 位于 `dev` 分支、revision 以 `1e9272afca41` 开头且工作树干净；`origin` 为
  `AtticusZeller/UniVTAC`、`upstream` 为 `univtac/UniVTAC`；`lab doctor` 全部为
  `PASS`；`lab method status` 的 `univtac` 行显示 `dev`、`clean=yes` 和正确远端；
  `tests/test_cli.py` 全部通过。
- **Return on failure:** 返回上述命令的完整输出；若 submodule 初始化失败，同时返回
  `git submodule status --recursive`。

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
