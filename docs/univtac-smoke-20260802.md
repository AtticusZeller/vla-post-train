# UniVTAC 本地单环境触觉仿真验收证据

## 验收结论

2026-08-02，用户在 Ubuntu 24.04 工作站的 NVIDIA GeForce RTX 4060 Laptop GPU
（8 GB）上完成 UniVTAC/TacEx 单环境 GUI 验收。Isaac Sim 4.5.0 成功创建 Franka、
GelSight Mini 和接触场景，触觉 debug view 可见；控制台进入 `Setup complete`，连续完成
多次环境 reset，没有 CUDA OOM、缺失资产或 articulation 创建失败。

```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate UniVTAC
export CUDA_HOME="$CONDA_PREFIX"
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

cd methods/univtac/third_party/TacEx
python scripts/demos/tactile_sim_approaches/check_taxim_sim.py \
  --num_envs 1 \
  --debug_vis \
  --rendering_mode performance
```

## 可观察证据

- Isaac Sim：4.5.0，Vulkan，driver 580.173.02；
- 环境：`cuda:0`，1 environment，physics/render step 均为 0.01 s；
- 初始化：scene creation 0.894 s，simulation start 18.382 s；
- 运行：多次输出 `Env reset num 1/2/3`，in-contact frames 从 588 增至 1,373；
- 性能抽样：physics 31.38–32.11 ms，tactile 5.08–5.11 ms；
- 资源抽样：GPU compute 39–50%，GPU memory 74.66–77.65%，RAM 76.3–76.7%；
- 用户截图可见 Franka、接触平面、Isaac Sim stage tree 与 GelSight `taxim` 触觉窗口。

![UniVTAC TacEx 单环境 GelSight 触觉仿真](../assets/univtac/local-smoke-20260802.png)

验收前的首个失败不是显存不足，而是 vendored TacEx 缺少
`Sensors/GelSight_Mini/Gelpad_low_res.usd`。该文件从 UniVTAC 历史提交 `b371b18`
原样恢复，Git blob 为 `54ec424ca942aa55cfdc1a168b5e71cdc6e16ab8`；恢复后相同命令通过。

## 原始证据与边界

- 原始 GUI 截图见 [`assets/univtac/local-smoke-20260802.png`](../assets/univtac/local-smoke-20260802.png)；
- 完整 Isaac Kit 日志见
  [`assets/univtac/isaac-sim-20260802-145247.log`](../assets/univtac/isaac-sim-20260802-145247.log)；
- 本次按用户要求将两份小型验收资产直接纳入根仓 `assets/univtac/`，便于云端和后续会话
  直接阅读；大型训练日志、视频、数据和 checkpoint 仍必须放到 `/mnt/data`；
- 该 smoke 只证明单环境 `performance` GUI 与触觉仿真工程链路，不证明数据采集、
  512-env 训练、策略质量或 Ubuntu 24.04 属于 Isaac Sim 4.5 官方支持平台；
- 启动期间仍有 rendering preset setting、DLSS 低分辨率和 Hydra scene delegate
  warning，但没有阻止场景初始化、触觉输出或连续 reset。
