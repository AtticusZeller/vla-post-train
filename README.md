# Agent Research Workspace

这是一个面向 VLA、WAM、Agent 与相关具身智能研究的私有工作区。研究者负责确定目标、边界和
验收标准，Agent 在这些边界内实现、验证并整理证据。

根仓库只负责 method 接入、通用实验编排、文档和证据管理。算法、框架、benchmark、backbone
与复现代码保留在独立的 `methods/*` Git submodule 中，不被改造成统一训练框架。

## 当前 Method

| 路径 | 分支 | 角色 |
| --- | --- | --- |
| `methods/lerobot` | `workspace` | 通用数据、策略、训练和机器人框架 |
| `methods/lerobot-xense` | `main` | Xense 真机控制、遥操作与数据采集 |
| `methods/xense-openpi` | `main` | Xense 模型训练、策略服务与推理客户端 |
| `methods/fastwam` | `workspace` | Fast-WAM 官方实现与 WAM 参照 |
| `methods/tacwam` | `main` | 触觉机器人操作的 WAM 协作实现 |

源码被固定到精确 revision；接入不代表环境、训练、推理或真机流程已经验证。当前证据边界见
对应的 `docs/<method>/overview.md`。

## 初始化

```bash
uv sync --python 3.12 --all-groups
git submodule update --init --recursive
./lab doctor
./lab method status
```

根环境只包含 YAML、W&B、Git/进程编排和质量检查工具。各 method 使用自己的依赖环境；
`lerobot-xense` 与 `xense-openpi` 明确共享环境。

## 稳定入口

```bash
./lab method focus
./lab method status
./lab config validate --all
./lab experiment dry-run <config.yaml>
./lab experiment run <config.yaml>
./lab experiment resume <run-id>
./lab experiment status <run-id>
./lab experiment summarize <run-id>
./lab report build <method>
```

只有形成具体实验事务时才创建 `experiments/<method>/`。完整 YAML 描述实验意图；根仓保留轻量
运行记录和摘要，大型日志、checkpoint、视频与数据写入
`/mnt/data/atticux/agent-workspace/<method>/<run-id>/`。

## 文档

- [`docs/AGENTS.md`](docs/AGENTS.md)：文档结构与写作约束。
- [`docs/workspace/overview.md`](docs/workspace/overview.md)：根仓边界与证据模型。
- `docs/<method>/overview.md`：method 的高层理解、非显然约束与验证边界。
- `docs/<area>/plan.md` / `log.md`：已确认的未完成事务与已验收的大改动摘要。
