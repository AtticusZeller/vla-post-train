# Writing the Plan

Most of the effort in this workflow is spent here, not in the editor. A plan that is agreed quickly
and vaguely produces more total work than one argued over for an hour, because every ambiguity
resurfaces later as a mid-implementation stop, a review finding, or a rewrite.

The plan is not an explainer for someone who has not seen the code. It is where two people who have
both read it converge: written for a reader who knows the codebase, it exists so that before
anything is edited the human is clear on what this change is really doing and the agent is clear on
exactly what to build. That is also where responsibility divides — the human owns intent, scope and
acceptance; the agent owns how it gets done.

Pitch it the way you would brief someone senior: not so coarse that they cannot judge it, not so
fine that the point is buried. Name a file, interface or field when it is what the judgement turns
on; an identifier that only proves you read the source is noise, and a page of them hides the two
that matter.

## Template

The `docs/AGENTS.md` contract defines the shape. Each transaction is one `##` chunk; each task
inside it uses:

```markdown
## <事务名称>

<Background: what is being built and why. Then the boundaries that constrain it -- environment
splits, contracts that must be preserved, capabilities explicitly out of scope. Each with the
evidence that established it.>

### Task: <可观察目标>

**Change**

- [ ] <what gets implemented or modified, and the reason it is done this way rather than the
      obvious alternative>

**Verification**

1. [ ] <a check the agent can actually run>

**Done**

- [ ] <an observable result someone else could confirm>
```

`Task = Change + Observable Evidence`. "实现完成" or "测试通过" are circular and cannot serve as
`Done`; name the thing you would look at to believe it.

## A worked task

From a serving integration, showing the level of detail that survives review:

```markdown
### Task: 服务端接受任意 prompt 而不依赖预计算缓存

训练配置是 `load_text_encoder: false` + `use_text_embed_cache: true`，靠预计算脚本编码数据集里的
task；而服务时 prompt 由机体侧实时传入，`LoadCachedTextEmbedding` 查不到缓存会抛
`FileNotFoundError`，足以在 episode 中途打断控制。

**Change**

- [ ] 派生 serving 版模型配置加载文本编码器；YAML 不改，`load_text_encoder` 是构造参数而非架构开关
- [ ] 派生 serving 版数据配置使链中不含 `LoadCachedTextEmbedding`。**只做上一条的话请求仍会在
      transform 阶段抛错，编码器根本没机会被调用**
- [ ] policy 自己 `encode_prompt` 并按 prompt 记忆化，再传 `context`/`context_mask`；直接传
      `prompt` 会让每次 chunk 推理重跑一遍 T5
- [ ] 构造后立即 `eval()`。这是记忆化的前置条件而非优化：文本编码器含 dropout，而模型内部那句
      `eval()` 管不到在其之外调用的 `encode_prompt`，否则首次编码会带噪声被缓存并一直复用

**Verification**

1. [ ] 用假 model 走完整构建路径，在 `tacwam` 环境运行

**Done**

- [ ] 未预先缓存的 prompt 不再触发 `FileNotFoundError`
- [ ] prompt 不变时 `encode_prompt` 只被调用一次，换 prompt 后增加到两次
- [ ] 断言构建返回时模型已处于 eval 模式，锁住上述 dropout 前置条件
```

Note what the items carry beyond the action: why this way, what breaks if a step is skipped, and a
`Done` condition that fails loudly if the mechanism silently regresses.

## Is the plan ready

Signs it is not, each of which cost a mid-implementation stop when missed:

- **A contract is named but never defined.** "对齐相机布局" without stating the layout means the
  first person to implement it has to invent one. If the value cannot be found in the code, that is
  a question for the human, not an assumption to make later.
- **A decision is deferred without being named.** "相机通道数在实现时一并定下" defers without
  saying who decides or on what evidence. Either settle it now or write it as an explicit open
  question with the options.
- **Imprecise verbs.** "自行组装 transform 链" hid the fact that a one-line config derivation would
  do. Vague verbs conceal how much work is actually involved and let two people read the same item
  differently.
- **`Done` restates `Change`.** If the acceptance condition is the change tense-shifted, nothing has
  been specified — ask what observation would distinguish a correct implementation from a plausible
  broken one.
- **Verification the agent cannot run.** Fine to include, but mark it as the user's and give the
  command and pass criterion, rather than leaving it as an untested claim.

Prefer resolving these by reading the code. Ask the human only for what the repository cannot
answer.

## Staying inside the plan

Two failure modes recur, both of which look reasonable while they happen:

**Working ahead of confirmation.** Drafting the code "while we discuss" feels efficient and quietly
converts an open question into a fait accompli — the human is now reviewing an implementation rather
than deciding a direction. If code exists before the plan is confirmed, say so plainly and treat it
as a draft the human may discard.

**Checking off without verifying.** Marking a task complete because the work feels done reliably
hides items that were never finished. Re-read each item against the code before the box goes from
`[ ]` to `[x]`; an item whose evidence cannot be produced is not done, and saying so costs far less
than having a reviewer find it.

A third, subtler one: **answering a question the user did not ask.** When they ask how a conflict is
resolved, resolve that conflict — expanding into adjacent design work buries the answer and spends
the plan's budget on something nobody agreed to.

## When the plan turns out to be wrong

It will. The response is not to patch quietly and mention it later, but to stop, bring the evidence
back, and correct the plan before continuing. Record the correction where it happened rather than
rewriting history: a plan that shows a conclusion being overturned teaches more than one that only
ever shows the final answer, and the reviewer needs to see which assumptions were revisited.
