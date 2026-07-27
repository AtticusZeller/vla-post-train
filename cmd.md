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

- **状态**：Passed（2026-07-27）。
- **证据**：用户已确认下列只读 CLI 验收通过，并完成 Explain Diff 5/5 理解门。
- **环境限制**：当前 `/mnt/data` 是只读挂载；恢复为 `rw` 前不要执行
  `experiment run`、W&B 在线汇总或任何 GPU 长跑。

请在新终端执行：

```bash
cd /root/vla-post-train

./lab doctor
./lab method status
./lab config validate --all

./lab experiment dry-run \
  experiments/flowdagger/configs/metaworld_assembly_smoke_b16_seed42.yaml
./lab experiment dry-run \
  experiments/dsrl-pi0/configs/libero90_task57_smoke_seed0.yaml
./lab experiment dry-run \
  experiments/rlinf/configs/libero10_task0_medium_seed0.yaml

uv run pytest
```

通过标准：

1. `doctor` 的根环境、四个 method 和 nested submodule 均为 `OK`；`artifact writes`
   因当前只读挂载显示 `WARN` 是已知环境状态。
2. `method status` 显示 FlowDAgger `dev`、DSRL `dev`、RLinf `personal-dev`、
   StarVLA `starVLA_dev`，且四个 checkout 均为 clean。
3. 9 份 YAML 全部通过；三个 dry-run 的 cwd、Conda 环境与原生入口分别是
   `train_flowdagger.py`、`python -m examples.launch_train_sim` 和
   `run_libero10_task0_comparison.sh medium`。
4. pytest 显示 `20 passed`。
5. 人工抽查三个 `experiments/<method>/report.md`：Flow full 明确为每点 25 回合；
   DSRL 500k revision 为 `7f48937d4553e95244cd81c79236a3256df80597`；
   RLinf medium 保留四个 code revision，而不是单一 revision。

以上命令保留为后续换机或新会话的回归入口。
