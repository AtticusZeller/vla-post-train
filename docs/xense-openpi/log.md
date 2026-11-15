# xense-openpi Log

## 2026-11-15 · π*0.6 价值模型多任务预训练 $V_{\mathrm{pre}}$ 与 cylinder-stack 初始化对照（`feature/pi-star-0.6`）

- **背景与目的：** 单任务价值模型不到半个 epoch 就过拟合，用户决定做多任务预训练，并在 cylinder-stack 的同一批留出
  episode 上比较"从 $V_{\mathrm{pre}}$ 初始化"与"从头训练"。
- **实现思路：** 训练脚本接受多个数据集，各数据集等概率采样、各自留出 10% episode，验证指标取数据集平均；按留出 MAE
  存最优权重并早停；`--init-params` 从已有权重出发，步数为 0 时就是零样本评测。10 个 `Xense/*` 数据集（9 个 bi_flexiv、
  1 个 bi_elite，1130 万帧）全部按成功示范处理，return 定义不变。cylinder-stack 不进预训练。
- **组件变化：** `scripts/recap/train_value.py` 支持多数据集、`--init-params`、`--best-metric`、`--patience`、
  `--final-episodes`；新增 `src/openpi/recap/checkpoints.py`；`value_data.py` 新增 `BalancedSampler`、`Split`，并在
  episode 表不按顺序首尾相接时报错。方法仓库 `bb315b4`、`ed0e224`。
- **主要文件：** `scripts/recap/train_value.py`、`src/openpi/recap/value_data.py`、`src/openpi/recap/checkpoints.py`；
  数字、数据集表与图见 [experiments.md](experiments.md) 的预训练一节。
- **验证：** `src/openpi/recap` 29 个单测通过，三处 mutation 各让一个测试失败。预训练 `gty4r7z9` 步 12000 最优、步 17000
  早停，无 NaN 与 Traceback。cylinder-stack 上零样本 MAE 0.0526；从头 0.0156（步 1750）；微调 0.0150（步 750）。结论：
  预训练让收敛更快，最优精度没有可分辨的差别，这个结论只在纯成功数据上成立（用户判断，2026-11-15）。之后每轮两种
  初始化并列，真正的检验等有失败数据（用户决定，2026-11-15）。
- **过程中的问题：**
  - 预训练前没有数据检查这一环（用户判断，2026-11-15），以下两处都是训练时才撞上的：`cube-color-sorting-0821` 的 Hub
    仓库多一个残留的 episode 元数据文件（12 行与正式文件重复），只在训练机的副本里移开；`pick_up_cube_0713` 的
    episode 168 有 4914 帧（中位 997），把该数据集其余 episode 的 return 压到 $-0.16$ 以内，而且落在留出集里。
    这版 $V_{\mathrm{pre}}$ 用的是没剔除的数据，数据检查做好后重训。
  - 计划里"不下触觉视频"做不到：这版 LeRobot 加载时要求所有视频键的文件齐全，缺了会补下整个仓库。
  - 64 个 data worker 的视频解码器缓存只增不减，10 个数据集时涨到约 950G 后持平（上限由视频文件数决定）。
  - HF `datasets` 的 arrow 缓存默认写在训练机 30G 的根盘，一度用到 98%；本会话产生的条目已删，之后用
    `HF_DATASETS_CACHE` 指到大盘（见 [cmd.md](cmd.md)）。
  - 一次并行下载用 `rjob ... -- bash -c "<脚本>"` 启动，引号被拆开，任务日志里打出了完整环境变量；两个日志当即删除。

## 2026-11-14 · π*0.6 目标任务初始化：advantage 文本条件、return 标签与价值模型（`feature/pi-star-0.6`）

- **背景与目的：** RECAP 第二阶段需要两样东西：能读 advantage 文本条件的策略，和从示范数据训练的价值模型 $V_\ell^0$。
  本次在测试数据集 `Xense/cylinder-stack-0909` 上把这两条链路做出来。
- **实现思路：** 策略侧只改数据链，不改模型：prompt 在 `Action:` 之前插 `Advantage: positive|negative`，训练时由单独的
  变换以 30% 概率丢弃，serving 复用同一条 `model_transforms` 所以从不丢弃；开关关闭时 token 与原 π0.5 格式逐元素相同。
  价值模型是 SigLIP So400m 加 Gemma3-270M 的单个 transformer，在 CLS 位置读出 201 个 bin；return 写在数据集外的旁路
  parquet，不改原数据集。价值模型直接读 `LeRobotDataset`，不走 bi_flexiv repack 链。
- **组件变化：** 新增 `src/openpi/recap/`（return、价值模型、Gemma3 骨干、价值数据）与 `scripts/recap/`（算 return、训练、
  画 $V$ 曲线）；`Pi0Config` 新增 `advantage_conditioned`、`advantage_dropout`；`pyproject.toml` 新增可选依赖组 `recap`
  （`gemma==4.0.1`）。`codebase.md` 改为描述本分支，`rl-exp` 的那份另存为 `codebase-rl-exp.md`。
- **主要文件：** `src/openpi/models/tokenizer.py`、`src/openpi/transforms.py`（条件与丢弃）；
  `src/openpi/recap/value_model.py`、`scripts/recap/train_value.py`；结构见 [codebase.md](codebase.md)，命令见
  [cmd.md](cmd.md)，数字见 [experiments.md](experiments.md)。
- **验证：** 条件链 8 个单测通过，三处 mutation 各自让测试失败；全数据集 prompt 最长 116 token（上限 128）。return
  226,975 行与数据集一一对应。价值模型 750 步后在留出的 15 个 episode 上 MAE 0.0149、相关系数 0.962，$V$ 曲线上升并在
  末帧到 0。
  **没有做：** 策略的 smoke 训练（用户决定降低优先级；试跑时 loss 发散，重算的 norm stats 里左夹爪一维
  `q01 = q99`，用户判断是该数据集的已知问题）；训练脚本里的早停与存最优权重没有实际跑过，留给预训练事务验证。

## 2026-11-14 · π*0.6 规格记入参考实现核对与目标任务初始化的决定

- **背景与目的：** 开始实现目标任务初始化之前，把 Evo-RL、PiStar、RLinf、RECAP on YAM 的做法与规格里的待定项对齐。
- **实现思路：** 子代理静态阅读四份参考实现与 Robometer，未运行；结论与用户讨论后定稿。规格区分论文原文、参考实现
  做法与本复现的选择。
- **组件变化：** `pi-star-06-spec.md` 新增参考实现核对表、return 归一化的几种口径与数值例子（本复现先用 Evo-RL
  `legacy`）、价值模型的构成与选择、prompt 格式、第一轮全 positive 与 $V$ 曲线门禁、Robometer 不作为价值来源、数据集
  按轮编号。原先"除以 $L_{\max}$"的公式改标为用户推测，论文没有给出公式。
- **主要文件：** [pi-star-06-spec.md](pi-star-06-spec.md)；未完成的实现见 [plan.md](plan.md)。
- **验证：** 表中数值手算核对；参考实现的结论没有通过运行验证。

## 2026-10-15 · `expo-ft` 分支：EXPO-FT 的多样本采样与 RoboTwin SFT 配置

- **背景与目的：** EXPO-FT 的 learner 改用 xense-openpi（见 [expo-ft/plan.md](../expo-ft/plan.md)），需要每个观测一次
  采 N 个候选、在调用方的 `jax.jit` 里批量推理，以及 RoboTwin 单任务的 SFT 配置。
- **实现思路：** 从 `rl-exp`（`bbd1c71`）开分支 `expo-ft`。`Pi0.sample_actions` 加 `num_samples` 与 `train`：prefix 只前向
  一次，KV cache 复制给 N 条去噪序列，输出按观测分组 (b·N, H, D)；与 RTC 参数同用时报错。`Policy.infer` 加 `is_batch`
  与 `for_training`（输出留在 jax，可在调用方 jit 内用），`num_samples`、`train` 为 static；rng 判断改为 `is not None`
  （jit 内是 tracer）。`num_steps` 保持非 static，因为现有调用把它当可追踪值。`sample_actions_with_prefix` 不动（RLT 在用）。
  RoboTwin SFT 配置 `configs/_examples/pi05_robotwin_beat_block_hammer_lora.yaml`：`LeRobotAlohaDataConfig`，
  与 RoboTwin 官方 π₀.₅ 基线相同的变换，动作列 `actions`，LoRA，H=16，batch 64，恒定 2.5e-5，4,000 步。
- **组件变化：** `src/openpi/models/pi0.py`、`src/openpi/policies/policy.py`，新增 `policy_batch_test.py` 与 YAML。
- **主要文件：** 同上。
- **验证：** 服务器 CPU 上：N 样本一次调用与 N 次单样本调用逐元素一致（pi0、pi05）；在调用方 jit 内构造并调用 `Policy`
  通过；`num_samples=1` 与 `bbd1c71` 原版 8 组输出逐位相同；`cmd.md` 那组 RL 单测 107 passed、2 skipped；models 与
  policies 下 42 passed，2 个已有失败在原版上同样复现。YAML 加载与恒定学习率已核对。

## 2026-10-10 · rlt-jax 可选择 actor 训练参考输入

- **背景与目的：** 为真机对照测试恢复 `corrected` 训练输入，同时保留正在测试的 `proposal`。
- **实现思路：** 通过 `rl.input_reference` 选择条件输入，默认 `corrected`；BC target、critic 与部署输入不变。
  该字段参与 checkpoint 训练条件检查，避免两种训练方案混用。旧 checkpoint 缺少该字段时拒绝恢复。
- **组件变化：** 配置解析、learner 参数传递、actor loss 与实验 YAML；两种模式共享现有 replay。
- **主要文件：** 方法仓库 `src/openpi/rlt/config.py`、`learner.py`、`td.py`；用法见 [cmd.md](cmd.md)。
- **验证：** YAML 校验、两种输入行为与 TacXense 数值对照共 13 项 CPU 测试通过；ruff 与 diff 检查通过。
  未进行真机训练或评估。

## 2026-09-29 · RLT（JAX）接入 xense-openpi：审查参考分支并补齐规格差异

- **背景与目的：** RLT 的实现要从 tacxense（torch）迁到 xense-openpi（JAX）。用户决定用 JAX，从 `main` 拉自己的分支，
  把别人已迁的代码逐个 commit 对照 [rlt-spec.md](rlt-spec.md) 审查，合格的 cherry-pick，缺的和不合规格的自己补。
  参考代码只作参考，不向其报告问题；pi0 改动与 phase one（prefix 前向、encoder 训练）由其作者验证，本次不再验证模型前向。
- **实现思路：**
  - **起点纠正。** 起初只看了 `origin/rlt-atticux` 的 7 个 commit，以为在线部分还没迁；实际 XenseRobotics-AI 的
    `feature/rlt-hubo`（09-27～09-28）在同一 `main` 上有 22 个非 merge commit，collector、learner、同步机器人协议、Pico4 接管、
    机器人端 `rlt_mode`、在线特征、serving、checkpoint、W&B / dump 都已迁。用户改为审全部 22 个。
  - **审查结论。** 逐模块对照规格：动作表示（§2）、网络结构（§3）、actor / critic loss（§4）、sliding 网格与终止对齐、
    warm_up 门控 actor、轮末才入库、UTD 预算、actor 每 2 次 critic 更新、每轮跑满欠账都一致；Pico4 接管控制器与 tacxense
    逐行一致。发现：F1 机器人端按 A 会截断挂起标签的单元、丢掉整个关键阶段（与 tacxense 同一个 bug）；F2 不支持
    stride=0；F3 replay 行缺 `timestamp` 与 chunk 级 `source`；F4 tacxense 数值对照默认路径不对，不设 `TACXENSE_ROOT` 会静默
    skip；F5 `c52e187` 的平滑惩罚与 BC/Q 权重日程不在规格里；F6 研究性选项未迁。用户决定：F1 修；F2 不实现、规格注明；
    F3 补；F5 不接入；F6 另立事务。
  - **接入方式。** 从 `origin/main`（`6b9a30f`）建 `feature/rlt-jax`，按顺序 cherry-pick 21 个 commit（跳过 `c52e187`），保留
    原作者，问题用我们自己的 commit 在其上修。每个 commit 检出后跑当时存在的 RLT 测试。两处失败都查明：upstream 的
    `411931e` 本身是中间态（机器人端开始要求请求带 `source`，collector 下一个 commit 才发），在 upstream 原 commit 上复现
    一致；`db854e8` 起的 3 个失败来自被跳过的 `c52e187`——它不只被 learner 调用，还有一个测试用到，计划里只预料到前者。
  - **外部审查。** 独立 agent 以计划与规格为规格审 diff，没有 blocker，两条 should-fix 都复现：R1 是 F1 修复引入的回归——
    X 与 B/Y 同一次读取时，B/Y 会给正在丢弃的窗口打上永远不会上报的标签，A 随之一直等、本轮结束不了；R2 是参考代码原有
    的问题——warm_up 后 B 在服务器间隙按下，窗口第一个 chunk 由 VLA 驾驶、之后换 actor。另有 dump 字段缺测试（R4）、
    `round_id` 比其他轮号少 1（R5）、旧 checkpoint 不能恢复（R3，只记录）。用户决定：X 立即视为关窗；间隙里请求的窗口推迟到
    本 chunk 结束再开（不改协议，代价是间隙里按的 B 晚一个 chunk）；`round_id` 从 1 开始。
  - **走过的弯路。** 本机没有 lerobot-xense 环境，改用 `uv sync` 建 `.venv`（`uv.lock` 只在本地忽略）；pytorch cu128 源约
    1 MB/s、中途断过两次，加长连接超时才装完。`source` / `timestamp` 往返测试第一版用 `sample(64)`，但 `sample` 最多返回
    `len(buffer)` 行（有放回），会漏行，改为比较 `state_dict`。
- **组件变化：** xense-openpi 新增 `feature/rlt-jax`：RLT phase one 与 phase two 全套（参考分支原样）加 6 个我们的 commit——
  去掉平滑惩罚与日程的调用（`736f0d5`）、A 键在标签挂起时延后（`abe0b04`）、replay 行 `source` 与 `timestamp`（`95f3ce7`）、
  X 立即关窗与间隙开窗推迟（`fffca65`）、`round_id` 从 1 开始（`3a3b5cc`）。根仓库 xense-openpi 的登记分支从 `main` 改为
  `feature/rlt-jax`；`rlt-spec.md` 注明 stride=0 边界 anchor 只作兼容模式保留（仅 tacxense 实现）。收尾时用户决定
  RLT 主线在 xense-openpi，`rlt-spec.md` 从 `docs/tacxense/` 移到本目录，只保留这一份，tacxense 的文档改为链接过来。
- **主要文件：** `methods/xense-openpi/examples/bi_flexiv_rizon4_rt/rlt_mode.py`（机器人端按键与段）、
  `src/openpi/rlt/{collector,learner,replay}.py`（在线轮、训练、replay 行）、`.gitmodules` 与 `scripts/lab.py`（登记分支）。
- **验证：** RLT 测试（`src/openpi/rlt`、`examples/bi_flexiv_rizon4_rt`、`rlt_policy_test`，`JAX_PLATFORMS=cpu`，带
  `TACXENSE_ROOT` 让 tacxense 对照用例实际执行；按用户决定不跑 `features_test` 与 pi0 `model_test`）：参考分支 tip 基线
  75 过 2 skip，最终 85 过 2 skip（skip 都是找不到 RLinf 参照的 phase one 用例）。新增行为各有 mutation 检查：去掉 A 键
  延后、X 关窗、间隙开窗推迟、dump 字段、`round_id` 修正，对应测试都失败。改动文件 ruff 干净，pyright 与参考分支同一批
  文件结果一致。根仓库 `test_repository_contract`、`test_cli` 通过，`./lab method status` 显示 `feature/rlt-jax` /
  `3a3b5cc` / clean。只有 CPU 单测与假机器人，没有 pi05 真实前向与真机运行，真机验证见 `plan.md`。
