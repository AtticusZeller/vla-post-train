# TacXense Log

## 2026-09-28 · RLT phase two 规格迁到工作区，只保留方法与公式

- **背景与目的：** RLT phase two 的规格原来只在 tacxense `docs/architecture.md` § 4.49–§ 4.53，和代码细节、
  历史经过混在一起。后续实现要迁到 xense-openpi 的 `rlt-atticux`，方法层面的要求先提到工作区这一层，
  人读规格了解方法，再去看代码。
- **实现思路：** 先按 `881fbdb` 逐字迁移五节，再按内容分流：采集规则、表示、网络结构、transition、loss、
  replay 规模与更新节奏的公式留在 `rlt-spec.md`，设计理由每条只留一句；日期、bug 经过和改动原因写成本文件
  下面几条上游条目；代码对应、配置取值、schema / 协议版本不进工作区文档，仍以 tacxense `architecture.md`
  那几节和 commit message 为准。`1715544` 的两个 actor 选项作为规格文末的研究性选项，不算 baseline。
  规格按用户的原始笔记补全了 transition 字段表、ã_train 的推导、actor / critic loss 与 warmup 估算公式。
  `docs/AGENTS.md` 新增 `<topic>-spec.md` 文件类型的约定。
  用户在第 1 节补了一条规则：标签挂起时按 A，先等该标签形成完整 terminal transition，再结束本轮、提交并归位，
  避免 A 截断执行单元、丢掉已按下但未上报的标签。tacxense 当前代码是否满足另行核对。
- **组件变化：** 新增 `docs/tacxense/rlt-spec.md`；tacxense 源文档不变。`rlt.md` 删掉与规格重复的 MLP 表示、
  网络结构、replay transition、采集工作流四节，以及已被 transition 计数取代的 rollout-unit warmup 一节，只留
  insert-ethernet 采集规程；`overview.md` 链接到 `rlt-spec.md`。
- **主要文件：** `docs/tacxense/rlt-spec.md`（方法规格）、`docs/AGENTS.md`（spec 文件约定）。
- **验证：** 逐字迁移那一版与 `881fbdb` 的原文用 `cmp` 比对一致；拆分版按源文逐节改写，没有再做机器比对。
  夹爪规则对照 `examples/bi_flexiv_rizon4_rt/intervention.py`，归一化公式对照 `rlt/action_codec.py`。
  对照时发现 tacxense § 4.49「实现对应」仍写着"越过阈值且夹爪一致才接管"，与 09-22 之后的代码不符，源文未改。

## 2026-09-24 · 上游 RLT：`rlt_fast` 的 warm_up 从 600 降到 250

- **背景与目的：** 关键阶段只有 2–3 s（`L=60–90`），`C=20`、stride 2 时每个 phase 只产出 21–36 行，600 行要攒
  17–29 个 phase 才让 actor 上场。
- **实现思路：** 按实测 `L≈70`（26 行）换算，250 约为 10 个已标注 phase，回到"约 10 个 phase 后上场"的原意。
- **组件变化：** 只改配置。
- **主要文件：** `methods/tacxense/config/rlt/rlt_fast.yaml`。
- **验证：** 源文未记录验证；resume 会拒绝 `warm_up` 不同的旧 checkpoint。

## 2026-09-23 · 接管与关键阶段的组合：sliding 观测缺失 + 组合测试

- **背景与目的：** `rlt_fast`（`replay_stride=2`）真机训练在打标签后报 `Missing raw observation for
  sliding replay index 2`。触发条件是先接管、握着按 b。用户确认接管与 b 的先后、重叠都合法，已写进
  上游 § 4.49。原有测试只覆盖单一事件路径，没有把这些事件组合起来。
- **实现思路：** 先做端到端组合测试，只替换机器人、手柄和特征提取器，runner、`RealEnvAdapter.step_chunk`
  和 `OperatorSignals` 都用真实代码。oracle 从机器人侧执行日志独立计算关键阶段和应入库的 anchor。
  修复前 612 例中有 78 例失败，对应两个问题：
  1. 录制在一次调用中途打开时，stride 观测缺失（68 例）。修法：runner 在 stride>0 时总是请求观测，
     机器人只在录制段存，runner 按段分配观测。网格仍然对齐，因为非最后一段都是满 C 步，且 C 能被
     stride 整除；这一点加了断言。
  2. stride=0 时，松手恰好落在握持段边界，留下的零长度段和随后的重启各开一个 anchor，同一窗口重复
     入库（10 例）。修法：零长度单元的 anchor 由真正执行的单元替换。
- **组件变化：** runner 新增按段分配观测；机器人端只在录制段做 stride 观测；remote 校验只要求录制段的
  观测；`CriticalTrace.add_anchor` 去掉重复 anchor。wire 字段不变，语义有变化：机器人端和服务端要一起
  更新。
- **主要文件：** `methods/tacxense/src/tacxense/rlt/online_runner.py`、`remote_env.py`、`critical_trace.py`、
  `tests/test_rlt_collection_matrix.py`。
- **验证：** 组合测试 612 例全过；`test_rlt_critical_trace`、`test_rlt_window_transactions`、
  `test_rlt_remote_env`、`test_rlt_online_runner`、`test_rlt_takeover_safety`、`test_rlt_action_contract`、
  `test_rlt_actor_usage_tally`、`test_rlt_operator_signals`、`test_rlt_rtc`、`test_rlt_policy` 全过。
  本机内存 15 GB，全量 `pytest tests/` 会被 OOM 杀掉，所以没有跑全量。改动文件的 ruff 发现数和格式
  差异与 HEAD 相同，没有新增。真机未验证。

## 2026-09-22 · 上游 RLT：夹爪按手决定，接管不再要求夹爪一致

- **背景与目的：** BiPico4 无条件把两只扳机都映射到夹爪，单手接管会把另一只手的夹爪松开，夹着的东西直接掉。
  此前接管还要求手柄夹爪与机器人一致，回合结束 home 不开爪（lerobot-xense 快速路径遗漏）时会把整个摇操永久拦死。
- **实现思路：** 只有 grip 按住的手跟随扳机；另一只手在停止驱动时锁存一次机器人最近的夹爪命令，之后恒定，
  不逐帧跟随实测：夹住物体时实测停在物体宽度上，重新下发会把夹持一点点松掉。修在 intervention 而不是
  teleop，因为 teleop 只能冻结实测值，拿不到机器人的夹爪命令。夹爪基本只有全开 / 全闭两态，跳变代价小于
  拦死，所以不一致不再阻止接管，开始驱动时跳到扳机值并逐手打 warning。
- **组件变化：** `Pico4InterventionController` 增加逐手的夹爪保持与跳变告警，去掉夹爪一致性门槛。
- **主要文件：** `methods/tacxense/examples/bi_flexiv_rizon4_rt/intervention.py`。
- **验证：** 源文未记录验证结果。

## 2026-09-22 · 上游 RLT：标签后特征物化批量化，drain 不封顶，C 改回 20

- **背景与目的：** 真机评测中按下成功 / 失败后机器人长时间不动，关键阶段越长停得越久，与人类介入无关（介入只
  多一次 forward，几百毫秒）。原因是 `_materialize_sliding_features` 对每个索引逐个调用 `Policy.infer`，而输入
  管线写死 `[None, ...]`，batch 恒为 1：一次标签要串行跑约 61 次 2B VLA 前向，每次还含 `num_steps` 步
  flow-matching 去噪，GPU 大部分时间在等 kernel launch。
- **实现思路：**
  1. 加离线批量通道 `Policy.infer_batch` / `FeatureExtractor.extract_batch`，组大小 `rl.replay_feature_batch_size`，
     61 次 forward 变成 4 次。异步 learner 这天明确暂不做。
  2. 删除 `max_updates_per_train_step`。RLinf 的封顶依赖仿真里采集几乎不花钱、warmup 后有独立的 learning stage
     清欠账，真机两条都不成立；封顶的实际效果是 actor 开始驾驶时 critic 落后自己数据几千次更新，操作员从回合
     时长上看不出来。
  3. 三个真机配置（`rlt_fast`、`rlt_0916`、`insert_ethernet_0917`）当天先从 `C=20` 统一到 `C=10`，又按真机对比
     实验改回 `C=20`：`C` 就是 base policy 一次应当执行的步数，实验里 20 步最好。`warm_up` 保持 600：150 步 phase
     在 `C=20` 下 66 行、`C=10` 下 71 行，差别不足以改门槛。
- **组件变化：** 新增批量特征提取与 `replay_feature_batch_size`；`RLTScheduleConfig` 与全部 YAML 删除
  `max_updates_per_train_step`，`_updates_to_run()` 直接返回 `pending_updates`。
- **主要文件：** `methods/tacxense/src/tacxense/rlt/online_runner.py`、`methods/tacxense/config/rlt/`。
- **验证：** 源文未记录批量化的验证结果。

## 2026-09-20 · 上游 RLT：MLP 结构、replay transition 与 replay 计数三条规格确立

- **背景与目的：**
  - MLP 结构：原来的 `model.mlp_backbone` 预设（`rlinf` = tanh + critic 每层 LayerNorm + RLinf init，`tacxense` =
    ReLU + 无 LayerNorm + PyTorch 默认 init，三个真机配置都写 `rlinf` + 3×256）把激活函数、LayerNorm 位置、
    初始化三件事绑成一个名字，想单独调一件只能再加预设。
  - replay transition：`_window_row` 在采集时把 `ref_chunk` 的人工步改写成归一化人工动作（RLinf 的 human-input
    约定），`td.actor_loss` 里又 `where(mask, actions, ref)` 一次：同一个替换做了两遍，第一遍是破坏性的，VLA
    在那一步建议了什么再也读不到。
  - replay 计数：rollout unit、transition 行混用作 replay、warmup 和容量的单位。
- **实现思路：**
  - baseline 定为 2×256 ReLU、LayerNorm 只给 critic，用三个独立开关代替预设。不继续对齐 RLinf 的 tanh、从 3×256
    降到 2×256，都是为了先立一个参数最少、最好排查的参照点。`mlp_backbone` 直接删除、不留兼容值：MLP I/O 变更
    已经让所有 stage-two checkpoint 必须重建，没有需要旧预设加载的权重。
  - replay 保留原始 VLA reference，ã_train 在训练时组合，数值与原来等价，训练行为不变。当天 review 发现实现给
    RTC committed zone 加了未经批准的 BC 例外，与完整 chunk 公式冲突，已删除；记下这一点是为了防止以后把
    "actor 不拥有 committed zone 的 Q 梯度"误推成"BC 也必须忽略 committed zone 的人工动作"。
  - 字段整理：`executed_actions` 移出 replay、只留在 dump；`window_id → episode_id`、
    `recording_enabled → is_critical`，旧名不保留别名；`transition_schema_version` 抬到 4。
  - replay 统一按 transition 行计数，UTD=5、actor 每 2 次 critic 更新一次，同步采集用 `replay_stride=2`；
    之后删除 `rollout_unit_id`，replay schema 升到 5，更新预算 schema 为 3。
- **组件变化：** MLP 配置字段、replay 行结构、`TransitionBuffer` 计数与更新预算。
- **主要文件：** `methods/tacxense/src/tacxense/rlt/mlp_policy.py`、`td.py`、`replay.py`、`online_runner.py`。
- **验证：** 源文记录 replay 计数与 stride 部分 CPU / fake 验收和外部 review 通过，真机性能验证 pending。

## 2026-09-18 · 上游 RLT：同步采集状态图与 MLP 输入输出 contract

- **背景与目的：**
  - 同步采集：状态图主体由维护者 09-18 给出，09-19 问答中逐条确认补充（运动键待命、接管与 release 规则、
    长介入的 anchor 等）；09-23 又确认 b 与接管互不约束，见 09-23 条目。
  - MLP 输入输出（源文未记日期，早于 09-20 的 MLP 结构规格）：此前只把两个真机配置切到 canonical，代码仍同时
    支持 raw execution、canonical、direct、reference residual、gripper sigmoid / clamp 与 `action_scale`；同一个
    `state` 键在 MLP 中还是 raw absolute 值，canonical action 只归一化 18D TCP、gripper 保持 [0, 1]。actor 输入、
    输出和 checkpoint 的 tensor 语义因此不唯一。
- **实现思路：**
  - 采集流程中被否的方案：把介入中的静止帧从时间轴里删掉（维护者因实现成本放弃）；用单独按键进入 / 退出介入、
    松开运动键只是换手部姿势（关键阶段很少需要松手换姿势，不值得多一步操作）；只把原 chunk 起点和重启点当
    anchor（长介入只有第一段能进 replay），改为人类介入每 C 步各算一个 anchor。
  - MLP 只保留一套 quantile-delta 表示，删除 `action_space`、`actor_output_mode`、`actor_residual_bound`、
    `execution_gripper_activation`、`action_scale`；`calibrate_action_scale.py` 改为 `audit_action_range.py`。当时
    人工接管步仍把 obs 的 `ref_chunk` 换成人工动作（RLinf 约定），09-20 被 replay transition 规格取代。
- **组件变化：** `CriticalTrace` 连续时间轴与 anchor；`ActionCodec` 绑定 VLA 的 state / action quantile stats；
  checkpoint 记录 `mlp_io_version`。
- **主要文件：** `methods/tacxense/src/tacxense/rlt/critical_trace.py`、`action_codec.py`、`checkpoint_binding.py`。
- **验证：** 源文记录 MLP 输入输出的公式、输入顺序、先加噪再 clip 等有单测，真机启动未验证。

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
