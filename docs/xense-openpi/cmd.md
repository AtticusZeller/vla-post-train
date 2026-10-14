# xense-openpi Commands

## RL 单测（共享层、RLT 与机器人端）

用途：改动 `src/openpi/rl/` 或 `examples/bi_flexiv_rizon4_rt/rlt_mode.py` 后回归。

前提：`methods/xense-openpi/.venv` 已由 `GIT_LFS_SKIP_SMUDGE=1 uv sync` 建好；`methods/tacxense` 已检出（数值对照用例
从这里导入 tacxense）。

```bash
cd methods/xense-openpi
JAX_PLATFORMS=cpu TACXENSE_ROOT=$(realpath ../tacxense) \
  .venv/bin/python -m pytest -q -rs -p no:cacheprovider \
  src/openpi/rl examples/bi_flexiv_rizon4_rt \
  --deselect src/openpi/rl/algos/rlt/features_test.py
```

预期：全部通过；`-rs` 里只有 `token_model_test` 找不到 RLinf 参照的 2 个 skip。出现 "TacXense reference not found"
说明 `TACXENSE_ROOT` 没生效，对照用例没有真正运行。`features_test` 跑真实 pi0 前向，本机不跑。


## rlt-jax 选择 actor 训练参考输入

前提：使用已支持 `input_reference` 的 `feature/rlt-jax`。在实验 YAML 的 `rl` 段设置：

```yaml
rl:
  input_reference: corrected # 原方案；proposal 使用原始 VLA reference
```

预期：`corrected` 在人工步使用人工替换后的 reference 作为 actor 训练输入；两种模式的 BC target 相同。
省略该项时使用 `corrected`。对照测试使用不同实验名从相同初始权重开始，不恢复另一方案的训练 checkpoint；
旧 checkpoint 缺少此字段，也会被训练条件检查拒绝。
