# EXPO-FT Commands

## 启动 RoboTwin 环境端

用途：在 RoboTwin 的环境里起 `run_client`，拨号到 learner（`train_pi_robo.py` 或 `eval_droid_policy.py`）监听的端口，
为它执行环境 RPC。

前提：RoboTwin 环境与资产已装好（见 [robotwin/overview.md](../robotwin/overview.md)）；learner 已在 `<port>` 上监听；
在 `methods/expo-ft` 下运行。服务器上另需 `VK_ICD_FILENAMES=/root/data/atticux/vulkan/nvidia_icd_egl.json`。

```bash
ROBOTWIN_ROOT=<robotwin checkout> PYTHONPATH=$PWD:$PWD/expo_ft/agents/vla/openpi/packages/xense-client/src <robotwin venv>/bin/python -m client.run_client --host <learner host> --port <port> --config-task-path configs/task/robotwin_beat_block_hammer.py
```

预期：日志出现 `Environment robotwin_beat_block_hammer_train_1 created successfully`；每次 reset 先跑一次专家筛种子，
再按该种子摆场景。
