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

已完成 benchmark 代码版本固定、远端登记和可恢复安装器修订；没有创建
`experiments/univtac/`、launcher、配置或运行手册，也没有下载数据。安装器目前是待本地
验收状态：静态检查已通过，云端已完成 Isaac Sim、Isaac Lab、cuRobo 和 TacEx Python
包的部分安装，但用户决定不继续解决 DSW 无头环境问题，因此尚未完成 `tacex_uipc`、
GPU smoke 或 GUI 验证。出现第一个明确实验后，再按具体 policy、task、预算和 seed
建立可复现配置；大型数据、checkpoint、视频和完整日志写入
`/mnt/data/atticux/vla-post-train/univtac/<run-id>/`。

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
版本、vcpkg bootstrap、工作目录和可选 GPU smoke 拆成可恢复步骤。云端迭代日志保存在
`/mnt/data/atticux/vla-post-train/univtac/install-fixed-20260802/`；最终一次按用户要求
主动中止，不代表端到端通过。下一步只在本地运行 `cmd.md` 的安装、GPU smoke 与 GUI
验收；通过前不得把该修订描述为已修复。

本地机的 RTX 4060 Laptop 8 GB 达到 Isaac Sim 4.5 的最低显存级别，但 16 GB RAM
低于官方 32 GB 最低要求，Ubuntu 24.04 也不在 4.5 文档列出的 20.04/22.04 支持范围。
因此先用单环境、低分辨率 smoke，避免 4K 多相机和并行数据采集；若出现 GUI/驱动兼容
问题，优先准备 Ubuntu 22.04 原生环境，而不是继续改算法或触觉代码。
