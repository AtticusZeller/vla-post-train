# TacXense 概览
## 定位

TacXense 是 Xense 面向双臂操作的视觉—触觉—语言—动作（VTLA）模型族，本工作区接入的是其中的
TacXense-V1 模仿学习基线；W1（world model）与 R1（RL）按上游自述属于同族的姊妹项目，不在
这个仓库里。模型结构是预训练 VLM 骨干（Qwen3-VL 或 Gemma 4）编码多视角图像与带状态的文本
prompt，DiT 式 action expert 交叉注意进 VLM hidden states，用 flow matching 去噪出动作块。

上游 `CLAUDE.md` 说明 TacXense 刻意镜像两个参照实现而不是自创约定：`xense-openpi` 提供
transform 栈、配置布局、serving 接口与 DDP 训练轨道，`starVLA` 提供 ZeRO-2 训练轨道。前者
就在本工作区（`methods/xense-openpi`），后者是外部仓库、未接入。

## 与其他 method 的边界

真机侧不在本仓库：机器人驱动、遥操作与数据采集属于 `lerobot-xense`。上游 README 要求机体主机
使用 `lerobot-xense` 环境并以 `--no-deps` 安装本仓库，训练与服务环境不带机器人 SDK。依赖里
声明的 `lerobot` 是 **PyPI 上游版本**（`>=0.5.1,<0.6`），不是工作区的 `methods/lerobot` fork，
两者在 `tacxense` 环境里不能互相替代。

## 环境

`conda_enviroment.yaml` 建出 `tacxense` 环境（Python 3.12、CUDA/cuDNN、ROS Humble 的 ARX5
运动学依赖、EtherCAT SOEM、带 libsvtav1 的 ffmpeg），Python 依赖由 `uv pip install -e .` 安装。
`qwen3_5_*` 变体另需 `scripts/install_qwen35_fastpath.sh`，`flash_attention_2` 需
`scripts/install_flash_attn.sh`。上游 README 明确这两步是 sdist + `--no-build-isolation`，且
缺失时会**静默回退**到慢路径或非 flash 注意力——"装上了"不等于"走的是预期内核"。

## 分支选择

本工作区把 TacXense 固定在 `feature/rlt-test`（此前为 `feature/rlt`，2026-09-17 切换），不是
默认分支 `main`：该分支是 RL token（RLT）工作线的测试分支。RLT 的两阶段架构、模型定义、训练
方式与数据来源见 [rlt.md](rlt.md)。服务侧 `serve_policy.py` 增加 `policy:rlt-checkpoint` 子
命令，switch 关闭时与纯 VLA 逐动作一致，经 `rlt_switch` kwarg 按请求切换 actor。切回其他分支
需要同时改 `.gitmodules` 与 `scripts/lab.py::_METHODS` 的 branch 字段，只改一处会让
`./lab method status` 失败。

## 当前边界

本工作区只完成接入：`.gitmodules`、`_METHODS` 注册表、contract 测试与文档就位。**没有**创建
`experiments/tacxense/`，没有建 conda 环境、没有取权重、没有训练、推理或真机证据。

上面的架构、RLT 与安装描述转述自上游 `README.md`、`CLAUDE.md` 与 `docs/current_state.md`，
属于上游声明而非本工作区的验证结论；`current_state.md` 的快照最后更新于 2026-09-08，当时
分支为 `fix/earbud-fine-manipulation`。该快照自述 RLT 的 CPU 单测通过、真机闭环仍待验证。

仓库为 private，根目录 `LICENSE` 为 Apache-2.0，GitHub 亦识别为该许可证。
