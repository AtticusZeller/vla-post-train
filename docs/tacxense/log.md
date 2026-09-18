# TacXense Log

## 2026-09-17 · 切换到 feature/rlt-test，补充 RLT 理解笔记

- **背景与目的：** RLT 训练实验需要在测试分支上进行，`feature/rlt` 不是实验所用分支；同时需要
  把 RLT 子系统（两阶段架构、模型定义、训练方式、数据来源）的代码阅读结论落成文档，供后续实验
  记录引用。
- **实现思路：** 子模块 `checkout` 到 `origin/feature/rlt-test` 的新跟踪分支；`.gitmodules` 与
  `scripts/lab.py::_METHODS` 的 branch 字段必须同步改，否则 `./lab method status` 会不一致
  （见 `overview.md` 的既有约束）。RLT 理解笔记独立成 `rlt.md`，不并入 `overview.md`——该主题
  信息量较大（架构、模型定义、训练阶段、数据来源、已知不确定性），符合"一个连贯主题在
  `overview.md` 里放不下"的分文件条件。
- **组件变化：** 新增 `docs/tacxense/rlt.md`；`overview.md` 的"分支选择"一节更新为
  `feature/rlt-test` 并链接到 `rlt.md`。
- **主要文件：** `.gitmodules`（tacxense branch 字段）、`scripts/lab.py`（`_METHODS["tacxense"]`
  branch 字段）、`docs/tacxense/rlt.md`（RLT 架构/模型/训练/数据理解笔记）。
- **验证：** `./lab method status` 显示 tacxense 行为 `feature/rlt-test` / `23a62139f794` /
  clean=yes，origin 与 upstream 均为官方 URL，与 `.gitmodules` 一致。
- **未做的事：** RLT 理解笔记转述自上游代码与文档阅读，本工作区未实际运行 Stage 1/Stage 2 训练
  或真机闭环，不构成验证结论；`rlt.md` 内已注明这一点。

## 2026-09-16 · 接入 TacXense submodule，固定在 feature/rlt

- **背景与目的：** 工作区需要 Xense 的触觉感知 VLA 模型线。此前只有 WAM 方向的 `tacwam` 与
  模型侧的 `xense-openpi`，TacXense 补齐 VTLA（视觉—触觉—语言—动作）这一条。
- **实现思路：** 官方仓库直连——`origin` 与 `upstream` 同为
  `https://github.com/XenseRobotics-AI/TacXense.git`，沿用 `methods/tacwam` 先例。不能走
  `add-method` skill 默认的 fork 流程：组织策略 `members_can_fork_private_repositories` 为
  false，且该仓库 `allow_forking` 为 false，私有仓库无法 fork；`Hubo1231` 是 org member，
  对目标仓库已有 push 权限，直连即可。pin 选择 `feature/rlt` 而非默认分支 `main`，该分支即
  RL token 工作线，比 `main` 领先 72 个提交、无落后。
- **组件变化：** 新增 `methods/tacxense` submodule；`scripts/lab.py::_METHODS` 增加 tacxense
  条目；`README.md` 与 `docs/workspace/overview.md` 的 method 清单从五个更新为六个；新增
  `docs/tacxense/{plan,log,overview,cmd}.md`。**未**创建 `experiments/tacxense/`——本次是
  纯接入，没有具体实验事务。
- **主要文件：** `.gitmodules`（path/url/branch）、`scripts/lab.py`（注册表）、
  `tests/test_cli.py` 与 `tests/test_repository_contract.py`（注册表与 docs 结构断言）、
  `docs/tacxense/overview.md`（定位、环境边界、分支选择、验证边界）。
- **验证：** `./lab method status` 退出码 0，tacxense 行显示 `feature/rlt` /
  `c130ea908c63` / clean=yes，origin 与 upstream 均为官方 URL；`./lab doctor` 除
  `artifact mount`（本机 `/mnt/data` 未挂载，与本次改动无关）外全部 OK，`nested submodules`
  为 all initialized；`uv run pytest` 43 passed（含注册表、`.gitmodules` 与 focus 三方一致的
  契约断言）；`ruff check` 与 `ty check` 通过。`ruff format --check`
  报两个文件待格式化，均与本次改动无关且属既有状态：`scripts/launchers/__init__.py`
  在 HEAD 中即未格式化，`tests/test_repository_contract.py` 的未格式化行位于用户已存在的
  在途修改中，本次只新增了 `EXPECTED_METHODS` 的一行。
- **未做的事：** 没有创建 conda 环境、没有取权重、没有训练或推理证据，也没有提交 commit。
  上游声明的架构与 RLT 能力见 `overview.md`，属转述而非本工作区验证结论。
