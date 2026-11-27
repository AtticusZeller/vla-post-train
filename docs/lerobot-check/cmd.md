# lerobot-check 命令

lerobot-check 命令在 `methods/lerobot-check` 下运行。`--repo-id` 与 `--dataset-root` 二选一即可，标注表、task spec 与
`.xense-viewer/` 下其他文件默认按[概览](overview.md)的文件约定读写。下面以 `pack_iphone_box_1119` 为例：

```bash
R=~/.cache/huggingface/lerobot/Xense/pack_iphone_box_1119
ID=Xense/pack_iphone_box_1119
```

## 启动 viewer 并接上 lerobot-check

用途：Subtask、DISTRIBUTION、CALIBRATION、COLLECTION 页面内直接运行 CLI（保存标注后自动重算分布）。

```bash
cd methods/xense-lerobot-viewer
LEROBOT_CHECK_DIR=$PWD/../lerobot-check bun dev
```

预期：浏览器打开 `http://localhost:3000`，进入数据集后各页按钮可直接运行；不设 `LEROBOT_CHECK_DIR` 时按钮只给出可复制命令。

## agent 标注

用途：按分界找帧、出结束帧拼图、校验、重标。完整流程见 lerobot-check 的 `docs/annotate.md`。

```bash
uv run lerobot-check info --repo-id $ID
# 每个分界一个 agent：第一轮共用窗口，第二轮用 episode_index,lo,hi 的窗口文件
uv run lerobot-check window-sheet --repo-id $ID --window-s 8:36 --samples 8 --crop head=90,40,550,360 --name b1_r1 -o /tmp/lerobot-check/window
uv run lerobot-check window-sheet --repo-id $ID --windows /tmp/lerobot-check/b1_windows.csv --samples 8 \
  --cameras head left_wrist right_wrist --crop head=90,40,550,360 --name b1_r2 -o /tmp/lerobot-check/window
# 前 N-1 段的结束帧拼图，给人审阅时每段一张整图
uv run lerobot-check boundary-sheet --repo-id $ID --crop head=90,40,550,360 --per-page 0 --columns 4 -o /tmp/lerobot-check/boundary
uv run lerobot-check validate --repo-id $ID
uv run lerobot-check relabel --repo-id $ID --dst ~/.cache/huggingface/lerobot/Xense/pack_iphone_box_1119_subtask
uv run lerobot-check verify-relabel --repo-id $ID --dst ~/.cache/huggingface/lerobot/Xense/pack_iphone_box_1119_subtask
```

预期：`window-sheet` 每行一条 episode、每格标帧号和秒数；`boundary-sheet` 每条 episode 一格（头部裁剪 + 两个腕部的
`end − 1`），人工复核行带绿色 `H`；`validate` 输出 `OK: <行数> rows covering <n>/<总数> episodes`；`relabel` 的目标目录
必须不存在，`verify-relabel` 最后一行为 `OK`。

## 分布与补采

用途：标注变动后手动重算分布；画好目标多边形后生成补采摆放和测试点（viewer 中的按钮做同样的事）。

```bash
uv run lerobot-check distribution --repo-id $ID
uv run lerobot-check suggest --repo-id $ID -n 10 --csv /tmp/lerobot-check/suggestions.csv
```

预期：分别写出 `.xense-viewer/distribution/` 与 `.xense-viewer/suggestions/` 下的 JSON；有 `head.json` 时位置为工具点。

## 头部相机标定

用途：选待点选帧、追加帧、求解外参（viewer 标定页的"Append 5 frames""换一帧""Run calibrate"按钮做同样的事）。

```bash
uv run lerobot-check calib-frames --repo-id $ID                       # 首次生成，已存在时拒绝覆盖
uv run lerobot-check calib-frames --repo-id $ID --append 5            # 每条臂追加 5 帧
uv run lerobot-check calib-frames --repo-id $ID --append 1 --arms left
uv run lerobot-check calibrate --repo-id $ID
```

预期：`calib-frames` 打印各臂新增帧数，已有条目原样保留；`calibrate` 写 `head.json`，每条臂给出 RMS、内点 RMS、留一误差和离群点。
验收线为每条臂内点 RMS ≤ 5 px、留一误差 ≤ 8 px。

## TCP 重标定转换（仅 `lerobot-check` 分支 `AtticusZeller/tcp-retarget`）

用途：将旧工具参数（如 `xenseflare`）录制的 LeRobot v3.0 数据集按刚体变换转换到新工具参数（如 `taccap-rs00`），写出不覆盖原目录的新副本并全量校验。该命令为低频一次性工具，按用户决定（2026-11-26）保留在 `lerobot-check` 分支 `AtticusZeller/tcp-retarget`（工作树 `~/worktrees/lerobot-check/tcp-retarget`），不合入 `lerobot-check` `main`。

```bash
cd ~/worktrees/lerobot-check/tcp-retarget
OLD=~/.local/share/robot-tool-snapshots/xense-robot-flexiv/xenseflare-2026-11-25T051632.630330Z.json
NEW=~/.local/share/robot-tool-snapshots/xense-robot-flexiv/taccap-rs00-2026-11-27T035244.808662Z.json
uv run lerobot-check retarget-tcp --repo-id $ID \
  --dst ~/.cache/huggingface/lerobot/Xense/pack_iphone_box_1119_taccap_rs00 \
  --old-tool "$OLD" --new-tool "$NEW"
uv run lerobot-check verify-tcp --repo-id $ID \
  --dst ~/.cache/huggingface/lerobot/Xense/pack_iphone_box_1119_taccap_rs00 \
  --old-tool "$OLD" --new-tool "$NEW"
```

预期：`retarget-tcp` 写出新数据集并硬链接视频（目标目录必须不存在）；`verify-tcp` 最后一行为 `OK`，报告正逆变换最大误差。
