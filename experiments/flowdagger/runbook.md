# FlowDAgger 运行手册

## 定位与环境

- 代码：`methods/flowdagger`，`origin` 为用户 fork，`upstream` 为微软官方仓库。
- 入口：在 `methods/flowdagger/flowdagger_pi05` 中执行 `train_flowdagger.py`。
- 已验证环境：Conda `dsrl_pi0`、Python 3.11.11、JAX/JAXLIB 0.8.0、MetaWorld 3.0.0。
- 持久化根目录：新运行使用 `/mnt/data/atticux/vla-post-train/flowdagger/<run-id>`；
  历史产物仍位于 `/mnt/data/atticux/FlowDAgger/`。

先确认 `/mnt/data` 为可写挂载、Conda 环境可用、W&B 已登录，再执行：

```bash
./lab config validate experiments/flowdagger/configs/metaworld_assembly_smoke_b16_seed42.yaml
./lab experiment dry-run experiments/flowdagger/configs/metaworld_assembly_smoke_b16_seed42.yaml
```

## 执行顺序与通过条件

1. smoke：完成 checkpoint、环境、策略、专家接管、反演、一次 BC update 和评测；
2. short b16：完成 100 BC steps、step 0/100 评测和 checkpoint100；
3. full b16：完成 4,000 BC steps和每 500 step 的 25 回合评测。

`bc_batch_size=64` 已在首次 BC update 触发 JAX contracting-dimension 错误。当前机器
的稳定化配置为 16；它不是源码默认值 256。

正式长跑先完成 dry-run，再由 `run-experiment` Skill 放入 tmux。`./lab experiment run`
自身是前台命令并将 console 实时写入外部产物目录。

## 评测、恢复与故障

- W&B 项目：`flowdagger`；本地退出码和 traceback 优先于 W&B 的 `finished`。
- full 每个 checkpoint 使用 25 个 episode。历史 full 的最终值为 0.8，step 1500 峰值
  为 1.0；不得写成 5 回合评测。
- 当前 launcher 不声明 resume 支持；`./lab experiment resume` 会无副作用报错。
- JAX/CUDA 注册与 `ptxas` 警告只有在进程失败或 traceback 出现时才判为故障。
- 单任务、seed 42 的结果仅用于当前实现验证和方向性判断。
