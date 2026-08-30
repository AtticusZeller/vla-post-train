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
触觉传感器包成 lerobot Camera。以本仓库使用的 Xense Python SDK API 为准，单个
传感器可提供以下模态；同一次 `selectSensorInfo()` 可请求多项，以保证它们来自同一帧。

| 模态 | SDK `OutputType` | SDK 原生数据 | 当前 LeRobot 封装 | 需要推理 |
|---|---|---|---|---|
| 校正视觉图像 | `Rectify` | `(H,W,3)`，BGR | `RECTIFY`；读出时转为 RGB 并交换前两维 | 否 |
| 无接触参考差分图 | `Difference` | `(H,W,3)`，BGR | `DIFFERENCE`；读出时转为 RGB 并交换前两维 | 否，但需要参考帧 |
| 深度图 | `Depth` | `(H,W)`，单位 mm | `DEPTH`；读出时交换前两维 | 是 |
| 2D marker 切向位移 | `Marker2D` | `(rows,cols,2)` | `MARKER_2D` | 是 |
| 稠密 3D 力分布 | `Force` | `(35,20,3)` | `FORCE` | 是 |
| 法向力分量 | `ForceNorm` | `(35,20,3)` | `FORCE_NORM` | 是 |
| 六维合力/力矩 | `ForceResultant` | `(6,)`，即 `Fx,Fy,Fz,Tx,Ty,Tz` | `FORCE_RESULTANT` | 是 |
| 当前 3D 表面网格 | `Mesh3D` | `(35,20,3)` | `MESH_3D` | 是 |
| 初始 3D 表面网格 | `Mesh3DInit` | `(35,20,3)` | `MESH_3D_INIT` | 是 |
| 3D 网格形变向量 | `Mesh3DFlow` | `(35,20,3)` | `MESH_3D_FLOW` | 是 |
| 传感器时间戳 | `TimeStamp` | 标量，单位 s | **尚未封装**为 `XenseOutputType` | 否 |

这里的“需要推理”表示需要加载 Xense SDK 的模型推理引擎；LeRobot 只请求并整理 SDK
输出，不在本仓库内实现图像到力、深度或网格的转换算法。`Rectify` / `Difference`
可以设置 `disable_infer=true` 快速启动，其余当前已封装模态不能关闭推理。

尺寸边界要以实际设备配置和运行时数组为准：默认 `rectify_size=(400,700)` 经本封装
交换前两维后记录为 `(400,700,3)`；marker 网格尺寸可能随传感器型号或标定包变化，
不要把 `rows×cols` 硬编码为固定值。

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

## TacCap 手持数采（UMI 式）落进数据集的形态

> **出处与适用范围**：本节全部内容来自分支 **`origin/dev/taccap-gripper`**
> （HEAD `b2154ab2`），**不在 `main` 上**——`main` 的工作树里没有下列任何文件，
> 因此本节路径一律写成 `分支路径:行号`，不做可点击链接（点了会 404）。
> 用 `git show origin/dev/taccap-gripper:<path>` 查看。
> 该分支与 main 是分叉关系：commit `872c7b86` 把所有机械臂 submodule 都删了，
> 只保留手持数采链路。

设备是 TacCap 手持夹爪（其 README 自称 *multimodal tactile data-collection
gripper*），机型名 `taccap_gripper` / `bi_taccap_gripper`，位姿来自装在夹爪顶部的
Pico4 Ultra 独立追踪器。

### 硬件 feature 如何变成数据集列

数据集列不是 `tcp.x` 这种硬件键，而是被
`src/lerobot/datasets/utils.py:615` 的 `hw_to_dataset_features()` 压缩过一层：

- 所有 `float` 型硬件键 **合并成一个 float32 一维数组**——`prefix=action` 出
  `action`，`prefix=observation` 出 `observation.state`，原始键名按**插入顺序**
  存进该列的 `names`。
- 所有 `tuple` 型（相机）各自独立成列 `observation.images.<camera_name>`，
  `names` 恒为 `["height","width","channels"]`。
- 再叠加 `src/lerobot/datasets/utils.py:73` 的 `DEFAULT_FEATURES`：`timestamp`
  float32 `(1,)`，`frame_index` / `episode_index` / `index` / `task_index`
  int64 `(1,)`。

所以**读数据集时想知道 state 每一维是什么，必须去看该列的 `names`**；维度顺序
完全由 robot 类里 features 的构建顺序决定。

### 单臂 `taccap_gripper` — 默认配置下的数据集列

默认值出自 `src/lerobot/robots/taccap_gripper/config_taccap_gripper.py`：
`enable_tracker=True`、`enable_gripper=True`、**`enable_imu=False`**、
`enable_wrist_camera=True`、`expected_tactiles_per_side=2`、
`tactile_output_types=["rectify"]`、腕部相机 640×480@30。

| 数据集列 | dtype | shape | names（即每一维的含义） |
|---|---|---|---|
| `action` | float32 | `(10,)` | `tcp.x,tcp.y,tcp.z,tcp.r1..tcp.r6,gripper.pos` |
| `observation.state` | float32 | `(10,)` | 同上（与 action 逐字相同） |
| `observation.images.tactile_left` | video | `(400,700,3)` | 左指视触觉 |
| `observation.images.tactile_right` | video | `(400,700,3)` | 右指视触觉 |
| `observation.images.wrist_cam` | video | `(480,640,3)` | 腕部 UVC |
| `timestamp` | float32 | `(1,)` | |
| `frame_index` `episode_index` `index` `task_index` | int64 | `(1,)` | |

- `tcp.*` 单位是米；`r1..r6` 是旋转矩阵的**前两列**（与 `vive_tracker` 同约定）。
- `gripper.pos` ∈ [0,1]，0=闭 1=开，来自编码器归一化。
- 定义在 `src/lerobot/robots/taccap_gripper/taccap_gripper.py:318`
  （`observation_features`）与同文件 `:340`（`action_features`）。
  **`action` 里没有任何相机**，图像只存在于 observation。

开启 `--robot.enable_imu=true` 后 `observation.state` 变成 `(19,)`，多出的 9 维
顺序是**按轴外层循环**，不是按传感器分组：

```
accel.x, gyro.x, mag.x,  accel.y, gyro.y, mag.y,  accel.z, gyro.z, mag.z
```

单位依次为 m/s²、rad/s、µT。`action` 维度**不变**，仍是 10——IMU 只进观测。

### 双臂 `bi_taccap_gripper`

所有键加 `left_` / `right_` 前缀，且**按侧分组**（left 的全部字段在前，然后
right），见 `src/lerobot/robots/bi_taccap_gripper/bi_taccap_gripper.py:195`。
默认（IMU 关）：

| 数据集列 | dtype | shape | names |
|---|---|---|---|
| `action` | float32 | `(20,)` | `left_tcp.x..left_tcp.r6, left_gripper.pos, right_tcp.x..right_tcp.r6, right_gripper.pos` |
| `observation.state` | float32 | `(20,)` | 同上 |
| `observation.images.{left,right}_tactile_{left,right}` | video | `(400,700,3)` | 4 路触觉 |
| `observation.images.{left,right}_wrist` | video | `(480,640,3)` | 2 路腕部 |

两个坑：

- **触觉键里的 `left`/`right` 指手指，不是手臂**，所以 `left_tactile_right`
  （左臂夹爪的右指）是合法且常见的键名。指别由 GSPS 序列号末位奇偶决定
  （单左双右），传感器与夹爪的配对靠 **USB hub** 而非序列号本身。
- **腕部相机键名两边不一致**：单臂是 `wrist_cam`，双臂是 `{side}_wrist`
  （没有 `_cam`）。写下游读取代码时不能想当然。

### 触觉图像 shape 的推导（别硬编码）

`src/lerobot/cameras/xense/configuration_xense.py:160` 起：`rectify_size` 默认
`(400,700)`，注释标称语义是 `(width,height)`，但赋值时是

```python
self.height = self.rectify_size[0]   # 400
self.width  = self.rectify_size[1]   # 700
```

于是数据集里的 shape 是 **`(400,700,3)`** 的横向图。名实不符，所以上游 README
反复强调 width/height 自动推导、不要写死。若把 `output_types` 换成
force / marker / mesh 一类非图像输出，同一段逻辑改走固定的 `height=35,width=20`
（对应 SDK 的 `(35,20,3)` 力分布），数据集列的 shape 随之变成 `(35,20,3)`。

**单臂与双臂的触觉默认输出不同**：单臂仍是 `["rectify"]`，双臂在 commit
`9ec78c23` 被改成 `["difference"]`（映射到 SDK 的 AugDifference，对比度增强的
背景差分）。两者都是免推理的纯矫正产物，shape 相同但**像素含义不同**，混用两批
数据前要确认这一项。

### 采集语义：self-driven + 平移帧

与本仓库其它机型最大的不同——**没有 teleoperator**：

- `src/lerobot/scripts/lerobot_record.py:194` 的
  `SELF_DRIVEN_RECORD_ROBOTS = {"taccap_gripper", "bi_taccap_gripper"}` 使
  `RecordConfig.__post_init__` 放行 `teleop=None`，命令行上没有任何
  `--teleop.*`。
- 设备是**被动**的：`send_action()` 是 no-op，电机从不使能，操作者用手掰夹爪
  走演示。观测和示教动作都由 robot 自己产出。
- 走专用的 `self_driven_record_loop`（同文件 `:285`），采用**平移帧**配对：
  `{obs[t-1], pose[t]}`，动作**领先观测一步**，是真正的「移动到下一处」目标，
  而非同帧配对那种退化的「动作＝当前状态」。代价是每个 episode 丢掉第一帧
  （首帧没有前驱）。

这也解释了 UMI 原始数据「只有观测没有动作」的问题在这里是怎么解决的：动作不来自
另一个指令源，而是取下一帧的位姿。

典型采集命令（无任何 `--teleop.*`，设备按序列号规则自动发现）：

```bash
lerobot-record \
    --robot.type=taccap_gripper --robot.id=right --robot.side=right \
    --dataset.repo_id=<org>/<dataset> \
    --dataset.num_episodes=1 --dataset.episode_time_s=10 \
    --dataset.single_task='Pick up the object'
```

### 坐标系

默认落在**世界系**：X 前、Y 左、Z 上、重力对齐，原点是 **Unity VR Client 启动
瞬间的头显位置**。两条硬约束写在
`src/lerobot/robots/taccap_gripper/README.md`：

- **不要在 episode 之间重启 Unity client**，否则后续录制全部换了原点。
- 手性约定 **TBD**：Pico 文档称右手系，SDK 的 `rerun_dual_with_tracker.py` 注释
  称左手系，尚未在真机核实。

UMI 式初始位姿对齐（把记录位姿 rebase 到部署机器人基座系，训练前无需后处理）
是**预留功能，默认关闭**：`enable_init_pose_alignment=False`，README 写明原因是
还没在真机部署硬件上验证过。关闭时数据留在原始 xrt 世界系，下游需自行换系。

### 与 main 的关系

`main` 上只有 `TaccapFollower`（从臂夹爪驱动），整套多模态采样在那条路径上
**只有 `position` 一维**经 `Gripper.get_gripper_position()` 变成 `gripper.pos`，
IMU、力矩、编码器速度全部丢弃。手持数采要用上表的格式，必须走
`origin/dev/taccap-gripper` 分支。两个分支尚未合并。

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
