---
name: develop-feature
description: Plan-driven development of a new feature or capability in a methods/* submodule or the workspace itself. The plan is agreed with the human first and then governs every subsequent step, including an external code review. Use whenever the user wants to build something non-trivial rather than make a small local fix -- adding a serving path, a new script, a subsystem, or reworking an existing one -- and also when resuming such work, reacting to a code review of it, or closing it out into docs and a pull request.
---

# Develop Feature

The plan is the contract. Code, review, tests and documentation all trace back to it, and nothing
gets written that the plan does not cover. That constraint is what makes a separate reviewer able to
judge the work, and what lets the pull request explain itself months later.

Expect most of the effort to land before any code is written. Time spent making the plan precise is
not overhead on the implementation — it is the implementation, decided in a form the human can still
change cheaply. `references/plan.md` holds the template, a worked example, and the recurring ways
plans turn out to be under-specified; read it before writing or amending one.

## 1. Align on a plan

Read the code together with the user before proposing anything. Investigate repository facts
yourself; ask only about decisions the evidence cannot settle — scope, architecture, interfaces,
acceptance criteria.

Write the plan into `docs/<area>/plan.md` following `references/plan.md`. Beyond the steps, record
**why**: the options considered, the evidence for the choice, and the provenance of anything ported
from elsewhere. That reasoning is what the reviewer checks against and what the pull request is
later written from, so a plan that lists only actions has already lost its most valuable half.

Present it and wait for explicit confirmation. Silence and agent confidence are not confirmation,
and neither is a plan the human has not yet seen in full — drafting code "while we discuss" converts
an open question into a fait accompli.

## 2. Execute, and interrupt yourself when reality diverges

Implement the confirmed plan autonomously. But plans are written before the code is read closely,
so they are routinely wrong in ways that only surface mid-implementation — an undefined contract, a
moved upstream baseline, an assumption that does not hold.

When that happens, stop. Do not improvise a fix and mention it afterwards; the human owns the
decision that the plan encodes. Report what you found with evidence, agree on the correction, update
the plan, then resume. Something discovered while implementing but resolved without the human is
exactly the kind of change a later reviewer cannot audit.

Check off items only after verifying each one against the code. Bulk-marking a task complete because
the work "feels done" reliably hides items that were never actually finished. `references/plan.md`
covers this and the other ways execution drifts away from an agreed plan.

## 3. Take an external code review against the plan

A fresh session reads the plan as the specification and reviews the diff. Feed its findings back
here rather than acting on them blindly: verify every claim yourself first, because a reviewer
without the session's context can misattribute causes even when it correctly spots the symptom.
Confirmed findings go back into the plan as new items, then get implemented like any other.

## 4. Run the gates in order

Only once the plan is fully implemented and its own tests pass:

1. **Static checks on the changed files only.** Follow `modern-python` for tooling. Scope every
   invocation to what this change touched — a shared repository will report hundreds of pre-existing
   findings otherwise, and reformatting files you did not write buries your diff. Run the type
   checker too, not just the linter: it catches a different class of defect, including ones that
   pass every test.
2. **Sync the documentation.** `neat-freak` covers the reconciliation. State what is verified and
   what is still `pending`; do not describe untested code as working.
3. **Commit.** `git-commit`, one or several commits.
4. **Ship.** A pull request via `gh-cli` for collaborative work, or a merge to `main` otherwise.

## 5. Close the plan out

Move each accepted transaction into `docs/<area>/log.md` **whole**, keeping its original
`Change` / `Verification` / `Done` structure, background sections and the wrong turns taken along the
way. A compressed summary loses the judgement, and the wrong turns are often the most useful part —
they show how a conclusion was reached and why the obvious alternative was rejected.

`plan.md` then keeps only what is still open. Durable conclusions — responsibilities, boundaries,
non-obvious rationale, verified limits — belong in `overview.md`. The pull request body is a short
summary of the thinking followed by that log, so a reviewer needs neither the branch nor this
workspace to follow it.

## Boundaries worth holding

- Verbatim copies of upstream code stay verbatim. Fix upstream bugs upstream and record them as open
  items; a local patch buys a small win and costs every future `diff`-based sync.
- Formal claims need evidence. Tests against fakes prove the wiring, not the behaviour — say so
  plainly rather than letting green tests imply a working system.
- Some verification only the user can run (hardware, credentials, a destructive environment step).
  Hand those over explicitly with the command and the pass criterion; commands you supplied are not
  evidence that they passed.
