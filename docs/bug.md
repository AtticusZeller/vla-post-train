# Bug Journal

> 开发过程中的硬核经验：触发情况、解决方案、原因解释。

<!-- 新 bug 追加到本行下方 -->

## 2026-07-30：根 `uv run` 的 PATH 抢占目标 Conda Python

- **触发：** `./lab experiment run` 自身由根 `.venv` 的 `uv run` 启动，再通过
  `conda run -n dsrl_pi0 python ...` 进入 FlowDAgger。
- **现象：** 第一次 MetaWorld-12 smoke 实际执行根 Python 3.12，导入阶段报
  `ModuleNotFoundError: No module named 'jax'`；尚未进入 GPU。
- **处理：** launcher 根据 `conda` 可执行文件与配置的环境名解析目标
  `<conda-root>/envs/<name>/bin`，将它显式放到子进程 PATH 首位。诊断确认实际 Python
  变为 `dsrl_pi0/bin/python`、JAX 0.8.0；后续 smoke 正常完成。
- **原因：** 当前环境中 `conda run` 不会可靠覆盖祖先进程显式传入且以根
  `.venv/bin` 开头的 PATH；不能仅凭命令包含 `conda run` 推断目标 Python 已生效。

## 2026-07-30：评估视频误用了 steering 的低清策略帧

- **触发：** `perform_control_eval` 将 `obs_to_img()` 的输出直接加入视频；该函数会按
  `resize_image=128` 缩放给 steering 网络使用，且沿用策略的 `corner3` 视角。
- **现象：** MP4 只有 128×128，画面偏俯视，无法清楚判断机械臂与对象交互。
- **处理：** 在 MetaWorld adapter 中新增共享同一 model/data 的独立 MuJoCo renderer；
  策略仍用 `corner3`，视频改用 `corner`、640×480、30 FPS，并只渲染配置要求保存的
  episode。用户已确认新视角与清晰度。
- **原因：** 模型输入和人类证据的优化目标不同；复用预处理帧会把模型分辨率和相机约束
  错误地施加到实验视频上。

## 2026-07-29：`lab experiment summarize` 因 wandb SDK API 变更而失败

- **触发：** `scripts/monitor.py::collect_wandb` 用 `run.scan_history(stream="system")`
  拉取 GPU system metrics，并用 `dict(run.summary)` 展开 run summary；当前锁定的
  `wandb==0.28.1` 已把 `stream` 参数移到 `history()`，`scan_history()` 不再接受该
  关键字，且 `run.summary` 顶层 `dict()` 转换后仍会保留嵌套字段（如 `_wandb`）为
  不可 JSON 序列化的 `SummarySubDict`。
- **现象：** `./lab experiment summarize <run_id>` 先报
  `TypeError: Run.scan_history() got an unexpected keyword argument 'stream'`；
  用 `run.history(stream="system", pandas=False)` 替换后又报
  `TypeError: Object of type SummarySubDict is not JSON serializable`。
- **处理：** 把 GPU system stream 调用改为 `run.history(stream="system",
  pandas=False)`；summary 展开改用 `getattr(run.summary, "_json_dict",
  run.summary)` 后再 `dict()`，同时兼容测试用的 plain-dict fake 和真实
  `HTTPSummary` 对象。`tests/test_monitor.py` 的 `FakeRun` 同步把
  `scan_history` 换成签名匹配的 `history`。
- **原因：** wandb 官方 Public API（`/wandb/wandb` 源码 `apis/public/runs.py`）
  在 `scan_history()` 里去掉了 `stream` 关键字，只有 `history()` 保留；`run.summary`
  是懒加载的 `HTTPSummary`，其 `_json_dict` 才是纯 dict 快照，直接 `dict()`
  顶层转换不会递归展开内部 `SummarySubDict`。

## 2026-07-28：Ray 从根 `uv run` 继承 working dir 后遗漏源码目录

- **触发：** 根 `lab` 通过 `uv run` 启动 RLinf 子进程，子进程再调用
  `ray.init()`；当前 Ray 默认启用 `RAY_ENABLE_UV_RUN_RUNTIME_ENV`。
- **现象：** Ray 自动将方法仓作为 working dir 打包，worker 从
  `/tmp/ray/.../working_dir_files/` 导入代码；LIBERO EnvWorker 报
  `ModuleNotFoundError: No module named 'rlinf.envs.venv'`，即使该目录在提交后的
  方法仓中存在。
- **处理：** 单节点共享源码实验在根配置中设置
  `RAY_ENABLE_UV_RUN_RUNTIME_ENV=0`，同时继续显式固定方法
  `UV_PROJECT_ENVIRONMENT`、`UV_NO_SYNC=1` 和方法入口；短 Ray worker probe
  已确认从提交后的 `methods/rlinf/rlinf/envs/venv/` 成功导入模块。
- **原因：** Ray 的 uv runtime-env hook 根据祖先 `uv run` 自动复制 driver
  环境；它与本项目“根 uv 环境只做编排、方法使用独立环境”的边界冲突，生成的
  working-dir 包并不等价于方法仓源码。

## 2026-07-27：Ray 工作目录导致 `uv` 误建第二套 RLinf 环境

- **触发：** 正式入口把 Ray `working_dir` 切换到根仓库的 RLinf 子模块，但只激活了
  `/root/RLinf/.venv`，未声明该路径也是 `uv` 的项目环境。
- **现象：** 第一次 worker 初始化在子模块下创建 `.venv` 并准备重新下载
  PyTorch/CUDA；改绑外部环境后，自动 sync 又改写了该环境并造成
  `huggingface-hub`/Transformers 版本冲突。两次均未进入 GPU 训练。
- **处理：** 安全中断运行并保留失败 run 记录；设置 `RLINF_VENV`、
  `UV_PROJECT_ENVIRONMENT=/root/RLinf/.venv` 和 `UV_NO_SYNC=1`，确认正式启动只解析
  现有 Python，不再自动同步或改写依赖。
- **原因：** 激活 `VIRTUAL_ENV` 不会改变 `uv` 默认按当前项目选择 `.venv` 的规则；
  Ray 改变工作目录后，两个环境路径不再一致。

## 2026-07-27：桌面工作区缺失只读挂载点导致 `apply_patch` 无法启动

- **触发：** 补丁工具在 bwrap 初始化阶段尝试挂载声明存在、实际缺失的 `.git`、
  `.agents` 和 `.codex` 目录。
- **现象：** `Can't mkdir ...: Read-only file system`，补丁尚未读取目标项目。
- **处理：** 只创建缺失的空 mount-point 目录后重试；未修改任何现有 Git 数据。
- **原因：** 桌面 workspace permission profile 与磁盘目录状态不一致，不是项目代码故障。

## 2026-07-27：`/mnt/data` 当前以只读方式挂载

- **触发：** `findmnt -T /mnt/data` 返回 `ro`。
- **影响：** 历史证据可读取，但新 `experiment run` 无法创建外部产物目录。
- **处理：** `lab doctor` 显示 WARN；运行入口在创建 metadata 前检查可写性并报错。
- **恢复标准：** DSW 将 OSS 重新以 `rw` 挂载后再启动任何新训练。

## 2026-07-27：`/mnt/data` 已恢复可写

- **验证：** `findmnt -T /mnt/data` 显示 `rw`，并通过 `test -w /mnt/data`。
- **影响：** 新实验可以创建 `/mnt/data/atticux/vla-post-train/<method>/<run-id>/` 产物目录。
