# Development Plan

> VLA 后训练研究仓库实施计划与当前状态。

## TacWAM 统一训练 / 推理配置接口（进行中）

* **目标：**为 `methods/tacwam` 设计一套风格统一、只包含实际所需字段的训练与推理
  配置接口，并用它驱动 Cosmos3-Edge 的训练和策略服务。
* **当前阶段：OpenPI-Xense 配置调查。**先拆清其训练命名配置、数据 / 模型 / 权重 /
  优化器配置、norm stats、checkpoint 加载、策略服务参数、真机 recipe 与运行时 CLI 的
  边界，产出摘要、阅读顺序和文件清单。
* **规范阶段：**在用户逐文件阅读和问答后，整理 TacWAM 配置规范文档；明确稳定字段、
  Cosmos 原生透传字段、训练 / 推理共享语义、覆盖优先级、校验规则和显式非目标，并由
  用户确认后再进入实现。
* **实现阶段（尚未授权）：**按确认后的规范做最小改动接入 Cosmos3-Edge；不整体搬运
  OpenPI 配置系统，不复制 `xense-client` 、Flexiv 环境、broker、recipe 或 recorder，
  不为尚未证明有用的配置项预留接口。
* **必须先回答的问题：**训练与推理是否引用同一个具名配置；dataset / action layout /
  normalization / horizon 如何保持一致；哪些参数属于任务语义、硬件 bench、单次运行调参
  或 Cosmos 原生执行层；checkpoint 如何携带或反查推理所需配置。
* **阶段一完成标准：**分支已建立；OpenPI-Xense 两条配置链路有代码依据的总结；给出按
  阅读顺序排列的最小文件清单；所有未核验项明确标记，且未修改 TacWAM / Cosmos 实现。
