---
name: summarize-experiment
description: Reconcile one VLA experiment's local record, explicit W&B evidence, and method-specific results. Use when the user asks to summarize a run, compare completed runs, or refresh a method report.
---

# Summarize Experiment

## Workflow

1. Read root `AGENTS.md`, `methods/<method>/AGENTS.md`, and
   `experiments/<method>/runbook.md`.
2. Inspect the selected `run.json`, its referenced config, existing `summary.json`, external log paths,
   and only the W&B URLs recorded for that run.
3. Check local exit code and traceback first. Distinguish engineering completion, directional evidence,
   and a formal result.
4. Run `./lab experiment summarize <run-id>` for an executable non-historical run. Do not rewrite an
   immutable historical summary from incomplete online data.
5. Verify the summary envelope contains status, primary metrics, resources, evidence, and
   method-specific results. Keep unknown historical fields null or explicitly unknown.
6. Run `./lab report build <method>`. Confirm only the marked result table changed; preserve human
   conclusions, failures, implementation notes, and evidence boundaries.
7. Report task, seed, episode count, revisions, W&B/local sources, resource accounting, and what cannot
   be generalized. Never convert a single-task or single-seed result into a suite-level claim.
