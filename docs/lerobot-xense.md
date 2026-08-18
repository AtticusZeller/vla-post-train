# lerobot-xense 模块

> `methods/lerobot-xense/` 是 Xense 触觉硬件栈的 LeRobot fork（工作区角色
> `framework`）。本文件记录根仓库视角下、跨会话需要复用的结构性结论。
> 它与官方 [lerobot](lerobot.md) 是**两个互不替代的 submodule**：官方那份用于
> rollout / policy 研究，这份用于 Xense 真机采集。

## 定位与边界

| 项 | 值 |
|---|---|
| origin（用户 fork） | `https://github.com/AtticusZeller/lerobot-xense.git` |
| 工作区登记 upstream | `https://github.com/Vertax42/lerobot-xense.git`（[lab.py:66](../scripts/lab.py#L66)） |
| 分支 / 当前 pin | `main` / `fa261c94` |
| 上游本体 | huggingface/lerobot **v5.1**（包版本 `lerobot 0.5.1`） |
| 许可证 | Apache-2.0（HuggingFace 版权头） |
| 体积 | 递归初始化后约 191 MB（7 个 `third_party` + 1 个嵌套） |

这份 fork 只做**数据采集与真机控制**：机械臂驱动、遥操作设备、触觉相机、夹爪、
recipe 化的 teleop/record CLI。模型训练与推理在
[xense-openpi](xense-openpi.md)。通用 lerobot 用法（dataset、policy、训练脚本）
沿用上游，fork 只在其上叠加 Xense 专有硬件。

## 环境约束

- Ubuntu 22.04 / 24.04，NVIDIA 驱动 ≥ 570.144，Python 3.12，PyTorch ≥ 2.2 + CUDA 12.8。
- 强制用 **mamba**（不是 conda）：`robostack-staging` 频道要装 ROS Humble + SOEM，
  conda 解算会慢到不可用。默认环境名 `lerobot-xense-py312`。
- 装法：`bash ./setup_env.sh --mamba <name>` 建环境，`bash ./setup_env.sh --install`
  装包与全部硬件 SDK。安装过程要 `sudo`（ARX5 实时能力 + udev 规则）。
- **这个环境同时是 xense-openpi 的运行环境**，两个方法共用一个 conda 环境。
- v5.1 起不再用 conda 钉 `ffmpeg`（robostack 的 ICU pin 与新 ffmpeg 冲突），
  视频编解码走 `torchcodec` + `av` wheel。
- ARX5 需要给 Python 解释器 `setcap cap_sys_nice+ep` 才能跑实时 CAN 线程。

### 选择性安装（值得记住）

`--install` 默认编译**所有**硬件 SDK。只用一两台设备时按硬件族选择即可：

```bash
bash ./setup_env.sh --install --flexiv --taccap   # 只装 Flexiv + TacCap
bash ./setup_env.sh --install --core              # 只装核心，不装任何 SDK
```

代码对部分安装是兼容的：`import lerobot` 和各 CLI 照常启动，缺 SDK 的设备只是不
出现在 `--robot.type` / `--teleop.type` 的候选里，构造它时才报错并给出重编提示。

### `third_party/` 依赖

| submodule | 安装出的包 |
|---|---|
| `ARX5_SDK` | `pyarx` |
| `libpyflexiv`（内含嵌套 `flexiv_rdk`） | `flexiv_rt` |
| `XenseVR-PC-Service` | `xensevr_pc_service_sdk` |
| `XGripper` | `xensegripper` |
| `elite-robots-cs-sdk`（C++） | `elite_cs_sdk` 的编译依赖 |
| `elite-robots-cs-sdk-python` | `elite_cs_sdk` |
| `taccap-gripper` | `xense.taccap` |

`xensesdk` **不是** submodule，从 PyPI 装 `xensesdk==2.0.1`（cp312 manylinux
wheel，内含打过补丁的 `libxense_c.so`）。

内网另有一套 GitLab 镜像：URL 在 `.gitmodules.gitlab`，用
`XENSE_GITLAB_HOST=<host> scripts/submodule-remote.sh gitlab` 只改本地 remote，
不动提交进 git 的 `.gitmodules`（host 地址因为仓库公开而不入库）。

## 代码结构

`src/lerobot/` 在上游基础上新增/替换的部分：

- [`robots/`](../methods/lerobot-xense/src/lerobot/robots) ——
  `flexiv_rizon4_rt` / `bi_flexiv_rizon4_rt`、`elite_cs66_rt` / `bi_elite_cs66_rt`、
  `arx5_follower` / `bi_arx5`，每种都是单臂 + 双臂成对。
- [`teleoperators/`](../methods/lerobot-xense/src/lerobot/teleoperators) ——
  `pico4` / `bi_pico4`（VR）、`spacemouse`（支持双设备）、`trlc_leader` / `bi_trlc`、
  `vive_tracker`、`gamepad` / `btgamepad`。
- [`cameras/`](../methods/lerobot-xense/src/lerobot/cameras) ——
  上游的 `opencv` / `realsense` 之外新增 `xense`（触觉相机）与 `zmq`（远程图像流）。
- [`grippers/`](../methods/lerobot-xense/src/lerobot/grippers) ——
  **本 fork 新增的设备族**，与 `cameras/` / `motors/` 平级。
- [`recipes/`](../methods/lerobot-xense/recipes) —— teleop / record 的 YAML 配置。

## 触觉相机的数据形态

[`cameras/xense/`](../methods/lerobot-xense/src/lerobot/cameras/xense) 把 Xense
触觉传感器包成 lerobot Camera。单个传感器一次可读出：3D 力分布 `35×20×3`、
6D 合力/力矩 `(6,)`、深度图 `700×400`、2D marker 切向位移 `35×20×2`、
3D mesh 形变 `35×20×3`。

注意该模块 README 的安装段落还停留在 `xensesdk==1.6.3` + 一堆手工 pip，与根
README 现在的 `xensesdk==2.0.1` 由 `setup_env.sh` 统一安装不一致；以根 README
和 `setup_env.sh` 为准。

## 夹爪抽象（fork 的核心设计之一）

见 [`grippers/README.md`](../methods/lerobot-xense/src/lerobot/grippers/README.md)。
夹爪是独立设备族，机械臂通过一个小契约驱动它，不关心底层是哪种：

| | `serial` | `taccap_follower` |
|---|---|---|
| 硬件 | 平行夹爪，USB 串口（XGripper） | 中心式 TacCap 夹爪，FDCAN 电机 |
| 控制 | 位置 + 力/速度上限 | MIT 阻抗（kp / kd / 前馈力矩） |
| 左右判定 | 板卡 SN 奇偶（奇→左） | 固件烧录的 SN |
| USB hub 上挂 | 腕部相机 + 2 路触觉 | 腕部相机 + 2 路 GSPS |
| SDK | `xensegripper` | `xense.taccap` |

两个 SDK 都是可选编译，`make_gripper_from_config` 只 import 选中的分支，所以缺
SDK 的机器上这个包仍可 import，错误推迟到 `connect()`。

配置是**一个带类型的块**而非一堆平铺 knob，经
[`GripperConfig`](../methods/lerobot-xense/src/lerobot/grippers/configs.py#L36)
（`draccus.ChoiceRegistry`）解码，因此把 `kp:` 写在 `type: serial` 下面或拼错字段
会**在解析期直接报错**，而不是被静默忽略。双臂只写一次，两侧各拿一份副本并盖上
`side`。`auto_discover_cameras: true` 时，腕部与触觉相机在 connect 时从该夹爪的
USB hub 上嗅探出来，recipe 里不需要写它们的 SN。

## recipe 机制

teleop 与 record 都由 `--config_path` 指向的 YAML 驱动，见
[`recipes/README.md`](../methods/lerobot-xense/recipes/README.md)：

```bash
lerobot-teleoperate --config_path=recipes/teleop/bi_elite_cs66_rt/diagonal-07.yaml
lerobot-record     --config_path=recipes/record/bi_flexiv_rizon4_rt/assemble_box.yaml
```

- 目录按 CLI 再按机型分：`recipes/{teleop,record}/<robot_type>/<name>.yaml`。
- **一个 recipe 是自包含的**：既带 bench 硬件（控制器 IP/SN、相机 SN、安装几何、
  每臂 home/start 位姿、`local_ip`），也带这次运行的调参（控制模式、伺服增益、
  夹爪力、dataset 字段）。加一台 bench = 加一个 recipe，不改 Python。
- 优先级：`dataclass 默认 < recipe < CLI --robot.xxx=`。
  （**与 xense-openpi 那边的推理客户端相反**，那边调参 flag 总是覆盖 recipe。）
- 同一台 bench 的 teleop 与 record recipe 里 `robot:` / `teleop:` 块应当逐字相同，
  自包含的代价就是这份重复需要人工保持同步。
- 关节角一律是**度**（J1..J7），这是 `flexiv_rt` 接受的单位。

## record 循环的 RT reset 语义（最容易出错的地方）

`bi_flexiv_rizon4_rt + bi_pico4` 走
[`flexiv_rizon4_rt_record_loop`](../methods/lerobot-xense/src/lerobot/scripts/lerobot_record.py#L575)
（通用路径是同文件 [record_loop:502](../methods/lerobot-xense/src/lerobot/scripts/lerobot_record.py#L502)）。
按下手柄 `A`（`go_start`）时机械臂由 C++ RT 线程接管回起始位姿，**录制不停**，
此时数据集的写入语义会切换：

| 帧 | `send_action` | 数据集写入 |
|---|---|---|
| 正常遥操作 | ✓ | `{obs[t], action[t]}` 直接帧 |
| 触发 reset 那一帧 | 跳过 | **跳过**（`obs[T]` 只留作下一帧的 prev） |
| RT 运动中 | 跳过 | `{obs[t-1], state_20d[t]}` **平移帧** |
| reset 结束后 | ✓ | 回到直接帧 |

平移帧的 action 取自当前观测里与 `robot.action_features` 同名的键（左右 TCP 各
9D + 夹爪各 1D = 20D，图像键自动排除），即记录机器人**实际到达**的位置而非遥操作
下发的指令——与 `bi_arx5_record_loop` 同一套约定。触发帧故意不写盘，否则
`obs[T]` 会重复出现两次。

RT 结束的那一帧会调用一次 `_sync_rt_teleop_to_robot_pose()`，把 Pico4 的
`_start_pos` 参考系重置到机器人当前位姿；少了这一步，reset 后第一次握持会因为
遥操作仍按 reset 前的位姿算增量而让机械臂跳变。

手柄按键与键盘事件是**同级输入**，统一进同一组 `events[]` 判断：右 `A`=go_start、
左 `X`=rerecord、左 `Y`=exit_early、右 `B`=stop_recording。

## 与 xense-openpi 的接口

- **状态/动作**：双臂 20D = 左右各「TCP 9D（xyz + 6D 旋转）+ 夹爪 1D」，由
  [`_proprioception_ft`](../methods/lerobot-xense/src/lerobot/robots/bi_flexiv_rizon4_rt/bi_flexiv_rizon4_rt.py#L323)
  与 [`action_features`](../methods/lerobot-xense/src/lerobot/robots/bi_flexiv_rizon4_rt/bi_flexiv_rizon4_rt.py#L357)
  定义，与 openpi 侧 `BiFlexivInputs` 的 20D 定义一一对应，两边都不做旋转编解码。
  `use_force: true` 会在**观测**里多出每臂 6D 力矩，动作维度不变。
- **相机命名**：录制里的 `head` / `left_wrist` / `right_wrist` 对应模型侧
  `base_0_rgb` / `left_wrist_0_rgb` / `right_wrist_0_rgb`。触觉相机（`*_tactile_*`）
  会被录进数据集，但当前 openpi 的 `bi_flexiv` 训练链路不消费它们。
- **数据集**：LeRobotDataset（parquet + mp4 + json/jsonl），recipe 里
  `repo_id: Xense/<task>`，openpi 的 YAML 配置以同名 `repo_id` 引用。
- **recipe 互通**：openpi 的推理客户端可以直接 `--args.robot-recipe` 指向本仓库
  `recipes/teleop/bi_flexiv_rizon4_rt/*.yaml`。两个仓库各有一份 bench 副本，**不保证
  同步**，换 bench 时两边都要看一眼。

## 当前接入状态与缺口

已完成：fork + submodule 接入（含 8 个嵌套 submodule 递归初始化）、`lab` 注册、
README 角色表、模块索引。

未完成，需要时补：

- 没有 `methods/lerobot-xense/AGENTS.md`（也没有 `CLAUDE.md`）。工作区规则要求改
  方法前先读它。
- 没有 `experiments/lerobot-xense/`，因此没有 runbook、没有采集 run 证据。
- [cmd.md](../cmd.md) 的接入验证块仍是 Pending。
- 从未在本工作区实际安装过：`setup_env.sh` 全流程、7 个 SDK 的编译、udev/setcap
  这些都只有上游文档保证，没有本地验证证据。首次安装应按 univtac 的先例把完整
  trace 存到 `/mnt/data/atticux/vla-post-train/` 下再写 runbook。
