# VLA 后训练研究工作区

这是一个私有的研究控制仓库，用于统一管理 VLA 后训练方法代码、实验配置、运行证据、
结果汇总和 Agent workflow。算法与第三方框架始终保留在独立 Git 仓库中，并通过
`methods/` submodule 固定到准确 revision。

## 首期方法

| 路径 | 分支 | 角色 |
| --- | --- | --- |
| `methods/flowdagger` | `dev` | FlowDAgger 官方实现 fork |
| `methods/dsrl-pi0` | `dev` | DSRL π0 第三方复现 |
| `methods/rlinf` | `personal-dev` | RECAP / STEAM 实验框架 |
| `methods/starvla` | `starVLA_dev` | VLA 训练与策略框架 |

OpenPI 与 LIBERO 继续由各方法按自身依赖闭包管理，首期不单独接入。

## 初始化

```bash
git clone --recurse-submodules https://github.com/AtticusZeller/vla-post-train.git
cd vla-post-train
uv sync --python 3.12 --all-groups
./lab doctor
./lab method status
```

根环境只包含 YAML、W&B、Git/进程编排和测试工具，不安装训练依赖。各 method 使用自己的
Conda、uv、venv 或 Docker 环境。

## 稳定入口

```bash
./lab config validate --all
./lab experiment dry-run experiments/flowdagger/configs/metaworld_assembly_smoke_b16_seed42.yaml
./lab experiment status <run-id>
./lab experiment summarize <run-id>
./lab report build <method>
```

`experiment run` 是前台进程并将完整日志写到
`/mnt/data/atticux/vla-post-train/<method>/<run-id>/`。长跑由
`.codex/skills/run-experiment` 按方法 runbook 放入 tmux。

## 证据分层

- `experiments/<method>/configs/`：实验意图；
- `experiments/<method>/runs/<run-id>/run.json`：执行事实；
- `summary.json`：可比较的核心结果；
- `runbook.md`：方法级环境、启动、恢复和故障手册；
- `report.md`：跨 run 的研究结论和证据边界；
- W&B 与 `/mnt/data`：完整曲线、大型日志、checkpoint、视频和数据。

完整论文笔记继续保存在 Obsidian。实现所需的论文上下文只在无官方实现的独立方法仓库中
保留最小副本。

架构和执行状态见 [`docs/architecture.md`](docs/architecture.md) 与
[`docs/plan.md`](docs/plan.md)；用户验收命令见 [`cmd.md`](cmd.md)。
