# DSRL π0 运行手册

## 定位与环境

- 代码：`methods/dsrl-pi0`；入口固定为 `python -m examples.launch_train_sim`。
- 方法：冻结 OpenPI `pi0_libero`，在 diffusion noise 空间训练 Pixel SAC steering。
- 任务：LIBERO-90 task 57，seed 0。
- 已验证环境：Conda `dsrl_pi0`、Python 3.11.11、JAX 0.5.0、
  `nvidia-cudnn-cu12==9.10.2.21`。
- 权重先下载到本地 POSIX cache，再同步 OSS；不要把 OpenPI 并发下载临时目录直接放 OSS。

完整安装与环境陷阱保留在 `methods/dsrl-pi0/docs/baseline.md`。启动前执行：

```bash
./lab config validate experiments/dsrl-pi0/configs/libero90_task57_smoke_seed0.yaml
./lab experiment dry-run experiments/dsrl-pi0/configs/libero90_task57_smoke_seed0.yaml
```

## 执行顺序与预算

1. smoke：约 3 分钟、1 GPU，只证明 rollout、evaluation 和 SAC update 链路；
2. 10k：约 45 分钟、0.75 GPU·小时，最终 10 回合评测；
3. 500k：约 19 小时、4 GPU、约 75.47 GPU·小时。

500k 已观测每卡峰值最高 85.3 GiB，复跑按 4 张至少 96 GiB 显存 GPU 预留。正式运行
必须使用 clean、远端可获取的 code/config revision；长跑由 Skill 在 tmux 中执行。

## 评测、恢复与故障

- W&B 项目随配置分别为 smoke、10k、500k 项目；只读取 YAML 明确列出的 run。
- 本地退出码和 traceback 优先于 W&B 状态。退出后的 `EGL_NOT_INITIALIZED` 在退出码 0、
  W&B 已同步且训练完成时视为清理警告。
- 当前 simulation 入口没有可靠的 checkpoint eval-only/resume 能力，launcher 不声明 resume。
- 正式结果仅为 task 57、seed 0、10 episode；10/10 不代表 LIBERO-90 总体表现。
- 历史 500k 代码基线由复现文档确认：
  `7f48937d4553e95244cd81c79236a3256df80597`。
