# TacXense RLT phase two 规格

RLT phase two 的方法规格：采集流程、MLP 表示与结构、replay transition、replay 规模与更新节奏。
实现要满足这里的规则；规格的演变历史见 [log.md](log.md)。RTC 模式不在本规格范围内。

来源：tacxense `docs/architecture.md` § 4.49–§ 4.53（`881fbdb`），依次对应本文第 1–5 节；代码对应与配置
取值仍在那几节。文末「研究性选项」来自 `1715544`，不属于 baseline。

## 1 同步采集工作流

```text
Episode Start
    │
    ▼
BASE VLA
Non-critical phase
不进入 Replay
    │
    │ 到达关键阶段，按 critical-phase 键 b（Pico B）
    │   - 在 chunk 中途按下时，从下一个 chunk 起才算关键数据
    │   - b 与 Human takeover 互不约束、先后任意：非关键阶段可以接管；握着接管不松手时
    │     也可以按 b。握着期间人类 step 按 C 步切成连续的段，b 从下一段的起点起算，
    │     这一段起点就是关键阶段第 0 步
    │
    ▼
══════════════════════════════════════
        Critical Phase Start
══════════════════════════════════════
    │
    ├─────────────────────────────────────────┐
    │                                         │
    │ Warmup                                  │ Online
    │                                         │
    ▼                                         ▼
BASE policy                               RL Actor
BASE chunk                               Actor chunk
    │                                         │
    │   - Warmup / Online 不由操作员控制：replay 达到 rlt_schedule.warm_up 后触发训练，
    │     本轮更新完成后，下一轮开窗由 actor 执行，没有额外的更新次数门槛。
    │     replay 只在 round commit 时增长，所以切换落在轮边界，一个窗口内不会换驾驶者
    │                                         │
    │             正常执行                    │
    └───────────────┬─────────────────────────┘
                    │
                    │ 每个合法 anchor 构造
                    │ C-step Replay Transition
                    ▼
                Replay Buffer


════════════ Human Intervention ════════════

BASE / Actor 正在执行一个 chunk：

P0 P1 P2 P3 P4 P5 P6 P7 P8 P9
         │
         │ Human takeover
         ▼

真实执行轨迹变成：

P0 P1 P2 | H3 H4 H5 H6 H7 | P'0 P'1 ...
          Human control        ↑
                              Human release
                              Policy Restart


Human takeover：
    └─ 可以在 chunk 内立即覆盖 policy，不需要等待原 chunk 执行结束
    - 按住运动键（SDK grip）只是待命，policy 继续执行。任一手柄相对按下时刻位移 ≥ 5 mm
      或转角 ≥ 3°，就从这一步开始算 Human takeover（夹爪键 SDK trigger 的变化不算运动）
    - 夹爪按手分别决定：只有 grip 按住的那只手，夹爪跟随自己的扳机
      （1 − trigger × width）；另一只手的夹爪保持机器人最近一次收到的夹爪命令
      （还没下发过则取实测），一直保持到它自己的 grip 按下为止
    - 夹爪开 / 闭不是接管的前置条件：某只手开始驱动时，它的夹爪立刻跳到扳机值；
      跳变跨过开 / 闭时打 warning
    - 接管后以接管时刻机器人的实际位姿为起点，按手柄的相对运动控制，不下发绝对位姿
    - 介入中手没动时机器人不动；这些静止帧仍记为人类 step

Human release：
    └─ 原 policy 尚未执行的 remainder 直接废弃
       ↓
       获取当前 observation
       ↓
       重新推理 BASE / Actor
       ↓
       建立新的 Policy-Restart Anchor
       ↓
       生成新的 policy chunk P'
    - 松开运动键即 Human release：intervention 结束，policy restart
    - 松开时手柄姿态与夹爪都应相对静止：松开前约 0.2 s 内手柄位移 ≥ 5 mm / 转角 ≥ 3°，
      或任一只手夹爪开 / 闭翻转过，打 warning；只告警，release 照常发生
    - 按下运动键后没有真正接管（运动没达到阈值）就松开，不算 release，也不重新推理
    - 不设单独的"进入 / 退出 intervention"按键


════════════ Replay 构建：边界 anchor（replay_stride=0）════════════

replay_stride>0 时动作执行和连续时间轴不变，anchor 改为第 5 节的 phase-relative 均匀网格，
restart / human 边界不再额外增加 row。

Anchor A：原 policy chunk 起点
Anchor B：Human release 后的 policy-restart 起点
人类介入超过一个 chunk 时：人类介入所在的第一个 chunk 是一个 anchor，此后每 C 个人类 step
各算一个 anchor

例如 C = 10：

真实执行：
step:    0 1 2 3 4 5 6 7 8 9 10 11 ...
source:  P P P H H H H H P'P'P' P' ...
                         ↑
                  Restart Anchor

Transition A：(s0, [P P P H H H H H P' P'], r0:9, s10)    source = MIXED
Transition B：(s8, [P' × 10], r8:17, s18)                  source = BASE / RL

Transition 可以重叠：Human release 后的新 policy step 既补满前一个 MIXED transition，
又从 restart anchor 开始形成新的 transition。

长介入（C = 10，第 3 步接管、第 23 步松手）：
  anchor = 0、10、20（人类段）、23（restart）
  transition = [0,10)、[10,20)、[20,30)、[23,33)
  其中 [20,30) 由 H20～H22 与 P'0～P'6 组成
s10、s30 这类落在 chunk 中途的观测，由机器人在执行 P' 时按需补采


════════════ 核心原则 ════════════

真实环境时间轴永远连续：P → HUMAN → P' → ...，不存在"空 step"。


════════════ Critical Phase End ════════════

BASE / RL → Human intervention（可选）→ Policy restart（可选）→ Success / Failure 标记
→ Critical Phase End

Critical Phase 的结束必须伴随明确的 Success / Failure reward label，最后有效的 replay window
包含 terminal reward：[ ... BASE / RL / HUMAN ... | reward ]，done = True

- 按下 Success / Failure 后，当前执行单元跑满 C 步才结束
  （policy chunk 是 C 步，人类段是 C 个人类 step）
- 如果这个单元被 Human release 提前打断，重启的 P' 仍属于关键阶段，P' 跑满后才结束
- 标签挂起时按 A，先等待该标签按上述规则形成完整 terminal transition，
  再结束本轮、提交已确认窗口并归位。
  这样避免 A 抢先截断执行单元，清除已按下但尚未上报的 Success / Failure 标签，
  导致该关键阶段的数据无法入库。
- terminal 窗口就是最后这个单元的 anchor 窗口：最后一步 reward 为 1（Success）或
  0（Failure），done = True
```

代价：重叠让同样采集时长产生更多 transition，每单位真实时间的更新预算随之增加；标签要等完整执行单元结束
才生效，若被 Human release 打断则等重启的 P' 跑满，期间机器人继续执行。

## 2 MLP 输入输出表示

phase two 只用一套表示，数值尺度全部由 frozen VLA checkpoint 自带的 quantile stats（$q_{01}$ / $q_{99}$）固定，
不从在线 replay 重新估计。归一化：

$$
\operatorname{norm}(x)
=
\operatorname{clip}\!\left(
2\,\frac{x-q_{01}}{q_{99}-q_{01}}-1,\;-1,\;1
\right)
$$

state 用 state stats，action 用 action stats：

$$
\tilde{\mathbf{s}} = \operatorname{norm}_{\text{state}}(\mathbf{s}),
\qquad
\tilde{\mathbf{a}} = \operatorname{norm}_{\text{action}}\!\left(\Delta(\mathbf{a};\mathbf{s})\right)
$$

其中 $\Delta$ 把手臂 TCP（位置与 rot6d）写成相对当前 state 的 delta，夹爪保持 absolute opening：

$$
\Delta(\mathbf{a};\mathbf{s})_{\text{tcp}} = \mathbf{a}_{\text{tcp}} - \mathbf{s}_{\text{tcp}},
\qquad
\Delta(\mathbf{a};\mathbf{s})_{\text{gripper}} = \mathbf{a}_{\text{gripper}}
$$

actor 是固定方差的 Gaussian，均值 $\boldsymbol{\mu}$ 是 MLP 最后一层的线性输出：

$$
\boldsymbol{\mu} = f_\theta\!\left(\left[\,\mathbf{z}_{\text{rl}},\;\tilde{\mathbf{s}},\;\tilde{\mathbf{a}}^{\text{ref}}_{0:C}\,\right]\right)
$$

$$
\text{训练：}\ \mathbf{a} = \operatorname{clip}(\boldsymbol{\mu} + \sigma\boldsymbol{\epsilon},\,-1,\,1),\ \boldsymbol{\epsilon}\sim\mathcal N(0, I)
\qquad
\text{部署：}\ \mathbf{a} = \operatorname{clip}(\boldsymbol{\mu},\,-1,\,1)
$$

执行时先做 inverse quantile 得到物理 TCP delta 与夹爪 opening，TCP delta 加回当前 raw state，得到 absolute
chunk 交给 absolute-target controller。controller 收到 absolute chunk，actor 的动作空间仍是 delta。

- proprio 的语义是当前 absolute state，只是做了归一化；raw state 单独保留给动作编解码。
- reference、人工执行动作、replay 动作与 BC target 都走同一个公式并 clip 到 $[-1, 1]$：critic 和 BC 看不到
  actor 做不出的值。
- reference dropout 只清零 actor 输入里的 reference，BC target 保持原值。

代价：proprio 与 VLA 自己看到的不同（VLA 的归一化不 clip）；超出 $q_{01}$/$q_{99}$ 的人工纠正在 BC target 里
被截断；clip 住的 rot6d 分量解码时重新正交化，旋转会有偏差。不采用"只 clip actor 输出、输入不 clip"：critic /
BC 会拟合 actor 永远做不出的动作。

## 3 MLP 网络结构

| 项目 | 配置 |
|---|---|
| 输入 | `[z_rl, proprio, ref_chunk[:C]]` 直接 concat（表示见第 2 节） |
| Actor 主干 | 2 × 256 |
| Critic 主干 | Twin-Q，每个 Q 网络 2 × 256 |
| 激活函数 | ReLU |
| Actor LayerNorm | 默认关闭 |
| Critic LayerNorm | 默认开启 |
| Actor 输出 | 线性输出 action chunk 均值 → Gaussian 采样 → clip[-1, 1] → denorm |
| Critic 输出 | 线性标量 $Q(s,a)$，不加激活 |

```text
actor:  [z_rl, s_prop, a_ref] → Linear(256) → ReLU → Linear(256) → ReLU → Linear(C*d)
critic: [z_rl, s_prop, a]     → Linear(256) → LayerNorm → ReLU
                              → Linear(256) → LayerNorm → ReLU → Linear(1)
```

- ReLU：没有饱和区，看 grad_norm 和死单元就能判断训练是否还在动。
- LayerNorm 只给 critic：TD 目标在移动，Q 的输入还带着 actor 正在变化的动作；actor 的输入全是固定统计量
  归一化后的量，尺度已经稳定。
- actor 输出头用很小的初始化，第一批动作落在归一化零点附近，actor 第一次上机时只轻微偏离 reference。
- 激活函数、actor LayerNorm、critic LayerNorm 是三个独立开关。训练不稳时先打开 actor LayerNorm；只有 2×256
  仍拟合不上 BC 目标并有证据指向容量不足时，才加宽。

## 4 Replay transition

原论文将一条 transition 简写为：

$$
\left\langle
\mathbf{x}_t,\;
\mathbf{a}_{t:t+C-1},\;
\tilde{\mathbf{a}}_{t:t+C-1},\;
r_t,\;
\mathbf{x}_{t+1}
\right\rangle
$$

论文在算法中用的是 chunk-level 简写。采用 environment-step 索引时，为避免歧义统一写为：

$$
T =
\left(
\mathbf{x}_t,\;
\mathbf{a}^{\mathrm{exec}}_{t:t+C-1},\;
\mathbf{a}^{\mathrm{ref}}_{t:t+C-1},\;
\mathbf{r}_{t:t+C-1},\;
\mathbf{x}_{t+C},\;
\mathbf{a}^{\mathrm{ref}}_{t+C:t+2C-1},\;
\mathrm{done},\;
\mathbf{m}^{\mathrm{human}}_{t:t+C-1}
\right)
$$

| 字段 | 含义 | 主要用途 |
|---|---|---|
| $\mathbf{x}_t$ | 当前 RL state | Actor、Critic |
| $\mathbf{a}^{\mathrm{exec}}_{t:t+C-1}$ | 实际执行的 action chunk | Critic |
| $\mathbf{a}^{\mathrm{ref}}_{t:t+C-1}$ | VLA 原始 reference chunk，始终保留原值 | Actor |
| $\mathbf{r}_{t:t+C-1}$ | chunk 内的 reward sequence | Critic TD target |
| $\mathbf{x}_{t+C}$ | chunk 执行后的 next state | Critic TD target |
| $\mathbf{a}^{\mathrm{ref}}_{t+C:t+2C-1}$ | next state 对应的 VLA reference chunk | 计算下一动作 $\mathbf{a}'$ |
| $\mathrm{done}$ | terminal 标志 | 控制是否 bootstrap |
| $\mathbf{m}^{\mathrm{human}}_{t:t+C-1}$ | human intervention mask | 构造训练时的 reference / BC target |

step 层面怎么填进一个 chunk（anchor 窗口、$\mathbf{m}^{\mathrm{human}}$ 的产生）由第 1 节规定。

### 4.1 Human intervention

replay buffer 中始终保留

$$
\mathbf{a}^{\mathrm{ref}} = \mathbf{a}^{\mathrm{VLA}}
$$

以及 $\mathbf{a}^{\mathrm{exec}}$ 与 $\mathbf{m}^{\mathrm{human}}$。在人类接管的位置：

$$
\mathbf{a}^{\mathrm{exec}} = \mathbf{a}^{\mathrm{human}}
$$

训练 actor 时，根据 intervention mask 动态构造实际使用的 reference，不在采集时替换：

$$
\boxed{
\tilde{\mathbf{a}}^{\mathrm{train}}
=
\left(1-\mathbf{m}^{\mathrm{human}}\right)
\odot \mathbf{a}^{\mathrm{ref}}
+
\mathbf{m}^{\mathrm{human}}
\odot \mathbf{a}^{\mathrm{exec}}
}
$$

其中 $\odot$ 表示逐元素乘法。因此人类介入位置 $\tilde{\mathbf{a}}^{\mathrm{train}} = \mathbf{a}^{\mathrm{human}}$，
未介入位置 $\tilde{\mathbf{a}}^{\mathrm{train}} = \mathbf{a}^{\mathrm{VLA}}$。

这样既符合原论文"human intervention 替换 reference"的训练逻辑，又保留了原始 VLA reference：可以分析 VLA
action 与 human correction 的差异，也能在不重采数据的前提下改变 reference 的构造方式。

### 4.2 Actor loss

actor 训练使用 $(\mathbf{x}_t,\ \tilde{\mathbf{a}}^{\mathrm{train}})$。当前 actor 生成：

$$
\mathbf{a}_\theta
\sim
\pi_\theta
\left(
\cdot
\mid
\mathbf{x}_t,\tilde{\mathbf{a}}^{\mathrm{train}}
\right)
$$

$$
\boxed{
\mathcal{L}_\pi
=
-Q_\psi\left(\mathbf{x}_t,\mathbf{a}_\theta\right)
+
\beta
\left\|
\mathbf{a}_\theta-\tilde{\mathbf{a}}^{\mathrm{train}}
\right\|_2^2
}
$$

$Q_\psi(\mathbf{x}_t,\mathbf{a}_\theta)$ 是 critic 网络输出的标量。actor 受两种监督：critic 对 actor 动作的评价，
推动 actor 选择更高 Q 的动作；$\tilde{\mathbf{a}}^{\mathrm{train}}$ 作为 BC / reference 约束。

> [!note]
> actor 的 RL loss 不直接使用 replay 中的 $\mathbf{a}^{\mathrm{exec}}$ 作为动作监督。只有发生 human intervention
> 时，$\mathbf{a}^{\mathrm{exec}}$ 才会通过 mask 进入 $\tilde{\mathbf{a}}^{\mathrm{train}}$。

- actor 的条件输入也用 $\tilde{\mathbf{a}}^{\mathrm{train}}$。已知副作用：人工步的条件输入与 BC target 相同，
  actor 有"把输入抄到输出"的捷径，靠 reference dropout 缓解。另一种做法（输入保持原始
  $\mathbf{a}^{\mathrm{ref}}$、只有 BC target 用 $\tilde{\mathbf{a}}^{\mathrm{train}}$）见文末研究性选项。
- 公式对完整 chunk 生效。RTC 的 committed 段只影响 Q 输入的拼接，不改变 actor 条件输入或 BC target。

### 4.3 Critic loss

critic 使用：

$$
\left(
\mathbf{x}_t,\;
\mathbf{a}^{\mathrm{exec}}_{t:t+C-1},\;
\mathbf{r}_{t:t+C-1},\;
\mathbf{x}_{t+C},\;
\mathbf{a}^{\mathrm{ref}}_{\mathrm{next}},\;
\mathrm{done}
\right)
$$

chunk return：

$$
R_t^{(C)}
=
\sum_{i=0}^{C-1}
\gamma^i r_{t+i}
$$

下一动作由 actor 根据 next state 和 next reference 生成：

$$
\mathbf{a}'
\sim
\pi_\theta
\left(
\cdot
\mid
\mathbf{x}_{t+C},
\mathbf{a}^{\mathrm{ref}}_{\mathrm{next}}
\right)
$$

与原论文一致的 TD target，$Q_{\psi'}$ 为 target critic：

$$
\boxed{
\hat{Q}
=
R_t^{(C)}
+
\left(1-\mathrm{done}\right)
\gamma^C
Q_{\psi'}
\left(
\mathbf{x}_{t+C},
\mathbf{a}'
\right)
}
$$

$$
\boxed{
\mathcal{L}_Q
=
\left(
Q_\psi
\left(
\mathbf{x}_t,
\mathbf{a}^{\mathrm{exec}}_{t:t+C-1}
\right)
-
\hat{Q}
\right)^2
}
$$

critic 的监督来自真实执行动作、真实 reward 和下一状态的 bootstrap。

bootstrap 侧的不对称是设计的一部分：$\mathbf{x}_{t+C}$ 的 reference 只能用原始 VLA chunk，未来步没有人工 mask，
所以 $\mathbf{a}'$ 永远是"VLA 建议下的 actor 动作"，而 $Q_\psi(\mathbf{x}_t, \mathbf{a}^{\mathrm{exec}})$ 的动作里
可能含人工修正。

### 4.4 Metadata

以下字段用于数据管理、调试和统计，不参与 loss：

```text
episode_id      一次关键阶段 = 一次尝试
round_id        一轮操作，可包含多次关键阶段
source          VLA / RL / HUMAN / MIXED（chunk 内任意两种来源共存即 MIXED）
is_critical     非关键阶段不入库，所以在 replay 里恒为 True
timestamp       与训练曲线、视频、机器日志对齐
```

## 5 Replay buffer 规模与更新节奏

### 5.1 定义

replay buffer 的单位统一为：

$$
\boxed{1\ \text{buffer row}=1\ \text{replay transition}}
$$

两个核心配置：

$$
\boxed{\texttt{warm\_up}=\text{开始 RL 更新前需要的 replay transitions 数}}
$$

$$
\boxed{\texttt{buffer\_size}=\text{最多保存的 replay transitions 数}}
$$

`buffer_size` 不要求填满，它只是容量上限，满后按行 FIFO 覆写；真正决定什么时候开始训练的是 `warm_up`，
且 $\texttt{buffer\_size} \ge \texttt{warm\_up}$。成败已确认的完整 window 在 round commit 时逐行入库。

### 5.2 一个 episode 能产生多少 replay transitions

先算 critical phase 的 environment steps：

$$
L=T_{\text{critical}}\times f
$$

例：$L=5\times30=150$ steps。

`replay_stride` 只改变 replay row 怎么从已执行轨迹切出，不改变机器人按 chunk 执行。

`stride=0` 按 executed chunk 边界存（第 1 节的边界 anchor 模式）：

$$
N_{\text{transition/ep}}
\approx
\frac{L}{C},
\qquad
1\text{ replay transition}\approx 1\text{ executed chunk}
$$

例：$150/10=15$ transitions/episode。

sliding-window `stride=s>0` 用 phase-relative 网格 $0, s, 2s, \dots$，每个 anchor 从同一条连续 step trace 取
$[\text{anchor}, \text{anchor}+C)$；restart / human 边界只改变逐步 source / mask，不额外创建 row：

$$
\boxed{
N_{\text{transition/ep}}
=
\left\lfloor
\frac{L-C}{s}
\right\rfloor+1
}
$$

例：`stride=2` 时 $\lfloor (150-10)/2 \rfloor+1 = 71$。

最后一个完整 terminal window 的起点 $L-C$ 不在网格上时额外加上它，保证最后一步 reward 落在唯一一条
`terminated=true` 的行上，此时总行数为 $\lceil (L-C)/s \rceil+1$。

同一个 5 秒 episode：

| 设置 | replay transitions / episode |
|---|---:|
| `stride=0`，按 chunk boundary | **15** |
| `stride=2`，overlap sliding window | **71** |

**特征对齐。** `stride=2` 时每个 sliding anchor 使用自身的 observation / VLA features：一行的 $\mathbf{x}_t$ 与
$\mathbf{a}^{\mathrm{ref}}$ 来自自己的 anchor，$\mathbf{x}_{t+C}$ 来自 anchor$+C$，不能复用 `stride=0` row 的 chunk
起点特征。机器人在 chunk 内按 stride 抓取 raw observation，phase 得到 success / failure 标签后才补算这些索引的
特征；未标注、discard、reset 或断连时丢弃。

### 5.3 怎么估计 warmup

先决定希望 base VLA 跑多少个有效 critical-phase episodes：

$$
N_{\text{warmup}}
=
N_{\text{episode}}
\times
N_{\text{transition/ep}}
$$

例如希望先跑约 10 个插入 episode：`stride=0` 为 $10\times15=150$ transitions，`stride=2` 为 $10\times71=710$
transitions。反过来：

$$
\boxed{
N_{\text{warmup episodes}}
\approx
\frac{\texttt{warm\_up}}
{N_{\text{transition/ep}}}
}
$$

例如 `warm_up=600`：`stride=0` 为 $600/15=40$ episodes，`stride=2` 为 $600/71\approx8.5$ episodes。

$$
\boxed{\text{不能脱离 stride 单独比较 warm\_up transitions}}
$$

`600 transitions @ stride=0` 和 `600 transitions @ stride=2` 代表的真实机器人数据量完全不同。所以配置内部统一
用 replay transitions，日志同时显示：

$$
\boxed{
\text{transitions}
+
\text{equivalent env steps}
+
\text{estimated episodes}
}
$$

例如：

```text
warm_up: 600 transitions
stride: 0
≈ 6000 env steps
≈ 200 s critical-phase data
≈ 40 episodes
```

`buffer_size` 按总训练预算设置得足够大即可，不把"填满 buffer"当成训练阶段目标。

### 5.4 更新节奏

只优化 phase-two MLP，UTD = 5，actor 每 2 次 critic 更新一次。

每个累计入库的 transition 对应 5 次 critic 更新预算；达到 warmup 前预算为 0，达到后补齐此前数据的预算：

$$
N^{\text{desired}}_{\text{critic}}
=
\begin{cases}
0, & |\mathcal D| < \texttt{warm\_up} \\
5\,N_{\text{committed}}, & \text{otherwise}
\end{cases}
\qquad
N_{\text{pending}} = \max\!\left(N^{\text{desired}}_{\text{critic}} - N^{\text{done}}_{\text{critic}},\ 0\right)
$$

- $|\mathcal D|$ 是 replay 当前行数，$N_{\text{committed}}$ 是只增不减的累计入库数：buffer 覆写旧行不倒扣已挣到
  的预算。
- actor 在 critic 第 2、4、6… 次更新之后各更新一次；第一次 critic 更新后不更新 actor。
- 每次训练把 $N_{\text{pending}}$ 全部跑完，不设单次上限：真机没有独立的 learning stage 能事后补欠账，而
  warm_up 一过 actor 就上机，封顶只会让 critic 落后自己的数据。代价是回合间暂停变长且不可预测，这个成本要在
  日志里看得见。

## 研究性选项（未验证）

两个选项用于 0924 run 之后的真机对照实验（见 [experiments.md](experiments.md)），默认值就是上面的 baseline。

**actor 条件输入（4.2）。** `corrected`（默认）即 $\tilde{\mathbf{a}}^{\mathrm{train}}$；`proposal` 时条件输入换成
原始 $\mathbf{a}^{\mathrm{ref}}$，也就是部署时 actor 实际看到的输入：

$$
\mathbf{a}_\theta \sim \pi_\theta\!\left(\cdot \mid \mathbf{x}_t,\ \mathbf{a}^{\mathrm{ref}}\right),
\qquad
\text{BC target 仍为 } \tilde{\mathbf{a}}^{\mathrm{train}}
$$

critic 与 replay 字段不变。人工步于是学"VLA proposal → 人工修正"的映射，没有抄输入的捷径。

**actor 输出（第 2 节）。** 动作空间与归一化不变，只改 actor 均值 $\mathbf{h}$ 怎么变成动作：

$$
\text{direct（默认）：}\ \mathbf{a} = \operatorname{clip}(\mathbf{h},\,-1,\,1)
\qquad
\text{residual：}\ \mathbf{a} = \operatorname{clip}\!\left(\mathbf{a}^{\mathrm{ref}}_{0:C} + \boldsymbol{\beta} \odot \tanh(\mathbf{h} / \boldsymbol{\beta}),\,-1,\,1\right)
$$

- $\mathbf{h}$ 是 MLP 均值，训练时已加噪声；$\boldsymbol{\beta}$ 逐维给出，单位是归一化动作（$\pm1$ 对应
  $q_{01}$–$q_{99}$）。
- 用 tanh 软上界而不是硬 clip：接近 $\beta$ 时梯度不会直接变 0。输出头初始化很小，新 actor 一开始约等于 VLA
  proposal，而 direct 一开始约等于"停在当前状态"。
- 残差的基准是 actor 这次的输入 reference，不受 reference dropout 影响：dropout 只清零 MLP 输入里的那份，否则
  被 drop 的样本会变成相对 0 的偏移。
- 配合 `corrected` 输入时，人工步的基准就是人工动作本身，残差可以直接学成 0；这个组合允许，但不推荐。
