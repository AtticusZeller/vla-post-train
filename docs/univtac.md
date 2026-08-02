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

已完成 benchmark 代码版本固定、远端登记、可恢复安装器修订，以及 Ubuntu 本地完整安装和
单环境 GUI/触觉仿真验收。当前 method 终点为 `dev@9ffd768`：Python 3.10、PyTorch
2.5.1+cu124、Isaac Sim 4.5.0、Isaac Lab 2.1.1、cuRobo、TacEx 与 `tacex_uipc`
安装成功；`pip check`、`uipc`/`curobo` 导入、CUDA 张量和 GelSight debug view 均通过。

仍没有创建 `experiments/univtac/`、launcher、配置或运行手册，也没有下载数据。出现第一个
明确实验后，再按具体 policy、task、预算和 seed 建立可复现配置；大型数据、checkpoint、
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

2026-08-02 的安装器修订 `dev@0876043` 把环境探测、Conda channel、PyPI 源、Isaac Lab/cuRobo
版本、vcpkg bootstrap、工作目录和可选 GPU smoke 拆成可恢复步骤。本地首次完整构建遇到
vcpkg `tinygltf v2.9.3` 上游 archive 哈希变化；在验证 tar 内容与目标提交后使用临时 overlay
完成构建。该 workaround 尚未固化进安装器，因此全新云端安装仍需重新验证这一下载点。

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
