# lerobot-check 概览

## 定位

lerobot-check 是独立的 LeRobot 数据集分析与标注工具仓库（`AtticusZeller/lerobot-check`，公开）。它读取 v3.0 数据集，
维护逐 episode、逐 subtask 的标注表，并从标注表派生帧占比、速度、物体初始位置、轨迹覆盖、补录建议和 subtask prompt
重标。训练和推理仍在 `xense-openpi`，采集仍在 `lerobot-xense`；三者之间通过 LeRobotDataset 和标注表衔接。

## 关键约定

- 标注表是唯一的阶段分界来源，prompt 在 subtask 的 `end` 帧切换；subtask 以松开物体为界。
- 第一期只用本体数据，物体位置取抓取 / 松开时刻的 TCP 位姿，坐标在各臂自己的基座坐标系下。head 相机标定与视觉分割
  属于第二期。
- 标注文件和报告不进公开仓库。
