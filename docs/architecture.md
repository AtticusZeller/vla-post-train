# 架构说明

## 边界

根仓库是研究编排与证据层。`methods/*` 是独立版本、依赖和发布边界；根脚本不导入方法
业务模块，也不把第三方配置复制成统一训练 API。

```text
experiment YAML
    → method launcher（构造 argv、cwd、环境）
    → method 原生入口
    → /mnt/data 大型产物 + W&B 完整过程
    → run.json / summary.json
    → report.md 标记结果表
```

## 配置边界

根层字段固定为 `schema_version`、`id`、`method`、`repository`、`environment`、
`runtime`、`tracking`。`native` 是方法专属数据；专用 launcher 只解释当前方法所需的
argv、环境变量、local summary 和指标声明。

`command` launcher 明确拒绝 shell 字符串，避免 YAML 内容被 shell 二次解释。

## 运行状态

新 run 先验证 traceability，再创建：

```text
experiments/<method>/runs/<run-id>/{run.json,summary.json}
/mnt/data/atticux/vla-post-train/<method>/<run-id>/{logs,...}
```

进程启动后立即写 PID；结束、Python 异常或 SIGINT/SIGTERM 后补全 finish、exit 与 signal。
`resume` 默认关闭。历史记录不执行，只冻结已有来源并允许 `code_revisions[]`。

## 报告边界

`report.py` 只更新 `<!-- lab:results:begin -->` 与 `<!-- lab:results:end -->` 之间的表格。
当前结论、异常解释、证据边界和后续决策始终由研究者维护。

W&B collector 只解析配置中的完整 run URL，读取 summary 与 system stream；本地退出码或
traceback 能将表面为 finished 的线上 run 判为失败。
