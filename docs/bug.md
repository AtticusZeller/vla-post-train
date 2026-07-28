# Bug Journal

> 开发过程中的硬核经验：触发情况、解决方案、原因解释。

<!-- 新 bug 追加到本行下方 -->

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
