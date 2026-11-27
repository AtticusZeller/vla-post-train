# lerobot-check Plan

## `pack_iphone_box_1119` TCP 重标定转换（`xenseflare` → `taccap-rs00`）

本地 `Xense/pack_iphone_box_1119`（及 5 段重标版 `pack_iphone_box_1119_subtask`）录制时使用的是错误 TCP 参数
`xenseflare`（`~/.local/share/robot-tool-snapshots/xense-robot-flexiv/xenseflare-2026-11-25T051632.630330Z.json`），
实际生效的手动标定工具为 `taccap-rs00`
（`~/.local/share/robot-tool-snapshots/xense-robot-flexiv/taccap-rs00-2026-11-27T035244.808662Z.json`）。
通过刚体右乘 $^{O}T_{\text{new}} = {}^{O}T_{\text{old}}\,({}^{F}T_{\text{old}})^{-1}\,{}^{F}T_{\text{new}}$ 将旧数据集中
`observation.state` 与 `action` 的双臂 TCP 转换到 `taccap-rs00` 坐标系，生成不覆盖原缓存的新数据集供后续上传
Hugging Face Hub，并同步 `.xense-viewer/` 侧车（用户确认，2026-11-26）。

### Task: 实现 `retarget-tcp` 与 `verify-tcp` 命令及单测

**Change**

- 在 `methods/lerobot-check` 新建 worktree（分支 `AtticusZeller/tcp-retarget`），新增 `src/lerobot_check/tcp_retarget.py`
  与 CLI 子命令 `retarget-tcp`、`verify-tcp`，支持读取两份 Flexiv 工具快照 JSON 并执行一般 $SE(3)$ 刚体变换
  （$R_{\text{old}}^\top R_{\text{new}} = I$ 时原样保留 `r1..r6`）。
- 只改写新目录中的 `data/*/*.parquet`（保持 Arrow schema/metadata 与非 TCP 列不变），重算 `meta/episodes/*/*.parquet`
  中 `stats/{action,observation.state}/*` 与 `meta/stats.json`，原样复制 `meta/tasks.parquet` 与 `meta/info.json`，
  硬链接 `videos/`，拒绝覆盖已存在目标目录。
- 提供标定侧车 payload 的 TCP 平移辅助函数（供 `frames.json` / `points.json` 复用同一变换）。

**Verification**

1. 单元测试覆盖纯平移、含旋转一般 $SE(3)$、往返可逆性、快照校验报错、防覆盖保护及完整 LeRobot v3.0 转换与校验。
2. 在新 worktree 运行 `uv run pytest`、`uv run ruff check .`、`uv run ruff format --check .`、`uv run ty check src/`。

**Done**

- 全部测试、lint、格式与类型检查通过，合成数据集往返逆变换最大误差 `< 1e-5` m。

### Task: 转换本地 `pack_iphone_box_1119` 与 `pack_iphone_box_1119_subtask` 并全量校验

**Change**

- 分别将 `~/.cache/huggingface/lerobot/Xense/pack_iphone_box_1119` 与 `pack_iphone_box_1119_subtask` 转换到
  `~/.cache/huggingface/lerobot/Xense/pack_iphone_box_1119_taccap_rs00` 与
  `~/.cache/huggingface/lerobot/Xense/pack_iphone_box_1119_taccap_rs00_subtask`（不覆盖原目录）。
- 对两份输出数据集运行 `verify-tcp` 并检查 `LeRobotDataset` 直接加载与视频硬链接。

**Verification**

1. 对两份新数据集全量 8 个 parquet、121 条 episode、274,083 帧运行 `verify-tcp`。
2. 使用转换后的 `points.json` 重跑 `lerobot-check calibrate`，核对 `T_cam_base`、重投影 RMS 与 `tool_offset` 收缩幅度。

**Done**

- 两份数据集 `verify-tcp` 输出 `OK`（逆变换最大位置误差 `< 1e-5` m，非 TCP 列零差异，视频均为硬链接）；重跑标定后左臂
  `tool_offset` 模长 `< 5` mm、右臂 `< 10` mm 且 RMS 与原标定差 `< 0.05` px。

### Task: 同步 `.xense-viewer/` 侧车并更新命令与下游文档

**Change**

- 为 `Xense/pack_iphone_box_1119_taccap_rs00` 同步 `.xense-viewer/` 侧车：复用 `task_spec.yaml`、`intrinsics.json`
  与更新 `repo_id`/`revision` 后的 subtask CSV，生成转换后的 `frames.json`、`points.json` 并运行 `calibrate` 与
  `distribution`。
- 更新 `docs/lerobot-check/cmd.md`（记录 `retarget-tcp` / `verify-tcp` 命令）与 `docs/lerobot-xense/plan.md`
  （注明 `xense-openpi` 必须基于新 TCP 数据集重算 `norm_stats.json`）。

**Verification**

1. 在 `Xense/pack_iphone_box_1119_taccap_rs00` 上运行 `lerobot-check validate`、`lerobot-check calibrate` 与
   `lerobot-check distribution`。
2. 核对 `git status` 与 `git diff`，确认公开仓库中无任何数据集或侧车文件。

**Done**

- `validate` 覆盖 121/121 episode，`calibrate` 与 `distribution` 正常产出侧车 JSON；文档与代码变更仅留在新 worktree。
