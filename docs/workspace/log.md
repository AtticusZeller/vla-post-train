# Workspace Log

## 2026-09-03 · 重构为 Agent Research Workspace

- **背景与目的：** 仓库需要从单一研究方向扩展为覆盖 VLA、WAM 与 Agent 研究的通用工作区，并清除已经退役的实验与方法入口。
- **实现思路：** 由 Human 固定研究方向和验收边界，Agent 按 `Task = Change + Observable Evidence` 实施；根仓库只负责编排、文档和证据，method 继续保持独立。
- **组件变化：** 重写 Agent 规则与 docs 约束，明确禁止范围外改动、Agent 自行完成可运行验证，并记录常用 Skill 的触发边界；文档改为 workspace/method 分区；现役 registry 收敛为五个 method；移除退役 method 的 gitlink、本地对象缓存、专用 launcher、suite 与旧实验依赖；项目元数据和默认产物路径改用 Agent Research Workspace。
- **主要文件：** `AGENTS.md` 定义协作边界，`docs/AGENTS.md` 定义文档契约，`scripts/lab.py` 保留通用实验接口，`tests/test_repository_contract.py` 检查仓库结构一致性。
- **验证：** lock、ruff、ty 与 43 项 pytest 均通过；通用 config、method status/focus 和文本扫描通过。退役缓存经远端同步、分支/ref/reflog、孤立提交与 index 审计确认无本地唯一改动后删除。清场后观察到 TacWAM 工作树被并发快进到远端新提交，根仓 pin 仍保持原值，等待研究者决定是否同步；`lab doctor` 除本机未挂载 `/mnt/data` 外全部通过。
