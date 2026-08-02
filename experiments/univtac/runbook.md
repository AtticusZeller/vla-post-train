# UniVTAC · N0-VTLA 远程推理运行手册

## 范围

本实验在本地 RTX 机器运行 UniVTAC `insert_hole`，通过 SSH TCP 转发连接云端 H20
上的 N0-VTLA ZMQ 推理服务。发布模型为 `NeoteAI/n0_VTLA_insert_hole`，配置
`sim_single_arm_tactile`，输出 50 步、8 维绝对关节动作。

这条链路不在 H20 上启动 Isaac Sim。云端只负责策略推理，本地 RTX 负责 Vulkan/RTX
仿真和触觉渲染。

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

## 本地前置条件

- Ubuntu 24.04、RTX 4060 Laptop；
- UniVTAC `dev` 与根仓当前提交；
- 已完成 UniVTAC 安装及 Omniverse EULA 接受；
- 在本地 `UniVTAC` Conda 环境安装客户端依赖：

```bash
conda run -n UniVTAC python -m pip install msgpack==1.1.2 pyzmq==27.1.0
```

## 建立安全转发

在本地另开终端，并保持会话运行：

```bash
ssh -N -L 5557:127.0.0.1:5557 aliyun_vla_rl_exp_atticux
```

转发建立后，本地客户端连接 `tcp://127.0.0.1:5557`。ZMQ 客户端每回合先发送
`reset`，让服务端重新捕获触觉基线；每次推理必须完整执行 50-step action chunk，
除非任务已经成功或达到 episode 上限。

## Smoke（5 episodes）

从根仓运行：

```bash
./lab config validate experiments/univtac/configs/insert_hole_n0_vtla_zmq_smoke.yaml
./lab experiment dry-run experiments/univtac/configs/insert_hole_n0_vtla_zmq_smoke.yaml
./lab experiment run experiments/univtac/configs/insert_hole_n0_vtla_zmq_smoke.yaml
```

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
