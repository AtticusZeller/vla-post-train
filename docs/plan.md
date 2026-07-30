# Development Plan

> VLA 后训练研究仓库实施计划与当前状态。

## FlowDAgger MetaWorld-12 正式实验

- 已确认 12 tasks × 3 seeds 的独立 steering-policy 协议；每个 run 使用 50 条
  adaptation rollout、4,000 BC steps、dual buffer 50/50 和每评估点 25 episodes。
- 已生成 12 份 smoke 与 36 份 formal YAML；正式汇总只在每个 task 三个 seed 完成后
  计算 task mean，并在 12 个 task 都完整时给出 macro Δ success rate。
- 已完成 12-task expert 预检、Assembly 端到端 dirty smoke、640×480 `corner`
  视频视觉验收、Explain Diff 与用户 5/5 理解门禁。
- 下一步：提交并推送 FlowDAgger method 与根仓库，使正式配置和代码可从远端恢复；
  随后启动正式 run。大型 checkpoint、日志与视频继续写入
  `/mnt/data/atticux/vla-post-train/flowdagger/`。
- 旧 Assembly batch-16 full 保留为历史单任务证据，不进入本 suite；当前正式进度以
  `experiments/flowdagger/metaworld12-report.md` 为准。

## STEAM Medium · seed 1 续训至 10k

- 从已完成的 seed 1 `global_step_1000` DCP checkpoint 恢复模型、optimizer 与
  scheduler，使用两张 H20 依次训练到 cumulative step 3,000、5,000、10,000。
- 三段训练统一把 cosine schedule 的 `total_training_steps` 延长为 10,000；这会在
  step 1,000 后重新进入延长后的学习率曲线，因此属于 continuation probe，不等同于
  从 step 0 使用 10k/30k schedule 的官方 full run。
- 每个目标 checkpoint 完成后立即在固定 eval seed 0 上评测 100 回合，并与原始
  40% baseline 对比。三个 checkpoint 均保留，用于判断能否稳定超过 70%。
- 根配置为
  `experiments/rlinf/configs/libero10_task0_medium_steam_seed1_continue10k_2gpu.yaml`；
  输出写入新的 formal run artifact，不改写原始 step 1,000 实验。
- 2026-07-30 首次 continuation 已验证恢复链路并运行至 step 1243，随后按用户要求
  为 FlowDAgger 释放两张卡而中断；未到 3k checkpoint，后续从 step 1000 重启。

## 目标

在 `/root/vla-post-train` 建立私有研究工作区。根仓库只管理 method submodule、实验配置、
运行证据、汇总文档和 Agent workflow，不包含算法源码，也不建立覆盖所有方法的训练环境。

## 最终结构

```text
vla-post-train/
├── AGENTS.md / CLAUDE.md
├── README.md / cmd.md / lab
├── pyproject.toml / uv.lock
├── .codex/skills/{add-method,run-experiment,summarize-experiment}/
├── methods/{flowdagger,dsrl-pi0,expo-ft,rlinf,starvla,lerobot}/
├── scripts/
│   ├── lab.py
│   ├── config.py / process.py / run_record.py / monitor.py / report.py
│   └── launchers/{command,flowdagger,dsrl_pi0,rlinf}.py
├── experiments/<method>/{runbook.md,report.md,configs/,runs/}
└── docs/{plan,architecture,log,bug,cognitive-debt}.md
```

## 已确认的设计

### 仓库与依赖

- 四个首期 method 均使用 HTTPS 用户 fork submodule，并固定准确 gitlink：
  FlowDAgger `dev`、DSRL π0 `dev`、RLinf `personal-dev`、StarVLA `starVLA_dev`。
- `origin` 指向用户 fork，`upstream` 指向官方仓库。未公开算法修改应进入普通私有 mirror，
  不得推送公共 fork。
- 所有外部算法、复现、framework 和 benchmark 代码统一放 `methods/`。自研方法从第一天
  起也是独立私有仓库。
- 第三方实现保留自身依赖闭包。首期不单独接入 OpenPI 或 LIBERO，也不为去重而修改嵌套依赖。
- 根仓库使用 Python 3.12 + uv；训练环境由各 method 自行维护。
- StarVLA、LeRobot 和 RLinf 标记为 framework。LeRobot 使用用户 fork 的干净
  `workspace` 分支，旧 `dev` 历史保持不变；仅接入 framework 时不创建实验目录。
- 首期之后新增的 method 沿用同一约定：LeRobot（framework，`workspace`）和
  EXPO-FT（method，`dev`，fork 自 `pd-perry/expo-ft`）。两者当前只固定代码版本，
  尚未创建 `experiments/<method>/` 或运行手册。

### 配置与启动

- YAML 使用 `schema_version: 1`。根层只解释 `id`、`method`、`repository`、
  `environment`、`runtime`、`tracking`，`native` 由方法 launcher 解释。
- 通用 launcher 只接受 argv 列表，不执行 shell 字符串。
- FlowDAgger 入口为 `train_flowdagger.py`；DSRL 为
  `python -m examples.launch_train_sim`；RLinf 为
  `run_libero10_task0_comparison.sh`。
- `lab` 只进入根目录并执行 `uv run python -m scripts.lab`。Python 负责校验、snapshot、
  进程、W&B 和报告更新。
- `experiment run` 前台执行，实时 tee 外部 console log，并在正常退出、异常或信号时补全
  `run.json` 与终态 summary。长跑由 Skill 放入 tmux。
- `resume` 只有在 launcher 明确声明支持时才执行；否则不创建任何新状态。

### 正式运行与证据

- 正式运行要求根 config 与 method code 均已提交、工作树干净，并能从配置的远端恢复。
  smoke/debug 可显式允许 dirty，但不能进入正式结论。
- `run.json` 记录 config 哈希、根和 method revision、cwd、argv、环境、主机/GPU、时间、
  PID、退出码、信号、产物路径和明确的 W&B run URL。
- 历史聚合实验使用 `historical: true` 与 `code_revisions[]`。未知值保留 `null` 并写入
  `unknown_fields`，不伪造时间或单一 revision。
- `summary.json` 统一包含 status、`primary_metrics[]`、resources、evidence 和
  method-specific results。W&B 只查询配置列出的 run，优先 summary；GPU 资源来自 system
  stream；本地退出码和 traceback 优先于 W&B 状态。
- `report build` 只替换 `report.md` 的标记表格，保留人工结论和证据边界。
- 新产物写入 `/mnt/data/atticux/vla-post-train/<method>/<run-id>/`；历史记录直接引用旧路径，
  不复制 checkpoint、视频或完整日志。

### 文档与 Agent workflow

- 根 `AGENTS.md` / `CLAUDE.md` 管跨仓库规则并保持字节一致；method 规则保留在其独立仓库。
- 方法级 `runbook.md` 维护环境、数据、原生命令、smoke/short/full 门槛、恢复、资源与故障。
- 方法级 `report.md` 汇总当前结论、配置比较、失败、资源、证据边界和下一步。
- `.codex/skills/run-experiment` 与 `summarize-experiment` 只表达英文 workflow，调用根
  `lab` 和 runbook，不复制确定性 Python 逻辑。
- `.codex/skills/add-method` 负责 fork/upstream、submodule、角色、Agent 分层和远端
  可恢复性；method Agent 文件只保留仓库专属规则，不复制根托管块。
- 论文笔记继续放 Obsidian；无官方实现的方法只在独立 repo 留下实现所需最小上下文。

## 历史迁移范围

- FlowDAgger：smoke、batch-64 失败 short、batch-16 short、batch-16 full；full 保留每个
  checkpoint 的 25 回合结果，修正“仅 5 回合”的过时描述。
- DSRL π0：smoke、10k、500k、初始化失败；500k 代码基线为
  `7f48937d4553e95244cd81c79236a3256df80597`，其他未知 revision 不推测。
- RLinf：MVP 与 medium 聚合实验；保留 source summary 的全部方法指标，medium 用多个已知
  code revision 和 stage W&B URL 表达迁移与恢复事实。

## 实施状态

- [x] 新建本地 Git / uv 项目并接入四个 submodule；
- [x] 更新并推送四个 method 的 Agent 基线；
- [x] 生成根 Agent 托管块与 VLA 专属规则；
- [x] 实现 CLI、schema、launchers、运行记录、W&B 汇总和标记表格更新；
- [x] 迁移 9 份配置与 10 条历史 run；
- [x] 创建三份 runbook 与方法级报告；
- [x] 创建并验证两个本地 Skill；
- [x] 完成 20 个单元测试与全量静态/CLI 验证；
- [x] 完成用户验收与 Explain Diff 五题理解门；
- [x] 创建私有 GitHub 远端；
- [x] 推送根提交并验证 authenticated recursive clone。

## 当前研究决策

- SARM / RA-BC 的 LIBERO clean-expert 验证暂缓，不保留未执行的实验草案；当前两卡预算
  已完成 STEAM Medium 的第二个训练 seed，后续优先用于 RL Token 长跑。
- STEAM Medium seed 1 使用与历史 seed 0 相同的 30 条 SFT、256 条固定 rollout、
  500-step ensemble value 和 1,000-step CFG；评测固定为 seed 0，并比较 step
  500/1,000 与同一 seed 0 baseline。已完成：baseline 40%、STEAM step 500 51%、
  step 1,000 66%；该结果仍是单任务、单训练 seed 的方向性证据。当前在 1,000 steps
  收尾；论文使用 30,000-step policy optimization，故不声称已经训练饱和。
- RLToken ManiSkill Stage 2 的 12 小时运行结束于 learner update 25,200，
  ``ready_for_online=0``，没有跨过 30,000-update warmup；此前“效果一般”的判断撤销。
  5,000-step unlimited run 仅用于验证官方参数和耗时，随后按用户决定中止。当前采用
  100-step progressive baseline：复用 Stage 1 step 2,000，保持官方 update cadence、
  critic:actor 和 BC/Q schedule，将 replay/warmup 缩为 5,000/10,000，使用 64-env
  固定评测每 20 steps 输出逐步结果；不设置墙钟限制。

## Framework 扩展状态

- [x] 清理四个旧 fork 的重复 Agent 托管块和纯空模板；
- [x] 从官方 LeRobot `main` 创建并推送 fork `workspace` 分支；
- [x] 添加 `methods/lerobot`，不创建实验配置或运行入口；
- [x] 标注 StarVLA、LeRobot 和 RLinf 的 framework 角色；
- [x] 创建 `add-method` Skill 并记录 framework 配置命名；
- [x] 完成全量 Agent、Skill、CLI、测试和递归恢复验证；
- [x] 完成用户验收与 Explain Diff 五题；
- [x] 提交并推送根 gitlink 与工作区更新。

## 验收

最终必须通过 ruff format/check、ty、pytest、全部配置校验、三个代表 dry-run、根 Agent
检查、三个 Skill 校验、method Agent 去重和大文件排查。推送后在 `/tmp` 做 authenticated
recursive clone，确认五个 gitlink 均可恢复。本任务不运行新的 GPU 实验或 LeRobot 代码。
