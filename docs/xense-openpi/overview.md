# xense-openpi 概览
## 定位

xense-openpi 是 Xense 平台的模型侧 OpenPI fork，负责训练配置、模型、norm stats、策略服务和
真机推理客户端。数据采集、机器人驱动与遥操作位于 `lerobot-xense`；两者通过 LeRobotDataset
和 recipe 语义连接。

## 关键接口

配置系统允许共享示例 YAML 与本地私有 YAML，并保留部分无法直接序列化的 Python 配置。
修改配置入口时必须确认训练、统计和服务脚本读取的是同一来源，避免某类 YAML 只对部分入口
可见。

双臂 Flexiv 的模型接口使用左右臂各 9D TCP 表示加 1D 夹爪位置，旋转采用连续 6D 表示。
当前正式 bi_flexiv 数据链路只包含视觉和本体状态；不能因为仓库存在 tactile 模型文件，就声称
该训练链路已经使用触觉输入。

`xense-client` 将机器人控制环与远端推理解耦：后台提前请求 action chunk，本地控制循环继续
消费队列。部署时低延迟机器人网络与推理数据网络应物理隔离，避免推理流量阻塞实时控制。

## RLT（JAX）

RLT 的方法规格见 [rlt-spec.md](rlt-spec.md)。xense-openpi 里的 JAX 实现在 `feature/rlt-jax` 分支：
phase one（token 编解码器、prefix cache、`scripts/rlt/train_token.py`）与 phase two（`src/openpi/rlt/` 的 collector、
learner、replay、在线特征，`scripts/rlt/train_rl.py`，机器人端 `examples/bi_flexiv_rizon4_rt/rlt_mode.py`，serving 用
`src/openpi/policies/rlt_policy.py`）。代码取自 XenseRobotics-AI 的 `feature/rlt-hubo`，逐个 commit 对照规格审查后
cherry-pick，参考代码只作参考，问题在我们的分支上修。

与规格或参考分支的差异：只实现 sliding replay（`replay_stride ≥ 1` 且整除 C），不实现 stride=0 边界 anchor；不接入
参考分支的 actor 平滑惩罚与 BC/Q 权重日程，actor loss 就是 $-Q+\beta\,\mathrm{BC}$；规格文末的研究性选项未迁；RTC 不在
范围内。机器人协议是新的 `openpi-rlt/1`，与 tacxense 的协议不兼容，机器人端与训练服务器要用同一分支。

验证边界：只有 CPU 单测（小维度假模型与假机器人）与 tacxense 的数值对照；pi05 真实前向与 phase one 由参考分支作者
验证，本工作区没有复跑；没有真机运行记录。

## 已知限制

当前 tactile 模型分支只是未接完整训练与采样接口的原型，没有可用配置和测试，因此不是可运行
的触觉 VLA。该方法与 lerobot-xense 共用环境，也是根仓环境隔离规则的例外。

工作区登记的 upstream 与方法 README 曾出现不同仓库归属；在执行 sync 或调整远端前仍需由
项目成员确认权威上游。当前没有根级实验配置、训练/推理记录或真机验收证据。
