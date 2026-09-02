# TacWAM 模块说明

## 定位

`methods/tacwam` 是触觉感知机器人操作的世界动作模型 method。当前代码首先实现了
Cosmos3-Edge BiFlexiv action-policy 的模型边界，并把 `cosmos-framework` 保持为外部
editable dependency，不复制框架源码。

## 来源与版本

- 协作仓库：`https://github.com/Hubo1231/TacWAM.git`
- 分支：`main`
- 当前 pin：`d42ff465a673b151482d6efb6d1cc4ab74b5faf6`
- GitHub 状态：private、非 fork
- 嵌套 submodule：无
- 许可证：仓库当前没有 LICENSE 文件或 GitHub license metadata；未经项目成员确认，
  不对外推断其授权范围

用户是该仓库的联合开发者，因此本工作区直接使用原仓库作为 `origin`，不创建个人 fork；
为兼容根仓 method registry，`upstream` 也指向同一 URL。

## 当前实现范围

- `src/tacwam/models/action_spec.py` 定义 TacXense/LeRobot 与 Cosmos 双臂 20D action
  layout 的双向转换。
- `src/tacwam/models/config.py` 固定外部 horizon 50、内部 horizon 52/53-frame WAM、
  64D padded action stream 和 BiFlexiv domain 配置。
- `src/tacwam/models/cosmos3_edge_policy.py` 包装 Cosmos backbone 的 training step 与
  action sampling，并向外返回 `[B, 50, 20]`。
- `src/tacwam/models/domain.py` 负责进程内 domain 注册及可选的 domain-12 action-head
  权重初始化。

README 明确说明数据加载、normalization stats、训练编排和 serving 尚未实现；在对应代码
和测试出现前，不把技术计划或模型边界描述成完整训练/推理链路。

## 接入边界

本次只完成直接 submodule 接入、method Agent 指南和根仓登记。不创建
`experiments/tacwam/`、配置、launcher、runbook 或结果报告，也不修改 TacWAM 模型实现。

## 验证边界

轻量环境以 NumPy 运行 action/config/domain contract 测试，结果为 6 passed；缺少 PyTorch
时策略 wrapper 测试按测试代码约定跳过 1 项。完整策略验证需要另行准备 Cosmos/PyTorch
环境，因此当前接入不构成训练、checkpoint 加载、推理服务或真机验证证据。
