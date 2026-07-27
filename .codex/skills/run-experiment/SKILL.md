---
name: run-experiment
description: Run a VLA post-training experiment through this repository's traceable lab workflow. Use when the user asks to smoke-test, launch, repeat, or monitor a configuration under experiments/*/configs.
---

# Run Experiment

## Workflow

1. Identify the config and method. Read root `AGENTS.md`, then
   `methods/<method>/AGENTS.md` and `experiments/<method>/runbook.md`.
2. Confirm `/mnt/data` is mounted read-write, the method environment is available, and the runbook's
   data, checkpoint, GPU, disk, W&B, and time prerequisites are satisfied.
3. Run `./lab config validate <config>` and `./lab experiment dry-run <config>`. Show the resolved
   cwd, argv, environment, artifact root, and tracking target before execution.
4. Follow the runbook's smoke → short → full gates. Never treat a smoke result as algorithm evidence.
5. For a formal run, confirm the root config and method revision are clean, committed, and remotely
   recoverable. Dirty runs require an explicit smoke/debug config and cannot support formal conclusions.
6. Call `./lab experiment run <config>`. Keep short runs in the foreground. Put an approved long run
   in tmux without changing the underlying `lab` command.
7. Monitor the local process/log and only the W&B runs named by the config. Local exit codes and
   tracebacks override an apparently finished W&B state.
8. Preserve both success and failure records. Report the run ID, metadata path, external artifact path,
   W&B URLs, and any evidence limitations.

Do not invent resume behavior. Call `./lab experiment resume <run-id>` only when the launcher declares
support; otherwise preserve the existing run unchanged.
