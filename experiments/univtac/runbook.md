# UniVTAC · N0-VTLA 远程推理运行手册

## 范围

本实验在实验室 RTX 4090 机器运行 UniVTAC `insert_hole`，通过 SSH TCP 转发连接云端
H20 上的 N0-VTLA ZMQ 推理服务；用户电脑通过 WebRTC 查看 4090 上的仿真。发布模型为
`NeoteAI/n0_VTLA_insert_hole`，配置
`sim_single_arm_tactile`，输出 50 步、8 维绝对关节动作。

这条链路不在 H20 上启动 Isaac Sim。云端只负责策略推理，4090 负责 Vulkan/RTX 仿真、
触觉渲染和 WebRTC 服务。

## 云端前置条件

- Conda 环境：`vtla`（Python 3.11）；
- checkpoint：
  `/mnt/data/atticux/vla-post-train/n0-vtla/checkpoints/n0_VTLA_insert_hole`；
- Hugging Face revision：`73a514c015c6745a14a3efdca92f25c6cfab5eb5`；
- 缓存：`/mnt/data/atticux/vla-post-train/n0-vtla/{cache,huggingface}`；
- 服务仅监听云端 `127.0.0.1:5557`，不得直接暴露无鉴权端口。

当前服务运行在 tmux `n0-vtla-zmq`。检查：

```bash
tmux has-session -t n0-vtla-zmq
ss -ltnp 'sport = :5557'
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader
```

## 4090 前置条件

- 推荐 Ubuntu 22.04、RTX 4090、NVIDIA 驱动和至少 32 GB RAM；
- UniVTAC `dev` 与根仓当前提交；
- 已完成 UniVTAC 安装及 Omniverse EULA 接受；
- 在 4090 的 `UniVTAC` Conda 环境安装 ZMQ 客户端依赖：

```bash
conda run -n UniVTAC python -m pip install msgpack==1.1.2 pyzmq==27.1.0
```

## 安装 4090 环境

从根仓统一恢复并安装：

```bash
git clone --recurse-submodules https://github.com/AtticusZeller/vla-post-train.git
cd vla-post-train
uv sync --python 3.12 --all-groups

set -o pipefail
bash methods/univtac/scripts/install.sh 2>&1 | tee "$HOME/univtac-install.log"

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate UniVTAC
python -m pip install msgpack==1.1.2 pyzmq==27.1.0
python -m pip check
python -c 'import torch, uipc; print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), uipc.__version__)'
```

首次启动 `isaacsim`，在交互终端阅读并接受 Omniverse EULA，退出后执行：

```bash
export ACCEPT_EULA=Y
bash methods/univtac/scripts/install.sh --gpu-smoke \
  2>&1 | tee "$HOME/univtac-4090-gpu-smoke.log"
```

## 建立推理与 WebRTC 网络

在 4090 另开终端并保持到 H20 的 ZMQ 隧道运行：

```bash
ssh -N -L 5557:127.0.0.1:5557 \
  -p 1022 root@nlb-q4893rwy28q2gtmo1a.cn-beijing.nlb.aliyuncsslb.com
```

转发建立后，4090 的客户端连接 `tcp://127.0.0.1:5557`。ZMQ 客户端每回合先发送
`reset`，让服务端重新捕获触觉基线；每次推理必须完整执行 50-step action chunk，
除非任务已经成功或达到 episode 上限。

WebRTC 使用 4090 的 TCP `49100`（信令）和 UDP `47998`（媒体流）。只向用户电脑的
IP 放行这两个端口；普通 `ssh -L` 不能替代 UDP 媒体链路。用户电脑通过 NVIDIA Isaac
Sim WebRTC Streaming Client 输入 4090 的可路由 IP；若不在同一局域网，先使用实验室
VPN/Tailscale 一类可路由网络。

若 4090 使用 UFW，把 `<CLIENT_IP>` 替换为用户电脑在同一可路由网络中的地址：

```bash
sudo ufw allow from <CLIENT_IP> to any port 49100 proto tcp
sudo ufw allow from <CLIENT_IP> to any port 47998 proto udp
sudo ufw reload
```

## Smoke（5 episodes）

从根仓运行：

```bash
./lab config validate experiments/univtac/configs/insert_hole_n0_vtla_zmq_smoke.yaml
./lab experiment dry-run experiments/univtac/configs/insert_hole_n0_vtla_zmq_smoke.yaml
./lab experiment run experiments/univtac/configs/insert_hole_n0_vtla_zmq_smoke.yaml
```

该配置显式使用 `--livestream 2`。WebRTC 会让宿主侧保持 headless；不会在 4090 本机
弹出 GUI，这是预期行为。

通过条件：

- 五个 episode 均完成且没有 ZMQ timeout、图像键错误、动作 shape 错误或非有限值；
- 每次服务端返回 `(50, 32)`，客户端只执行前 8 维；
- 日志出现逐 chunk server/roundtrip latency；
- 输出记录每个 seed 的 success/failed 及最终成功率；
- 视频和完整日志位于该 run 的
  `~/vla-post-train-artifacts/univtac/<run-id>/` 目录。

5-episode smoke 只证明跨机工程链路，成功率只作为方向性结果，不构成模型质量结论。

## 故障证据

失败时返回：根 run ID、`run.json`、`logs/console.log`、服务端 tmux 日志、首次异常前
后各 100 行，以及 `nvidia-smi`。本地异常 exit code 优先于服务端仍存活这一状态。
