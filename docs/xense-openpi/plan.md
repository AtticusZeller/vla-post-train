# xense-openpi Plan

## RL 后训练代码按层重组（`rl-exp`）

RLT 现在平铺在 `src/openpi/rlt/`，按方法组织。后续要在同一仓库复现 EXPO-FT 等真机在线 RL 算法，让它们共用机器人连接、
VLA 封装和评测，新算法需要有明确的位置。expo-ft 按角色分目录（`data/`、`networks/`、`agents/alg/`），但层之间有反向
依赖（`data/replay_buffer.py` import `agents/alg/batch_utils.py`），EXPO 专用的 `PixelEditMultiplexer` 也放在共享的
`networks/` 里，增删一个算法要动好几个目录。这里取折中：共享部分按层放，算法私有部分收进 `algos/<name>/`，只允许算法
依赖共享层，反过来不行。

放在 `src/openpi/rl/` 而不是 `packages/` 下的独立包：训练服务器用 conda 环境加 `pip install -e .` 安装，独立包要多一步
安装；分层由下面的依赖方向测试保证，效果相同。

分支：从 `feature/rlt-jax`（`3a3b5cc`）建 `rl-exp`。`feature/rlt-jax` 冻结给真机验证，验证中的修复提交在
`feature/rlt-jax` 上，再合并进 `rl-exp`。为了让这类合并能跟随改名，搬移单独成一个 commit，只改 import 和路径，不夹带
逻辑改动。本事务在 `rl-exp` 上的本地 commit 属于改动本身；push 等你要求再做。
**2026-09-30 变更：** 用户决定不再单独验证 `feature/rlt-jax`，它的两项真机检查并入「rl-exp 真机试跑」，根仓登记先切到
`rl-exp`；`feature/rlt-jax` 停在 `3a3b5cc`，不再更新。

约束：RLT 行为不变，基线是 `3a3b5cc` 上 RLT CPU 测试 85 passed、2 skipped（2026-09-29 本机实测）；机器人协议
`openpi-rlt/1`、`serve_policy.py policy:rlt`、机器人端 `--args.rlt` 的名字都不变。

不在本事务：EXPO-FT；按 `algo:` 字段分派配置和统一的 `scripts/rl/train.py`（现在只有 RLT 一个训练算法，等第二个出现
再做）；拆 collector（放在评测事务里做，评测是它的第二个使用方）。

目标布局：

```text
src/openpi/rl/
  env/protocol.py         ← rlt/env_protocol.py
  vla/frozen.py           ← rlt/vla.py
  vla/action_space.py     ← rlt/action_space.py
  algos/rlt/              ← rlt/ 其余模块与测试；policies/rlt_policy.py → algos/rlt/serving.py
configs/rl/rlt/           ← configs/rlt/
scripts/rl/rlt/           ← scripts/rlt/
```

### Task: RLT 代码搬到新布局，行为不变

**Change**

- [x] 从 `feature/rlt-jax` 建 `rl-exp`。
- [x] 搬移 commit（`60152ab`）：`git mv` 模块、测试、配置和脚本；只改 import、`_CONFIG_DIR` 这类路径常量，以及
      docstring、注释和 `examples/bi_flexiv_rizon4_rt/README.md` 里的路径。
      **执行中的修正：** 仓库 `.gitignore` 的 `env/`（虚拟环境模板规则）会让 `src/openpi/rl/env/` 里的新文件被忽略，
      `__init__.py` 当场就加不进去。保留计划的目录名，在 `.gitignore` 里加一条只针对这个目录的例外；其他 `env/` 照旧忽略。
- [x] 解耦 commit（`a894f83`）：`vla.resolve` 改为接收 `vla_config`、`vla_checkpoint`、`repo_id`，不再接收 RLT 的
      `TokenTrainingConfig`；`cache_identity`（prefix cache 的身份）移到 RLT 的 `prefix_cache`；`directory_fingerprint`
      移进 `vla/frozen.py`。不做这一步，搬到共享层的 `frozen.py` 就要反向 import `algos/rlt`。
- [x] 依赖方向测试（`src/openpi/rl/layering_test.py`）：`openpi.rl` 的共享层不 import `openpi.rl.algos`；`src/openpi` 里
      `rl/` 之外的模块不 import `openpi.rl`（`scripts/`、`examples/` 不受限）。以后每加一个算法都靠它守住分层。
      **执行中的修正：** 只检查非测试模块。共享层的 `vla/action_space_test.py` 用 RLT 的 TacXense 参照做数值对照，也测了
      RLT 的 `diagnostics.output_metrics`；测试跨层引用参照实现是合理的，挪走它们只会拆散现有对照。相对 import 也会解析
      成绝对名再检查。

**Verification**

1. [x] 按新路径跑 RLT CPU 测试：87 passed、2 skipped（85 个原有测试加 2 个依赖方向测试；skip 仍是找不到 RLinf 参照）。
2. [x] `git show -M --name-status 60152ab`：31 个非空文件全部是 `R`（相似度 86%–100%），没有 `D`；`A` 只有 4 个新的空
       `__init__.py`。
3. [x] 临时分支上改 `feature/rlt-jax` 的 `src/openpi/rlt/collector.py` 一行并提交，合并进 `rl-exp` 的临时副本：自动合并，
       改动落在 `src/openpi/rl/algos/rlt/collector.py:107`，没有重建旧目录；两个临时分支已删除。
4. [x] 三处 mutation 都让依赖方向测试失败，撤掉后通过：共享层绝对 import `algos`、共享层相对 import `..algos`、
       `openpi.transforms` import `openpi.rl`。
5. [x] `serve_policy.py policy:rlt --help`、`train_rl.py`、`train_token.py`、`precompute_prefix.py` 的 `--help` 都正常。
6. [x] ruff 0.16.9（`uv.lock` 的版本）对 39 个改动文件 check 与 format 都干净；pyright 1.1.414 在同一批文件上现在和
       `3a3b5cc` 都是 4 errors、10 warnings，去掉路径与行号后逐条相同（缺 lerobot `bi_pico4`、tacxense 运行时才导入、
       None 检查）。

**Done**

- [x] `src/openpi/rlt/`、`scripts/rlt/`、`configs/rlt/`、`src/openpi/policies/rlt_policy.py` 不再存在；新路径下原有 RLT
      测试 85 passed、2 skipped。
- [x] 第 3 项的模拟合并落在新路径上，没有冲突。
- [x] 第 4 项的检查先失败、撤掉后通过。

### Task: 实现文档写清代码组织、运行时数据流和人的流程

**Change**

- [x] method 仓库新建 `docs/rl/implementation.md`（`0a53bc3`，中文，与该仓库 `docs/` 一致），包含：
  1. 分层与依赖方向，指向依赖方向测试；
  2. 共享层和 `algos/rlt/` 各模块的职责，写到模块级，不列函数；
  3. `rlt-spec.md` 的概念对应到模块：关键阶段窗口与标签、sliding anchor 与 replay transition、MLP 表示、chunked TD
     与 UTD 节奏、phase one；
  4. 运行时数据流：机器人端与训练服务器两个进程，一轮里的消息顺序，训练发生在哪一步，产物写到哪里（`rl/<round>/`、
     `transitions/`、`events.jsonl`、W&B 三个轴）；
  5. 人的流程：操作员一轮的操作（A 开始、B 开窗、接管、B / Y 打标签、X 作废、A 结束，服务器训练时机器人归位等待）；
     研发流程：`<algo>-spec.md` → `plan.md` → 代码与本文档 → 训练 / 评测 → `experiments.md` → 下一步经确认进
     `plan.md`，并注明 spec、plan、experiments 在研究工作区 `vla-post-train` 的 `docs/xense-openpi/`；
  6. 接口与版本：机器人协议 `openpi-rlt/1`、配置位置、resume contract（`training_contract` / `OPERATIONAL_FIELDS`）、
     checkpoint 布局；训练服务器上旧路径的个人配置（`configs/rlt/*.yaml`）需要手动挪到 `configs/rl/rlt/`；
  7. 新算法接入清单：spec、`algos/<name>/`、配置示例、脚本、对照参考实现的数值测试、评测 arm、本文档对应章节。
     **执行中的修正：** 评测 arm 还不存在，文档只写现状，这一条随评测事务补进清单。

**Verification**

1. [x] 脚本抽出文档里 47 个反引号路径逐一检查：被标出的 9 个都不是仓库文件（W&B 轴名、协议名、`algos/*` 写法、特意
       提到的旧位置 `configs/rlt/`），或在其他目录下确实存在（`configs/rl/rlt/_example.yaml`、工作区的 `plan.md`、
       `rlt-spec.md`）。

**Done**

- [x] 第 3 节覆盖 `rlt-spec.md` 第 1–5 节，外加 phase one。
- [x] 路径检查没有缺失。

### Task: 根仓登记 `rl-exp`

原计划等 `feature/rlt-jax` 真机验证通过再做；2026-09-30 用户决定先登记。根仓暂存区里你的改动（`.gitmodules`、
`scripts/lab.py`、`README.md` 也在其中）还没提交，下面的登记改动只留在工作区、不暂存，和你暂存的内容分开，等你先提交
暂存区。gitlink 等试跑结束再记：试跑期间 `rl-exp` 顶上的试跑提交会被 amend，现在记下的提交之后会从 `origin/rl-exp`
上消失。

**Change**

- [x] 合并 `feature/rlt-jax` 上验证期间的修复：不需要，`feature/rlt-jax` 在 `3a3b5cc` 之后没有新 commit。
- [x] push `rl-exp` 到 origin（试跑提交 `7464fec`）。
- [x] 根仓 `.gitmodules`、`scripts/lab.py::_METHODS`、`README.md` 的 xense-openpi 行（原来写的 `main` 已过时）改为
      `rl-exp`；`docs/xense-openpi/overview.md` 的 RLT 节去掉代码路径，改为链接实现文档；`cmd.md` 换成新路径。
- [ ] 试跑结束后把 gitlink 记到 `origin/rl-exp` 上的最终提交，你要求后提交根仓。

**Verification**

1. [x] `./lab method status` 显示 xense-openpi 为 `rl-exp`（`7464fec`）、clean。
2. [x] 根仓 `tests/` 43 passed（工作区状态，含你暂存的改动）。
3. [x] `cmd.md` 的单测命令照原样运行：101 passed、2 skipped，skip 都是 `token_model_test` 找不到 RLinf 参照。

**Done**

- [ ] 根仓 gitlink 指向的提交在 `origin/rl-exp` 上。
- [x] `overview.md` 里不再有 `src/`、`scripts/` 路径。

## 算法无关的带标签评测（`rl-exp`）

现在只有 RLT 在线采集模式能打成功 / 失败标签。普通推理通道（`serve_policy.py policy:rlt`）在机器人端没有打标签的入口，
也没有统一记录；训练中途统计的成功率混着策略变化和操作员的 discard。评测要做到：冻结策略、固定次数、按键打标签，所有
方法写同一种记录。每次评测只测一个方法（2026-09-29 用户决定，不做同一 session 内交替和盲评）；比较两次评测时要看它们的
时间是否接近，环境漂移会混进差别。结果用 analyze-experiment 记进 `docs/xense-openpi/experiments.md`（各算法共用这一个
文件）。

评测走机器人会话协议，复用训练用的机器人端模式，不走普通推理通道。原因：RLT 训练是同步 chunk，actor 只在关键阶段窗口里
驾驶；普通推理通道是异步 chunk 队列，`policy:rlt` 的开关作用于整条 episode，两处都和训练条件不同，评出来的差别会混进
执行方式的差别。部署条件（异步、RTC）下的评测是另一个问题，不在本事务。

约束：评测不写 replay、不训练；RLT 训练行为不变。依赖上一个事务的新布局。

### Task: 从 RLT collector 拆出一轮会话，训练行为不变

**Change**

- [x] 新增 `openpi.rl.env.session`（`6b01a67`）：负责一轮的 reset、chunk 往返和窗口生命周期（开窗、无标签关窗、标签、
      作废、轮结束）；调用方只决定每个 chunk 的动作和 source，并消费这些事件。
- [x] RLT `collector` 改为在这些事件上构造 critical trace 和 replay 行。
- [x] `RunLogger` 移到共享层 `openpi.rl.run_logger`，日志轴改为必填的构造参数（RLT 的 round / update / chunk 留在
      `diagnostics.AXES`，评测用 `eval.AXES` 的 round / trial）。

**Verification**

1. [x] RLT 原有测试仍全部通过（本事务后全套 101 passed、2 skipped）；`collector_test` 只改了 logger 的构造（一行 import、
       一行构造），断言没动。
2. [x] `session_test` 7 个用例：chunk 中途请求开窗、接管分成多段、标签挂起时按 A、X 作废后可重新开窗、连接断开，外加
       reset 请求转发阈值与 stride、没有开窗时的标签被忽略。两处 mutation（没开窗也认标签、作废不关窗）各让一个用例失败。

**Done**

- [x] `collector_test` 的断言原样通过。
- [x] session 单测覆盖上面 5 种情形。

### Task: 评测服务端

**Change**

- [x] `openpi.rl.eval`（`2faafa0`）：arm 接口是"给定观测和窗口状态，返回一个 chunk 和 source"；一次评测只跑一个 arm；
      一个有标签的窗口就是一个 trial；不写 replay、不训练。
- [x] RLT 的 arm 放在 `algos/rlt/eval_arm.py`：`rlt` 是窗口内 actor 均值、窗口外 VLA；`vla` 是全程 VLA，即
      `FeatureExtractor` 参考块的前 C 步（`RLTPolicy` 关掉开关时返回全部 R 步）。actor 从 `rl/<round>` 或 `actor_critic_round*.pkl`
      加载；`serving.py` 拆出加载函数，评测与 serving 共用同一套 VLA 与 token checkpoint 的身份校验。
      **限制：** `vla` arm 与 RLT 共用特征计算，需要该 run 的 phase one token checkpoint，但不需要 RL checkpoint；
      还没做 phase one 的纯 VLA 基线测不了。
- [x] `scripts/rl/eval.py <rlt 配置> --exp-name <run> --arm vla|rlt [--actor <路径>] --trials N --eval-name <名字>`：
      攒够 N 个有标签 trial 后结束。输出 `<run>/eval/<名字>/trials.jsonl`（arm、轮号、标签、窗口步数、人工步数、第一个
      人工步的位置、chunk 数、墙钟时长、是否作废）和 W&B 的 `trial/*` 轴；结束时打印统计。连接断开时丢弃整轮的 trial，
      与训练一致。同名评测已存在时要 `--overwrite`。
- [x] 指标：自主成功 = 标签为 success 且窗口内人工步为 0；主指标 = 自主成功数 / 有标签 trial 数；X 作废的 trial 单独
      计数，不进分母。X 同时作废本轮已标的 trial 和正开着的窗口，与训练里 X 丢弃本轮数据一致。

**Verification**

1. [x] `eval_test` 5 个用例：两轮分别产生自主成功与带接管的失败，字段、步数、首个人工步、chunk 数、汇总与"arm 只在窗口
       内收到 `window_open=True`"都有断言；X 作废；连接断开丢整轮且不占轮号；无标签关窗不成 trial；全作废时成功率为
       NaN。mutation"作废也计数"与"标签即写入而非轮末写入"分别让 2 个与 4 个用例失败。
2. [x] `eval_arm_test`：`rlt` 在窗口内等于 actor 均值 decode 后的动作、source 为 `actor`；`rlt` 窗口外与 `vla` 窗口内外都等于
       `ref_exec[:C]`、source 为 `vla`；未知 arm 被拒。
3. [ ] 真机 smoke（你执行）：机器人端照常 `--args.rlt --args.pico4-intervention`，服务器依次跑
       `python scripts/rl/eval.py <配置> --exp-name <run> --arm vla --trials 2 --eval-name smoke-vla` 与
       `--arm rlt --trials 2 --eval-name smoke-rlt`，各自的 `trials.jsonl` 有 2 个未作废的有标签 trial。

**Done**

- [x] 第 1、2 项通过，作废不进分母、连接断开丢整轮各有断言。
- [ ] 第 3 项的 `trials.jsonl` 与终端统计一致。
- [x] 实现文档补上评测的运行时数据流、操作员流程与接入清单里的评测 arm；机器人 README 注明同一模式可接评测服务器。

### Task: 外部审查的修正

独立审查（以本 plan 为规格，读 `feature/rlt-jax..rl-exp` 的 5 个 commit）没有 blocker 和 should-fix。审查方另做了差分
测试：旧 collector（`feature/rlt-jax`）与新 collector 在 40 个随机种子、每个 6 轮（含接管、标签、作废、零长度段）上的
replay 行、指标、状态行与每个请求逐项相同，只差墙钟 `timestamp`。三条 nit 核实属实，已修（`8e3681c`）：

**Change**

- [x] `scripts/rl/eval.py` 先加载 arm 再建输出目录：原来 `--actor` 错了会留下空的 `eval/<name>/`，重跑被拦；`--eval-name`
      只允许单层名字，原来 `--eval-name ../rl --overwrite` 会删掉该 run 的 RL checkpoint。
- [x] `eval.Arm` 补上脚本握手要用的 `space`；实现文档不再说评测脚本已能按配置构造任意算法的 arm（目前只接 RLT 配置）。
- [x] `eval_arm_test` 改为对照 `Learner.mean`，不再复写同一个公式；上面 `vla` arm 的描述改正为前 C 步。

**Verification**

1. [x] 全套 101 passed、2 skipped；ruff、pyright 对改动文件干净。
2. [x] `--eval-name` 取 `../rl`、`.`、空串、`a/b` 都被拒；用找不到 VLA checkpoint 的配置跑，加载失败后没有留下 `eval/<name>/`。

**Done**

- [x] 上面两项的观察结果。

未处理（审查方标为猜想，与训练行为一致）：操作员在窗口开着、没有挂起标签时按 A，这个窗口不计 trial，也没有提示；
`layering_test` 看不到经 `importlib` 的动态导入。

## rl-exp 真机试跑

`rl-exp` 已推到 origin。末尾的空提交 `7464fec`（`test(rl): trial rl-exp on the robot`）在 commit message 里列出下面三项检查
和同步方式。试跑发现的问题在这里汇报，修正 amend 进这个试跑提交再 force-push，前面 6 个已审查的提交不动；因此机器人主机
与训练服务器用 `git fetch origin && git reset --hard origin/rl-exp` 同步，不用 `git pull`。第一次跑之前，把训练服务器上的
个人 RLT 配置从 `configs/rlt/` 挪到 `configs/rl/rlt/`，加载器不再读旧目录。

第 4、5 项原是 `feature/rlt-jax` 的真机验证（标签挂起时按 A 不丢关键阶段、窗口内不换驾驶者），2026-09-30 起改在 `rl-exp`
上做；试跑提交的 commit message 里还没有这两项，下次 amend 时补上。

### Task: rl-exp 在真机上跑通 serving、训练与评测

**Change**

- 无新改动；试跑中的修正并入试跑提交。

**Verification**（用户执行）

1. [ ] 训练服务器：`python scripts/serve_policy.py --port 8001 policy:rlt --policy.config <配置> --policy.exp-name <run>`。
2. [ ] 机器人端 `--args.rlt --args.pico4-intervention`，服务器 `python scripts/rl/rlt/train_rl.py <配置> --exp-name <run>`
       跑一轮并给一个窗口打标签。用一个可以多加一轮数据的 run；或在配置里设 `rl.token_checkpoint`，换一个新的 `--exp-name`。
3. [ ] 评测 smoke：即「评测服务端」的第 3 项。
4. [ ] 同第 2 项的设置：一轮内按 B 开窗、按 Y 标失败后立刻按 A。
5. [ ] warm_up 之后，在机器人停着等下一个 chunk 时按 B 开窗。

**Done**

- [ ] 第 1 项终端出现 "Serving RLT actor"：重组后的 VLA、token、actor 加载在真实 checkpoint 上可用。
- [ ] 第 2 项服务器终端出现 "<Label> labeled: … +N transitions"，轮末摘要正常：共享的一轮会话照旧驱动机器人。
- [ ] 第 3 项同「评测服务端」的 Done。
- [ ] 第 4 项：机器人跑满当前单元才归位，服务器终端出现 "Failure labeled: … +N transitions"，轮末摘要
      `data : +N transitions` 中 N > 0。
- [ ] 第 5 项：该窗口的每个 chunk 在服务器日志 / W&B chunk 轴上都是 actor（`use_actor=True`），没有先 VLA 后 actor。

没有覆盖：`precompute_prefix.py`、`train_token.py` 在真实数据上的运行。
