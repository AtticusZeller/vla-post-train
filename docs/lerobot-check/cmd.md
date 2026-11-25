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

用途：数据集信息、某分界的人工样例、标注后校验。完整流程见 lerobot-check 的 `docs/annotate.md`。

```bash
uv run lerobot-check info --repo-id $ID
uv run lerobot-check exemplars --repo-id $ID --boundary flip_lid:close_lid --max-episodes 3 -o /tmp/lerobot-check/exemplars
uv run lerobot-check validate --repo-id $ID
```

预期：`exemplars` 每个样例写一张 PNG，分界帧红框标出；没有人工样例时提示后以 0 退出。`validate` 输出
`OK: <行数> rows covering <n>/<总数> episodes`，有违规时逐条打印并以非零退出。

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
