---
name: xense-openpi-pipeline
description: Run the Xense pi0.5 collect-train-infer pipeline (LeRobot data on HF → norm stats and training on xense-training-h100 → checkpoint archive on COS → policy server on 03-xense-inference → robot client on elite-robot-client), or any single stage of it. Use when the user asks to prepare a Xense dataset for training, train or fine-tune a xense-openpi config, upload or pull checkpoints, deploy a model or client branch to the inference server or robot, or split a long-horizon task into per-frame subtask prompts.
---

# Xense OpenPI Pipeline

The machines, branches, reusable scripts, and acceptance checks for taking a LeRobot dataset to a
running robot policy. Exact commands live in `docs/xense-openpi/cmd.md`; this Skill says which stage
needs which machine, script, and evidence. Read `docs/xense-openpi/plan.md` and `log.md` first when
resuming work.

## Branches

| Branch | Remote | Use |
| --- | --- | --- |
| `chore/remove-jax-cudnn-attention` | upstream `XenseRobotics-AI/xense-openpi` | Main training branch. The shared h100 repo and the 03 inference repo run it. |
| `feat/egg-carton-subtask` | fork `AtticusZeller/xense-openpi` | Subtask variant: per-frame prompts, dataset tools in `scripts/egg_carton_two_stage/`, keyboard prompt switching in the bi-elite client. Based on `feat/elite-rerun`. |
| `feat/elite-rerun` | upstream | Standard bi-elite robot client. |

Ask which branch a task uses; default to the main training branch. Use the subtask branch only when
one episode mixes stages with very different action distributions and the user wants per-stage
prompts. See `docs/xense-openpi/subtask-prompt-spec.md`.

## Machines

| Machine | Role | Environment and rules |
| --- | --- | --- |
| `xense-training-h100` (8×H100) | data checks, norm stats, training, COS upload | Turn history off first (`unset HISTFILE; set +o history`). **Never edit `/root/data/xense-openpi`**: others train from it. Copy the needed branch to `/root/localstorage/<task>/xense-openpi` and run with `PYTHONPATH=$PWD/src`. Data scripts: conda `lerobot-xense` with `CUDA_VISIBLE_DEVICES= JAX_PLATFORMS=cpu HF_HUB_OFFLINE=1`. Training: conda `hb-openpi`. Datasets: `/root/localstorage/hf_cache/lerobot/<repo_id>`. `source /public/bin/network_accelerate` for HF and W&B. Long jobs in tmux with `remain-on-exit on`. |
| `elite-robot-client` | robot client; only HF account that can write `Xense/*` (DingYFa) | Reachable only when the laptop is on Wi-Fi `Dobot_nova5-5G` (192.168.111.x); `Connection reset` on another network. Repo `~/Elite-08_Olorin/xense-openpi`, conda `~/miniforge3/envs/lerobot-xense`. Jump host for 03. |
| `03-xense-inference` | policy server | Repo `~/src/xense-openpi`, checkpoints in `checkpoints/<config>/<step>/`, `~/coscli`. No tmux. `/home` is nearly full: check `df -h ~` before pulling. |
| COS `cos://data-1460349206/xense_checkpoints/elite_egg_checkpoints/` | checkpoint archive | Layout `<config>/<step>/`. |

## Stages

Each stage ends with evidence. Do not move on before it.

1. **Get the data.**
   - Download from HF with the `v3.0` revision.
   - Run ffprobe over every mp4. All files must share one codec. Official `lerobot-edit-dataset delete_episodes` re-encodes to AV1, and mixed codecs break the official merge.
   - Evidence: episode/frame counts match `meta/info.json`, and there is one codec.
2. **Edit the data** (only when needed). Prefer official LeRobot tools at default settings. For the subtask variant, run `scripts/egg_carton_two_stage/` in this order:
   - `drop_episodes.py` (metadata-only delete), then `verify_drop.py`.
   - `relabel.py` (per-frame task from `cuts.csv`), then `verify_relabel.py`.
   - `merge.py` (official `merge_datasets` plus pre-checks).
   - `compare_frames.py` over every episode.
   - `check_prompts.py`.
   - Evidence: each verifier prints `OK`, and `check_prompts` prints `mismatches=0`.
   - Write outputs to new directories. Sources stay read-only.
3. **Config and norm stats.**
   - Put the YAML in `configs/_examples/` and check that `get_config(name)` resolves it.
   - Run `scripts/compute_norm_stats.py --config-name <name> --skip-hub-sync`.
   - Evidence: `norm_stats.json` is written.
   - Report any dimension whose q01 and q99 nearly coincide. pi05 quantile-normalizes without clipping and then bins state into the prompt, so tiny jitter there becomes large token jumps. The user decides what to do about it.
4. **Train.**
   - Run on h100, inside tmux, with `hb-openpi` and the copy's `PYTHONPATH`. Set `WANDB_ENTITY=XenseRobotics`.
   - Check that all 8 GPUs are free first.
   - Evidence: `Step 0` appears within minutes. Later, `Step <last>` appears and the final checkpoint save finishes.
   - Report loss, grad_norm, s/it and ETA from the tmux log. A run from a non-git copy or an unpushed branch is not a formal run; say so.
5. **Archive to COS.**
   - Ask which steps to upload.
   - Upload the whole step directory (params, train_state, assets) with `/root/coscli cp -r`.
   - Evidence: the exit code is 0, and `coscli du` matches the local file count and bytes.
6. **Serve on 03.**
   - Pull only `_CHECKPOINT_METADATA`, `assets/` and `params/`. Never pull `train_state/`.
   - Make sure the config YAML exists in the 03 repo, and check it with `get_config`.
   - Evidence: file count and bytes match the source, and the `norm_stats.json` md5 matches.
   - Start `scripts/serve_policy.py` only when the user asks.
7. **Robot client.**
   - Put elite on the client branch the model needs: fetch from the fork, or use a `git bundle` when only local commits exist. Do not rewrite elite's own branches or stashes.
   - Run `pytest examples/bi_elite_cs66_rt` there.
   - Evidence: the tests pass, then the user's dry-run (`--args.dry-run`) and a real run.
   - Keyboard prompt switching needs an interactive terminal, so the user runs it.

## Approval gates

Ask before each of these:
- any HF upload (DingYFa account; move the `v3.0` tag after replacing files);
- COS upload scope;
- pushing a branch;
- starting a server or a real-robot run;
- deleting checkpoints, datasets or tmux sessions.

Training specs (steps, LR schedule, batch size) belong to the user. Report anything odd, such as a run continuing past the cosine decay steps, but do not change it yourself.
