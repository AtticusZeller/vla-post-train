# TacWAM 常用命令

推理是双机形态：**GPU 机**跑策略服务，**机体机**跑控制闭环。两侧环境不同且不可合并。

## GPU 机 · 环境准备

`conda_enviroment.yaml` 的 pip 段已包含 `-e packages/xense-client` 与 `-e .[test]`，
一次创建即可，无需单独安装 xense-client。

```bash
cd methods/tacwam && mamba env create -f conda_enviroment.yaml && mamba activate tacwam
```

## GPU 机 · 启动策略服务

```bash
cd methods/tacwam && python scripts/serve_policy.py --config <config_name> --checkpoint-dir <ckpt_dir> --port 8000
```

> **尚未在真实权重或真机上验证。** 相机几何取自训练配置，与训练侧同源；但所有测试都基于
> fake model，没有 checkpoint、GPU 或真机证据。

## 机体机 · 启动控制闭环

机体侧沿用 lerobot-xense 环境，**不要**安装 tacwam（torch 版本与之冲突）。

```bash
cd methods/tacwam && mamba activate lerobot-xense && python -m examples.bi_flexiv_rizon4_rt.main --args.robot-recipe forward-05 --args.host <gpu_机_ip> --args.port 8000
```

先不下发动作、只打印策略输出的干跑模式：

```bash
cd methods/tacwam && mamba activate lerobot-xense && python -m examples.bi_flexiv_rizon4_rt.main --args.robot-recipe forward-05 --args.host <gpu_机_ip> --args.port 8000 --args.dry-run
```

> **不要启用 `--args.rtc-enabled`。** RTC 需要服务端在去噪时冻结动作前缀、且模型以相同语义
> 训练过，TacWAM 两者都不具备；启用后会得到未受前缀约束的动作块，在 merge 点造成跳变。
> 原因见 [overview.md](overview.md)。

## 测试

websocket 契约回环测试不需要 GPU、权重或真机：

```bash
cd methods/tacwam && mamba activate tacwam && pytest tests/test_serve_websocket.py
```

## 待用户验证

- **状态：** 已通过（2026-09-03）
- **目的：** 确认 `conda_enviroment.yaml` 能一次装出可用环境。
- **命令：** `mamba env update -f conda_enviroment.yaml --prune` 后 `pytest -q`
- **结果：** 环境更新无报错，`48 passed`。之后 `spdlog` 从 YAML 移入
  `packages/xense-client/pyproject.toml`，重装该包与全量测试均已复验通过。
