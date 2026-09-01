# Cosmos 模块说明

## 定位

`methods/cosmos` 是 NVIDIA Cosmos-Framework 官方仓库的用户 fork submodule，当前作为
`framework` 接入。它提供 Cosmos 3 的训练、数据适配、action policy 与推理服务框架；
根仓库只管理其版本、编排和证据。

## 来源与版本

- fork：`https://github.com/AtticusZeller/cosmos-framework.git`
- upstream：`https://github.com/NVIDIA/cosmos-framework.git`
- 分支：`xense`
- 当前 pin：`0e034bc98ffa3c3dfa19f037871f3a8bbc1c4d05`
- 官方默认分支：`main`
- 嵌套 submodule：无
- 根目录许可证：OpenMDW License Agreement 1.1；分发或复用前需按仓库许可证核验

## 接入边界

本次只完成 fork、`xense` 分支、版本固定、submodule 和适配边界记录。不迁移
OpenPI-Xense 文件，不修改 Cosmos 训练或推理代码，不创建 `experiments/cosmos/`、
实验配置、launcher 或 runbook。

## 已确认的 Xense 边界

- **迁移文件清单：空。** `xense-client`、Flexiv 真机环境、broker、recipe、recorder
  和 examples 继续留在 `methods/xense-openpi`。
- OpenPI-Xense 继续负责真机运行、WebSocket 客户端、action chunk broker 和 Flexiv
  控制；Cosmos-Framework 后续只负责训练与模型推理服务。
- 两仓库通过 OpenPI WebSocket 协议连接，不在 Cosmos 内嵌入或复制
  `xense-client`。

## 后续适配清单（本次不实施）

### Cosmos 训练侧

1. 新增 Flexiv 双臂 LeRobot dataset adapter，将原始数据统一为 20D EE-pose：
   `[left_xyz(3), left_rot6d(6), left_gripper(1), right_xyz(3), right_rot6d(6), right_gripper(1)]`。
2. 补充 dataset factory/export 与 normalization stats。
3. 新增 Cosmos3-Nano Flexiv 微调 recipe 和 TOML；训练前确认绝对/相对姿态、rotation
   6D、夹爪定义、帧率和 action chunk 长度。
4. 先核验目标 Nano checkpoint 是否真正包含可复用的 ManipArena 20D domain action
   head；若新增 Flexiv domain ID，则不得声称直接继承该 20D 先验。

### Cosmos 推理服务侧

1. 增加一个薄 Xense policy-service adapter，复用 Cosmos 现有 OpenPI
   `WebsocketPolicyServer`。
2. 把 Xense observation 的 `state` / `images` / `prompt` 映射为 Cosmos sample，并映射
   `head` / `left_wrist` / `right_wrist` 三路相机。
3. 保证服务端的 20D 归一化、姿态变换和 action chunk 语义与训练完全一致。
4. 将 Cosmos 当前的 `{"action": ...}` 响应适配为 Flexiv 客户端消费的
   `{"actions": ...}`，不修改 `xense-client`。

### 仅作为改写依据的 OpenPI-Xense 代码

- `src/openpi/policies/bi_flexiv_policy.py`：20D 动作顺序与变换规则。
- `examples/bi_flexiv_rizon4_rt/env.py`：真机 observation/action contract。
- `examples/bi_flexiv_rizon4_rt/main.py`：WebSocket client、broker 和 environment 连接。
- `packages/xense-client/src/xense_client/websocket_client_policy.py`：传输协议。
- `packages/xense-client/src/xense_client/action_chunk_broker.py` 与
  `rtc_action_chunk_broker.py`：action chunk 消费语义。

## 证据边界

上述内容只是已确认的后续改写范围，不代表已实现、已训练或已完成真机验证。Cosmos 的
上游能力描述也不等同于本工作区的训练、仿真或真机成功率证据。未来记录结果时需保留具体
checkpoint、数据、硬件、seed、评测协议和本地退出状态。
