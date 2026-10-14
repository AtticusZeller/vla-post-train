---
name: analyze-experiment
description: Analyze a finished RL/VLA training run's W&B data and write the result into docs/<method>/experiments.md as a raw record, an analysis, and a next-step list. Use whenever the user pastes a W&B run URL, asks 看一下/分析一下实验数据, asks why a run's metrics look flat, dead, stuck, or too good, asks whether a policy actually improved, or asks to record or write up an experiment result — including when they only paste the link with no question attached.
---

# Analyze Experiment

Turn one finished run into a durable record. The output is a section in
`docs/<method>/experiments.md`; the reasoning that produced it is the point, not the metric dump.

This skill covers runs launched **outside** `./lab experiment` (on a robot host, another machine, a
bare `train_rl.py`). For a run that has a local `experiments/<method>/run.json`, use
`summarize-experiment` instead — it reconciles local metadata with W&B, which this skill does not.

## What the user must provide

Only two things are genuinely required: **the W&B run URL** and **which method** it belongs to.
The method is usually inferable from the project name; confirm rather than assume.

Everything else in the config, metric, and revision space you can get yourself — do that first,
so the questions you eventually ask are ones the repository genuinely cannot answer.

## What to ask the user for, and when

Ask after the first pass over the data, not before. A question asked cold wastes the user's time;
a question asked with a number attached gets a useful answer.

Ask about these, because no amount of reading finds them:

- **Why the run stopped**, when state is not `finished`. Crashed, killed, out of tape, "I went home".
  This decides whether the tail of the data is trustworthy.
- **Qualitative observations from the robot.** What failure actually looked like, why the operator
  took over when they did, whether anything about the setup changed mid-run. The logs record that an
  intervention happened, never why.
- **External reference points.** When proposing a hyperparameter change, the user often knows what
  a comparable implementation uses. Ask, and ask whether that implementation's action space and
  reward structure match this one — a ratio that does not transfer is worse than no reference.
- **Their own read of the data.** They have priors you do not. Record these in the document marked
  as theirs, including the ones you disagree with; say where you disagree and why.
- **What is out of scope this round.** Prevents you from writing a next-step list they have already
  decided against, and gives the `暂不处理` section its content.

Do not ask for: config values, metric values, code revisions, field semantics, or anything else
reachable from W&B, git, or the method source.

## Workflow

### 1 Pull the data once

```bash
uv run --with wandb --with pandas python \
  .codex/skills/analyze-experiment/scripts/fetch_wandb_run.py <run-url> --out <scratchpad>/<run-id>
```

Writes `config.json`, `summary.json`, `meta.json`, `history.pkl` and prints the run state plus a
metric-group inventory (`episode/*`, `update/*`, `chunk/*`, …). Every later question reads
`history.pkl` locally. Re-querying W&B per question is slow and its history endpoint times out on
wide runs — the script already retries that.

Do not try to read the run through a browser. The numbers you need are not on the dashboard.

### 2 Establish what the numbers mean before trusting any of them

Read `docs/<method>/` — the topic file that documents the training contract, plus `plan.md` for what
this run was supposed to demonstrate. Then read the method source for the fields you are about to
build an argument on. Get the submodule's commit hash; the record is worthless without it.

This step is what separates an analysis from a screenshot. A logged name tells you nothing about its
semantics: you have to know where a reward is written, what a "step" advances, what the discount
exponent is applied to, and which of two similar-looking fields the trainer actually consumes.

Concretely, each time you are about to make a claim, find the line that produces the number.
An argument built from a metric's *name* will be wrong roughly as often as the name is suggestive.

### 3 Check the headline metric for confounds first

Before computing anything else, ask what besides policy quality could produce the headline number,
and split the metric along it. Human intervention, auto-retry, early truncation, a changing task
distribution — any of these can carry a success rate on their own.

Report every group with its `n` and a significance test. Splitting shrinks `n` fast, and a bare
percentage over nine episodes reads as a conclusion when it is noise. `scipy.stats.fisher_exact`
is the right tool for success/failure tables.

Also isolate the segment that is actually comparable: the pre-intervention or pre-warmup portion of
the same run is usually the only baseline available, and it is usually tiny. Say so rather than
quietly comparing against it.

### 4 Derive what the metrics *should* be, then compare

This is where the analysis earns its keep. A metric is only interpretable against a prediction.

From the reward structure, discount, horizon, and episode length you can usually compute the value a
converged critic ought to report, and compare it with the logged one. A 6× gap is a finding; "Q looks
low" is not. Same for gradient ratios, residuals, and update counts — work out the expected magnitude
from the config, then look.

Two failure modes to actively test for, because both look like success:

- **Flat is not dead.** Compare the loss against the target's spread. A loss far below the target
  standard deviation means the model fits its targets well and has reached a fixed point — the
  question then becomes whether the fixed point is the right one, which is a different investigation
  than "it stopped learning".
- **Converged is not converged to something useful.** Shrinking gradient norms and shrinking output
  residuals read as healthy training. Check *what* the output converged onto. A policy that converges
  onto its own reference signal has trained stably into an identity map.

When several independent signals agree on an explanation, say that they do — that is what raises a
guess to a leading hypothesis. When they do not, keep both readings and design the experiment that
separates them.

### 5 Write the record

Read `references/record-template.md` for the format contract and follow it. Append a new section at
the top of `docs/<method>/experiments.md`, creating the file with its header if it does not exist.

`docs/AGENTS.md` governs everything under `docs/`; read it before writing. Chinese, concise,
identifiers and paths unchanged.

Keep observation, inference, and conjecture visibly separate — the value of this document a month
later is entirely in knowing which of its claims were actually established. Mark unverified claims
`- [ ] **未验证**` with the check that would settle them.

### 6 Report, and stop

Tell the user what changed on disk, what the leading conclusion is, and which decisions are now
theirs. Do not move next-step items into `plan.md`, do not edit `plan.md`'s existing tasks, and do not
commit — those are separate, user-owned acts. If the run supplies evidence for a `Done` condition in
`plan.md`, point at it and let them decide.

## Boundaries

A single run, single task, single seed is directional evidence. Do not write a suite-level or
algorithm-level claim out of it, and do not let a confident-sounding analysis smuggle one in.

Report the run's state honestly. A crashed run's last episodes may be partial; a run still in flight
will produce different numbers an hour later, so record the state and the cut-off you used.

When the data cannot answer a question, the answer is which measurement would — not a plausible story.
