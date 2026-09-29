# xense-openpi Commands

## RLT 单测（phase two 与机器人端）

用途：改动 `src/openpi/rlt/` 或 `examples/bi_flexiv_rizon4_rt/rlt_mode.py` 后回归。

前提：`methods/xense-openpi/.venv` 已由 `GIT_LFS_SKIP_SMUDGE=1 uv sync` 建好；`methods/tacxense` 已检出（数值对照用例
从这里导入 tacxense）。

```bash
cd methods/xense-openpi
JAX_PLATFORMS=cpu TACXENSE_ROOT=$(realpath ../tacxense) \
  .venv/bin/python -m pytest -q -rs -p no:cacheprovider \
  src/openpi/rlt examples/bi_flexiv_rizon4_rt src/openpi/policies/rlt_policy_test.py \
  --deselect src/openpi/rlt/features_test.py
```

预期：全部通过；`-rs` 里只有 `token_model_test` 找不到 RLinf 参照的 2 个 skip。出现 "TacXense reference not found"
说明 `TACXENSE_ROOT` 没生效，对照用例没有真正运行。`features_test` 跑真实 pi0 前向，本机不跑。
