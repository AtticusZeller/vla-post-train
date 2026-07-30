# FlowDAgger 模块

## 定位

`methods/flowdagger/` 是微软 FlowDAgger 官方实现的用户 fork。当前工作区扩展了
π0.5 MetaWorld 路径，用于按任务独立训练 noise-space steering policy。算法代码留在
method submodule；实验协议、YAML、运行记录和跨 run 汇总留在根仓库。

## MetaWorld-12 协议

- 任务：Assembly、Bin Picking、Box Close、Coffee Pull、Dial Turn、Door Lock、
  Hammer、Hand Insert、Lever Pull、Pick Place、Soccer、Stick Push。
- 每个任务独立训练一个 steering policy，不是联合多任务 steering policy。
- 正式 seeds：`0, 1, 42`，共 `12 × 3 = 36` 个正式 run。
- 每个 run：10 条 seed-expert 轨迹；随后 40 条在线轨迹，每条轨迹后执行 100 个
  BC step，共 4,000 BC step 和 50 条 adaptation rollout。
- dual buffer 将 intervention/autonomous 样本按 50/50 混合；稳定化 batch size 为 16。
- 每个评估点跑 25 episodes；前 2 个 episode 保存视频。

协议真身是 `experiments/flowdagger/metaworld12_suite.yaml`。执行
`./lab experiment suite-configs flowdagger` 可确定性生成 12 份 smoke 和 36 份
formal YAML；`./lab report suite flowdagger` 生成机器可读与中文汇总。

## 策略与视频相机

π0.5 继续使用 `corner3`、256×256 的策略观察，避免改变预训练视觉分布。评估证据使用
独立 MuJoCo renderer，从 `corner` 机位生成 640×480、30 FPS 视频；视频不会复用
steering 网络的 128×128 预处理输入。用户已确认该视角和清晰度可用。

## 结果与证据链

成功运行写出 `{artifact_path}/flowdagger_result.json`，包含任务、seed、真实 W&B URL、
base/final/Δ success rate、逐评估点结果、训练计数和视频元数据。根 `lab` 将动态 URL
与结果文件路径写回 `run.json`，`experiment summarize` 再合并本地结果与明确的 W&B
run。

套件汇总只接受本地退出码为 0、协议匹配、phase 为 `full` 且结果文件完整的 run。
一个任务的 3 个 seed 全部完成后，其 task mean 才进入最终 12-task macro Δ SR。
当前正式进度见 `experiments/flowdagger/metaworld12-report.md`。

## 已验证边界

- 12 个 scripted expert 均在固定 seed 预检中达到 5/5 成功。
- Assembly dirty smoke 已贯通训练、checkpoint、前后评估、W&B、结构化 JSON 和高清 MP4。
- smoke 只有 1 个 BC step、1 个 eval episode，且代码当时未提交，只证明工程路径。
- 历史 Assembly batch-16 full 是单任务、单 seed 方向性证据，不进入 MetaWorld-12 汇总。

运行环境、启动门槛和故障处理见
`experiments/flowdagger/runbook.md`；用户命令见根 `cmd.md`。
