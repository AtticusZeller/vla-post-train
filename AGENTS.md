# Agent Research Workspace · Agent Rules

Human sets the boundaries; agent implements and verifies within them.
Ask for decisions, not for work the agent can perform.

## 1. Ownership

Human owns intent, scope, architecture, interfaces, task decomposition, and acceptance criteria.

Agent owns implementation, local technical decisions, testing, debugging, lint/typecheck, and evidence
collection.

The agent may propose options or task breakdowns. Human approval determines the plan. Do not change
human-owned decisions, expand scope, or weaken acceptance criteria without explicit approval.

## 2. Before Implementation

Read relevant code, project documentation, and applicable repository instructions first. For continued
work, read the relevant `docs/<area>/plan.md` and `docs/<area>/log.md`, then compare their claims with
the current code and working tree.

Read-only requests remain read-only. Inspection and non-destructive diagnostics may proceed before
implementation approval; do not modify source, configuration, or dependencies during that phase.

Before implementation, make the task explicit: goal, scope and non-goals, affected components,
interfaces, expected behavior, constraints, and observable acceptance criteria. Every task must define:

```text
Task = Change + Observable Evidence

Change: what will be implemented or changed
Verification: how correctness will be checked
Done: the observable result that counts as accepted
```

Investigate repository facts yourself. Ask focused questions only for unresolved human-owned decisions
or context that available evidence cannot establish. Surface contradictions between the request, plan,
documentation, and code. Do not infer intended behavior solely from the current implementation.

Present the refined task or plan for explicit confirmation. Silence, lack of objection, and agent
confidence are not confirmation. An explicit instruction to execute an already agreed plan counts as
confirmation.

## 3. Implementation and Verification

After confirmation, implement the approved plan autonomously. Follow `karpathy-guidelines`: make the
smallest surgical change, avoid speculative design, state assumptions explicitly, and keep each changed
line traceable to the approved task.

Do not add unrequested features, abstractions, dependencies, refactors, or cleanup.

Assumptions may resolve local implementation details only. Scope, architecture, interfaces, task
decomposition, expected behavior, and acceptance criteria require human confirmation.

For each task, run the loop:

```text
change -> test -> inspect failure -> fix -> retest
```

Run every relevant check available in the current environment.
Do not ask the user to run checks the agent can run.
Diagnose failures from logs, tracebacks, and reproducible observations; each retry must test a concrete
hypothesis. Never bypass a failing check or weaken an assertion merely to obtain a pass. Rerun checks
invalidated by a later fix.

Inspect the final diff for unintended changes and preserve pre-existing or unrelated work. Do not
commit or push unless the user asks.

## 4. Evidence and Stop Conditions

A task is complete only when observable evidence satisfies every acceptance criterion. Report changed
behavior, checks run, acceptance status, and remaining limitations. Commands supplied to the user are
not evidence that they passed.

Stop the affected work and return the smallest unresolved decision when:

- a human-owned decision or acceptance criterion must change;
- intent remains ambiguous after relevant investigation;
- the next action is destructive or irreversible without explicit authorization;
- debugging repeats without new evidence or meaningful progress;
- required hardware, data, credentials, or environment access blocks verification.

When a problem is not immediately solvable, gather context in this order:

1. repository code, tests, configuration, logs, and project documentation;
2. current official library or API documentation through `ctx7` / `find-docs`;
3. relevant upstream issues and fixes through authenticated `gh`;
4. the user, only for information or decisions that the preceding sources cannot provide.

Distinguish observed facts from hypotheses and never present an unverified workaround as a confirmed
fix.

## 5. Skills

Use an available Skill whenever the task matches its description. Read its `SKILL.md` before acting. A
Skill provides execution guidance; it does not expand task scope or authorization.

Repository workflows:

- `develop-feature` — build a new feature or capability under a human-confirmed plan that then
  governs implementation, external review, gates, and closeout.
- `add-method` — add, replace, or register a method, framework, benchmark, or backbone submodule.
- `run-experiment` — validate, smoke-test, launch, repeat, or monitor an experiment configuration.
- `summarize-experiment` — reconcile evidence, summarize a run, or compare completed runs.

General workflows used regularly in this repository:

- `karpathy-guidelines` — implementation, code review, and refactoring discipline.
- `context7-cli` / `find-docs` — current library, framework, SDK, API, CLI, and cloud documentation.
- `gh-cli` — GitHub URLs, issues, pull requests, and authenticated repository operations.
- `modern-python` — Python project initialization and tooling migration.
- `skill-creator` — creating or materially updating a reusable Skill.
- `init-repo-agents` — initializing new repository rules or auditing a confirmed rules update. This
  repository has custom rules, so never run its create-only initializer over the existing files.
- `neat-freak` — explicitly requested knowledge, documentation, or workspace closeout.
- `git-commit` — only when the user asks to commit.
- `explain-diff-html` — only when the user asks for a rich diff explanation.

Do not turn these Skills into an automatic lifecycle or invoke closeout, explanation, or commit Skills
merely because implementation finished.

## 6. Workspace Boundaries

This repository is the orchestration, documentation, and evidence layer for VLA, WAM, agent, and
related embodied-AI research. Algorithm, framework, benchmark, backbone, and reproduction code belongs
in independent `methods/*` Git submodules.

- Before changing a method, read its own `AGENTS.md` or `CLAUDE.md`. Before running a configured
  experiment, also read `experiments/<method>/runbook.md` when it exists.
- Keep method-specific environments isolated unless a method's own documentation explicitly defines a
  shared environment.
- Formal runs require a clean method checkout, a committed root configuration, and root and method
  revisions available from their remotes.
- Dirty checkouts are allowed only for explicitly labeled smoke or debugging runs. A smoke run proves
  the engineering path only; single-task, single-seed, or low-episode evidence cannot establish a
  broader algorithmic claim.
- Store checkpoints, datasets, videos, complete logs, rollouts, W&B caches, and other large artifacts
  under `/mnt/data/atticux/agent-workspace/` rather than in the checkout.
- Treat local exit codes and tracebacks as authoritative when they disagree with a tracking service.
  Preserve traceable records for both successful and failed runs.
- Put deterministic reusable mechanics in `scripts/`. Add or change a repository-local Skill only when
  the workflow is stable, reusable, and within the approved scope.
- Prefer a user-controlled fork as `origin` and the official repository as `upstream`; use a private
  mirror for unpublished work that must not enter a public fork.

The root toolchain is Python 3.12 with uv, ruff, ty, and pytest. `lab` is the stable root entry point;
experiment parameters live in complete YAML configurations when a concrete experiment exists.

## 7. Documentation and Language

Before editing anything under `docs/`, read `docs/AGENTS.md`. Documentation is human-facing project
context, not a copy of code or Git history.

- Write `AGENTS.md`, `CLAUDE.md`, repository-local Skills, code comments, and docstrings in English.
- Write `README.md` and human-facing files under `docs/` in Chinese.
- Use Google-style docstrings and comments that explain why, not line-by-line mechanics.
