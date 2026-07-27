# Bug Journal

> 开发过程中的硬核经验：触发情况、解决方案、原因解释。

<!-- 新 bug 追加到本行下方 -->

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
