# FlowDAgger 运行手册

## 定位与环境

- 代码：`methods/flowdagger`，`origin` 为用户 fork，`upstream` 为微软官方仓库。
- 原生入口：`methods/flowdagger/flowdagger_pi05/train_flowdagger.py`。
- 已验证环境：Conda `dsrl_pi0`、Python 3.11、JAX/JAXLIB 0.8.0、
  MetaWorld 3.0.0。
- 新产物：`/mnt/data/atticux/vla-post-train/flowdagger/<run-id>/`。
- 历史 Assembly 产物：`/mnt/data/atticux/FlowDAgger/`，只作为旧实验依据。

运行前必须确认：

```bash
cd /root/vla-post-train
findmnt -T /mnt/data
./lab doctor
./lab method status
```

`/mnt/data` 必须为 `rw`；W&B 标准凭据必须可用。正式 run 还要求根仓与 method
工作树干净、配置已提交，且两个 revision 都能从远端恢复。

## MetaWorld-12 协议

协议真身是 `experiments/flowdagger/metaworld12_suite.yaml`：

- 12 个任务，每个任务单独训练一个 steering policy；
- seeds `0, 1, 42`，共 36 个正式 run；
- 10 条 seed-expert + 40 条在线轨迹，共 50 条 adaptation rollout；
- 4,000 BC steps，每条在线轨迹后 100 steps，batch size 16；
- dual buffer intervention/autonomous 50/50；
- step 0 与每 500 steps 评估 25 episodes；
- 每个评估点保存前 2 个 640×480、30 FPS 视频；
- `takeover_min/max=5/60`（协议 `metaworld12-v2`，恢复上游官方默认）：脚本专家在
  每回合第 5~60 步之间随机接管、开到回合结束，未启用课程扩展。旧协议 `v1` 用过
  更窄的 `0/25`，会导致高精度接触任务在评估时卡死，见 `docs/bug.md`。

生成和检查配置：

```bash
./lab experiment suite-configs flowdagger
./lab config validate --all
./lab experiment dry-run \
  experiments/flowdagger/configs/metaworld12_assembly_full_seed42.yaml
```

## Smoke 与正式运行

每个任务只有一份 seed-42 smoke。Smoke 允许 dirty checkout，只证明任务注册、checkpoint、
专家、反演、BC、评估和视频链路，不进入 suite 汇总：

```bash
./lab experiment run \
  experiments/flowdagger/configs/metaworld12_assembly_smoke_seed42.yaml
```

正式运行使用对应 `*_full_seed*.yaml`。`experiment run` 是前台命令；长跑由
`run-experiment` Skill 放入 tmux。示例：

```bash
./lab experiment run \
  experiments/flowdagger/configs/metaworld12_assembly_full_seed42.yaml
```

当前根工作树会在启动后写入新的 `run.json`，因此同一工作树中的下一个正式 run 必须在
前一个 run 完成、汇总、提交并推送运行记录后再启动。不要在 dirty root 上绕过正式门禁。

## 评估、视频与汇总

- 策略观察保持 `corner3`、256×256；人类视频使用独立 `corner` renderer，
  640×480、30 FPS。
- 每个正式评估点的统计口径始终是 25 episodes；只录前 2 个，不改变统计样本数。
- 本地退出码和 traceback 优先于 W&B 的 run state。
- 成功运行必须存在 `{artifact_path}/flowdagger_result.json`，且 `run.json` 的
  `sources` 与 `tracking.run_urls` 已动态回填。

完成一个 run 后：

```bash
./lab experiment summarize <run-id>
./lab report suite flowdagger
```

`experiments/flowdagger/metaworld12-report.md` 显示当前进度。一个任务的 3 个 seed
全部完成后才进入 task mean；12 个任务全部完整后才给出 macro Δ success rate。

## 已知故障与边界

- batch size 64 曾在首次 BC update 触发 JAX contracting-dimension 错误；当前正式配置
  固定为已验证的 16，不声称是严格源码默认配置。
- 根 `uv run` 的 `.venv/bin` 曾抢占 Conda Python；launcher 现在将目标 Conda env
  的 `bin` 放到 PATH 首位。
- JAX/CUDA 注册与旧 `ptxas` 警告只有在进程失败或出现 traceback 时才判为故障。
- 当前 launcher 不支持恢复；`experiment resume` 会无副作用报错。中断前应确认最近
  checkpoint，任何重跑都使用新的 run ID。
- 旧 Assembly 单 seed full 与所有 smoke 都不能外推为 MetaWorld-12 结论。
- 协议 `v1`（`takeover_min/max=0/25`）下已完成的 15 个正式 run 标记
  `historical: true`，不进入协议 `v2` 的正式汇总；详见 `docs/bug.md`
  2026-07-31 条目。
