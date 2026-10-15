# RoboTwin 概览

RoboTwin 2.0 是基于 SAPIEN 的双臂操作 benchmark，默认机器人是 Aloha-AgileX（两臂各 6 个关节加 1 个夹爪，共 14 维
关节动作；头部相机和左右腕部相机）。本工作区只把它当仿真环境用：EXPO-FT 的环境端直接 import `envs/` 下的任务类。

- **任务接口：** `setup_demo(seed, is_test)` 按种子摆场景；`get_obs` 返回三路相机与关节状态；`take_action` 执行一步
  14 维关节目标（内部用 TOPP 插值并推进物理）；`check_success` 判定成功；`step_lim` 来自
  `env_cfg/task_config/_eval_step_limit.yml`（`beat_block_hammer` 为 400）。
- **官方评测协议：** 种子从 `100000 × (1 + seed)` 起；每个种子先让专家 `play_once`，专家规划失败或未成功的种子跳过；
  指令按 `seen` / `unseen` 从 `description/` 生成。
- **依赖：** 独立的 Python 3.10 环境（NumPy 1.x ABI）、带 Vulkan 的 GPU、CuRobo（专家规划器在 reset 时就会建，
  不可缺）；pytorch3d 只用于点云，可不装。资产从 HuggingFace `TianxingChen/RoboTwin2.0` 单独下载。
- **数据：** 官方采集数据以图像比特存相机帧，有两种字节格式，必须用 `decode_image_bit` 解码；自写解码器会在其中
  一种上把红蓝通道弄反。用现成的 LeRobot 转换结果时要核对颜色与仿真渲染一致。
