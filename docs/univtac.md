# UniVTAC 模块说明

## 定位与边界

`methods/univtac/` 是 UniVTAC 视触觉操作仿真与评测平台的独立 Git submodule，
在本工作区登记为 `benchmark`。它负责接触丰富型任务的仿真、专家数据采集、基线策略训练
和统一评测；根仓库负责未来实验的配置、运行证据与跨 run 报告。

- 用户 fork：`https://github.com/AtticusZeller/UniVTAC.git`
- 官方 upstream：`https://github.com/univtac/UniVTAC.git`
- 工作分支：`dev`
- 许可证：仓库实际 `LICENSE` 为 Apache-2.0；上游 README 中的 MIT 文案与之不一致。

## 环境约束

上游当前支持 Linux、Python 3.10、NVIDIA Isaac Sim 4.5、Isaac Lab 2.1.1、cuRobo，
并依赖仓库内 `third_party/TacEx` 的定制实现。公开 TacEx upstream 不能直接替代该目录，
因为 UniVTAC 使用了项目专属的触觉 API 修改。

根 Python 3.12 环境不安装这些训练与仿真依赖。后续首次实验应先建立独立 Conda 环境，
并在 `experiments/univtac/runbook.md` 记录安装、smoke、数据路径、GPU 要求和已验证版本。

## 代码结构

- `envs/`：任务、机器人、传感器和环境公共逻辑；
- `scripts/`：数据采集、并行评测、回放和可视化；
- `policy/`：ACT、消融实验和 ViTAL 等策略实现；
- `task_config/`：任务与数据采集配置；
- `third_party/TacEx/`：UniVTAC 所需的定制触觉仿真依赖；
- `docs/`：安装、数据采集、任务创建和策略部署说明。

## 当前接入状态

已完成 benchmark 代码版本固定、远端登记、可恢复安装器，以及 Ubuntu 本地完整安装和
单环境 GUI/触觉仿真验收。2026-08-02，当前 DSW 也完成全部 Python/CUDA 构建链：
Python 3.10、PyTorch 2.5.1+cu124、Isaac Sim 4.5.0、Isaac Lab 2.1.1、cuRobo、TacEx、
`tacex_uipc 0.1.0` 与 `pyuipc 0.9.0` 均已安装，`pip check` 和 `import uipc` 通过；
libuipc CUDA backend 已针对 H20 的 `sm_90` 编译成功。

云端运行边界与安装边界必须分开：该 DSW 的 `vulkaninfo` 只枚举 CPU llvmpipe，系统
Vulkan ICD 目录没有 NVIDIA JSON；显式使用现有 NVIDIA ICD 后仍以
`VK_ERROR_INCOMPATIBLE_DRIVER` 失败。Isaac Sim headless 因而显示 `Driver Version: 0`、
空 GPU 表和 `No device could be created`。这证明当前容器没有建立可用的 NVIDIA Vulkan
graphics 路径；除此之外，NVIDIA 对 H20 的[直接答复](https://forums.developer.nvidia.com/t/does-the-h20-graphics-card-support-isaac-lab-isaac-sim/339701)
和 Isaac Sim 官方仓库的 [H20 讨论](https://github.com/isaac-sim/IsaacSim/discussions/446)
均确认 H20 没有 RT Cores、位于 Isaac Sim 支持范围之外。因此即使补齐匹配版本的 Vulkan
用户态栈，也不能把 H20 变成受支持的 Isaac Sim GPU。安装器现会把 graphics device
创建失败判为 exit 1，不再把 `SimulationApp` 提前 exit 0 误报为成功。

当前运行分工确定为本地 RTX 4060 承担 Isaac Sim/TacEx/UniVTAC 仿真，云端 H20 承担
模型训练与推理。只有云端换成满足 Isaac Sim 要求的 RTX GPU 后，才重新验证云端仿真；
不再为当前 H20 尝试混装驱动、手工注入 ICD 或寻找 `physics-only` 绕过路径。

仍没有创建 `experiments/univtac/`、launcher、配置或运行手册，也没有下载数据。出现第一
个明确实验后，再按具体 policy、task、预算和 seed 建立可复现配置；大型数据、checkpoint、
视频和完整日志写入 `/mnt/data/atticux/vla-post-train/univtac/<run-id>/`。

2026-08-01 在当前 DSW 上实测上游 `scripts/install.sh`：首次安装会因 `set -e` 与
`conda env list | grep UniVTAC` 无匹配而在创建环境前以 exit code 1 静默结束。
安装器后半段另有 vcpkg 条件/路径和最终工作目录问题；本轮未改脚本，也未占用正在运行
RLinf formal run 的 GPU。可搜索问题摘要见 `docs/bug.md`，完整 trace 和分析见
`/mnt/data/atticux/vla-post-train/univtac/install-20260801T124939Z/`。

用户要求排除 fork 个人改动后，我新增的 `27d9aec` Agent 文件已由 `1e9272a` 完整
撤销并推送；撤销后的 fork `dev` 与官方 `main@05bcd3e` 文件树和安装脚本 blob 完全
一致。第二次安装仍在同一点 exit 1，证据见
`/mnt/data/atticux/vla-post-train/univtac/install-20260801T132145Z-reverted/`，因此已排除
个人提交和 submodule 接入对该安装故障的影响。

2026-08-02 的安装器修订把环境探测、Conda/PyPI 源、Isaac Lab/cuRobo 版本、vcpkg、
工作目录和 GPU smoke 拆成可恢复步骤。云端使用经过 gzip、源码内容与目标 commit 校验的
tinygltf 临时 overlay 完成余下 5 个 vcpkg ports；随后补齐 libuipc 未声明的 `mypy`
依赖和嵌套 pip 官方源，并修复 stub-only `pyuipc` 包遮蔽编译扩展的问题。完整安装证据在
`/mnt/data/atticux/vla-post-train/univtac/install-cloud-20260802T1612Z/`；H20 smoke 与
GPU foundation 探针分别在同级 `h20-gpu-smoke.log` 和 `gpu-foundation-probe.log`。

首次 GUI 启动并非显存 OOM，而是 UniVTAC vendored TacEx 在移除 Git LFS 文件时漏掉
`Gelpad_low_res.usd`，robot USD 的 payload 因此无法解析。资产提交 `4423bb7` 从本仓历史
`b371b18` 恢复相同 blob；随后用户以以下命令完成真实窗口验收：

```bash
cd methods/univtac/third_party/TacEx
python scripts/demos/tactile_sim_approaches/check_taxim_sim.py \
  --num_envs 1 \
  --debug_vis \
  --rendering_mode performance
```

控制台进入 `Setup complete` 并连续 reset，GPU compute 抽样 39–50%、显存
74.66–77.65%。截图、完整 Kit 日志、控制台摘要和未消除 warning 见
[`univtac-smoke-20260802.md`](univtac-smoke-20260802.md)。

本地机的 RTX 4060 Laptop 8 GB 达到 Isaac Sim 4.5 的最低显存级别，但 16 GB RAM
低于官方 32 GB 最低要求，Ubuntu 24.04 也不在 4.5 文档列出的 20.04/22.04 支持范围。
因此已验证的运行合同仍限定为单环境 `performance` smoke，避免 4K 多相机和并行数据采集；
若后续大规模 workload 出现 GUI/驱动兼容或内存问题，优先准备 Ubuntu 22.04 与更大内存/
显存环境，而不是据此修改算法或触觉代码。
