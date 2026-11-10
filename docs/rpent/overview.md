# RPent 概览

RPent（Recursive Physical Agent）是 RLinf 组织的具身 agent 框架：用 LLM agent 做规划，调用冻结的 VLA 或其他动作
原语执行，靠记忆和反思在与物理世界的交互中积累能力。上游强调 service-oriented、standardized、composable 的设计。
以下描述转述自上游 README、`AGENTS.md` 与 `pyproject.toml`，本工作区**没有**安装或运行过它。

- **与 RLinf 的关系：** RPent 不自带训练栈，机器人的 Env 与 VLA 复用 RLinf 的实现，RPent 只写薄适配。`pyproject.toml`
  的 `rlinf` extra 通过 git 依赖固定 `RLinf/RLinf` 的 `release/v0.4`。本工作区的 [`methods/rlinf`](../rlinf/overview.md)
  是另一个 revision，两者不保证一致。
- **代码结构（上游 `AGENTS.md`）：** `rpent/planner`、`session`、`prompt` 管规划与执行会话；`tools`、`memory` 管工具与观察、
  记忆；`robots/<robot>/` 放各机器人集成（libero、robocasa、robotwin、franka、dual_franka、yam、robodojo）；
  `cli`、`dashboard`、`evaluation` 是入口与结果。
- **评测对象（上游声明）：** LIBERO、LIBERO-PRO、RoboCasa365 Target50、RoboTwin C2R；真机有 Franka 单臂与双臂。上游报告
  Codex / GPT-6 Astra 在 LIBERO-PRO 全部八个 suite 上 92.63%（741/800）。
- **安装按场景分 extra：** `.[libero-pro]`（推荐默认）、`.[robocasa]`、`.[robotwin]`、`.[franka]`。Python
  `>=3.10,<3.13`。任务记忆来自 Hugging Face 数据集 `RLinf/RPent-memory`，跟随当前分支、没有固定 revision。
- **上游 agent 规则：** `AGENTS.md` 是开发约定（模块归属、接口契约、测试与 PR），不是真机操作规则；
  `.agents/skills/` 提供 `review-pr`、`docs-check`、`verify-change`、`add-robot` 四个 skill。

## 非显然约束

- 上游另有 `release/v0.1` 与 `reproduce/{libero,robocasa,robotwin}` 分支。本工作区固定 `workspace`（即 `main` 的 `ed6b922`），
  不是任何一个复现分支；要复现论文数字时需要先核对该用哪个分支。
- 记忆数据不固定 revision，同一代码在不同时间读到的记忆可能不同，对比实验前需要先记下数据集 revision。

## 当前边界

只完成接入：fork、`workspace` 分支、submodule gitlink 与本文档。没有建环境、没有取权重和记忆数据，没有任何运行证据。
