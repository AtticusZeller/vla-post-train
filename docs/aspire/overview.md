# ASPIRE 概览

ASPIRE（Agentic /Skills Discovery for Robotics）用冻结的前沿 LLM 驱动 coding agent，写出并迭代 code-as-policy
机器人控制程序，把验证过的修复存成可复用的 skill。"训练"是 skill 精炼，没有梯度更新；"模型"是一个 skill 库。以下描述
转述自上游 README 与项目页，本工作区**没有**运行或复现过其中任何结果。

- **三个部分（上游描述）：** 记录感知、规划、抓取、控制调用的多模态 trace 的闭环执行引擎；按任务检索的 skill 库；
  对任务序列与控制程序做进化搜索的 `evosearch`。
- **两套 agent skill：** `iterative-debugging`（看 rollout trace、定位失败、修程序、重跑验证）和 `evosearch`，
  分别放在上游 `.claude/skills/` 与 `.codex/skills/`。仿真流程由这两套 skill 驱动，不需要上游 `AGENTS.md`。
- **评测对象：** LIBERO-Pro、Robosuite、BEHAVIOR-1K；真机是 YAM 机械臂（System 2 agent 通过 MCP 工具操作）。
  上游报告 Claude Opus 5.5 在这三个 benchmark 上的成功率为 97–100%，10 个 LIBERO-Pro 任务上随底层模型从 15% 升到 99%。
- **代码：** Python 包 `cap_harness`（`src/cap_harness/`）；`scripts/` 下是各 provider 的 bootstrap 与 System 2 启动脚本。
  `pyproject.toml` 要求 Python `>=3.10,<3.13`。

## 非显然约束

- **上游 `AGENTS.md` 是真机规则。** 它规定 agent 只能通过已配置的 `mcp__cap__*` 工具操作机器人，只适用于真机
  System 2 会话。本工作区没有改它；在 `methods/aspire` 里用 Codex 工作时它会被读到。
- **LLM 生成的代码有完整 import 权限，且没有沙箱。** 上游要求在无凭据、限制网络的隔离主机上运行，仿真 agent 不得
  接触物理硬件。
- **依赖较重。** 6 个嵌套 submodule 在 `third_party/`：LIBERO-PRO、robosuite、contact_graspnet_pytorch、sam3、
  curobo、BEHAVIOR-1K；SAM3 权重是 Hugging Face 受限仓库，需要先申请权限和 token；cuRobo 在 bootstrap 时编译。
  上游为 L40、RTX 4090、RTX 5090、RTX 5880 提供 profile，本机 RTX 4060 不在其中。
- **LLM 调用有成本。** 每次实验按上游要求要先报告 GPU、凭据、服务、预计时长、seed 划分与输出路径并等确认。

## 当前边界

只完成接入：fork、`workspace` 分支、submodule gitlink 与本文档。嵌套 submodule 未检出，没有建环境、没有取权重，
没有任何运行证据。
