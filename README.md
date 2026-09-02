# VLA 后训练研究工作区

这是一个私有的研究控制仓库，用于统一管理 VLA/VTLA 后训练方法代码、实验配置、运行证据、
结果汇总和 Agent workflow。算法与第三方框架始终保留在独立 Git 仓库中，并通过
`methods/` submodule 固定到准确 revision。

## 已接入仓库

| 路径 | 分支 | 类型 | 角色 |
| --- | --- | --- | --- |
| `methods/flowdagger` | `dev` | method | FlowDAgger 官方实现 fork |
| `methods/dsrl-pi0` | `dev` | method | DSRL π0 第三方复现 |
| `methods/expo-ft` | `dev` | method | EXPO-FT 官方实现 fork |
| `methods/rlinf` | `personal-dev` | framework | RECAP / STEAM / RLToken 训练与实验框架 |
| `methods/starvla` | `starVLA_dev` | framework | VLA 训练与策略框架 |
| `methods/lerobot` | `workspace` | framework | 数据、策略、训练与机器人基础框架 |
| `methods/univtac` | `dev` | benchmark | 视触觉仿真、数据采集、策略训练与评测平台 |
| `methods/n0-vtla` | `workspace` | method | N0-VTLA 官方实现 fork（视触觉后训练与推理） |
| `methods/xense-openpi` | `main` | framework | OpenPI 的 Xense 触觉扩展 fork |
| `methods/lerobot-xense` | `main` | framework | LeRobot 的 Xense 触觉扩展 fork |
| `methods/xense-lerobot-viewer` | `main` | tool | LeRobot 数据集可视化查看器（直接 pin 官方仓库，无 fork）|
| `methods/t-rex` | `workspace` | method | T-Rex 触觉反应灵巧操作官方实现 fork |
| `methods/tabero` | `workspace` | method | Tabero 触觉基础模型与基准官方实现 fork |
| `methods/cosmos` | `xense` | framework | NVIDIA Cosmos-Framework 训练与服务框架 fork；预留 Flexiv/Xense 适配边界 |
| `methods/tacwam` | `main` | method | TacWAM 触觉感知世界动作模型；直接协作仓库，不使用 fork |
| `methods/fastwam` | `workspace` | method | Fast-WAM 世界动作模型官方实现 fork（LIBERO / RoboTwin 训练与评测） |

官方 OpenPI 与 LIBERO 继续由各方法按自身依赖闭包管理，不单独接入；Xense 触觉扩展
变体（xense-openpi、lerobot-xense）已接入，与官方 LeRobot/OpenPI 相互独立。
LeRobot 与 expo-ft 当前只固定代码版本。UniVTAC 已完成安装器修复和本地 RTX 4060
单环境触觉仿真验收，但尚未创建实验配置或运行手册；当前采用本地仿真、云端模型推理。

## 初始化

```bash
git clone https://github.com/AtticusZeller/vla-post-train.git
cd vla-post-train
uv sync --python 3.12 --all-groups
./lab method focus xense      # 只拉当前关注的 method（见下）
./lab doctor
./lab method status
```

## Focus profile · 只保留当前关注的 method

`main` 分支始终记录全部 method 的 gitlink，[`focus.yaml`](focus.yaml) 只决定本机
工作树里实际 checkout 哪些。切换不改 `.gitmodules`、不分叉历史，可随时还原。

```bash
./lab method focus                  # 打印当前 profile 与各 method 状态
./lab method focus xense --dry-run  # 预览将删除的工作树，不做改动
./lab method focus xense            # 收敛到 Xense 触觉线的 6 个仓库
./lab method focus all              # 还原全部
```

停用一个 method 会执行 `git submodule deinit -f` 删除其工作树，并一并删掉 `deinit`
留下的空目录，所以 `methods/` 下只剩当前关注的仓库。切换前会列出体积清单并要求确认
（`--yes` 可跳过）。`.git/modules/` 里的对象库不受影响，因此还原不
需要联网重新 clone。**注意清单里标为「无法从 git 恢复」的条目**（例如 univtac 的
`third_party/curobo`、`IsaacLab`、`TacEx/**/build`）是 gitignore 掉的手动安装产物，
删除后需重跑该方法的安装器。

被停用的 method 在 `./lab doctor` 里显示为 `SKIP`、在 `./lab method status` 里显示
为 `inactive`，都不计为失败。

活跃集合记录在本机 `.git/config` 的 `submodule.active` pathspec 列表里（不是每个
submodule 的 `submodule.<name>.active`——后者会被 `git submodule update --init`
改写回 `true`）。删掉目录后 git 会把 gitlink 视为已删除，因此同时给它打上
`--skip-worktree`，让 `git status` 保持干净。两者都是本机 config 与 index 状态，
不进入任何提交。

根环境只包含 YAML、W&B、Git/进程编排和测试工具，不安装训练依赖。各 method 使用自己的
Conda、uv、venv 或 Docker 环境。

## 稳定入口

```bash
./lab config validate --all
./lab experiment dry-run experiments/flowdagger/configs/metaworld_assembly_smoke_b16_seed42.yaml
./lab experiment suite-configs flowdagger
./lab experiment dry-run experiments/flowdagger/configs/metaworld12_assembly_full_seed42.yaml
./lab report suite flowdagger
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
