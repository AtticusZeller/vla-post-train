# xense-openpi Plan

## π*0.6 经验改进循环：带标记的采集、标签文件与读标签的 SFT（`feature/pi-star-0.6`）

**状态：已逐项确认，用户已说开工（2026-11-16）。代码与本地能做的验证已完成，方法仓库 `4a5c4e0`、`682473c`、
`10639c6`，外部审查的修正 `43adfc6`、`0662e99`、`cad7e92`（都已推送到 `origin/feature/pi-star-0.6`）；未勾的只剩
真机 smoke 及其验收。** 方法见 [pi-star-06-spec.md](pi-star-06-spec.md) 的「经验改进循环」。
现在的代码只能做第 0 轮：样本里没有 `advantage` 字段时一律当 positive，优势标签只在画图时算，机器人端录下来的数据
分不出哪些帧是人接管的、哪条 episode 失败了。本事务补齐第 $k\ge1$ 轮需要的四段：带标记的采集、给初始示范补标记并
合并、把优势标签存成文件并过门禁、认可后写回数据集供策略训练读取。

已定的边界（用户决定，2026-11-16，依据见规格）：

- 采集只用同步、不开 RTC 的运行方式；RTC 下的接管不在本事务。
- 接管的实现取 `feature/rlt-jax` 的 `962f953` 那一版，不沿用本分支现有的。本分支现有的版本要双手同握才接管，读不到
  机械臂位姿或手柄断开时会不声不响地继续跑策略，也没有读 A/B/X/Y 按键的代码；`962f953` 的版本单手即可接管、另一只
  手保持位姿与夹爪、手柄异常时报错终止，并带 200 Hz 的按键采样。
  这五个文件在 `origin/rl-exp`（`7464fec`）上与 `962f953` 逐字相同。
- 成功 / 失败的按键沿用 rl-exp：B 成功，Y 失败，X 作废。
- 阈值先用 PiStar 的做法（只在 rollout 的非介入帧上取分位数），Evo-RL 的做法做成一个选项留作对比。
- 接管前的帧不特殊处理，由价值模型打标签。

- 三个事实存成数据集里的逐帧列：`is_intervention`（bool）、`episode_success`（bool，同一条 episode 里取值相同）、
  `round`（int64，初始示范为 0）。逐帧列是 feature，官方的合并一定保留；LeRobot 0.5.1 的 `save_episode` 没有写自定义
  episode 元数据的入口。
- 优势标签每次尝试单独存一份 parquet，不动数据集；认可的那一份写回数据集成为一列，SFT 用带标签的数据集。
- 采集时握住 grip 只是预备，手柄移动超过 5 mm 或 3° 才接管。
- 没有标签就结束的 episode 不保存：按 X、中途按 A、到步数上限、Ctrl+C 都算。
- 按下 B 或 Y 的那一帧是这条 episode 的最后一帧，录制立即停止，之后才归位，归位过程不录。
- rollout 只录 head 与两个腕部相机，视频编码与示范相同（h264）；示范用于训练的副本去掉四路触觉视频。

不在本事务：RTC 或双频率运行方式下的接管；每轮的训练配置与超参数；$N$ 与 positive 比例的取值；价值模型在见过的数据
上标签偏弱的问题；bi_flexiv 以外的机器人；PyTorch 训练路径；修改 lerobot-xense。

### Task: 机器人端的接管换成 `962f953` 那一版

**Change**

- [x] 从 `962f953` 原样复制 `examples/bi_flexiv_rizon4_rt/` 下的 `intervention.py`、`button_edges.py`、
      `pico_button_edges_test.py`、`pico_button_monitor_test.py`、`pico_takeover_motion_test.py`。不复制 `rlt_mode.py`，
      `main.py` 里的 `--args.rlt` 也不带过来：那是 RLT 的会话协议，这里用不到。原样复制是为了以后能用 `diff` 跟上
      rl-exp 上的修复；需要的新行为都写在下一个任务的新文件里。
- [x] `main.py` 与 README 里"双手同握"的说明改成"任一只手"。普通推理加 `--args.pico4-intervention` 的行为因此改变：
      单手即可接管，手柄异常时终止而不是继续跑策略。

**Verification**

1. [x] 三个复制过来的测试在项目环境里运行。
2. [x] `git diff 962f953 -- <上面五个文件>` 为空。

**Done**

- [x] 三个测试文件全部通过，输出里的用例数与在 `962f953` 上运行时相同。
- [x] 第 2 项的 diff 为空。

### Task: 采集模式录下介入、成功 / 失败与轮次

现在 `recorder.py` 丢掉了动作里已有的 `is_intervention`；`is_episode_complete` 恒为 False，episode 只能靠步数上限或
Ctrl+C 结束，没有地方打成功 / 失败；一条结束后机械臂归位就立刻开始下一条，操作员来不及复位场景。

**Change**

- [x] `main.py` 新增 `--args.record-round <k>`，给出时进入采集模式：要求同时有 `--args.record` 与
      `--args.pico4-intervention`，与 RTC、`--args.action-hz > 0` 同用时直接退出（接管本来就不支持）。不给时，录制与
      推理的行为和现在完全一样，数据集里也不多出列。
- [x] 新文件里实现 episode 的按键控制，包在现有的环境外面：机械臂归位后等操作员按 A 才开始；B、Y 结束这一条并记下
      成功或失败；X 或中途按 A 结束且不保存；到步数上限、Ctrl+C 同样不保存。按键事件由这一层在每步取观测时取走，
      不改复制来的 `intervention.py`（它原本会把按键事件塞进发给策略服务器的观测里）。
- [x] 采集模式下握住 grip 只是预备，手柄移动超过 5 mm 或 3° 才接管；用 `962f953` 里已有的 `TakeoverMotion`。
- [x] 采集模式下录制多写三列：`is_intervention` 取自每步动作里已有的标记；`round` 是命令行给的常数；
      `episode_success` 在这一条结束时才知道，保存前填进整条。不保存的 episode 清掉缓冲，不占 episode 编号。

**Verification**

1. [x] 单测：假环境、假策略、假手柄，真的 `LeRobotDataset` 写到临时目录（小图）。依次跑：全程自主后按 B；中途接管
       若干步再松手后按 B；按 Y；按 X；到步数上限。读回数据集核对。
2. [x] 三处故意改错各让一个用例失败：不保存的 episode 也存了；`is_intervention` 错开一帧；`episode_success` 只填了
       最后一帧。
3. [ ] 真机 smoke（你执行）：策略服务照常启动，机器人端
       `python -m examples.bi_flexiv_rizon4_rt.main --args.robot-recipe <bench> --args.host <ip> --args.port <port>
       --args.record --args.record-repo-id <repo>_v1 --args.record-root <dir> --args.task "<任务>"
       --args.pico4-intervention --args.record-round 1 --args.num-episodes 4`，四条依次是：自主成功按 B、中途接管后
       按 B、按 Y、按 X。之后在该目录上跑下一个任务里的检查脚本。

**Done**

- [x] 第 1 项读回的数据集里：保存了 3 条，X 与步数上限的两条不在；每条的 `episode_success` 整条相同且与按键一致；
      `is_intervention` 为真的帧恰好是假手柄接管的那几步；接管那几步的 `action` 等于假手柄给的动作，松手后的第一步
      触发了一次新的推理。
- [ ] 第 3 项：检查脚本报 3 条 episode、1 条失败、有介入帧的 episode 1 条，没有不一致。

### Task: 初始示范补标记，与 rollout 数据集合并

LeRobot 的合并要求各数据集的 features 完全相同，初始示范不补这三列就合不进去。

> **实现中发现并已定（用户决定，2026-11-16）。** 只补三列还不够。`Xense/cylinder-stack-0909` 的 `info.json` 与
> 机器人端录制器写出的 features 有两处不同，官方合并会在 `validate_all_metadata` 上直接报错：
>
> 1. 示范多四路触觉视频（`observation.images.{left,right}_tactile_{left,right}`，400×700）；录制器只录 head 与
>    两个腕部相机，策略也只用这三路。
> 2. 示范的视频编码是 `h264`；录制器原来用 `LeRobotDataset.create` 的默认值 `libsvtav1`，`info.json` 里记成
>    `av1`。features 里视频的 `info` 含编码，编码不同也算 features 不同。
>
> 定下的做法：采集模式录 `h264`（`--args.record-vcodec`，默认 `h264`）；`mark_initial_dataset.py` 补三列的同时
> 去掉 rollout 里没有的视频流，产出只供训练用的副本，源数据集不动。没有选让采集也录触觉：要开触觉传感器并改环境
> 的观测，而策略不用触觉。

**Change**

- [x] 新增 `scripts/recap/mark_initial_dataset.py --src <数据集> --dst <新目录>`：用 LeRobot 官方的 `add_features` 给
      每一帧加 `is_intervention = False`、`episode_success = True`、`round = 0`，产出新副本，源数据集不动。Evo-RL 给旧
      数据集补列用的也是 `add_features`。
- [x] 上面定下的两处：`mark_initial_dataset.py` 加 `--remove-features <feature>…`，补列与去掉视频流用官方的
      `modify_features` 一次做完（`add_features` 本来就是它的包装），被去掉的流的视频不复制；采集模式的录制器按
      `--args.record-vcodec` 编码，普通的 `--args.record` 不变。
- [x] 合并用官方的 `merge_datasets`，不写新的合并代码，命令记进 `cmd.md`。它要是在这三列上出错，停下来报告，
      不自己写合并。命令是官方的 `lerobot-edit-dataset --operation.type merge`。
- [x] `check_dataset.py` 增加对这三列的检查：三列齐全；`episode_success` 与 `round` 在一条 episode 内取值相同；
      `round = 0` 的 episode 没有介入帧；并报每一轮的 episode 数、失败数、有介入的 episode 数与介入帧占比。数据集
      没有这三列时照旧只做原来的检查。
- [x] `compute_returns.py` 的成功 / 失败改为读 `episode_success` 列，去掉 `--success-column`（它读的是 episode 元数据
      里的列，我们不往那里写）；数据集没有这一列时仍然全部按成功算。

**Verification**

1. [x] 单测：临时目录里造一个小的示范数据集和一个带三列的小 rollout 数据集，补标记、合并，核对合并集。
2. [x] 在训练机上给 cylinder-stack 的副本补标记，跑检查脚本与 `compute_returns.py`。
       实际是在本地跑的，不是训练机（Agent，2026-11-16）：代码没提交，送不到训练机，于是把 cylinder-stack 的
       `meta/`、`data/` 和三路相机的视频取到本地。四路触觉视频没有取，本地用空文件占位——LeRobot 载入时只查文件
       在不在，补标记时这四路被去掉、不会被读。
3. [x] 两处定下的做法：单测里示范多一路视频，不去掉时官方合并拒绝，去掉后 features 与 rollout 逐项相同并合并成功；
       采集的单测核对录下的编码是 h264。再用真的 cylinder-stack 补标记副本与录制器按真机分辨率（480×640）写出的
       数据集过官方的 `validate_all_metadata`。

**Done**

- [x] 第 1 项的合并集里：示范那几条 `round = 0`、全部成功、没有介入帧；rollout 那几条的三列与合并前逐帧相同；
      `observation.state` 与 `action` 与两个源数据集逐帧相同；抽帧解码的图像与源相同。
- [x] 第 2 项：检查脚本无不一致；新的 return 文件与补标记之前算出的逐行相同。
- [x] 第 3 项：补标记后的 cylinder-stack 副本，features 与录制器写出的逐项相同，三路视频都是 h264，
      `validate_all_metadata` 通过；226,975 帧原有的列与源数据集逐帧相同。真的示范与真的 rollout 的整份合并还没跑过，
      要等第一轮采集。

### Task: 优势标签存成文件，门禁图读这份文件，认可后写回数据集

**Change**

- [x] `openpi.recap.advantage` 增加按规格打标签的函数：输入逐帧优势、是否初始示范、是否介入、positive 比例与阈值
      做法，输出逐帧标签、来源（`initial`、`intervention`、`value`）和阈值。阈值做法两种：`rollout`（默认，PiStar）
      与 `all`（Evo-RL）。
- [x] 新增 `scripts/recap/label_advantage.py`：读数据集的三列、return 文件、一个或多个 $V$ 预测文件，要求预测覆盖
      数据集的每一帧，缺帧就报错；写出标签 parquet（`episode_index`、`frame_index`、`advantage`、`positive`、
      `source`）和同名的 JSON（$N$、比例、阈值做法、阈值、各来源的帧数与 positive 占比、预测文件的路径）。
      全部帧的预测现在分在 `heldout_predictions.parquet` 与 `--final-train-episodes` 写出的
      `train_predictions.parquet` 两个文件里，所以接受多个。
- [x] `plot_value.py` 改为读标签文件，不再自己算标签：背景与边框的颜色来自文件，强制 positive 的帧用第三种颜色。
      人在门禁图上看到的因此就是训练要用的那一份。原来的 `--advantage-horizon`、`--positive-fraction` 两个参数移到
      打标签脚本。
- [x] 新增 `scripts/recap/write_advantage_labels.py --src <数据集> --labels <标签 parquet> --dst <新目录>`：先核对标签
      文件的每条 episode 帧数与数据集一致，再用官方的 `add_features` 加一列 `advantage_positive`（bool），产出带标签
      的新副本，并把标签的 JSON 拷进副本的 `meta/` 以便日后查这份标签是怎么打出来的。源数据集不动。
      代价：`add_features` 会把视频整份复制一遍，每个带标签的数据集都是一份完整副本；只有认可的那一份才写回，所以
      每轮多一份。

> **与计划的两处出入（Agent，2026-11-16）。**
>
> 1. 标签 parquet 比上面列的多两列 `return` 与 `value`（用户同意，2026-11-16）。门禁图要画这两条曲线，带上它们图
>    就只依赖标签文件，不用再回头找预测文件。
> 2. 第 2 项验证没有用整个 cylinder-stack：现有的预测只覆盖 30 条 episode（15 条留出加训练集的前 15 条），而打标签
>    要求预测覆盖数据集的每一帧。实际做法是在本地取这 30 条的帧，构造三列（前 15 条当初始示范，留出的 15 条当第 1 轮
>    rollout，其中两条各标一段介入），用 `value-cylinder-finetune-vpre-clean-trainpred` 的两个预测文件打标签并出图。
>    给整个数据集打标签之前，要先用 `--final-train-episodes` 对全部训练 episode 做一次预测。所以现在还没有哪个
>    完整的数据集写进了优势标签；只有示范的数据集也不需要写，它的每一帧按规则都是 positive，与没有这一列时的训练
>    相同。

**Verification**

1. [x] 单测：两种阈值做法下，初始示范帧与介入帧都是 positive；`rollout` 做法下第三类帧里 positive 的占比等于给定
       比例；`all` 做法下阈值等于全部帧上的分位数；预测缺一帧时报错。两处故意改错（介入帧不强制、阈值取错集合）
       各让一个用例失败。
2. [x] 用现有的 cylinder-stack 预测加上人为构造的三列跑通脚本与出图。真的带失败与介入的数据要等第一轮采集。

**Done**

- [x] 第 1 项的断言成立。
- [x] 第 2 项：JSON 里各来源的帧数之和等于数据集帧数；`value` 来源的 positive 占比等于给定比例；图上三种颜色的
      分段与标签文件一致。
- [x] 写回后的副本里 `advantage_positive` 与标签文件逐帧相同，其余列与源数据集逐帧相同；标签文件少一帧时脚本报错
      且不产出副本。

### Task: 策略训练读数据集里的优势标签列

**Change**

- [x] 打开 advantage 条件时，数据集有 `advantage_positive` 列就按它给样本填 `positive` 或 `negative`，后面的
      `DropAdvantage` 与 `TokenizePrompt` 不改。数据集没有这一列时样本里没有 `advantage` 字段，仍然全部按 positive，
      即现在第 0 轮的行为。训练用哪份标签因此只由配置里的数据集决定，不另设标签文件的路径。
- [x] 训练开始时在日志里打印这一列的 positive 占比；没有这一列时打印"全部按 positive"。选错数据集时能从日志第一屏
      看出来。
- [x] 配置示例加一份指向带标签数据集的 YAML。

**Verification**

1. [x] 单测：带 `advantage_positive` 列的小数据集，取样本并解码 prompt。
2. [x] 现有的条件链 8 个单测照旧通过。

**Done**

- [x] 标为 negative 的帧 prompt 里是 `Advantage: negative`，标为 positive 的是 `Advantage: positive`；条件被丢弃的
      样本两者都没有；数据集没有这一列时 token 与改动前逐元素相同。

### Task: 外部审查的修正

一个不带实现会话上下文的子代理以本事务和规格为准，只读审查了 `2b7bb10..10639c6`（2026-11-16）。它没有发现与计划或
规格相悖的行为；下面是它报出、经 Agent 逐条核实的问题。标签管线、训练读标签列、范围三类它查过没有发现问题。
用户随后定了两条待决的问题，并要求审查改用边界用例的测试来做，见后三条。

**Change**

- [x] 作废的 episode 的相机画面会留进下一条已保存 episode 的视频。LeRobot 的 `clear_episode_buffer` 只删 image
      feature 的临时图片，按视频录的相机不删；作废的 episode 不占编号，下一条写进同一个目录，编码时把多出来的旧帧
      一并编进去。作废的那条比下一条长时就会发生（X、步数上限、Ctrl+C 都容易满足）。训练取帧不错位，但作废的
      画面留在数据集里，合并与写回都会带走，检查脚本查不出。上游 lerobot 0.5.1 与 lerobot-xense 都复现。改法：
      采集的录制器在作废时自己删掉这几路相机的临时图片目录。这是任务二「不保存的 episode 清掉缓冲」没有做到的部分。
- [x] 补一个单测守住「按键事件不发给策略服务器」：原有的单测在去掉这一条的实现后仍然全过，因为假手柄的按键总被
      环境层先取走。实现本身没有问题。
- [x] 第二次 Ctrl+C 强制退出前先把数据集收尾（用户决定，2026-11-16：退出前文件应该收尾）。episode 进行中按
      Ctrl+C 后，机械臂归位的几秒里再按一次，程序走 `os._exit`，跳过 `finalize()`。实测（Agent，2026-11-16）：录两条
      已保存的 episode 后不调 `finalize()` 就退出，上游 lerobot 与 lerobot-xense 下数据 parquet 都读不出（没有文件
      尾），episode 元数据文件没有生成，`LeRobotDataset` 打不开；调了就正常。只按一次 Ctrl+C、或在等 A 时按，走的是
      正常收尾，不受影响。改法：SIGINT 的处理从 `main.py` 里的闭包挪成 `collection.stop_on_sigint`（`main.py` 在
      本机导入不了，闭包测不到），强制退出前先调 `finalize()`，收尾失败也照样退出。
- [x] `collection_columns.load_frames` 对缺三列的数据集报错，不再按初始示范补（用户决定，2026-11-16）。它是
      `label_advantage.py` 与 `write_advantage_labels.py` 读帧的入口；原来用普通 `--args.record` 录下的 rollout 误传
      进来会得到一份全 positive 的标签。初始示范先用 `mark_initial_dataset.py` 补三列再打标签。
      `compute_returns.py`（没有 `episode_success` 时全部按成功）与 `check_dataset.py`（没有三列时只做原来的检查）
      不变。
- [x] 用边界用例把采集和打标签再过一遍（用户决定，2026-11-16：审查靠测试暴露问题，不靠读 diff）。Agent 把每个
      用例真的跑过采集栈或标签脚本，看存下了什么：
      - 采集 14 例：归位时与等 A 时按下的 B / Y、同一步读到 Y 和 B、踩在步数上限那一步的 B、握着 grip 跨到下一条、
        接管中到步数上限或按 X 后的下一条、连按两次 B、先 Y 后 B、中途按 A 后的下一条、整次会话全部作废。只有
        「按 A 后同一次取观测里又读到 B」会存下 1 帧的 episode，其余都符合预期。1 帧的 episode 能通过检查、算
        return、打标签、写回并解码，不处理。
      - 标签 17 例：只有 rollout、全部帧都是介入、单帧 episode、`positive_fraction` 取 0 和 1、预测里有 NaN、重复
        行、缺一条 episode、全部优势相等、标签写回别的数据集、写回已有标签的数据集、给已有三列的数据集再补标记。
        该报错的都报了错，报错时没有留下半份数据集。预测里的 `inf` 不报错，$V$ 的输出有界，不处理。
      - 采集栈录下的数据集（含 1 帧的那条）接着过检查脚本、算 return、打标签、写回、读回最后一帧：全程通过。

> 另有一条 Agent 判断不用处理（Agent，2026-11-16）：`reset()` 里清掉上一条 episode 最后的夹爪指令这一行没有单测，
> 要在一条 episode 的第一步就接管才用得到，而接管至少要先握住再移动，两步之后已经有本条的指令。

**Verification**

1. [x] 采集单测加一条：每条已保存 episode 的视频时长等于它的帧数，临时图片目录里没有剩下的图片。脚本里本来就有
       「到步数上限的 13 帧作废，下一条按 Y 保存 6 帧」这一对。
2. [x] 采集单测加一条：控制器交给策略代理的按键事件恒为空，同一个按键能从环境那一侧取到。
3. [x] 两条新单测各自在去掉对应实现后失败。
4. [x] 采集单测加一条：第一条按 B 保存，第二条进行中触发一次中断，归位时再触发一次；`os._exit` 换成抛异常，
       之后不再调 `finalize()`，数据集读得出那一条 7 帧的 episode。
5. [x] 采集单测加三组按键边界：开始前按下的 Y 不给这条打标签；同一步读到 Y 和 B 以先读到的为准；踩在步数上限那
       一步的 B 照样保存。再加一条：上一条结束时还握着的 grip，在下一条里不移动就不算接管。
6. [x] 帧表单测：一列都没有、只有两列的数据集都报错；没补标记的示范报错，补过的读得出 12 帧、`round` 全为 0。
7. [x] 第 4 项去掉 `finalize()` 后失败；第 5 项的「先读到的为准」去掉对应判断后失败。
8. [x] 真信号、真 `os._exit`：单独起一个进程，装上 `stop_on_sigint`，episode 进行中与归位时各给自己发一次 SIGINT。

**Done**

- [x] 修之前第 1 项失败（6 帧的 episode 视频有 13 帧），修之后通过；审查者的复现脚本在上游 lerobot 与 lerobot-xense
      下都从 13 帧变成 6 帧。
- [x] 第 8 项在上游 lerobot 与 lerobot-xense 下进程都以 1 退出，`finally` 没有执行，留下的数据集读得出 1 条
      episode、7 帧。
- [x] 训练环境下相关各组单测 220 个通过（审查前 210 个），lerobot-xense 源码下机器人端 41 个通过、1 个跳过。
      `main.py` 在本机导入不了（缺 `flexiv_rt` 与 Pico4 的包），只过了编译、ruff 与 pyright；它调用
      `stop_on_sigint` 的那一行要到真机 smoke 才真正执行。

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
