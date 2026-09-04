# TacWAM Plan

## 待与上游协作者确认

- [ ] `packages/xense-client/pyproject.toml` 声明 `requires-python = ">=3.7"`，但源码含
      `Dict[...] | None`（3.10+ 语法且该文件未启用 postponed annotations）。TacWAM 的 3.12 环境
      不暴露该问题，但按元数据在 3.7–3.9 独立安装会在导入阶段失败。这是 xense-openpi 上游的
      问题，本仓库为保持逐字同步不就地修改，需向该仓库反馈
