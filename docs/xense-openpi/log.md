# xense-openpi Log

## 2026-09-29 · RLT（JAX）接入 xense-openpi：审查参考分支并补齐规格差异

- **背景与目的：** RLT 的实现要从 tacxense（torch）迁到 xense-openpi（JAX）。用户决定用 JAX，从 `main` 拉自己的分支，
  把别人已迁的代码逐个 commit 对照 [rlt-spec.md](../tacxense/rlt-spec.md) 审查，合格的 cherry-pick，缺的和不合规格的自己补。
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
  `feature/rlt-jax`；`rlt-spec.md` 注明 stride=0 边界 anchor 只作兼容模式保留（仅 tacxense 实现）。
- **主要文件：** `methods/xense-openpi/examples/bi_flexiv_rizon4_rt/rlt_mode.py`（机器人端按键与段）、
  `src/openpi/rlt/{collector,learner,replay}.py`（在线轮、训练、replay 行）、`.gitmodules` 与 `scripts/lab.py`（登记分支）。
- **验证：** RLT 测试（`src/openpi/rlt`、`examples/bi_flexiv_rizon4_rt`、`rlt_policy_test`，`JAX_PLATFORMS=cpu`，带
  `TACXENSE_ROOT` 让 tacxense 对照用例实际执行；按用户决定不跑 `features_test` 与 pi0 `model_test`）：参考分支 tip 基线
  75 过 2 skip，最终 85 过 2 skip（skip 都是找不到 RLinf 参照的 phase one 用例）。新增行为各有 mutation 检查：去掉 A 键
  延后、X 关窗、间隙开窗推迟、dump 字段、`round_id` 修正，对应测试都失败。改动文件 ruff 干净，pyright 与参考分支同一批
  文件结果一致。根仓库 `test_repository_contract`、`test_cli` 通过，`./lab method status` 显示 `feature/rlt-jax` /
  `3a3b5cc` / clean。只有 CPU 单测与假机器人，没有 pi05 真实前向与真机运行，真机验证见 `plan.md`。
