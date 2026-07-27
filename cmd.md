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

## 用户验收

- **状态**：Passed（2026-07-27）。
- **证据**：用户已确认下列只读 CLI 验收全部通过，并已通过 Explain Diff 五题理解门。
- **目的**：确认 LeRobot framework、第五个 submodule、`add-method` Skill 和 method
  Agent 去重在用户终端中均可恢复且不影响既有实验入口。
- **环境限制**：当前 `/mnt/data` 是只读挂载；恢复为 `rw` 前不要执行
  `experiment run`、W&B 在线汇总或任何 GPU 长跑。

请在新终端执行：

```bash
cd /root/vla-post-train

./lab doctor
./lab method status
./lab config validate --all
git submodule status --recursive

./lab experiment dry-run \
  experiments/flowdagger/configs/metaworld_assembly_smoke_b16_seed42.yaml
./lab experiment dry-run \
  experiments/dsrl-pi0/configs/libero90_task57_smoke_seed0.yaml
./lab experiment dry-run \
  experiments/rlinf/configs/libero10_task0_medium_seed0.yaml

test ! -e experiments/lerobot
if rg -n 'init-repo-agents:managed' \
  methods/*/AGENTS.md methods/*/CLAUDE.md; then
  echo "method Agent 文件仍含重复根托管块" >&2
  exit 1
fi

uv run python \
  /root/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  .codex/skills/add-method
uv run pytest
```

通过标准：

1. `doctor` 的根环境、五个 method 和 nested submodule 均为 `OK`；`artifact writes`
   因当前只读挂载显示 `WARN` 是已知环境状态。
2. `method status` 显示 FlowDAgger `dev`、DSRL `dev`、RLinf `personal-dev`、
   StarVLA `starVLA_dev`、LeRobot `workspace`，且五个 checkout 均为 clean。
3. 9 份 YAML 全部通过；三个 dry-run 的 cwd、Conda 环境与原生入口分别是
   `train_flowdagger.py`、`python -m examples.launch_train_sim` 和
   `run_libero10_task0_comparison.sh medium`。
4. `git submodule status --recursive` 的顶层 LeRobot revision 为
   `0d383d09f2051444de211739196a28cc94736861`，所有行均无 `-`、`+` 或 `U` 前缀。
5. `experiments/lerobot` 不存在，method Agent 扫描无输出，`add-method` 显示
   `Skill is valid!`。
6. pytest 显示 `21 passed`。

失败时请返回完整命令输出；本次不运行 LeRobot 或任何 GPU 实验。
